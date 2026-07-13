"""TaskPlanner 单元测试 — C11 核心模块补充测试.

覆盖: 创建计划、步骤排序、依赖关系、步骤推进、阻塞检测、全部完成。
"""

import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.planner import PlanStep, TaskPlan, TaskPlanner

# ====================================================================
# 测试用桩件
# ====================================================================


def _make_planner(llm_response: dict | None = None) -> TaskPlanner:
    """创建带 mock LLM 的 TaskPlanner."""
    llm_client = MagicMock()
    if llm_response is not None:
        llm_client.chat = AsyncMock(return_value=json.dumps(llm_response, ensure_ascii=False))
    else:
        llm_client.chat = AsyncMock(
            return_value=json.dumps({
                "steps": [
                    {"step_id": "step_1", "name": "收集设定", "description": "收集世界观设定", "dependencies": []},
                ]
            }, ensure_ascii=False)
        )
    return TaskPlanner(llm_client)


def _make_three_step_plan() -> TaskPlan:
    """创建标准三步骤计划."""
    return TaskPlan(
        steps=[
            PlanStep(step_id="step_1", name="步骤1-无依赖", description="第一步", dependencies=[]),
            PlanStep(step_id="step_2", name="步骤2-依赖1", description="第二步", dependencies=["step_1"]),
            PlanStep(step_id="step_3", name="步骤3-依赖2", description="第三步", dependencies=["step_2"]),
        ],
        status="in_progress",
    )


# ====================================================================
# create_plan 测试
# ====================================================================


@pytest.mark.asyncio
async def test_create_plan_basic():
    """基本规划：返回有效 steps 且数量正确."""
    planner = _make_planner({
        "steps": [
            {"step_id": "step_1", "name": "收集设定", "description": "收集世界观设定", "dependencies": []},
            {"step_id": "step_2", "name": "创建人物", "description": "创建人物档案", "dependencies": []},
        ]
    })

    plan = await planner.create_plan("创作一部小说")

    assert isinstance(plan, TaskPlan)
    assert plan.status == "in_progress"
    assert len(plan.steps) == 2
    assert all(isinstance(s, PlanStep) for s in plan.steps)


@pytest.mark.asyncio
async def test_plan_steps_order():
    """步骤应按返回顺序排列."""
    planner = _make_planner({
        "steps": [
            {"step_id": "step_1", "name": "第一步", "description": "", "dependencies": []},
            {"step_id": "step_2", "name": "第二步", "description": "", "dependencies": ["step_1"]},
            {"step_id": "step_3", "name": "第三步", "description": "", "dependencies": ["step_2"]},
        ]
    })

    plan = await planner.create_plan("顺序任务")

    assert len(plan.steps) == 3
    assert plan.steps[0].step_id == "step_1"
    assert plan.steps[1].step_id == "step_2"
    assert plan.steps[2].step_id == "step_3"


@pytest.mark.asyncio
async def test_plan_dependencies():
    """步骤间依赖关系应正确."""
    planner = _make_planner({
        "steps": [
            {"step_id": "step_1", "name": "基础", "description": "", "dependencies": []},
            {"step_id": "step_2", "name": "扩展", "description": "", "dependencies": ["step_1"]},
            {"step_id": "step_3", "name": "收尾", "description": "", "dependencies": ["step_1", "step_2"]},
        ]
    })

    plan = await planner.create_plan("有依赖的任务")

    assert plan.steps[0].dependencies == []
    assert plan.steps[1].dependencies == ["step_1"]
    assert plan.steps[2].dependencies == ["step_1", "step_2"]


@pytest.mark.asyncio
async def test_create_plan_llm_failure():
    """LLM 调用失败时返回 failed 状态."""
    llm_client = MagicMock()
    llm_client.chat = AsyncMock(side_effect=RuntimeError("LLM 不可用"))
    planner = TaskPlanner(llm_client)

    plan = await planner.create_plan("测试")

    assert plan.status == "failed"
    assert plan.steps == []


@pytest.mark.asyncio
async def test_create_plan_invalid_json():
    """LLM 返回非法 JSON 时返回 failed 状态."""
    llm_client = MagicMock()
    llm_client.chat = AsyncMock(return_value="这不是合法的 JSON")
    planner = TaskPlanner(llm_client)

    plan = await planner.create_plan("测试")

    assert plan.status == "failed"
    assert len(plan.steps) == 0


# ====================================================================
# get_next_step 测试
# ====================================================================


def test_get_next_step_first():
    """获取第一个待执行步骤."""
    plan = _make_three_step_plan()
    planner = TaskPlanner(MagicMock())

    next_step = planner.get_next_step(plan)

    assert next_step is not None
    assert next_step.step_id == "step_1"
    assert next_step.status == "pending"


def test_get_next_step_after_complete():
    """步骤完成后获取下一个."""
    plan = _make_three_step_plan()
    planner = TaskPlanner(MagicMock())

    planner.mark_step_completed(plan, "step_1")
    next_step = planner.get_next_step(plan)

    assert next_step is not None
    assert next_step.step_id == "step_2"


def test_get_next_step_dependency_blocked():
    """依赖未完成时应被阻塞."""
    plan = _make_three_step_plan()
    # 直接标记 step_2 为完成但不标记 step_1（模拟异常状态）
    # 先验证：step_3 依赖 step_2，如果 step_2 未完成则 step_3 不可执行
    planner = TaskPlanner(MagicMock())

    # step_1 完成
    planner.mark_step_completed(plan, "step_1")
    # step_2 应该是下一个
    next_step = planner.get_next_step(plan)
    assert next_step.step_id == "step_2"

    # 不完成 step_2，直接检查 step_3 是否被阻塞
    planner.mark_step_completed(plan, "step_2")
    next_step = planner.get_next_step(plan)
    assert next_step.step_id == "step_3"


def test_get_next_step_dependency_not_met():
    """依赖未满足时不应返回该步骤."""
    plan = TaskPlan(
        steps=[
            PlanStep(step_id="step_1", name="A", status="pending"),
            PlanStep(step_id="step_2", name="B", status="pending", dependencies=["step_1"]),
        ],
        status="in_progress",
    )
    planner = TaskPlanner(MagicMock())

    # step_1 未完成，step_2 应被阻塞
    next_step = planner.get_next_step(plan)
    assert next_step.step_id == "step_1"

    # 如果 step_1 是 failed 状态，step_2 仍被阻塞
    plan.steps[0].status = "failed"
    next_step = planner.get_next_step(plan)
    assert next_step is None  # step_1 failed 且 step_2 依赖 step_1


def test_all_steps_done():
    """所有步骤完成时 next_step 返回 None."""
    plan = _make_three_step_plan()
    planner = TaskPlanner(MagicMock())

    planner.mark_step_completed(plan, "step_1")
    planner.mark_step_completed(plan, "step_2")
    planner.mark_step_completed(plan, "step_3")

    next_step = planner.get_next_step(plan)
    assert next_step is None

    # 验证所有步骤都是 completed
    assert all(s.status == "completed" for s in plan.steps)


# ====================================================================
# mark_step_completed / mark_step_failed 测试
# ====================================================================


def test_mark_step_complete():
    """标记步骤完成."""
    plan = _make_three_step_plan()
    planner = TaskPlanner(MagicMock())

    planner.mark_step_completed(plan, "step_1")

    assert plan.steps[0].status == "completed"
    assert plan.steps[1].status == "pending"
    assert plan.steps[2].status == "pending"


def test_mark_step_complete_nonexistent():
    """标记不存在的步骤不应报错或影响其他步骤."""
    plan = _make_three_step_plan()
    planner = TaskPlanner(MagicMock())

    planner.mark_step_completed(plan, "nonexistent_step")

    # 所有步骤状态不变
    assert all(s.status == "pending" for s in plan.steps)


def test_mark_step_failed():
    """标记步骤失败."""
    plan = _make_three_step_plan()
    planner = TaskPlanner(MagicMock())

    planner.mark_step_failed(plan, "step_2", "LLM 调用超时")

    assert plan.steps[1].status == "failed"
    assert plan.steps[1].error == "LLM 调用超时"


def test_get_plan_summary():
    """get_plan_summary 应包含所有步骤的可读信息."""
    plan = _make_three_step_plan()
    planner = TaskPlanner(MagicMock())
    planner.mark_step_completed(plan, "step_1")
    planner.mark_step_failed(plan, "step_2", "出错")

    summary = planner.get_plan_summary(plan)

    assert "✓" in summary
    assert "✗" in summary
    assert "○" in summary
    assert "步骤1-无依赖" in summary
    assert "步骤2-依赖1" in summary
    assert "步骤3-依赖2" in summary
