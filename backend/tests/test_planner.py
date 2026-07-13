import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.planner import PlanStep, TaskPlan, TaskPlanner

# ====================================================================
# 测试1: create_plan 使用 LLM 返回正确的 TaskPlan
# ====================================================================


@pytest.mark.asyncio
async def test_create_plan_with_llm():
    llm_client = MagicMock()
    llm_client.chat = AsyncMock(return_value=json.dumps({
        "steps": [
            {"step_id": "step_1", "name": "收集设定", "description": "收集世界观设定", "dependencies": []},
            {"step_id": "step_2", "name": "创建人物", "description": "创建人物档案", "dependencies": ["step_1"]},
            {"step_id": "step_3", "name": "写大纲", "description": "规划卷大纲", "dependencies": ["step_2"]},
        ]
    }))

    planner = TaskPlanner(llm_client)
    plan = await planner.create_plan("创作一部玄幻小说第一章")

    assert isinstance(plan, TaskPlan)
    assert plan.status == "in_progress"
    assert len(plan.steps) == 3

    assert plan.steps[0].step_id == "step_1"
    assert plan.steps[0].name == "收集设定"
    assert plan.steps[0].description == "收集世界观设定"
    assert plan.steps[0].dependencies == []
    assert plan.steps[0].status == "pending"

    assert plan.steps[1].step_id == "step_2"
    assert plan.steps[1].dependencies == ["step_1"]

    assert plan.steps[2].step_id == "step_3"
    assert plan.steps[2].dependencies == ["step_2"]


# ====================================================================
# 测试2: get_next_step 返回第一个 pending 步骤
# ====================================================================


def test_get_next_step_returns_first_pending():
    plan = TaskPlan(
        steps=[
            PlanStep(step_id="step_1", name="步骤1", status="pending"),
            PlanStep(step_id="step_2", name="步骤2", status="pending", dependencies=["step_1"]),
            PlanStep(step_id="step_3", name="步骤3", status="pending", dependencies=["step_2"]),
        ],
        status="in_progress",
    )

    planner = TaskPlanner(MagicMock())
    next_step = planner.get_next_step(plan)

    assert next_step is not None
    assert next_step.step_id == "step_1"


# ====================================================================
# 测试3: mark_step_completed 后 get_next_step 返回下一步
# ====================================================================


def test_mark_step_completed_then_get_next():
    plan = TaskPlan(
        steps=[
            PlanStep(step_id="step_1", name="步骤1", status="pending"),
            PlanStep(step_id="step_2", name="步骤2", status="pending", dependencies=["step_1"]),
            PlanStep(step_id="step_3", name="步骤3", status="pending", dependencies=["step_2"]),
        ],
        status="in_progress",
    )

    planner = TaskPlanner(MagicMock())
    planner.mark_step_completed(plan, "step_1")

    # 确认步骤1已标记为完成
    assert plan.steps[0].status == "completed"

    # 下一步应为步骤2
    next_step = planner.get_next_step(plan)
    assert next_step is not None
    assert next_step.step_id == "step_2"


# ====================================================================
# 测试4: mark_step_failed 后 get_plan_summary 包含 ✗ 标记
# ====================================================================


def test_mark_step_failed_then_summary():
    plan = TaskPlan(
        steps=[
            PlanStep(step_id="step_1", name="收集设定", description="收集世界观设定", status="completed"),
            PlanStep(step_id="step_2", name="创建人物", description="创建人物档案", status="pending", dependencies=["step_1"]),
            PlanStep(step_id="step_3", name="写大纲", description="规划卷大纲", status="pending", dependencies=["step_2"]),
        ],
        status="in_progress",
    )

    planner = TaskPlanner(MagicMock())
    planner.mark_step_failed(plan, "step_2", "LLM 调用超时")

    assert plan.steps[1].status == "failed"
    assert plan.steps[1].error == "LLM 调用超时"

    summary = planner.get_plan_summary(plan)
    assert "✗" in summary
    assert "创建人物" in summary
    assert "收集设定" in summary
    assert "写大纲" in summary
