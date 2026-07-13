import os
import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.agent_engine import WritingAgent
from agents.tools.base import Tool, ToolResult

# ====================================================================
# 测试用桩件（复用自 test_agent_engine.py 的模式）
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
# 测试用例：工具调用深度限制
# ====================================================================


@pytest.mark.asyncio
async def test_tool_call_within_limit_completes(
    llm_client, tool_registry, conversation_repo, stub_tool
):
    """LLM 连续 2 次返回 action=tool，验证正常执行并完成"""
    llm_client.chat_json = AsyncMock(
        side_effect=[
            {"action": "tool", "tool": "stub_tool", "args": {"novel_id": "n1"}},
            {"action": "tool", "tool": "stub_tool", "args": {"novel_id": "n2"}},
            {"action": "reply", "text": "完成"},
        ]
    )
    llm_client.chat = AsyncMock(return_value="工具执行完成。")
    agent = _build_agent(llm_client, tool_registry, conversation_repo)

    events = await _collect(agent, "请连续调用工具")

    types = [e[0] for e in events]

    # 应该有 2 次 tool_call 和 2 次 tool_result
    tool_call_count = types.count("tool_call")
    tool_result_count = types.count("tool_result")
    assert tool_call_count == 2, f"期望 2 次 tool_call，实际 {tool_call_count}"
    assert tool_result_count == 2, f"期望 2 次 tool_result，实际 {tool_result_count}"

    # 应该有 token 事件
    assert "token" in types

    # 最后应该是 complete 事件
    assert types[-1] == "complete"
    complete_payload = events[-1][1]
    assert "conversation_id" in complete_payload
    assert "message_id" in complete_payload

    # 不应该有 error 事件
    assert "error" not in types

    # stub_tool 应该被执行了 2 次
    assert stub_tool.execute_mock.call_count == 2


@pytest.mark.asyncio
async def test_tool_call_exactly_five_completes(
    llm_client, tool_registry, conversation_repo, stub_tool
):
    """LLM 连续 5 次返回 action=tool，验证正常完成（不触发限制）"""
    llm_client.chat_json = AsyncMock(
        side_effect=[
            {"action": "tool", "tool": "stub_tool", "args": {"novel_id": "n1"}},
            {"action": "tool", "tool": "stub_tool", "args": {"novel_id": "n2"}},
            {"action": "tool", "tool": "stub_tool", "args": {"novel_id": "n3"}},
            {"action": "tool", "tool": "stub_tool", "args": {"novel_id": "n4"}},
            {"action": "tool", "tool": "stub_tool", "args": {"novel_id": "n5"}},
            {"action": "reply", "text": "完成"},
        ]
    )
    llm_client.chat = AsyncMock(return_value="工具执行完成。")
    agent = _build_agent(llm_client, tool_registry, conversation_repo)

    events = await _collect(agent, "请连续调用5次工具")

    types = [e[0] for e in events]

    tool_call_count = types.count("tool_call")
    tool_result_count = types.count("tool_result")
    assert tool_call_count == 5, f"期望 5 次 tool_call，实际 {tool_call_count}"
    assert tool_result_count == 5, f"期望 5 次 tool_result，实际 {tool_result_count}"

    # 不应该有 error 事件
    assert "error" not in types

    # 最后应该是 complete 事件
    assert types[-1] == "complete"

    # stub_tool 应该被执行了 5 次
    assert stub_tool.execute_mock.call_count == 5


@pytest.mark.asyncio
async def test_tool_call_exceeds_limit_yields_error(
    llm_client, tool_registry, conversation_repo, stub_tool
):
    """LLM 连续 6 次返回 action=tool，验证第 6 次时 yield error, code=E4005"""
    llm_client.chat_json = AsyncMock(
        side_effect=[
            {"action": "tool", "tool": "stub_tool", "args": {"novel_id": "n1"}},
            {"action": "tool", "tool": "stub_tool", "args": {"novel_id": "n2"}},
            {"action": "tool", "tool": "stub_tool", "args": {"novel_id": "n3"}},
            {"action": "tool", "tool": "stub_tool", "args": {"novel_id": "n4"}},
            {"action": "tool", "tool": "stub_tool", "args": {"novel_id": "n5"}},
            {"action": "tool", "tool": "stub_tool", "args": {"novel_id": "n6"}},
        ]
    )
    llm_client.chat = AsyncMock(return_value="工具执行完成。")
    agent = _build_agent(llm_client, tool_registry, conversation_repo)

    events = await _collect(agent, "请连续调用6次工具")

    types = [e[0] for e in events]

    # 前 5 次正常执行
    tool_call_count = types.count("tool_call")
    tool_result_count = types.count("tool_result")
    assert tool_call_count == 5, f"期望 5 次 tool_call（第6次被拦截），实际 {tool_call_count}"
    assert tool_result_count == 5, f"期望 5 次 tool_result，实际 {tool_result_count}"

    # 应该有 error 事件，code=E4005
    assert "error" in types
    error_event = next(e for e in events if e[0] == "error")
    assert error_event[1]["code"] == "E4005"
    assert "5" in error_event[1]["message"]

    # 仍然应该有 complete 事件（持久化后）
    assert "complete" in types

    # stub_tool 应该被执行了 5 次（第6次被拦截）
    assert stub_tool.execute_mock.call_count == 5
