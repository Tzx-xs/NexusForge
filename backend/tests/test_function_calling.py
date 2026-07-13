"""WritingAgent._get_llm_decision_native() 单元测试。

测试原生 Function Calling 路径的决策逻辑以及降级到旧 _get_llm_decision() 的行为。
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.agent_engine import WritingAgent
from infrastructure.ai.llm_client import ToolCall, ToolCallResult

# ====================================================================
# 桩件 / 辅助函数
# ====================================================================

def _make_tool_call(id: str, name: str, args: dict) -> ToolCall:
    return ToolCall(id=id, function_name=name, arguments=args)


def _make_tool_call_result(*, content: str | None = None,
                           tool_calls: list | None = None,
                           finish_reason: str = "stop") -> ToolCallResult:
    return ToolCallResult(
        content=content,
        tool_calls=tool_calls or [],
        finish_reason=finish_reason,
    )


# ====================================================================
# Fixtures
# ====================================================================

@pytest.fixture
def mock_provider():
    provider = MagicMock()
    provider.chat = AsyncMock(return_value="ok")
    return provider


@pytest.fixture
def llm_client(mock_provider):
    from infrastructure.ai.llm_client import LLMClient
    client = LLMClient(mock_provider)
    client.model = "gpt-4"
    client.temperature = 0.7
    client.max_tokens = 4096
    return client


@pytest.fixture
def conversation_repo():
    repo = MagicMock()
    repo.create_conversation = MagicMock(
        return_value=type("Conv", (), {"id": "conv_1"})()
    )
    repo.get_conversation = MagicMock(
        return_value=type("Conv", (), {"id": "conv_1"})()
    )
    repo.list_messages = MagicMock(return_value=[])
    repo.add_message = MagicMock(
        return_value=type("Msg", (), {"id": "msg_1"})()
    )
    return repo


@pytest.fixture
def tool_registry():
    registry = MagicMock()
    registry.to_openai_schemas = MagicMock(return_value=[
        {"type": "function", "function": {"name": "test_tool", "description": "test"}},
    ])
    registry.get = MagicMock(return_value=None)
    return registry


@pytest.fixture
def agent(llm_client, tool_registry, conversation_repo):
    return WritingAgent(
        llm_client=llm_client,
        tool_registry=tool_registry,
        conversation_repo=conversation_repo,
    )


# ====================================================================
# _get_llm_decision_native — 单工具
# ====================================================================

@pytest.mark.asyncio
async def test_get_llm_decision_native_single_tool(agent, llm_client):
    """单工具决策：验证返回 dict 含 action='tool' 和 tool_call_id。"""
    llm_client.chat_with_tools = AsyncMock(return_value=_make_tool_call_result(
        tool_calls=[_make_tool_call("call_abc", "test_tool", {"x": 1})],
        finish_reason="tool_calls",
    ))

    messages = [{"role": "user", "content": "调用工具"}]
    tools_schema = [{"type": "function", "function": {"name": "test_tool"}}]
    decision = await agent._get_llm_decision_native(messages, tools_schema)

    assert decision is not None
    assert decision["action"] == "tool"
    assert decision["tool"] == "test_tool"
    assert decision["args"] == {"x": 1}
    assert decision["tool_call_id"] == "call_abc"


@pytest.mark.asyncio
async def test_get_llm_decision_native_single_tool_with_content(agent, llm_client):
    """单工具决策时 content 非空也被正确保留。"""
    llm_client.chat_with_tools = AsyncMock(return_value=_make_tool_call_result(
        content="我将为您调用工具",
        tool_calls=[_make_tool_call("call_1", "query_bible", {"novel_id": "n1"})],
        finish_reason="tool_calls",
    ))
    messages = [{"role": "user", "content": "查设定"}]
    decision = await agent._get_llm_decision_native(messages, [])
    assert decision is not None
    assert decision["action"] == "tool"
    assert decision["tool"] == "query_bible"


# ====================================================================
# _get_llm_decision_native — 多工具
# ====================================================================

@pytest.mark.asyncio
async def test_get_llm_decision_native_multi_tool(agent, llm_client):
    """多工具决策：验证返回 dict 含 action='tools'。"""
    llm_client.chat_with_tools = AsyncMock(return_value=_make_tool_call_result(
        tool_calls=[
            _make_tool_call("call_1", "query_characters", {"novel_id": "n1"}),
            _make_tool_call("call_2", "query_bible", {"novel_id": "n1"}),
        ],
        finish_reason="tool_calls",
    ))
    messages = [{"role": "user", "content": "查角色和设定"}]
    decision = await agent._get_llm_decision_native(messages, [])

    assert decision is not None
    assert decision["action"] == "tools"
    tools = decision["tools"]
    assert isinstance(tools, list)
    assert len(tools) == 2
    assert tools[0]["tool"] == "query_characters"
    assert tools[0]["tool_call_id"] == "call_1"
    assert tools[1]["tool"] == "query_bible"
    assert tools[1]["tool_call_id"] == "call_2"


# ====================================================================
# _get_llm_decision_native — 无工具 / 回复
# ====================================================================

@pytest.mark.asyncio
async def test_get_llm_decision_native_no_tool(agent, llm_client):
    """无工具决策：验证返回 action='reply'。"""
    llm_client.chat_with_tools = AsyncMock(return_value=_make_tool_call_result(
        content="好的，已理解您的需求。",
        finish_reason="stop",
    ))
    messages = [{"role": "user", "content": "你好"}]
    decision = await agent._get_llm_decision_native(messages, [])

    assert decision is not None
    assert decision["action"] == "reply"
    assert decision["text"] == "好的，已理解您的需求。"


# ====================================================================
# _get_llm_decision_native — 降级路径
# ====================================================================

@pytest.mark.asyncio
async def test_get_llm_decision_native_fallback_on_none(agent, llm_client):
    """chat_with_tools 返回 None 时触发降级：返回 None。"""
    llm_client.chat_with_tools = AsyncMock(return_value=None)
    decision = await agent._get_llm_decision_native([], [])
    assert decision is None


@pytest.mark.asyncio
async def test_get_llm_decision_native_fallback_on_exception(agent, llm_client):
    """chat_with_tools 抛出异常时触发降级：返回 None。"""
    llm_client.chat_with_tools = AsyncMock(side_effect=RuntimeError("FC failed"))
    decision = await agent._get_llm_decision_native([], [])
    assert decision is None


# ====================================================================
# _get_llm_decision_native — 消息格式
# ====================================================================

@pytest.mark.asyncio
async def test_tool_result_message_format_native(agent, llm_client, tool_registry, conversation_repo):
    """验证原生路径使用 tool 角色而非 user 角色。

    通过 mock _get_llm_decision_native 直接模拟返回 decision，
    然后验证 _execute_single_tool 中 llm_messages 追加格式。
    """
    from agents.tools.base import Tool, ToolResult

    # 注册一个真实的桩工具
    stub_tool = MagicMock(spec=Tool)
    stub_tool.name = "test_tool"
    stub_tool.requires_confirmation = False
    stub_tool.validate_args = MagicMock(return_value=(True, ""))
    stub_tool.execute = AsyncMock(return_value=ToolResult(success=True, data={"echo": "ok"}))
    tool_registry.get = MagicMock(return_value=stub_tool)

    llm_messages = [{"role": "system", "content": "test"}]
    decision = {
        "action": "tool",
        "tool": "test_tool",
        "args": {"x": 1},
        "tool_call_id": "call_native_001",
    }
    state = {"tool_call_count": 0, "assistant_text": "", "last_tool_name": None, "last_tool_args": None}

    async for _ in agent._execute_single_tool(decision, llm_messages, plan=None, state=state):
        pass

    # 验证追加的消息使用 tool 角色
    assert len(llm_messages) == 2  # system + tool result
    appended = llm_messages[1]
    assert appended["role"] == "tool"
    assert appended["tool_call_id"] == "call_native_001"
    assert "result" in appended["content"]
