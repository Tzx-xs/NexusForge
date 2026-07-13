"""AftermathPipelineStep 适配器包装单元测试。

该适配器将 AftermathPipeline 包装为标准 PipelineStep，供 StoryPipeline 集成使用。
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.pipeline.aftermath import AftermathPipeline, AftermathPipelineStep
from engine.pipeline.context import PipelineContext, StepResult

# ====================================================================
# Fixtures
# ====================================================================

@pytest.fixture
def mock_aftermath_pipeline():
    """Mock AftermathPipeline.run() 返回带 step_results 的 PipelineContext。"""
    pipeline = MagicMock(spec=AftermathPipeline)
    pipeline.run = AsyncMock(return_value=PipelineContext(
        novel_id="novel_1",
        chapter_id="ch_1",
        chapter_index=3,
    ))
    return pipeline


@pytest.fixture
def adapter(mock_aftermath_pipeline):
    return AftermathPipelineStep(mock_aftermath_pipeline)


@pytest.fixture
def valid_context():
    """包含 generated_content 和 chapter_id 的有效 PipelineContext。"""
    ctx = PipelineContext(novel_id="novel_1", chapter_id="ch_1", chapter_index=3)
    ctx.set("generated_content", "这是第三章的正文内容。云泽站在星渊崖边。")
    ctx.set("chapter_id", "ch_1")
    return ctx


# ====================================================================
# execute — 成功路径
# ====================================================================

@pytest.mark.asyncio
async def test_aftermath_pipeline_step_execute(adapter, mock_aftermath_pipeline, valid_context):
    """执行成功返回 StepResult(status='success')。"""
    result = await adapter.execute(valid_context)

    assert isinstance(result, StepResult)
    assert result.status == "success"
    assert result.step_name == "aftermath_pipeline"

    output = result.output
    assert output["executed"] is True
    assert output["chapter_id"] == "ch_1"
    assert isinstance(output["step_count"], int)

    # 确认内部 aftermath pipeline 被调用
    mock_aftermath_pipeline.run.assert_awaited_once()
    run_args = mock_aftermath_pipeline.run.call_args
    inner_ctx, chapter_content = run_args.args
    assert chapter_content == "这是第三章的正文内容。云泽站在星渊崖边。"
    assert inner_ctx.novel_id == "novel_1"
    assert inner_ctx.chapter_id == "ch_1"


# ====================================================================
# execute — 缺失 content
# ====================================================================

@pytest.mark.asyncio
async def test_aftermath_pipeline_step_missing_content(adapter):
    """缺少 chapter_content 时跳过（返回 status='skipped'）。"""
    ctx = PipelineContext(novel_id="novel_1", chapter_id="ch_1")
    ctx.set("generated_content", "")
    ctx.set("chapter_id", "ch_1")

    result = await adapter.execute(ctx)

    assert result.status == "skipped"
    assert result.step_name == "aftermath_pipeline"
    assert result.output["reason"] is not None
    assert "missing" in result.output["reason"].lower()


@pytest.mark.asyncio
async def test_aftermath_pipeline_step_missing_chapter_id(adapter):
    """缺少 chapter_id 时跳过。"""
    ctx = PipelineContext(novel_id="novel_1")
    ctx.set("generated_content", "正文内容")
    # chapter_id 未设置
    result = await adapter.execute(ctx)
    assert result.status == "skipped"


# ====================================================================
# execute — 内部异常不阻塞
# ====================================================================

@pytest.mark.asyncio
async def test_aftermath_pipeline_step_exception(adapter, valid_context):
    """内部异常不阻塞，返回 status='success'（而非 failed）。"""
    adapter._inner.run = AsyncMock(side_effect=ValueError("内部处理失败"))

    result = await adapter.execute(valid_context)

    assert result.status == "success"  # 即使内部失败也标记成功
    assert result.output["executed"] is False
    assert "内部处理失败" in result.output["error"]


# ====================================================================
# rollback — no-op
# ====================================================================

@pytest.mark.asyncio
async def test_aftermath_pipeline_step_rollback(adapter, valid_context):
    """rollback 不抛异常，是安全的 no-op。"""
    try:
        await adapter.rollback(valid_context)
    except Exception as e:
        pytest.fail(f"rollback 不应抛出异常: {e}")


# ====================================================================
# execute — 参数透传
# ====================================================================

@pytest.mark.asyncio
async def test_aftermath_pipeline_step_passes_data(adapter, mock_aftermath_pipeline, valid_context):
    """验证 inner ctx.data 正确透传了外部 ctx.data。"""
    valid_context.set("extra_key", "extra_value")
    await adapter.execute(valid_context)

    inner_ctx = mock_aftermath_pipeline.run.call_args.args[0]
    assert inner_ctx.data.get("extra_key") == "extra_value"
    assert inner_ctx.novel_id == "novel_1"
    assert inner_ctx.chapter_index == 3
