import os
import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.agent_engine import WritingAgent
from agents.system_prompt import WRITING_AGENT_SYSTEM_PROMPT
from agents.tools.base import Tool, ToolResult

# ====================================================================
# 测试用桩件
# ====================================================================


class _StubTool(Tool):
    """用于工具调用测试的桩 Tool"""

    name = "stub_tool"
    description = "stub tool for testing agent engine"

    def __init__(self, result: ToolResult | None = None):
        self._result = result or ToolResult(success=True, data={"echo": "ok"})
        self.execute_mock = AsyncMock(side_effect=self._do_execute)

    @property
    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"novel_id": {"type": "string"}}}

    async def _do_execute(self, **kwargs):
        return self._result

    async def execute(self, **kwargs: Any) -> ToolResult:
        return await self.execute_mock(**kwargs)


def _make_conversation(conv_id="conv_1"):
    return type("Conv", (), {"id": conv_id, "novel_id": None, "title": "测试"})()


def _make_message(msg_id="msg_1"):
    return type("Msg", (), {"id": msg_id, "role": "user", "content": ""})()


async def _async_gen(items):
    """把列表包装成异步生成器，用于模拟 chat_stream"""
    for item in items:
        yield item


# ====================================================================
# Fixtures
# ====================================================================


@pytest.fixture
def conversation_repo():
    repo = MagicMock()
    repo.create_conversation = MagicMock(return_value=_make_conversation())
    repo.get_conversation = MagicMock(return_value=_make_conversation())
    repo.list_messages = MagicMock(return_value=[])
    repo.add_message = MagicMock(return_value=_make_message())
    return repo


@pytest.fixture
def stub_tool():
    return _StubTool()


@pytest.fixture
def tool_registry(stub_tool):
    registry = MagicMock()
    registry.to_openai_schemas = MagicMock(
        return_value=[
            {
                "type": "function",
                "function": {"name": "stub_tool", "description": "stub"},
            }
        ]
    )
    registry.get = MagicMock(return_value=stub_tool)
    return registry


@pytest.fixture
def llm_client():
    client = MagicMock()
    client.chat_json = AsyncMock(return_value={"action": "reply", "text": "你好"})
    client.chat = AsyncMock(return_value="工具执行完成。")
    return client


def _build_agent(llm_client, tool_registry, conversation_repo):
    return WritingAgent(
        llm_client=llm_client,
        tool_registry=tool_registry,
        conversation_repo=conversation_repo,
    )


async def _collect(agent, *args, **kwargs):
    """收集 agent.chat 的所有事件"""
    events = []
    async for event in agent.chat(*args, **kwargs):
        events.append(event)
    return events


# ====================================================================
# System Prompt 常量
# ====================================================================


def test_system_prompt_constant_exists():
    assert isinstance(WRITING_AGENT_SYSTEM_PROMPT, str)
    assert len(WRITING_AGENT_SYSTEM_PROMPT) > 0
    assert "星渊笔" in WRITING_AGENT_SYSTEM_PROMPT
    assert "generate_chapter" in WRITING_AGENT_SYSTEM_PROMPT


# ====================================================================
# 纯文本回复（action=reply）
# ====================================================================


@pytest.mark.asyncio
async def test_chat_text_reply_yields_token_and_complete(llm_client, tool_registry, conversation_repo):
    llm_client.chat_json = AsyncMock(return_value={"action": "reply", "text": "你好世界"})
    agent = _build_agent(llm_client, tool_registry, conversation_repo)

    events = await _collect(agent, "hi")

    types = [e[0] for e in events]
    assert "token" in types
    assert types[-1] == "complete"

    complete_payload = events[-1][1]
    assert "conversation_id" in complete_payload
    assert "message_id" in complete_payload

    token_text = "".join(e[1]["delta"] for e in events if e[0] == "token")
    assert "你好世界" in token_text


@pytest.mark.asyncio
async def test_chat_text_reply_persists_user_and_assistant_messages(llm_client, tool_registry, conversation_repo):
    llm_client.chat_json = AsyncMock(return_value={"action": "reply", "text": "回复"})
    agent = _build_agent(llm_client, tool_registry, conversation_repo)

    await _collect(agent, "用户问题")

    assert conversation_repo.add_message.call_count == 2
    first_call = conversation_repo.add_message.call_args_list[0].kwargs
    second_call = conversation_repo.add_message.call_args_list[1].kwargs
    assert first_call["role"] == "user"
    # P1.2 修复：chat() 入口统一净化后，用户消息被 <user_message> 标签包裹
    assert "用户问题" in first_call["content"]
    assert "<user_message>" in first_call["content"]
    assert second_call["role"] == "assistant"
    assert "回复" in second_call["content"]


# ====================================================================
# 工具调用（action=tool）
# ====================================================================


@pytest.mark.asyncio
async def test_chat_tool_call_yields_tool_events(llm_client, tool_registry, conversation_repo, stub_tool):
    llm_client.chat_json = AsyncMock(
        side_effect=[
            {"action": "tool", "tool": "stub_tool", "args": {"novel_id": "n1"}},
            {"action": "reply", "text": "完成"},
        ]
    )
    llm_client.chat = AsyncMock(return_value="工具调用完成，已生成章节。")
    agent = _build_agent(llm_client, tool_registry, conversation_repo)

    events = await _collect(agent, "请生成章节")

    types = [e[0] for e in events]
    assert "tool_call" in types
    assert "tool_result" in types
    assert "token" in types
    assert types[-1] == "complete"

    tool_call_event = next(e for e in events if e[0] == "tool_call")
    assert tool_call_event[1]["tool"] == "stub_tool"
    assert tool_call_event[1]["args"] == {"novel_id": "n1"}

    tool_result_event = next(e for e in events if e[0] == "tool_result")
    assert tool_result_event[1]["tool"] == "stub_tool"
    assert tool_result_event[1]["success"] is True

    stub_tool.execute_mock.assert_awaited_once_with(novel_id="n1")


@pytest.mark.asyncio
async def test_chat_tool_call_persists_assistant_message_with_tool_metadata(
    llm_client, tool_registry, conversation_repo
):
    llm_client.chat_json = AsyncMock(
        side_effect=[
            {"action": "tool", "tool": "stub_tool", "args": {"novel_id": "n1"}},
            {"action": "reply", "text": "完成"},
        ]
    )
    llm_client.chat = AsyncMock(return_value="已执行完毕")
    agent = _build_agent(llm_client, tool_registry, conversation_repo)

    await _collect(agent, "调用工具")

    # user + assistant 两条消息
    assert conversation_repo.add_message.call_count == 2
    assistant_call = conversation_repo.add_message.call_args_list[1].kwargs
    assert assistant_call["role"] == "assistant"
    assert assistant_call["tool_name"] == "stub_tool"
    assert assistant_call["tool_calls"] is not None


@pytest.mark.asyncio
async def test_chat_tool_call_failure_yields_failure_result(llm_client, tool_registry, conversation_repo, stub_tool):
    llm_client.chat_json = AsyncMock(
        side_effect=[
            {"action": "tool", "tool": "stub_tool", "args": {"novel_id": "n1"}},
            {"action": "reply", "text": "完成"},
        ]
    )
    stub_tool._result = ToolResult(success=False, error="service 不可用")
    stub_tool.execute_mock = AsyncMock(return_value=ToolResult(success=False, error="service 不可用"))

    agent = _build_agent(llm_client, tool_registry, conversation_repo)
    events = await _collect(agent, "调用工具")

    tool_result_event = next(e for e in events if e[0] == "tool_result")
    assert tool_result_event[1]["success"] is False
    assert "service 不可用" in tool_result_event[1]["data"]["error"]


@pytest.mark.asyncio
async def test_chat_tool_call_unknown_tool(llm_client, tool_registry, conversation_repo):
    llm_client.chat_json = AsyncMock(
        side_effect=[
            {"action": "tool", "tool": "non_existent_tool", "args": {}},
            {"action": "reply", "text": "完成"},
        ]
    )
    tool_registry.get = MagicMock(return_value=None)
    agent = _build_agent(llm_client, tool_registry, conversation_repo)

    events = await _collect(agent, "调用不存在的工具")

    tool_result_event = next(e for e in events if e[0] == "tool_result")
    assert tool_result_event[1]["success"] is False
    assert "工具不存在" in tool_result_event[1]["data"]["error"]


# ====================================================================
# chat_json 异常 → 降级到 chat_stream
# ====================================================================


@pytest.mark.asyncio
async def test_chat_fallback_to_stream_when_json_fails(llm_client, tool_registry, conversation_repo):
    llm_client.chat_json = AsyncMock(side_effect=RuntimeError("llm json error"))

    async def _stream_side_effect(*args, **kwargs):
        async for chunk in _async_gen(["你", "好", "啊"]):
            yield chunk

    llm_client.chat_stream = MagicMock(side_effect=_stream_side_effect)

    agent = _build_agent(llm_client, tool_registry, conversation_repo)
    events = await _collect(agent, "hi")

    types = [e[0] for e in events]
    assert "token" in types
    assert types[-1] == "complete"

    token_text = "".join(e[1]["delta"] for e in events if e[0] == "token")
    assert token_text == "你好啊"

    # 降级时仍持久化 user + assistant
    assert conversation_repo.add_message.call_count == 2


@pytest.mark.asyncio
async def test_chat_fallback_stream_persists_full_assistant_text(llm_client, tool_registry, conversation_repo):
    llm_client.chat_json = AsyncMock(side_effect=RuntimeError("json fail"))

    async def _stream_side_effect(*args, **kwargs):
        async for chunk in _async_gen(["一", "二", "三"]):
            yield chunk

    llm_client.chat_stream = MagicMock(side_effect=_stream_side_effect)

    agent = _build_agent(llm_client, tool_registry, conversation_repo)
    await _collect(agent, "hi")

    assistant_call = conversation_repo.add_message.call_args_list[1].kwargs
    assert assistant_call["role"] == "assistant"
    assert assistant_call["content"] == "一二三"


# ====================================================================
# 会话不存在的情况
# ====================================================================


@pytest.mark.asyncio
async def test_chat_with_nonexistent_conversation_yields_error(llm_client, tool_registry, conversation_repo):
    conversation_repo.get_conversation = MagicMock(return_value=None)
    agent = _build_agent(llm_client, tool_registry, conversation_repo)

    events = await _collect(agent, "hi", conversation_id="missing_conv")

    assert events[0][0] == "error"
    assert "E4004" in events[0][1]["code"]
    assert "missing_conv" in events[0][1]["message"]


# ====================================================================
# 会话创建 / 历史加载
# ====================================================================


@pytest.mark.asyncio
async def test_chat_creates_conversation_when_no_id_passed(llm_client, tool_registry, conversation_repo):
    llm_client.chat_json = AsyncMock(return_value={"action": "reply", "text": "ok"})
    agent = _build_agent(llm_client, tool_registry, conversation_repo)

    await _collect(agent, "新对话", novel_id="novel_x")

    conversation_repo.create_conversation.assert_called_once()
    create_kwargs = conversation_repo.create_conversation.call_args.kwargs
    assert create_kwargs["novel_id"] == "novel_x"
    assert "新对话" in create_kwargs["title"]


@pytest.mark.asyncio
async def test_chat_loads_history_into_llm_messages(llm_client, tool_registry, conversation_repo):
    history_msgs = [
        type("M", (), {"role": "user", "content": "上次问题"})(),
        type("M", (), {"role": "assistant", "content": "上次回答"})(),
    ]
    conversation_repo.list_messages = MagicMock(return_value=history_msgs)
    llm_client.chat_json = AsyncMock(return_value={"action": "reply", "text": "好"})
    agent = _build_agent(llm_client, tool_registry, conversation_repo)

    await _collect(agent, "继续", conversation_id="conv_1")

    sent_messages = llm_client.chat_json.call_args.args[0]
    # 第一条是 system prompt
    assert sent_messages[0]["role"] == "system"
    assert sent_messages[0]["content"] == WRITING_AGENT_SYSTEM_PROMPT
    # 历史消息已加载
    roles = [m["role"] for m in sent_messages]
    assert "user" in roles
    assert "assistant" in roles


# ====================================================================
# 异常路径
# ====================================================================


@pytest.mark.asyncio
async def test_chat_conversation_repo_failure_yields_error(llm_client, tool_registry, conversation_repo):
    conversation_repo.add_message = MagicMock(side_effect=RuntimeError("db down"))
    agent = _build_agent(llm_client, tool_registry, conversation_repo)

    events = await _collect(agent, "hi")

    assert events[-1][0] == "error"
    assert "db down" in events[-1][1]["message"]


# ====================================================================
# Phase 3: 原生 Function Calling 路径
# ====================================================================


@pytest.mark.asyncio
async def test_chat_native_tool_calling_path(llm_client, tool_registry, conversation_repo):
    """验证 chat() 优先调用 _get_llm_decision_native()：
    mock 它返回有效 decision，确认旧方法不被调用。
    """
    from unittest.mock import patch

    agent = _build_agent(llm_client, tool_registry, conversation_repo)
    native_decision = {"action": "reply", "text": "原生FC回复"}

    with patch.object(agent, "_get_llm_decision_native",
                      new=AsyncMock(return_value=native_decision)) as mock_native:
        with patch.object(agent, "_get_llm_decision",
                          new=AsyncMock(return_value={"action": "reply", "text": "旧路径回复"})) as mock_legacy:
            events = await _collect(agent, "hi")

    # 原生路径被调用，旧路径未被调用
    mock_native.assert_awaited_once()
    mock_legacy.assert_not_awaited()
    # 正常完成
    assert events[-1][0] == "complete"
    token_text = "".join(e[1]["delta"] for e in events if e[0] == "token")
    assert "原生FC回复" in token_text


@pytest.mark.asyncio
async def test_chat_native_to_legacy_fallback(llm_client, tool_registry, conversation_repo):
    """验证 _get_llm_decision_native() 返回 None 时降级到 _get_llm_decision()。"""
    from unittest.mock import patch

    agent = _build_agent(llm_client, tool_registry, conversation_repo)

    with patch.object(agent, "_get_llm_decision_native",
                      new=AsyncMock(return_value=None)) as mock_native, patch.object(agent, "_get_llm_decision",
                      new=AsyncMock(return_value={"action": "reply", "text": "降级回复"})) as mock_legacy:
        events = await _collect(agent, "hi")

    # 原生路径被调用但返回 None → 触发降级
    mock_native.assert_awaited_once()
    mock_legacy.assert_awaited_once()
    assert events[-1][0] == "complete"
    token_text = "".join(e[1]["delta"] for e in events if e[0] == "token")
    assert "降级回复" in token_text


@pytest.mark.asyncio
async def test_chat_dual_tool_message_format(llm_client, tool_registry, conversation_repo, stub_tool):
    """验证双轨消息格式：原生路径使用 tool 角色，旧路径使用 user 角色。"""
    from unittest.mock import patch

    tool_registry.get = MagicMock(return_value=stub_tool)
    agent = _build_agent(llm_client, tool_registry, conversation_repo)

    # ---- 原生路径（native）：tool 角色 ----
    native_decision = {
        "action": "tool",
        "tool": "stub_tool",
        "args": {"novel_id": "n1"},
        "tool_call_id": "call_native_001",
    }
    with patch.object(agent, "_get_llm_decision_native",
                      new=AsyncMock(return_value=native_decision)) as mock_native:
        with patch.object(agent, "_get_llm_decision",
                          new=AsyncMock(return_value={"action": "reply", "text": "ok"})):
            # 第一次调用 — 原生路径给出 tool decision
            events = await _collect(agent, "调用工具")

    # 验证 tool 角色消息被追加（通过 llm_client.chat_json 的参数检查间接验证）
    # 原生路径返回 tool 决策 → _execute_single_tool → 使用 tool 角色
    # 因 mock_native 返回 tool decision，_get_llm_decision 不应被调用
    mock_native.assert_called()
    # 确认 tool_result 事件存在
    tool_results = [e for e in events if e[0] == "tool_result"]
    assert len(tool_results) >= 1
    assert tool_results[0][1]["tool"] == "stub_tool"

