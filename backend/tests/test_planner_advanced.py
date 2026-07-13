"""PlanValidator / PlanExecutor 单元测试 — Phase 2.3 Planner 模块完善。

覆盖：
- PlanValidator: 空计划 / 缺失依赖 / 自引用 / 循环依赖 / 合法计划
- TaskPlanner.revise_plan: 反馈为空 / LLM 成功 / LLM 失败
- PlanExecutor: 顺序执行成功 / 失败停止 / 重试机制 / 回调
"""
import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.planner import (
    ExecutionResult,
    PlanExecutor,
    PlanStep,
    PlanValidator,
    TaskPlan,
    TaskPlanner,
    ValidationResult,
)

# ====================================================================
# PlanValidator 测试
# ====================================================================


class TestPlanValidator:
    """PlanValidator 全路径覆盖。"""

    def _validator(self) -> PlanValidator:
        return PlanValidator()

    def test_empty_plan_invalid(self):
        """空步骤计划应判定为非法。"""
        plan = TaskPlan(steps=[])
        result = self._validator().validate(plan)
        assert result.is_valid is False
        assert "no steps" in result.errors[0].lower()

    def test_valid_plan_passes(self):
        """合法计划（无循环、依赖完整）应通过校验。"""
        plan = TaskPlan(
            steps=[
                PlanStep(step_id="step_1", name="A"),
                PlanStep(step_id="step_2", name="B", dependencies=["step_1"]),
                PlanStep(step_id="step_3", name="C", dependencies=["step_1", "step_2"]),
            ]
        )
        result = self._validator().validate(plan)
        assert result.is_valid is True
        assert result.errors == []

    def test_missing_dependency_detected(self):
        """依赖不存在的 step_id 应报错。"""
        plan = TaskPlan(
            steps=[
                PlanStep(step_id="step_1", name="A", dependencies=["ghost"]),
            ]
        )
        result = self._validator().validate(plan)
        assert result.is_valid is False
        assert any("ghost" in err for err in result.errors)

    def test_self_dependency_detected(self):
        """自引用依赖应报错。"""
        plan = TaskPlan(
            steps=[
                PlanStep(step_id="step_1", name="A", dependencies=["step_1"]),
            ]
        )
        result = self._validator().validate(plan)
        assert result.is_valid is False
        assert any("depends on itself" in err for err in result.errors)

    def test_cycle_detected(self):
        """循环依赖应被检测并报错。"""
        plan = TaskPlan(
            steps=[
                PlanStep(step_id="step_1", name="A", dependencies=["step_3"]),
                PlanStep(step_id="step_2", name="B", dependencies=["step_1"]),
                PlanStep(step_id="step_3", name="C", dependencies=["step_2"]),
            ]
        )
        result = self._validator().validate(plan)
        assert result.is_valid is False
        assert any("Cycle detected" in err for err in result.errors)

    def test_diamond_dependencies_pass(self):
        """钻石型依赖（A→B,C→D）合法。"""
        plan = TaskPlan(
            steps=[
                PlanStep(step_id="step_1", name="A"),
                PlanStep(step_id="step_2", name="B", dependencies=["step_1"]),
                PlanStep(step_id="step_3", name="C", dependencies=["step_1"]),
                PlanStep(step_id="step_4", name="D", dependencies=["step_2", "step_3"]),
            ]
        )
        result = self._validator().validate(plan)
        assert result.is_valid is True

    def test_validation_result_dataclass_fields(self):
        """ValidationResult 字段应完整。"""
        result = ValidationResult(is_valid=True, errors=[])
        assert result.is_valid is True
        assert result.errors == []


# ====================================================================
# TaskPlanner.revise_plan 测试
# ====================================================================


class TestRevisePlan:
    """TaskPlanner.revise_plan 多轮修正。"""

    @pytest.mark.asyncio
    async def test_empty_feedback_returns_original(self):
        """反馈为空时应直接返回原计划。"""
        planner = TaskPlanner(llm_client=MagicMock())
        original = TaskPlan(
            steps=[PlanStep(step_id="step_1", name="A")],
            status="in_progress",
        )
        result = await planner.revise_plan(original, "")
        assert result is original

    @pytest.mark.asyncio
    async def test_revise_plan_success_preserves_completed(self):
        """修正后已完成步骤应保留在前。"""
        llm_client = MagicMock()
        llm_client.chat = AsyncMock(
            return_value='{"steps": [{"step_id": "step_2", "name": "B", "description": "new", "dependencies": []}]}'
        )
        planner = TaskPlanner(llm_client=llm_client)

        original = TaskPlan(
            steps=[
                PlanStep(step_id="step_1", name="A", status="completed"),
                PlanStep(step_id="step_2", name="B", status="failed", error="旧错误"),
            ]
        )
        result = await planner.revise_plan(original, "重试 step_2")

        assert result.status == "in_progress"
        assert result.steps[0].step_id == "step_1"
        assert result.steps[0].status == "completed"  # 已完成保留
        assert result.steps[1].step_id == "step_2"
        assert result.steps[1].status == "pending"  # 新步骤重置为 pending

    @pytest.mark.asyncio
    async def test_revise_plan_llm_failure_returns_failed(self):
        """LLM 调用失败时返回 failed 状态，但保留原步骤。"""
        llm_client = MagicMock()
        llm_client.chat = AsyncMock(side_effect=RuntimeError("LLM 不可用"))
        planner = TaskPlanner(llm_client=llm_client)

        original = TaskPlan(
            steps=[PlanStep(step_id="step_1", name="A")],
        )
        result = await planner.revise_plan(original, "改一下")
        assert result.status == "failed"
        assert result.steps == original.steps


# ====================================================================
# PlanExecutor 测试
# ====================================================================


async def _stub_callback_always_success(step: PlanStep) -> tuple[bool, str]:
    """永远成功的桩 callback。"""
    return True, f"output_{step.step_id}"


async def _stub_callback_always_fail(step: PlanStep) -> tuple[bool, str]:
    """永远失败的桩 callback。"""
    return False, f"error_{step.step_id}"


async def _stub_callback_raise(step: PlanStep) -> tuple[bool, str]:
    """抛异常的桩 callback。"""
    raise RuntimeError(f"exception_{step.step_id}")


class TestPlanExecutor:
    """PlanExecutor 全路径覆盖。"""

    def _three_step_plan(self) -> TaskPlan:
        return TaskPlan(
            steps=[
                PlanStep(step_id="step_1", name="A"),
                PlanStep(step_id="step_2", name="B", dependencies=["step_1"]),
                PlanStep(step_id="step_3", name="C", dependencies=["step_2"]),
            ],
            status="in_progress",
        )

    @pytest.mark.asyncio
    async def test_execute_all_success(self):
        """三步顺序成功执行。"""
        executor = PlanExecutor(
            step_callback=_stub_callback_always_success,
            max_retries=0,
        )
        plan = self._three_step_plan()

        result = await executor.execute(plan)

        assert result.success is True
        assert result.completed_step_ids == ["step_1", "step_2", "step_3"]
        assert plan.status == "completed"
        assert all(s.status == "completed" for s in plan.steps)

    @pytest.mark.asyncio
    async def test_execute_failure_stops_pipeline(self):
        """步骤失败时停止后续执行。"""
        executor = PlanExecutor(
            step_callback=_stub_callback_always_fail,
            max_retries=0,
        )
        plan = self._three_step_plan()

        result = await executor.execute(plan)

        assert result.success is False
        assert result.failed_step_id == "step_1"
        assert result.error == "error_step_1"
        assert result.completed_step_ids == []
        assert plan.status == "failed"
        assert plan.steps[0].status == "failed"
        assert plan.steps[0].error == "error_step_1"
        assert plan.steps[1].status == "pending"  # 后续步骤未触发

    @pytest.mark.asyncio
    async def test_execute_exception_triggers_retry(self):
        """异常应触发重试，最终全部失败。"""
        call_count = {"n": 0}

        async def _flaky_callback(step: PlanStep) -> tuple[bool, str]:
            call_count["n"] += 1
            raise RuntimeError(f"attempt {call_count['n']}")

        executor = PlanExecutor(
            step_callback=_flaky_callback,
            max_retries=2,
        )
        plan = TaskPlan(steps=[PlanStep(step_id="step_1", name="A")])

        result = await executor.execute(plan)

        assert result.success is False
        # max_retries=2 → 总共 3 次调用
        assert call_count["n"] == 3
        assert "attempt 3" in result.error

    @pytest.mark.asyncio
    async def test_execute_retry_then_success(self):
        """前 N 次失败、最后一次成功。"""
        call_count = {"n": 0}

        async def _recovering_callback(step: PlanStep) -> tuple[bool, str]:
            call_count["n"] += 1
            if call_count["n"] < 3:
                return False, "transient error"
            return True, "ok"

        executor = PlanExecutor(
            step_callback=_recovering_callback,
            max_retries=3,
        )
        plan = TaskPlan(steps=[PlanStep(step_id="step_1", name="A")])

        result = await executor.execute(plan)

        assert result.success is True
        assert call_count["n"] == 3
        assert result.completed_step_ids == ["step_1"]

    @pytest.mark.asyncio
    async def test_step_complete_callback_invoked(self):
        """on_step_complete 回调应被每步调用。"""
        completed: list[str] = []
        executor = PlanExecutor(
            step_callback=_stub_callback_always_success,
            max_retries=0,
        )
        plan = self._three_step_plan()

        await executor.execute(plan, on_step_complete=lambda s: completed.append(s.step_id))

        assert completed == ["step_1", "step_2", "step_3"]

    @pytest.mark.asyncio
    async def test_executor_respects_dependencies(self):
        """依赖未完成时不可执行该步骤。"""
        executed: list[str] = []

        async def _track_callback(step: PlanStep) -> tuple[bool, str]:
            executed.append(step.step_id)
            return True, "ok"

        # step_2 依赖 step_1，但 step_1 状态预设为 failed
        plan = TaskPlan(
            steps=[
                PlanStep(step_id="step_1", name="A", status="failed"),
                PlanStep(step_id="step_2", name="B", dependencies=["step_1"]),
            ]
        )
        executor = PlanExecutor(step_callback=_track_callback, max_retries=0)

        result = await executor.execute(plan)

        # step_1 已 failed 不会重新执行；step_2 依赖未满足 → 直接结束
        assert result.success is True  # 没有可执行的步骤也算"完成"
        assert executed == []
        assert result.completed_step_ids == []

    @pytest.mark.asyncio
    async def test_execution_result_dataclass(self):
        """ExecutionResult 字段完整性。"""
        result = ExecutionResult(success=True, completed_step_ids=["a", "b"])
        assert result.success is True
        assert result.completed_step_ids == ["a", "b"]
        assert result.failed_step_id == ""
        assert result.error == ""
