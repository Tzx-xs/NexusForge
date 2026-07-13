"""LLMClient.chat_with_tools 与 ToolCall/ToolCallResult 数据类测试。"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from infrastructure.ai.llm_client import LLMClient, ToolCall, ToolCallResult

# ====================================================================
# Helpers
# ====================================================================

def _make_tool_call(*, id: str = "call_abc", name: str = "test_tool",
                     args: str = '{}') -> dict:
    """构建 OpenAI 兼容的 tool_call dict。"""
    return {
        "id": id,
        "type": "function",
        "function": {"name": name, "arguments": args},
    }


# ====================================================================
# Fixtures
# ====================================================================

@pytest.fixture
def mock_provider():
    provider = MagicMock()
    provider.chat = AsyncMock(return_value="普通文本回复")
    return provider


@pytest.fixture
def llm_client(mock_provider):
    client = LLMClient(mock_provider)
    # chat_with_tools 引用了 self.model / self.temperature / self.max_tokens
    # 但这些字段未在 __init__ 中定义，为测试手动设置
    client.model = "gpt-4"
    client.temperature = 0.7
    client.max_tokens = 4096
    return client


# ====================================================================
# ToolCall 数据类
# ====================================================================

class TestToolCall:
    """ToolCall 数据类序列化测试。"""

    def test_defaults(self):
        tc = ToolCall()
        assert tc.id == ""
        assert tc.type == "function"
        assert tc.function_name == ""
        assert tc.arguments == {}

    def test_with_values(self):
        tc = ToolCall(
            id="call_abc123",
            type="function",
            function_name="generate_chapter",
            arguments={"novel_id": "n1"},
        )
        assert tc.id == "call_abc123"
        assert tc.function_name == "generate_chapter"
        assert tc.arguments["novel_id"] == "n1"

    def test_with_dict_arguments(self):
        tc = ToolCall(
            id="call_xyz",
            function_name="query_bible",
            arguments={"novel_id": "n1", "setting_type": "world"},
        )
        assert tc.arguments["setting_type"] == "world"
        assert len(tc.arguments) == 2


# ====================================================================
# ToolCallResult 数据类
# ====================================================================

class TestToolCallResult:
    """ToolCallResult 数据类正确创建。"""

    def test_defaults(self):
        r = ToolCallResult()
        assert r.content is None
        assert r.tool_calls == []
        assert r.finish_reason == "stop"

    def test_with_content_only(self):
        r = ToolCallResult(content="你好世界")
        assert r.content == "你好世界"
        assert r.tool_calls == []
        assert r.finish_reason == "stop"

    def test_with_tool_calls(self):
        tc = ToolCall(id="call_1", function_name="tool_a", arguments={"x": 1})
        r = ToolCallResult(content="好的", tool_calls=[tc], finish_reason="tool_calls")
        assert r.content == "好的"
        assert len(r.tool_calls) == 1
        assert r.tool_calls[0].function_name == "tool_a"
        assert r.tool_calls[0].id == "call_1"
        assert r.finish_reason == "tool_calls"


# ====================================================================
# chat_with_tools — 无 tools 参数
# ====================================================================

@pytest.mark.asyncio
async def test_chat_with_tools_no_tools(llm_client, mock_provider):
    """无 tools 参数时不改变现有行为，返回纯文本 ToolCallResult。"""
    mock_provider.chat = AsyncMock(return_value="纯文本回复")
    result = await llm_client.chat_with_tools(
        messages=[{"role": "user", "content": "你好"}],
        tools=None,
    )
    assert result is not None
    assert result.content == "纯文本回复"
    assert result.tool_calls == []
    assert result.finish_reason == "stop"
    # 验证 provider.chat 被调用但不含 tools
    mock_provider.chat.assert_awaited_once()
    call_kwargs = mock_provider.chat.call_args.kwargs
    assert call_kwargs["tools"] is None


# ====================================================================
# chat_with_tools — 单工具调用
# ====================================================================

@pytest.mark.asyncio
async def test_chat_with_tools_success_single(llm_client, mock_provider):
    """单工具调用成功：验证返回 ToolCallResult 含一个 tool_call。"""
    mock_provider.chat = AsyncMock(return_value={
        "content": None,
        "tool_calls": [
            _make_tool_call(id="call_abc123", name="generate_chapter",
                            args='{"novel_id": "n1"}'),
        ],
        "finish_reason": "tool_calls",
    })
    result = await llm_client.chat_with_tools(
        messages=[{"role": "user", "content": "生成章节"}],
        tools=[{"type": "function", "function": {"name": "generate_chapter"}}],
    )
    assert result is not None
    assert len(result.tool_calls) == 1
    tc = result.tool_calls[0]
    assert tc.id == "call_abc123"
    assert tc.function_name == "generate_chapter"
    assert tc.arguments == {"novel_id": "n1"}
    assert result.finish_reason == "tool_calls"
    assert result.content is None


@pytest.mark.asyncio
async def test_chat_with_tools_success_with_text_and_tool(llm_client, mock_provider):
    """单工具调用时 content 和 tool_calls 同时存在。"""
    mock_provider.chat = AsyncMock(return_value={
        "content": "我将为您查询角色信息",
        "tool_calls": [
            _make_tool_call(id="call_456", name="query_characters",
                            args='{"novel_id": "n1"}'),
        ],
        "finish_reason": "tool_calls",
    })
    result = await llm_client.chat_with_tools(
        messages=[{"role": "user", "content": "查角色"}],
        tools=[{"type": "function", "function": {"name": "query_characters"}}],
    )
    assert result is not None
    assert result.content == "我将为您查询角色信息"
    assert len(result.tool_calls) == 1


# ====================================================================
# chat_with_tools — 多工具并行调用
# ====================================================================

@pytest.mark.asyncio
async def test_chat_with_tools_success_parallel(llm_client, mock_provider):
    """多工具调用成功：验证返回 ToolCallResult 含多个 tool_calls。"""
    mock_provider.chat = AsyncMock(return_value={
        "content": None,
        "tool_calls": [
            _make_tool_call(id="call_1", name="query_characters",
                            args='{"novel_id": "n1"}'),
            _make_tool_call(id="call_2", name="query_bible",
                            args='{"novel_id": "n1", "setting_type": "world"}'),
        ],
        "finish_reason": "tool_calls",
    })
    result = await llm_client.chat_with_tools(
        messages=[{"role": "user", "content": "查角色和设定"}],
        tools=[
            {"type": "function", "function": {"name": "query_characters"}},
            {"type": "function", "function": {"name": "query_bible"}},
        ],
    )
    assert result is not None
    assert len(result.tool_calls) == 2
    assert result.tool_calls[0].function_name == "query_characters"
    assert result.tool_calls[0].id == "call_1"
    assert result.tool_calls[1].function_name == "query_bible"
    assert result.tool_calls[1].id == "call_2"
    assert result.finish_reason == "tool_calls"


# ====================================================================
# chat_with_tools — 异常处理
# ====================================================================

@pytest.mark.asyncio
async def test_chat_with_tools_provider_exception_returns_none(llm_client, mock_provider):
    """Provider 抛出异常时返回 None。"""
    mock_provider.chat = AsyncMock(side_effect=RuntimeError("provider timeout"))
    result = await llm_client.chat_with_tools(
        messages=[{"role": "user", "content": "hi"}],
        tools=[{"type": "function", "function": {"name": "test"}}],
    )
    assert result is None
    mock_provider.chat.assert_awaited_once()


@pytest.mark.asyncio
async def test_chat_with_tools_invalid_json_arguments(llm_client, mock_provider):
    """tool_calls 的 arguments 为无效 JSON 时兜底到 {"_raw": raw_str}。"""
    mock_provider.chat = AsyncMock(return_value={
        "content": None,
        "tool_calls": [
            _make_tool_call(id="call_bad", name="test_tool",
                            args="not valid json at all!!"),
        ],
        "finish_reason": "tool_calls",
    })
    result = await llm_client.chat_with_tools(
        messages=[{"role": "user", "content": "hi"}],
        tools=[{"type": "function", "function": {"name": "test_tool"}}],
    )
    assert result is not None
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].arguments["_raw"] == "not valid json at all!!"


@pytest.mark.asyncio
async def test_chat_with_tools_empty_tool_calls_list(llm_client, mock_provider):
    """tool_calls 为空列表时视为纯文本回复。"""
    mock_provider.chat = AsyncMock(return_value={
        "content": "没有需要调用的工具",
        "tool_calls": [],
        "finish_reason": "stop",
    })
    result = await llm_client.chat_with_tools(
        messages=[{"role": "user", "content": "hi"}],
        tools=[{"type": "function", "function": {"name": "test"}}],
    )
    assert result is not None
    assert result.content == "没有需要调用的工具"
    assert result.tool_calls == []
    assert result.finish_reason == "stop"
