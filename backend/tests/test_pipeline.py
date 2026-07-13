import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.pipeline.context import PipelineContext, PipelineStatus, StepResult


def test_pipeline_context_creation():
    ctx = PipelineContext(novel_id="novel_1", chapter_id="ch_1")

    assert ctx.novel_id == "novel_1"
    assert ctx.chapter_id == "ch_1"
    assert ctx.chapter_index is None
    assert ctx.step_results == []
    assert ctx.data == {}
    assert ctx.status == PipelineStatus.PENDING
    assert ctx.total_tokens_used == 0


def test_pipeline_context_add_result():
    ctx = PipelineContext(novel_id="novel_1")

    result = StepResult(
        step_name="test_step",
        status="success",
        output={"key": "value"},
    )

    ctx.add_step_result(result)

    assert len(ctx.step_results) == 1
    assert ctx.step_results[0].step_name == "test_step"
    assert ctx.step_results[0].status == "success"


def test_step_result_success():
    result = StepResult(
        step_name="test_step",
        status="success",
        output={"key": "value"},
    )

    assert result.step_name == "test_step"
    assert result.status == "success"
    assert result.output == {"key": "value"}
    assert result.error is None
    assert result.duration_ms == 0


def test_step_result_failure():
    result = StepResult(
        step_name="test_step",
        status="failed",
        error="Something went wrong",
    )

    assert result.status == "failed"
    assert result.error == "Something went wrong"


def test_pipeline_context_data_storage():
    ctx = PipelineContext(novel_id="novel_1")
    ctx.set("key1", "value1")
    ctx.set("key2", {"nested": "value2"})

    assert ctx.get("key1") == "value1"
    assert ctx.get("key2")["nested"] == "value2"
    assert ctx.get("nonexistent", "default") == "default"


def test_step_result_with_metadata():
    result = StepResult(
        step_name="test_step",
        status="success",
        metadata={"model": "gpt-4", "tokens": 100},
    )

    assert result.metadata["model"] == "gpt-4"
    assert result.metadata["tokens"] == 100


def test_pipeline_status_enum():
    assert PipelineStatus.PENDING == "pending"
    assert PipelineStatus.RUNNING == "running"
    assert PipelineStatus.PAUSED == "paused"
    assert PipelineStatus.COMPLETED == "completed"
    assert PipelineStatus.FAILED == "failed"


def test_pipeline_context_default_values():
    ctx = PipelineContext(novel_id="novel_1")

    assert ctx.chapter_id is None
    assert ctx.chapter_index is None
    assert ctx.current_step == ""
    assert ctx.started_at is None
    assert ctx.completed_at is None
    assert ctx.retry_count == {}


def test_step_result_default_duration():
    result = StepResult(step_name="test", status="success")
    assert result.duration_ms == 0
    assert result.output is None
    assert result.error is None
    assert result.metadata == {}
