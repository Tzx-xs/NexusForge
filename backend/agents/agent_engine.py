from __future__ import annotations

import asyncio
import json
import os
import time as _time
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Any, cast
from uuid import uuid4

if TYPE_CHECKING:
    from agents.planner import TaskPlan
    from agents.tools.base import Tool

from agents.memory_compressor import MemoryCompressor
from agents.planner import TaskPlanner
from agents.system_prompt import WRITING_AGENT_SYSTEM_PROMPT
from agents.tools.base import ToolResult
from agents.tools.registry import ToolRegistry
from config.defaults import DEFAULT_MAX_TOOL_CALLS
from config.logging import get_logger
from infrastructure.ai.llm_client import LLMClient
from infrastructure.persistence.conversation_repo import ConversationRepository

logger = get_logger(__name__)


class WritingAgent:
    """Agent 主编排器

    接收用户消息 → LLM 决策调用哪个 Tool → 执行 Tool → 流式返回结果。
    支持两种模式：
    1. Function Calling 模式（统一通过 chat_json 决策）：LLM 返回决策 JSON，Agent 解析执行
    2. 纯文本模式（chat_json 失败时降级）：LLM 直接流式返回文本
    """

    def __init__(
        self,
        llm_client: LLMClient,
        tool_registry: ToolRegistry,
        conversation_repo: ConversationRepository,
    ):
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.conversation_repo = conversation_repo
        self.memory_compressor = MemoryCompressor(llm_client)
        self.planner = TaskPlanner(llm_client)

    # ------------------------------------------------------------------
    # 主对话入口
    # ------------------------------------------------------------------

    async def chat(
        self,
        message: str,
        conversation_id: str | None = None,
        novel_id: str | None = None,
    ) -> AsyncGenerator[tuple[str, Any], None]:
        """主对话循环 — 编排入口

        yields (event_type, data) 元组：
        - ("message", {"conversation_id": "..."})
        - ("plan", {"plan_summary": "...", "steps": [...]})
        - ("tool_call", {"tool": name, "args": {...}, "tool_call_id": "..."})
        - ("tool_confirm", {"tool": name, "message": "..."})
        - ("tool_result", {"tool": name, "success": bool, "data": {...}, "tool_call_id": "..."})
        - ("token", {"delta": "..."})
        - ("plan_complete", {"summary": "...", "total_steps": ..., "completed_steps": ...})
        - ("complete", {"conversation_id": "...", "message_id": "..."})
        - ("error", {"code": "...", "message": "..."})
        """
        try:
            # ---- Step 0: 统一净化用户消息（覆盖所有路径：原生FC/JSON降级/流式降级）----
            # P0 修复：之前仅 _get_llm_decision 降级路径净化，主路径与流式降级未净化
            message = self._sanitize_user_message(message)

            # ---- Step 1: 获取/创建会话 ----
            conv_id, is_new = await self._prepare_conversation(
                conversation_id, novel_id, message,
            )

            # ---- Step 2: 创建/获取计划（仅新会话） ----
            plan = None
            if is_new:
                async for event in self._create_or_update_plan(message):
                    yield event
                    if event[0] == "plan":
                        plan = event[1].get("plan")

            # ---- Step 3: 构建 system content（含计划信息） ----
            system_content = WRITING_AGENT_SYSTEM_PROMPT
            if plan is not None and plan.status != "failed" and plan.steps:
                plan_summary = self.planner.get_plan_summary(plan)
                system_content += (
                    f"\n\n[任务计划]\n{plan_summary}\n"
                    "请按照上述计划逐步执行，每完成一步再开始下一步。"
                )

            # ---- Step 4: 加载历史 + 记忆压缩 ----
            llm_messages = await self._load_and_compress_history(conv_id, system_content)

            # ---- Step 5: 工具调用主循环 ----
            # 使用可变 dict 传递状态，方便子方法修改
            state: dict[str, Any] = {
                "tool_call_count": 0,
                "assistant_text": "",
                "last_tool_name": None,
                "last_tool_args": None,
            }

            while True:
                tools_schema = self.tool_registry.to_openai_schemas()

                # 优先使用原生 Function Calling
                decision = await self._get_llm_decision_native(llm_messages, tools_schema)

                # 原生失败则降级到旧的 JSON prompt 方式
                if decision is None:
                    logger.debug("Native tool calling failed, falling back to JSON prompt")
                    decision = await self._get_llm_decision(llm_messages, tools_schema, message)

                if decision is None:
                    # 降级：纯文本流式回复
                    async for token in self.llm_client.chat_stream(llm_messages):
                        state["assistant_text"] += token
                        yield "token", {"delta": token}
                    break

                action = decision.get("action", "reply")

                if action == "tool":
                    # 单工具
                    if state["tool_call_count"] >= DEFAULT_MAX_TOOL_CALLS:
                        yield "error", {
                            "code": "E4005",
                            "message": "工具调用次数过多(已达5次上限),请简化需求或分步执行",
                        }
                        async for event in self._finalize_chat(
                            state["assistant_text"], conv_id,
                            state["last_tool_name"], state["last_tool_args"],
                        ):
                            yield event
                        return

                    async for event in self._execute_single_tool(
                        decision, llm_messages, plan, state,
                    ):
                        yield event

                    if plan is not None and self._is_plan_complete(plan):
                        yield "plan_complete", {
                            "summary": self.planner.get_plan_summary(plan),
                            "total_steps": len(plan.steps),
                            "completed_steps": sum(
                                1 for s in plan.steps if s.status == "completed"
                            ),
                        }
                        plan = None

                elif action == "tools":
                    # 多工具并行
                    tool_calls_list = decision.get("tools", [])
                    if not isinstance(tool_calls_list, list):
                        tool_calls_list = []

                    if state["tool_call_count"] + len(tool_calls_list) > DEFAULT_MAX_TOOL_CALLS:
                        yield "error", {
                            "code": "E4005",
                            "message": "工具调用次数过多(已达5次上限),请简化需求或分步执行",
                        }
                        async for event in self._finalize_chat(
                            state["assistant_text"], conv_id,
                            state["last_tool_name"], state["last_tool_args"],
                        ):
                            yield event
                        return

                    async for event in self._execute_parallel_tools(
                        decision, llm_messages, plan, state,
                    ):
                        yield event

                    if plan is not None and self._is_plan_complete(plan):
                        yield "plan_complete", {
                            "summary": self.planner.get_plan_summary(plan),
                            "total_steps": len(plan.steps),
                            "completed_steps": sum(
                                1 for s in plan.steps if s.status == "completed"
                            ),
                        }
                        plan = None

                else:
                    # 直接文本回复
                    text = decision.get("text", "") or ""
                    if not text:
                        async for token in self.llm_client.chat_stream(llm_messages):
                            text += token
                            yield "token", {"delta": token}
                    else:
                        for chunk in self._split_to_chunks(text):
                            yield "token", {"delta": chunk}
                    state["assistant_text"] = text
                    break

            # ---- Step 6: 持久化 assistant 消息 ----
            async for event in self._finalize_chat(
                state["assistant_text"], conv_id,
                state["last_tool_name"], state["last_tool_args"],
            ):
                yield event

        except (KeyboardInterrupt, SystemExit):
            raise
        except ValueError as e:
            # E4004: 会话不存在（来自 _prepare_conversation）
            yield "error", {"code": "E4004", "message": str(e)}
        except Exception as e:
            logger.exception("WritingAgent.chat failed")
            yield "error", {"code": "E5000", "message": str(e)}

    # ------------------------------------------------------------------
    # 子方法：对话生命周期
    # ------------------------------------------------------------------

    async def _prepare_conversation(
        self,
        conversation_id: str | None,
        novel_id: str | None,
        message: str,
    ) -> tuple[str, bool]:
        """获取或创建会话，持久化用户消息

        Args:
            conversation_id: 现有会话 ID（可选）
            novel_id: 关联小说 ID（可选）
            message: 用户消息内容

        Returns:
            (conversation_id, is_new_conversation) 元组
        """
        is_new = False
        if conversation_id:
            conv = self.conversation_repo.get_conversation(conversation_id)
            if not conv:
                # 由 chat() 的 try/except 捕获
                raise ValueError(f"会话不存在: {conversation_id}")
        else:
            conv = self.conversation_repo.create_conversation(
                novel_id=novel_id,
                title=message[:20] + ("..." if len(message) > 20 else ""),
            )
            conversation_id = conv.id
            is_new = True

        # 持久化用户消息
        self.conversation_repo.add_message(
            conversation_id=conversation_id,
            role="user",
            content=message,
        )

        return str(conversation_id), is_new

    async def _load_and_compress_history(
        self,
        conversation_id: str,
        system_content: str,
    ) -> list[dict[str, str]]:
        """加载会话历史并压缩

        Args:
            conversation_id: 会话 ID
            system_content: 系统 prompt 内容（含计划信息）

        Returns:
            压缩后的 LLM 消息列表 [{"role": ..., "content": ...}]
        """
        # 加载历史消息
        history = self.conversation_repo.list_messages(conversation_id)

        # 构建 system message
        llm_messages: list[dict[str, str]] = [
            {"role": "system", "content": system_content},
        ]
        for msg in history:
            llm_messages.append({"role": msg.role, "content": msg.content})

        # 记忆压缩（压缩早期消息）
        system_msg = llm_messages[0]
        history_messages = llm_messages[1:]
        compressed_history = await self.memory_compressor.compress(history_messages)
        return [system_msg] + compressed_history

    async def _create_or_update_plan(
        self,
        user_message: str,
    ) -> AsyncGenerator[tuple[str, Any], None]:
        """仅新会话创建计划

        Yields:
            ("plan", {"plan_summary": ..., "steps": [...], "plan": TaskPlan})
        """
        plan = await self.planner.create_plan(user_message)
        if plan.status != "failed" and plan.steps:
            plan_summary = self.planner.get_plan_summary(plan)
            yield "plan", {
                "plan_summary": plan_summary,
                "plan": plan,
                "steps": [
                    {
                        "step_id": s.step_id,
                        "name": s.name,
                        "description": s.description,
                        "status": s.status,
                    }
                    for s in plan.steps
                ],
            }
        else:
            yield "plan", {"plan_summary": "", "plan": None, "steps": []}

    async def _finalize_chat(
        self,
        assistant_text: str,
        conversation_id: str,
        last_tool_name: str | None,
        last_tool_args: dict | None,
    ) -> AsyncGenerator[tuple[str, Any], None]:
        """持久化 assistant 消息

        Yields:
            ("complete", {"conversation_id": ..., "message_id": ...})
        """
        if last_tool_name is not None:
            saved = self.conversation_repo.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=assistant_text,
                tool_calls=json.dumps(
                    {"tool": last_tool_name, "args": last_tool_args},
                    ensure_ascii=False,
                ),
                tool_name=last_tool_name,
            )
        else:
            saved = self.conversation_repo.add_message(
                conversation_id=conversation_id,
                role="assistant",
                content=assistant_text,
            )

        yield "complete", {
            "conversation_id": conversation_id,
            "message_id": saved.id,
        }

    # ------------------------------------------------------------------
    # 工具执行：统一生命周期
    # ------------------------------------------------------------------

    async def _execute_tool_with_lifecycle(
        self,
        tool: Tool,
        tool_args: dict[str, Any],
        llm_messages: list[dict[str, str]],
        plan: TaskPlan | None,
    ) -> AsyncGenerator[tuple[str, Any], None]:
        """统一工具执行生命周期（10步）

        1. 生成唯一 tool_call_id
        2. yield ("tool_call", ...)
        3. 工具查找确认（由调用方保证 tool 不为 None）
        4. requires_confirmation 检查（F-008）
        5. validate_args 参数校验（C9）
        6. tool.execute(**tool_args)
        7. yield ("tool_result", ...)
        8. 成功时 _explain_tool_result
        9. 成功时 _advance_plan_step(plan)
        10. yield ("_result", (result_text, success, tool_name, tool_args))

        Yields:
            ("tool_call", ...), 可选 ("tool_confirm", ...), ("tool_result", ...),
            ("_result", (result_text, success, tool_name, tool_args))
        """
        # Step 1: 生成唯一 tool_call_id
        tool_call_id = f"call_{uuid4().hex[:12]}"
        tool_name = tool.name

        # Step 2: yield tool_call
        yield "tool_call", {
            "tool": tool_name,
            "args": tool_args,
            "tool_call_id": tool_call_id,
        }

        # Step 3: tool 已由调用方保证不为 None

        # Step 4: requires_confirmation 检查（F-008）
        if tool.requires_confirmation:
            yield "tool_confirm", {
                "tool": tool_name,
                "message": f"工具 '{tool_name}' 需要确认执行",
            }
            if os.environ.get("SKIP_DESTRUCTIVE_TOOLS", "").lower() == "true":
                logger.warning(
                    "SKIP_DESTRUCTIVE_TOOLS 已启用，跳过破坏性工具: %s(%s)",
                    tool_name, tool_args,
                )
                yield "tool_result", {
                    "tool": tool_name,
                    "success": False,
                    "data": {"error": f"破坏性工具 '{tool_name}' 已被安全策略跳过"},
                    "tool_call_id": tool_call_id,
                }
                result_text = f"破坏性工具 {tool_name} 已被安全策略跳过。"
                yield "_result", (result_text, False, tool_name, tool_args)
                return
            else:
                logger.warning("执行破坏性工具: %s(%s)", tool_name, tool_args)

        # Step 5: validate_args 参数校验（C9）
        is_valid, error_msg = tool.validate_args(tool_args)
        if not is_valid:
            result = ToolResult(success=False, error=f"参数校验失败: {error_msg}")
        else:
            # Step 6: execute
            result = await tool.execute(**tool_args)

        # Step 7: yield tool_result
        yield "tool_result", {
            "tool": tool_name,
            "success": result.success,
            "data": result.data if result.success else {"error": result.error},
            "tool_call_id": tool_call_id,
        }

        # Step 8 & 9: 成功时解释结果 + 推进计划
        if result.success:
            result_text = await self._explain_tool_result(
                llm_messages, tool_name, tool_args, result.data,
            )
            if plan is not None and plan.steps:
                self._advance_plan_step(plan)
        else:
            result_text = f"工具 {tool_name} 执行失败：{result.error}"

        # Step 10: 返回结果元组
        yield "_result", (result_text, result.success, tool_name, tool_args)

    # ------------------------------------------------------------------
    # 单工具执行
    # ------------------------------------------------------------------

    async def _execute_single_tool(
        self,
        decision: dict[str, Any],
        llm_messages: list[dict[str, str]],
        plan: TaskPlan | None,
        state: dict[str, Any],
    ) -> AsyncGenerator[tuple[str, Any], None]:
        """执行单个工具（委托 _execute_tool_with_lifecycle）

        Args:
            decision: LLM 决策 {"action": "tool", "tool": ..., "args": ...}
            llm_messages: LLM 消息历史（会被追加工具结果）
            plan: 当前任务计划（会被推进）
            state: 可变状态字典（tool_call_count, assistant_text, last_tool_name, last_tool_args）
        """
        # 获取工具名和参数
        tool_name = decision.get("tool", "") or ""
        tool_args = decision.get("args", {})
        if not isinstance(tool_args, dict):
            tool_args = {}

        # 查找工具
        tool = self.tool_registry.get(tool_name)
        if not tool:
            state["tool_call_count"] += 1
            tc_id = f"{tool_name}_{int(_time.time() * 1000)}_{state['tool_call_count']}"
            yield "tool_call", {
                "tool": tool_name, "args": tool_args, "tool_call_id": tc_id,
            }
            yield "tool_result", {
                "tool": tool_name,
                "success": False,
                "data": {"error": f"工具不存在: {tool_name}"},
                "tool_call_id": tc_id,
            }
            tool_result_text = f"抱歉，工具 {tool_name} 不可用。"
        else:
            # 委托统一生命周期
            state["tool_call_count"] += 1
            result_text = ""
            success = False
            async for event_type, event_data in self._execute_tool_with_lifecycle(
                tool, tool_args, llm_messages, plan,
            ):
                if event_type == "_result":
                    result_text, success, *_ = event_data
                else:
                    yield event_type, event_data

            tool_result_text = result_text

        # 工具结果追加到消息历史
        if "tool_call_id" in decision:
            # 原生 Function Calling 路径：使用 tool 角色格式
            llm_messages.append({
                "role": "tool",
                "tool_call_id": decision["tool_call_id"],
                "content": json.dumps({"result": tool_result_text}, ensure_ascii=False),
            })
        else:
            # 旧路径（降级）：使用 user 角色格式
            llm_messages.append({"role": "user", "content": f"[工具结果] {tool_result_text}"})
        state["assistant_text"] = tool_result_text
        state["last_tool_name"] = tool_name
        state["last_tool_args"] = tool_args

        # 流式输出（chunked）
        for chunk in self._split_to_chunks(tool_result_text):
            yield "token", {"delta": chunk}

    # ------------------------------------------------------------------
    # 多工具并行执行
    # ------------------------------------------------------------------

    async def _execute_parallel_tools(
        self,
        decision: dict[str, Any],
        llm_messages: list[dict[str, str]],
        plan: TaskPlan | None,
        state: dict[str, Any],
    ) -> AsyncGenerator[tuple[str, Any], None]:
        """执行多个工具（并行执行独立工具，串行执行依赖工具）

        Args:
            decision: LLM 决策 {"action": "tools", "tools": [...]}
            llm_messages: LLM 消息历史（会被追加工具结果）
            plan: 当前任务计划（会被推进）
            state: 可变状态字典
        """
        # 解析工具列表
        tool_calls_list = decision.get("tools", [])
        if not isinstance(tool_calls_list, list):
            tool_calls_list = []

        if not tool_calls_list:
            return

        # 分类工具：无依赖（独立）vs 有依赖
        independent_tcs: list[tuple] = []
        dependent_tcs: list[tuple] = []
        for tc in tool_calls_list:
            t_name = tc.get("tool", "")
            t_tool = self.tool_registry.get(t_name)
            if t_tool and t_tool.depends_on:
                dependent_tcs.append((t_name, tc.get("args", {}), t_tool))
            else:
                independent_tcs.append((t_name, tc.get("args", {}), t_tool))

        all_results: list[tuple[str, dict, Any]] = []
        last_tc_info: tuple[str, dict] | None = None

        # ---- 并行执行独立工具 ----
        if independent_tcs:
            async def _exec_one(item: tuple) -> tuple:
                t_name, t_args, t_tool = item
                if not isinstance(t_args, dict):
                    t_args = {}
                if not t_tool:
                    return (t_name, t_args, ToolResult(success=False, error=f"工具不存在: {t_name}"))
                # requires_confirmation 检查（C10）
                if getattr(t_tool, "requires_confirmation", False):
                    return (t_name, t_args, ToolResult(success=False, error=f"工具 {t_name} 需要确认后才能执行"))
                # validate_args（C9）
                is_valid, error_msg = t_tool.validate_args(t_args)
                if not is_valid:
                    return (t_name, t_args, ToolResult(success=False, error=f"参数校验失败: {error_msg}"))
                result = await t_tool.execute(**t_args)
                return (t_name, t_args, result)

            parallel_results = await asyncio.gather(
                *[_exec_one(item) for item in independent_tcs],
            )
            for t_name, t_args, result in parallel_results:
                all_results.append((t_name, t_args, result))
                last_tc_info = (t_name, t_args)

        # ---- 串行执行依赖工具 ----
        for t_name, t_args, t_tool in dependent_tcs:
            if not isinstance(t_args, dict):
                t_args = {}
            if not t_tool:
                result = ToolResult(success=False, error=f"工具不存在: {t_name}")
            elif getattr(t_tool, "requires_confirmation", False):
                result = ToolResult(success=False, error=f"工具 {t_name} 需要确认后才能执行")
            else:
                is_valid, error_msg = t_tool.validate_args(t_args)
                if not is_valid:
                    result = ToolResult(success=False, error=f"参数校验失败: {error_msg}")
                else:
                    result = await t_tool.execute(**t_args)
            all_results.append((t_name, t_args, result))
            last_tc_info = (t_name, t_args)

        # ---- 统一 yield 结果并更新消息历史 ----
        # 判断是否为原生 Function Calling 路径（检查 tools 列表是否有 tool_call_id）
        tool_calls_list_raw = decision.get("tools", [])
        is_native_fc = bool(
            isinstance(tool_calls_list_raw, list)
            and tool_calls_list_raw
            and "tool_call_id" in tool_calls_list_raw[0]
        )

        combined_texts: list[str] = []
        for idx, (t_name, t_args, result) in enumerate(all_results):
            state["tool_call_count"] += 1
            tc_id = f"{t_name}_{int(_time.time() * 1000)}_{state['tool_call_count']}"
            yield "tool_call", {
                "tool": t_name, "args": t_args, "tool_call_id": tc_id,
            }

            if not result.success and "不存在" in (result.error or ""):
                yield "tool_result", {
                    "tool": t_name,
                    "success": False,
                    "data": {"error": result.error},
                    "tool_call_id": tc_id,
                }
                result_text = f"抱歉，工具 {t_name} 不可用。"
            elif result.success:
                yield "tool_result", {
                    "tool": t_name,
                    "success": True,
                    "data": result.data,
                    "tool_call_id": tc_id,
                }
                result_text = await self._explain_tool_result(
                    llm_messages, t_name, t_args, result.data,
                )
            else:
                yield "tool_result", {
                    "tool": t_name,
                    "success": False,
                    "data": {"error": result.error},
                    "tool_call_id": tc_id,
                }
                result_text = f"工具 {t_name} 执行失败：{result.error}"

            combined_texts.append(result_text)

            # 原生 Function Calling 路径：每个工具结果单独以 tool 角色追加
            if is_native_fc and idx < len(tool_calls_list_raw):
                original_tc_id = tool_calls_list_raw[idx].get("tool_call_id", "")
                llm_messages.append({
                    "role": "tool",
                    "tool_call_id": original_tc_id,
                    "content": json.dumps({"result": result_text}, ensure_ascii=False),
                })

        combined_text = "\n".join(combined_texts)
        if last_tc_info:
            state["last_tool_name"] = last_tc_info[0]
            state["last_tool_args"] = last_tc_info[1]

        # 旧路径（降级）：使用 user 角色格式，将所有结果合并为一条消息
        if not is_native_fc:
            llm_messages.append({"role": "user", "content": f"[工具结果] {combined_text}"})
        state["assistant_text"] = combined_text

        # 计划步骤推进：每个成功工具推进一步
        if plan is not None and plan.steps:
            success_count = sum(1 for _, _, r in all_results if r.success)
            for _ in range(success_count):
                self._advance_plan_step(plan)

        # 流式输出（chunked）
        for chunk in self._split_to_chunks(combined_text):
            yield "token", {"delta": chunk}

    # ------------------------------------------------------------------
    # 计划管理
    # ------------------------------------------------------------------

    def _advance_plan_step(self, plan: TaskPlan) -> None:
        """将计划中第一个 pending 步骤推进为 completed。

        从 planner 导入类型会导致循环引用，此处使用 duck-typing。
        """
        next_step = self.planner.get_next_step(plan)
        if next_step is not None:
            self.planner.mark_step_completed(plan, next_step.step_id)

    def _is_plan_complete(self, plan: TaskPlan) -> bool:
        """检查计划的所有步骤是否都已完成。"""
        if not plan.steps:
            return False
        return all(s.status == "completed" for s in plan.steps)

    # ------------------------------------------------------------------
    # 安全与辅助方法
    # ------------------------------------------------------------------

    @staticmethod
    def _sanitize_user_message(msg: str) -> str:
        """清理用户消息，防止 prompt 注入攻击。

        1. 移除消息中的 ```json ``` 标记，防止用户注入 JSON 代码块
        2. 将消息包裹在 <user_message> XML 标签中
        3. 检测并拒绝包含系统指令覆盖关键词的消息
        """
        # 检测系统指令覆盖关键词组合
        dangerous_patterns = [
            ("忽略", "系统"),
            ("忽略", "提示"),
            ("你是", "系统"),
            ("系统提示", ""),
            ("覆盖", "指令"),
            ("ignore", "system"),
            ("override", "system"),
            ("bypass", "instruction"),
        ]
        msg_lower = msg.lower()
        for kw1, kw2 in dangerous_patterns:
            if kw1.lower() in msg_lower and (not kw2 or kw2.lower() in msg_lower):
                return (
                    "<user_message>[安全提示] 检测到可能包含系统指令覆盖的消息，"
                    "已进行安全过滤。请重新表述您的请求。</user_message>"
                )

        # 移除 ```json ``` 代码块标记
        sanitized = msg.replace("```json", "").replace("```", "")

        # 包裹在 XML 标签中
        return f"<user_message>{sanitized}</user_message>"

    async def _get_llm_decision_native(
        self,
        messages: list[dict[str, str]],
        tools_schema: list[dict[str, Any]],
    ) -> dict | None:
        """
        使用原生 Function Calling 让 LLM 决策。

        返回与 _get_llm_decision() 兼容的 dict 格式：
        - {"action": "tool", "tool": "name", "args": {...}}             — 单工具
        - {"action": "tools", "tools": [{"name": ..., "args": ...}, ...]} — 多工具
        - {"action": "reply", "text": "..."}                              — 直接回复
        - None  — 失败，触发降级
        """
        try:
            result = await self.llm_client.chat_with_tools(
                messages=messages,
                tools=tools_schema,
            )
        except Exception as e:
            logger.debug("Native tool calling failed: %s", e)
            return None  # 触发降级到旧 _get_llm_decision()

        if result is None:
            return None  # 触发降级到旧 _get_llm_decision()

        if result.tool_calls:
            if len(result.tool_calls) == 1:
                tc = result.tool_calls[0]
                return {
                    "action": "tool",
                    "tool": tc.function_name,
                    "args": tc.arguments,
                    "tool_call_id": tc.id,
                }
            else:
                tools_list = []
                for tc in result.tool_calls:
                    tools_list.append({
                        "tool": tc.function_name,
                        "args": tc.arguments,
                        "tool_call_id": tc.id,
                    })
                return {
                    "action": "tools",
                    "tools": tools_list,
                }

        # 无 tool_calls，纯文本回复
        return {
            "action": "reply",
            "text": result.content or "",
        }

    async def _get_llm_decision(
        self,
        messages: list[dict[str, str]],
        tools_schema: list[dict[str, Any]],
        user_message: str,
    ) -> dict | None:
        """让 LLM 决策：调用工具还是直接回复

        返回 {"action": "tool"|"tools"|"reply", "tool": ..., "tools": [...], "args": ..., "text": ...}
        返回 None 表示降级到纯文本流式模式
        """
        decision_prompt = f"""分析用户请求，决定下一步动作。

用户消息：{user_message}

可用工具：
{json.dumps(tools_schema, ensure_ascii=False, indent=2)}

请以严格 JSON 格式返回决策：
- 若需要调用单个工具：{{"action": "tool", "tool": "工具名", "args": {{参数}}}}
- 若需要同时调用多个无依赖工具：{{"action": "tools", "tools": [{{"tool": "工具名", "args": {{参数}}}}, ...]}}
- 若直接回复：{{"action": "reply", "text": "回复内容"}}

只返回 JSON，不要其他内容。"""

        try:
            result = await self.llm_client.chat_json(
                messages + [{"role": "user", "content": decision_prompt}],
                system_prompt="你是决策助手，只输出合法 JSON。",
            )
            return result
        except Exception as e:
            logger.warning("LLM decision failed, fallback to stream: %s", e)
            return None

    async def _explain_tool_result(
        self,
        messages: list[dict[str, str]],
        tool_name: str,
        tool_args: dict[str, Any],
        tool_data: dict[str, Any],
    ) -> str:
        """让 LLM 用自然语言解释工具执行结果"""
        explain_prompt = f"""工具 {tool_name} 已执行完成。

调用参数：{json.dumps(tool_args, ensure_ascii=False)}
执行结果：{json.dumps(tool_data, ensure_ascii=False, default=str)}

请用简洁的自然语言向用户解释这个结果（1-3句话）。不要重复 JSON，用通俗语言说明发生了什么、结果如何。"""

        try:
            result = await self.llm_client.chat(
                messages + [{"role": "user", "content": explain_prompt}],
            )
            return cast("str", result)
        except Exception as e:
            logger.warning("Explain tool result failed: %s", e)
            return f"工具 {tool_name} 执行完成，结果：{tool_data}"

    @staticmethod
    def _split_to_chunks(text: str, chunk_size: int = 80) -> list[str]:
        """将文本按字符数切分为小块，模拟流式输出"""
        if not text:
            return []
        return [text[i: i + chunk_size] for i in range(0, len(text), chunk_size)]
