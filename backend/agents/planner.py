from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from config.logging import get_logger

logger = get_logger(__name__)


# ====================================================================
# 数据结构
# ====================================================================


@dataclass
class PlanStep:
    """计划中的单个步骤"""
    step_id: str
    name: str
    description: str = ""
    status: str = "pending"  # pending | in_progress | completed | failed
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)  # 前置步骤的 step_id 列表
    error: str = ""


@dataclass
class TaskPlan:
    """任务计划"""
    steps: list[PlanStep] = field(default_factory=list)
    current_step_index: int = 0
    status: str = "pending"  # pending | in_progress | completed | failed


@dataclass
class ValidationResult:
    """计划校验结果"""
    is_valid: bool
    errors: list[str] = field(default_factory=list)


@dataclass
class ExecutionResult:
    """计划执行结果"""
    success: bool
    completed_step_ids: list[str] = field(default_factory=list)
    failed_step_id: str = ""
    error: str = ""


class StepExecutor(Protocol):
    """步骤执行器接口（供 PlanExecutor 注入）。

    将 PlanStep 映射为具体工具调用。实现方可对接 ToolRegistry、
    ChapterService 或任意可调用对象。
    """

    async def __call__(self, step: PlanStep) -> tuple[bool, str]:
        """执行单个步骤。

        Returns:
            (success, output_or_error)
        """
        ...


# ====================================================================
# TaskPlanner — 计划生成与状态管理
# ====================================================================


class TaskPlanner:
    """任务规划器

    将用户创作需求分解为有序步骤序列,每步有明确输入/输出/前置条件。
    使用 LLM 将自然语言意图转化为 Plan-and-Execute 任务图。
    """

    def __init__(self, llm_client: Any) -> None:
        """llm_client: 具备 chat() 方法的 LLM 客户端"""
        self.llm_client = llm_client

    async def create_plan(self, user_intent: str) -> TaskPlan:
        """调用 LLM 将用户意图分解为步骤序列

        返回 TaskPlan,包含有序的 PlanStep 列表。
        如果 LLM 调用失败,返回空 TaskPlan(status='failed')。
        """
        prompt = f"""将以下创作任务分解为有序步骤序列。

任务描述：
{user_intent}

请以 JSON 格式返回步骤列表,每个步骤包含:
- step_id: 步骤唯一标识(如 "step_1")
- name: 步骤名称(简短)
- description: 步骤描述
- dependencies: 前置步骤的 step_id 列表(空列表表示无前置)

返回格式:
{{"steps": [
    {{"step_id": "step_1", "name": "...", "description": "...", "dependencies": []}},
    {{"step_id": "step_2", "name": "...", "description": "...", "dependencies": ["step_1"]}}
]}}

只返回 JSON,不要其他内容。"""

        try:
            result = await self.llm_client.chat([
                {"role": "user", "content": prompt}
            ])
            # result 可能是 str 或 dict
            if isinstance(result, str):
                plan_data = json.loads(result)
            else:
                plan_data = result

            steps = []
            for step_data in plan_data.get("steps", []):
                step = PlanStep(
                    step_id=step_data["step_id"],
                    name=step_data["name"],
                    description=step_data.get("description", ""),
                    dependencies=step_data.get("dependencies", []),
                )
                steps.append(step)

            return TaskPlan(steps=steps, status="in_progress")
        except Exception:
            logger.exception("TaskPlanner.create_plan failed")
            return TaskPlan(steps=[], status="failed")

    async def revise_plan(self, original: TaskPlan, feedback: str) -> TaskPlan:
        """基于反馈修正已有计划（多轮对话场景）。

        保留已完成步骤，让 LLM 决定 pending/failed 步骤如何调整。
        feedback 为空时直接返回原计划。

        Args:
            original: 原始计划（含已完成/失败状态）
            feedback: 用户或上游给出的修正说明

        Returns:
            修正后的新 TaskPlan；LLM 失败时返回 failed 状态的空计划。
        """
        if not feedback:
            return original

        completed_ids = [s.step_id for s in original.steps if s.status == "completed"]
        pending_steps = [
            {"step_id": s.step_id, "name": s.name, "description": s.description, "status": s.status}
            for s in original.steps if s.status != "completed"
        ]

        prompt = f"""已有创作计划需要修正。

已完成步骤（不可修改）：
{json.dumps(completed_ids, ensure_ascii=False)}

待修正步骤：
{json.dumps(pending_steps, ensure_ascii=False)}

修正说明：
{feedback}

请输出修正后的步骤序列（不含已完成步骤），格式同 create_plan：
{{"steps": [{{"step_id": "...", "name": "...", "description": "...", "dependencies": [...]}}]}}

只返回 JSON。"""

        try:
            result = await self.llm_client.chat([{"role": "user", "content": prompt}])
            plan_data = json.loads(result) if isinstance(result, str) else result

            new_steps = [
                PlanStep(
                    step_id=step_data["step_id"],
                    name=step_data["name"],
                    description=step_data.get("description", ""),
                    dependencies=step_data.get("dependencies", []),
                )
                for step_data in plan_data.get("steps", [])
            ]
            # 保留已完成步骤在前
            completed_steps = [s for s in original.steps if s.status == "completed"]
            return TaskPlan(steps=completed_steps + new_steps, status="in_progress")
        except Exception:
            logger.exception("TaskPlanner.revise_plan failed")
            return TaskPlan(steps=original.steps, status="failed")

    def get_next_step(self, plan: TaskPlan) -> PlanStep | None:
        """返回下一个待执行的步骤

        按顺序查找第一个 status='pending' 且所有依赖已完成的步骤。
        无则返回 None。
        """
        completed_ids = {s.step_id for s in plan.steps if s.status == "completed"}
        for step in plan.steps:
            if step.status != "pending":
                continue
            if all(dep in completed_ids for dep in step.dependencies):
                return step
        return None

    def mark_step_completed(self, plan: TaskPlan, step_id: str) -> None:
        """标记步骤为已完成"""
        for step in plan.steps:
            if step.step_id == step_id:
                step.status = "completed"
                return

    def mark_step_failed(self, plan: TaskPlan, step_id: str, error: str) -> None:
        """标记步骤为失败"""
        for step in plan.steps:
            if step.step_id == step_id:
                step.status = "failed"
                step.error = error
                return

    def get_plan_summary(self, plan: TaskPlan) -> str:
        """返回可读的计划摘要"""
        lines = []
        for step in plan.steps:
            status_icon = {"pending": "○", "in_progress": "●", "completed": "✓", "failed": "✗"}.get(step.status, "?")
            lines.append(f"{status_icon} {step.name}: {step.description}")
        return "\n".join(lines)


# ====================================================================
# PlanValidator — 计划可行性校验
# ====================================================================


class PlanValidator:
    """校验 TaskPlan 可行性：循环依赖、空步骤、缺失依赖、自引用。

    用法：
        result = PlanValidator().validate(plan)
        if not result.is_valid:
            logger.warning("Plan invalid: %s", result.errors)
    """

    def validate(self, plan: TaskPlan) -> ValidationResult:
        errors: list[str] = []

        if not plan.steps:
            errors.append("Plan has no steps")
            return ValidationResult(is_valid=False, errors=errors)

        step_ids = {s.step_id for s in plan.steps}

        for step in plan.steps:
            # 自引用检测
            if step.step_id in step.dependencies:
                errors.append(f"Step '{step.step_id}' depends on itself")

            # 缺失依赖检测
            for dep in step.dependencies:
                if dep not in step_ids:
                    errors.append(
                        f"Step '{step.step_id}' depends on missing step '{dep}'"
                    )

        # 循环依赖检测（DFS）
        cycle = self._detect_cycle(plan)
        if cycle:
            errors.append(f"Cycle detected: {' -> '.join(cycle)}")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def _detect_cycle(self, plan: TaskPlan) -> list[str]:
        """DFS 检测循环依赖，返回环上的 step_id 序列；无环返回 []。"""
        graph: dict[str, list[str]] = {s.step_id: list(s.dependencies) for s in plan.steps}
        visiting: set[str] = set()
        visited: set[str] = set()
        stack: list[str] = []

        def dfs(node: str) -> list[str]:
            if node in visiting:
                # 找到环：从 stack 中截取从 node 开始的部分
                idx = stack.index(node)
                return stack[idx:] + [node]
            if node in visited:
                return []
            visiting.add(node)
            stack.append(node)
            for dep in graph.get(node, []):
                cycle = dfs(dep)
                if cycle:
                    return cycle
            stack.pop()
            visiting.discard(node)
            visited.add(node)
            return []

        for node_id in graph:
            cycle = dfs(node_id)
            if cycle:
                return cycle
        return []


# ====================================================================
# PlanExecutor — 任务执行编排
# ====================================================================


class PlanExecutor:
    """按计划顺序执行步骤，支持失败重试与状态回调。

    不直接调用工具，而是通过注入的 ``StepExecutor`` 回调执行具体逻辑，
    保持与 ToolRegistry / ChapterService 解耦。

    用法：
        executor = PlanExecutor(step_callback=my_callback, max_retries=2)
        result = await executor.execute(plan)
    """

    def __init__(
        self,
        step_callback: StepExecutor,
        max_retries: int = 2,
        planner: TaskPlanner | None = None,
    ) -> None:
        self._callback = step_callback
        self._max_retries = max_retries
        self._planner = planner or TaskPlanner(llm_client=None)

    async def execute(
        self,
        plan: TaskPlan,
        on_step_complete: Callable[[PlanStep], None] | None = None,
    ) -> ExecutionResult:
        """按依赖顺序执行计划。

        Args:
            plan: 待执行计划（执行过程中会原地更新步骤状态）
            on_step_complete: 每步完成后的回调（可选）

        Returns:
            ExecutionResult：成功时含全部已完成 step_id；失败时含失败步骤 ID 与错误信息。
        """
        completed: list[str] = []

        while True:
            step = self._planner.get_next_step(plan)
            if step is None:
                break

            step.status = "in_progress"
            success, output = await self._execute_with_retry(step)

            if success:
                self._planner.mark_step_completed(plan, step.step_id)
                completed.append(step.step_id)
                if on_step_complete is not None:
                    on_step_complete(step)
            else:
                self._planner.mark_step_failed(plan, step.step_id, output)
                plan.status = "failed"
                return ExecutionResult(
                    success=False,
                    completed_step_ids=completed,
                    failed_step_id=step.step_id,
                    error=output,
                )

        plan.status = "completed"
        return ExecutionResult(success=True, completed_step_ids=completed)

    async def _execute_with_retry(self, step: PlanStep) -> tuple[bool, str]:
        """带重试的步骤执行。重试间隔按 0.5s * attempt 递增。"""
        import asyncio

        last_error = ""
        for attempt in range(self._max_retries + 1):
            try:
                success, output = await self._callback(step)
                if success:
                    return True, output
                last_error = output or "未知错误"
            except Exception as e:
                last_error = str(e)
                logger.warning(
                    "PlanExecutor step '%s' attempt %s failed: %s",
                    step.step_id,
                    attempt + 1,
                    e,
                )

            if attempt < self._max_retries:
                await asyncio.sleep(0.5 * (attempt + 1))

        return False, last_error
