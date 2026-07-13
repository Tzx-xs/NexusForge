import asyncio
import os
import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.agent_engine import WritingAgent
from agents.tools.base import Tool, ToolResult

# ====================================================================
# 测试用桩件
# ====================================================================


class _StubIndependentToolA(Tool):
    """无依赖的工具 A"""

    name = "tool_a"
    description = "independent tool A"
    depends_on: list[str] = []

    def __init__(self, result: ToolResult | None = None):
        self._result = result or ToolResult(success=True, data={"tool": "a", "echo": "ok"})
        self.execute_mock = AsyncMock(side_effect=self._do_execute)
        self._executed = False

    @property
    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"input": {"type": "string"}}}

    async def _do_execute(self, **kwargs):
        self._executed = True
        return self._result

    async def execute(self, **kwargs: Any) -> ToolResult:
        return await self.execute_mock(**kwargs)


class _StubIndependentToolB(Tool):
    """无依赖的工具 B"""

    name = "tool_b"
    description = "independent tool B"
    depends_on: list[str] = []

    def __init__(self, result: ToolResult | None = None):
        self._result = result or ToolResult(success=True, data={"tool": "b", "echo": "ok"})
        self.execute_mock = AsyncMock(side_effect=self._do_execute)
        self._executed = False

    @property
    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"input": {"type": "string"}}}

    async def _do_execute(self, **kwargs):
        self._executed = True
        return self._result

    async def execute(self, **kwargs: Any) -> ToolResult:
        return await self.execute_mock(**kwargs)


class _StubDependentToolC(Tool):
    """依赖 tool_a 的工具 C"""

    name = "tool_c"
    description = "dependent tool C, depends on tool_a"
    depends_on = ["tool_a"]

    def __init__(self, result: ToolResult | None = None):
        self._result = result or ToolResult(success=True, data={"tool": "c", "echo": "ok"})
        self.execute_mock = AsyncMock(side_effect=self._do_execute)
        self._executed = False

    @property
    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"input": {"type": "string"}}}

    async def _do_execute(self, **kwargs):
        self._executed = True
        return self._result

    async def execute(self, **kwargs: Any) -> ToolResult:
        return await self.execute_mock(**kwargs)


class _StubDependentToolD(Tool):
    """依赖 tool_a 和 tool_b 的工具 D"""

    name = "tool_d"
    description = "dependent tool D, depends on tool_a and tool_b"
    depends_on = ["tool_a", "tool_b"]

    def __init__(self, result: ToolResult | None = None):
        self._result = result or ToolResult(success=True, data={"tool": "d", "echo": "ok"})
        self.execute_mock = AsyncMock(side_effect=self._do_execute)
        self._executed = False

    @property
    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {"input": {"type": "string"}}}

    async def _do_execute(self, **kwargs):
        self._executed = True
        return self._result

    async def execute(self, **kwargs: Any) -> ToolResult:
        return await self.execute_mock(**kwargs)


def _make_conversation(conv_id="conv_1"):
    return type("Conv", (), {"id": conv_id, "novel_id": None, "title": "测试"})()


def _make_message(msg_id="msg_1"):
    return type("Msg", (), {"id": msg_id, "role": "user", "content": ""})()


async def _async_gen(items):
    for item in items:
        yield item


# ====================================================================
# 辅助：构建多工具 ToolRegistry mock
# ====================================================================


def _make_multi_tool_registry(tools_map: dict[str, Tool]):
    """根据工具名→工具实例的映射，构建 mock ToolRegistry"""
    registry = MagicMock()
    registry.to_openai_schemas = MagicMock(
        return_value=[
            {
                "type": "function",
                "function": {"name": name, "description": tool.description},
            }
            for name, tool in tools_map.items()
        ]
    )
    registry.get = MagicMock(side_effect=lambda name: tools_map.get(name))
    return registry


# ====================================================================
# 辅助：构建基础 mock
# ====================================================================


def _make_conversation_repo():
    repo = MagicMock()
    repo.create_conversation = MagicMock(return_value=_make_conversation())
    repo.get_conversation = MagicMock(return_value=_make_conversation())
    repo.list_messages = MagicMock(return_value=[])
    repo.add_message = MagicMock(return_value=_make_message())
    return repo


def _make_llm_client():
    client = MagicMock()
    client.chat_json = AsyncMock(return_value={"action": "reply", "text": "你好"})
    client.chat = AsyncMock(return_value="工具执行完成。")
    return client


async def _collect(agent, *args, **kwargs):
    events = []
    async for event in agent.chat(*args, **kwargs):
        events.append(event)
    return events


# ====================================================================
# 测试用例 1: 并行执行无依赖工具
# ====================================================================


@pytest.mark.asyncio
async def test_parallel_independent_tools():
    """两个工具都没有 depends_on，LLM 返回 action="tools"，验证两个工具都被并行执行"""
    tool_a = _StubIndependentToolA()
    tool_b = _StubIndependentToolB()
    tools_map = {"tool_a": tool_a, "tool_b": tool_b}

    tool_registry = _make_multi_tool_registry(tools_map)
    conversation_repo = _make_conversation_repo()
    llm_client = _make_llm_client()

    # LLM 返回多工具调用决策，然后回复
    llm_client.chat_json = AsyncMock(
        side_effect=[
            {
                "action": "tools",
                "tools": [
                    {"tool": "tool_a", "args": {"input": "hello"}},
                    {"tool": "tool_b", "args": {"input": "world"}},
                ],
            },
            {"action": "reply", "text": "完成"},
        ]
    )
    llm_client.chat = AsyncMock(return_value="工具执行完成。")

    agent = WritingAgent(
        llm_client=llm_client,
        tool_registry=tool_registry,
        conversation_repo=conversation_repo,
    )

    events = await _collect(agent, "请同时调用 tool_a 和 tool_b")

    types = [e[0] for e in events]

    # 两个工具都应该被调用
    tool_call_count = types.count("tool_call")
    tool_result_count = types.count("tool_result")
    assert tool_call_count == 2, f"期望 2 次 tool_call，实际 {tool_call_count}"
    assert tool_result_count == 2, f"期望 2 次 tool_result，实际 {tool_result_count}"

    # 两个工具都应该被执行
    assert tool_a.execute_mock.call_count == 1, f"tool_a 应被调用 1 次，实际 {tool_a.execute_mock.call_count}"
    assert tool_b.execute_mock.call_count == 1, f"tool_b 应被调用 1 次，实际 {tool_b.execute_mock.call_count}"

    # 不应该有 error 事件
    assert "error" not in types

    # 最后应该是 complete 事件
    assert types[-1] == "complete"

    # 验证 tool_call 事件包含正确的工具名
    tool_names_in_events = [e[1]["tool"] for e in events if e[0] == "tool_call"]
    assert "tool_a" in tool_names_in_events
    assert "tool_b" in tool_names_in_events


# ====================================================================
# 测试用例 2: 串行执行有依赖工具
# ====================================================================


@pytest.mark.asyncio
async def test_serial_dependent_tools():
    """工具 B 的 depends_on=["tool_a"]，验证工具 A 先执行，工具 B 后执行"""
    tool_a = _StubIndependentToolA()
    tool_c = _StubDependentToolC()
    tools_map = {"tool_a": tool_a, "tool_c": tool_c}

    tool_registry = _make_multi_tool_registry(tools_map)
    conversation_repo = _make_conversation_repo()
    llm_client = _make_llm_client()

    # 用共享列表记录执行顺序
    execution_order = []

    async def _tool_a_exec(**kwargs):
        execution_order.append("tool_a")
        return ToolResult(success=True, data={"tool": "a"})

    async def _tool_c_exec(**kwargs):
        execution_order.append("tool_c")
        return ToolResult(success=True, data={"tool": "c"})

    tool_a.execute_mock = AsyncMock(side_effect=_tool_a_exec)
    tool_c.execute_mock = AsyncMock(side_effect=_tool_c_exec)

    llm_client.chat_json = AsyncMock(
        side_effect=[
            {
                "action": "tools",
                "tools": [
                    {"tool": "tool_a", "args": {"input": "first"}},
                    {"tool": "tool_c", "args": {"input": "second"}},
                ],
            },
            {"action": "reply", "text": "完成"},
        ]
    )
    llm_client.chat = AsyncMock(return_value="工具执行完成。")

    agent = WritingAgent(
        llm_client=llm_client,
        tool_registry=tool_registry,
        conversation_repo=conversation_repo,
    )

    events = await _collect(agent, "请调用 tool_a 和 tool_c")

    types = [e[0] for e in events]

    # 两个工具都应该被调用
    tool_call_count = types.count("tool_call")
    assert tool_call_count == 2, f"期望 2 次 tool_call，实际 {tool_call_count}"

    # 工具 A 应该在工具 C 之前执行
    assert execution_order == ["tool_a", "tool_c"], (
        f"执行顺序应为 [tool_a, tool_c]，实际 {execution_order}"
    )

    # 不应该有 error 事件
    assert "error" not in types

    # 最后应该是 complete 事件
    assert types[-1] == "complete"


# ====================================================================
# 测试用例 3: 混合并行+串行
# ====================================================================


@pytest.mark.asyncio
async def test_mixed_parallel_serial():
    """三个工具：tool_a(无依赖) + tool_b(无依赖) + tool_c(依赖 tool_a)，验证混合场景"""
    tool_a = _StubIndependentToolA()
    tool_b = _StubIndependentToolB()
    tool_c = _StubDependentToolC()
    tools_map = {"tool_a": tool_a, "tool_b": tool_b, "tool_c": tool_c}

    tool_registry = _make_multi_tool_registry(tools_map)
    conversation_repo = _make_conversation_repo()
    llm_client = _make_llm_client()

    # 用共享列表记录执行顺序
    execution_order = []

    async def _a_exec(**kwargs):
        await asyncio.sleep(0.01)  # 模拟一点延迟以区分并行串行
        execution_order.append("tool_a")
        return ToolResult(success=True, data={"tool": "a"})

    async def _b_exec(**kwargs):
        await asyncio.sleep(0.005)
        execution_order.append("tool_b")
        return ToolResult(success=True, data={"tool": "b"})

    async def _c_exec(**kwargs):
        execution_order.append("tool_c")
        return ToolResult(success=True, data={"tool": "c"})

    tool_a.execute_mock = AsyncMock(side_effect=_a_exec)
    tool_b.execute_mock = AsyncMock(side_effect=_b_exec)
    tool_c.execute_mock = AsyncMock(side_effect=_c_exec)

    llm_client.chat_json = AsyncMock(
        side_effect=[
            {
                "action": "tools",
                "tools": [
                    {"tool": "tool_a", "args": {"input": "a"}},
                    {"tool": "tool_b", "args": {"input": "b"}},
                    {"tool": "tool_c", "args": {"input": "c"}},
                ],
            },
            {"action": "reply", "text": "完成"},
        ]
    )
    llm_client.chat = AsyncMock(return_value="工具执行完成。")

    agent = WritingAgent(
        llm_client=llm_client,
        tool_registry=tool_registry,
        conversation_repo=conversation_repo,
    )

    events = await _collect(agent, "请同时调用三个工具")

    types = [e[0] for e in events]

    # 三个工具都应该被调用
    tool_call_count = types.count("tool_call")
    tool_result_count = types.count("tool_result")
    assert tool_call_count == 3, f"期望 3 次 tool_call，实际 {tool_call_count}"
    assert tool_result_count == 3, f"期望 3 次 tool_result，实际 {tool_result_count}"

    # tool_c (有依赖) 必须最后执行
    assert execution_order[-1] == "tool_c", (
        f"依赖工具 tool_c 应最后执行，实际执行顺序 {execution_order}"
    )

    # tool_a 和 tool_b 应该在 tool_c 之前执行
    assert "tool_a" in execution_order[:2], f"tool_a 应在 tool_c 之前执行，实际 {execution_order}"
    assert "tool_b" in execution_order[:2], f"tool_b 应在 tool_c 之前执行，实际 {execution_order}"

    # 不应该有 error 事件
    assert "error" not in types

    # 最后应该是 complete 事件
    assert types[-1] == "complete"


# ====================================================================
# 测试用例 4: 多工具调用超出限制
# ====================================================================


@pytest.mark.asyncio
async def test_parallel_tools_exceeds_limit():
    """单次多工具调用 + 已有调用次数超出限制，验证 yield E4005"""
    tool_a = _StubIndependentToolA()
    tool_b = _StubIndependentToolB()
    tools_map = {"tool_a": tool_a, "tool_b": tool_b}

    tool_registry = _make_multi_tool_registry(tools_map)
    conversation_repo = _make_conversation_repo()
    llm_client = _make_llm_client()

    # 前 4 次单工具调用 + 第 5 次多工具调用（2 个工具），总计 6 个工具>5 上限
    llm_client.chat_json = AsyncMock(
        side_effect=[
            {"action": "tool", "tool": "tool_a", "args": {"input": "1"}},
            {"action": "tool", "tool": "tool_a", "args": {"input": "2"}},
            {"action": "tool", "tool": "tool_a", "args": {"input": "3"}},
            {"action": "tool", "tool": "tool_a", "args": {"input": "4"}},
            {"action": "tools", "tools": [
                {"tool": "tool_a", "args": {"input": "5"}},
                {"tool": "tool_b", "args": {"input": "6"}},
            ]},
        ]
    )
    llm_client.chat = AsyncMock(return_value="工具执行完成。")

    agent = WritingAgent(
        llm_client=llm_client,
        tool_registry=tool_registry,
        conversation_repo=conversation_repo,
    )

    events = await _collect(agent, "请调用工具")

    types = [e[0] for e in events]

    # 前 4 次应该正常执行
    tool_call_count = types.count("tool_call")
    assert tool_call_count == 4, f"期望 4 次 tool_call，实际 {tool_call_count}"

    # 应该有 E4005 错误
    assert "error" in types
    error_event = next(e for e in events if e[0] == "error")
    assert error_event[1]["code"] == "E4005"

    # 仍然应该有 complete 事件
    assert "complete" in types


# ====================================================================
# 测试用例 5: 有依赖工具的未知工具处理
# ====================================================================


@pytest.mark.asyncio
async def test_parallel_with_unknown_tool():
    """多工具调用中包含不存在的工具，验证错误处理"""
    tool_a = _StubIndependentToolA()
    tools_map = {"tool_a": tool_a}

    tool_registry = _make_multi_tool_registry(tools_map)
    conversation_repo = _make_conversation_repo()
    llm_client = _make_llm_client()

    llm_client.chat_json = AsyncMock(
        side_effect=[
            {
                "action": "tools",
                "tools": [
                    {"tool": "tool_a", "args": {"input": "valid"}},
                    {"tool": "nonexistent_tool", "args": {}},
                ],
            },
            {"action": "reply", "text": "完成"},
        ]
    )
    llm_client.chat = AsyncMock(return_value="工具执行完成。")

    agent = WritingAgent(
        llm_client=llm_client,
        tool_registry=tool_registry,
        conversation_repo=conversation_repo,
    )

    events = await _collect(agent, "请调用工具")

    types = [e[0] for e in events]

    # 两个 tool_call 和两个 tool_result 都应该出现
    tool_call_count = types.count("tool_call")
    tool_result_count = types.count("tool_result")
    assert tool_call_count == 2, f"期望 2 次 tool_call，实际 {tool_call_count}"
    assert tool_result_count == 2, f"期望 2 次 tool_result，实际 {tool_result_count}"

    # 应该有一个失败的 tool_result
    fail_results = [e for e in events if e[0] == "tool_result" and not e[1]["success"]]
    assert len(fail_results) == 1, f"期望 1 个失败 tool_result，实际 {len(fail_results)}"
    assert "不存在" in fail_results[0][1]["data"]["error"]

    # 不应该有 error 事件（工具不存在是 tool_result 失败，不是系统 error）
    # 最后应该是 complete 事件
    assert types[-1] == "complete"
