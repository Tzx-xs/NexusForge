"""GenerationPipeline 单元测试 — C11 核心模块补充测试.

覆盖: 锁获取、PipelineContext/StepResult 序列化、检查点保存/加载/can_resume。
"""

import os
import sys
import tempfile
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.pipeline.context import PipelineContext, PipelineStatus, StepResult
from engine.pipeline.recovery import PipelineRecoveryManager

# ====================================================================
# 锁获取测试（模拟 ChapterRepository.try_acquire_generation_lock）
# ====================================================================


class _StubChapterRepo:
    """模拟 ChapterRepository 的生成锁行为."""

    def __init__(self, lock_result: bool = True):
        self._lock_result = lock_result
        self._lock_call_count = 0
        self._last_args = None

    def try_acquire_generation_lock(self, novel_id: str, chapter_num: int) -> bool:
        self._lock_call_count += 1
        self._last_args = (novel_id, chapter_num)
        return self._lock_result

    def get_by_id(self, chapter_id: str):
        return None


class _AlwaysFalseLockRepo(_StubChapterRepo):
    """永远获取不到锁的仓库."""

    def __init__(self):
        super().__init__(lock_result=False)


def test_acquire_lock_success():
    """章节状态为 draft 时获取锁成功."""
    repo = _StubChapterRepo(lock_result=True)
    result = repo.try_acquire_generation_lock("novel_1", 1)

    assert result is True
    assert repo._lock_call_count == 1
    assert repo._last_args == ("novel_1", 1)


def test_acquire_lock_fail_already_generating():
    """章节已在生成中，锁获取失败."""
    repo = _AlwaysFalseLockRepo()
    result = repo.try_acquire_generation_lock("novel_1", 1)

    assert result is False
    assert repo._lock_call_count == 1


def test_acquire_lock_fail_completed_chapter():
    """已完成章节锁获取失败."""
    repo = _AlwaysFalseLockRepo()
    result = repo.try_acquire_generation_lock("novel_1", 5)

    assert result is False


def test_acquire_lock_different_chapters():
    """不同章节的锁互不影响."""
    repo = _StubChapterRepo(lock_result=True)

    assert repo.try_acquire_generation_lock("novel_1", 1) is True
    assert repo.try_acquire_generation_lock("novel_1", 2) is True
    assert repo.try_acquire_generation_lock("novel_2", 1) is True
    assert repo._lock_call_count == 3


# ====================================================================
# PipelineContext 序列化往返
# ====================================================================


def test_pipeline_context_to_dict_roundtrip():
    """PipelineContext 序列化为 dict 后能正确反序列化."""
    ctx = PipelineContext(
        novel_id="novel_1",
        chapter_id="ch_5",
        chapter_index=5,
        status=PipelineStatus.RUNNING,
        current_step="generating_content",
    )
    ctx.set("genre", "玄幻")
    ctx.set("target_words", 2000)
    ctx.total_tokens_used = 5000
    ctx.started_at = 1710000000.0
    ctx.retry_count = {"step_1": 1}

    data = ctx.to_dict()

    assert isinstance(data, dict)
    assert data["novel_id"] == "novel_1"
    assert data["chapter_id"] == "ch_5"
    assert data["status"] == "running"
    assert data["data"]["genre"] == "玄幻"
    assert data["total_tokens_used"] == 5000

    # 反序列化
    restored = PipelineContext.from_dict(data)
    assert restored.novel_id == ctx.novel_id
    assert restored.chapter_id == ctx.chapter_id
    assert restored.chapter_index == ctx.chapter_index
    assert restored.status == ctx.status
    assert restored.current_step == ctx.current_step
    assert restored.get("genre") == "玄幻"
    assert restored.get("target_words") == 2000
    assert restored.total_tokens_used == 5000
    assert restored.started_at == 1710000000.0
    assert restored.retry_count == {"step_1": 1}


def test_pipeline_context_to_dict_with_step_results():
    """包含 StepResult 列表时序列化往返正确."""
    ctx = PipelineContext(novel_id="n1")
    ctx.add_step_result(StepResult(step_name="step_1", status="success", output={"key": "val"}))
    ctx.add_step_result(StepResult(step_name="step_2", status="failed", error="some error"))

    data = ctx.to_dict()
    restored = PipelineContext.from_dict(data)

    assert len(restored.step_results) == 2
    assert restored.step_results[0].step_name == "step_1"
    assert restored.step_results[0].status == "success"
    assert restored.step_results[0].output == {"key": "val"}
    assert restored.step_results[1].step_name == "step_2"
    assert restored.step_results[1].status == "failed"
    assert restored.step_results[1].error == "some error"


def test_pipeline_context_from_dict_defaults():
    """空字典反序列化应使用默认值."""
    ctx = PipelineContext.from_dict({})

    assert ctx.novel_id == ""
    assert ctx.chapter_id is None
    assert ctx.status == PipelineStatus.PENDING
    assert ctx.current_step == ""
    assert ctx.data == {}
    assert ctx.step_results == []
    assert ctx.total_tokens_used == 0


# ====================================================================
# StepResult 序列化往返
# ====================================================================


def test_step_result_to_dict_roundtrip():
    """StepResult 序列化为 dict 后能正确反序列化."""
    result = StepResult(
        step_name="generate_content",
        status="success",
        duration_ms=1500,
        output={"word_count": 2000, "style": "玄幻"},
        metadata={"model": "gpt-4", "tokens": 3500},
    )

    data = result.to_dict()
    restored = StepResult.from_dict(data)

    assert restored.step_name == "generate_content"
    assert restored.status == "success"
    assert restored.duration_ms == 1500
    assert restored.output == {"word_count": 2000, "style": "玄幻"}
    assert restored.metadata == {"model": "gpt-4", "tokens": 3500}
    assert restored.error is None


def test_step_result_to_dict_with_error():
    """失败 StepResult 序列化往返正确."""
    result = StepResult(
        step_name="review",
        status="failed",
        error="LLM API timeout after 3 retries",
        duration_ms=30000,
    )

    data = result.to_dict()
    restored = StepResult.from_dict(data)

    assert restored.status == "failed"
    assert restored.error == "LLM API timeout after 3 retries"
    assert restored.duration_ms == 30000


def test_step_result_to_dict_defaults():
    """默认值的 StepResult 序列化往返正确."""
    result = StepResult(step_name="minimal", status="pending")

    data = result.to_dict()
    restored = StepResult.from_dict(data)

    assert restored.step_name == "minimal"
    assert restored.status == "pending"
    assert restored.duration_ms == 0
    assert restored.output is None
    assert restored.error is None
    assert restored.metadata == {}


# ====================================================================
# PipelineRecoveryManager 检查点测试
# ====================================================================


@pytest.fixture
def temp_checkpoint_dir():
    """使用临时目录存放检查点文件."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def test_checkpoint_save_and_load(temp_checkpoint_dir):
    """保存检查点后能正确加载."""
    mgr = PipelineRecoveryManager(storage_path=temp_checkpoint_dir)
    ctx = PipelineContext(
        novel_id="novel_cp_1",
        chapter_id="ch_3",
        chapter_index=3,
        status=PipelineStatus.RUNNING,
        current_step="generating_content",
    )
    ctx.set("outline", "第一章大纲")
    ctx.set("content_preview", "林渊推开门...")

    mgr.save_checkpoint(ctx, pipeline_name="generation")
    loaded = mgr.load_checkpoint("novel_cp_1", pipeline_name="generation")

    assert loaded is not None
    assert loaded.novel_id == "novel_cp_1"
    assert loaded.chapter_id == "ch_3"
    assert loaded.chapter_index == 3
    assert loaded.status == PipelineStatus.RUNNING
    assert loaded.current_step == "generating_content"
    assert loaded.get("outline") == "第一章大纲"
    assert loaded.get("content_preview") == "林渊推开门..."


def test_checkpoint_can_resume_exists(temp_checkpoint_dir):
    """检查点存在时 can_resume 返回 True."""
    mgr = PipelineRecoveryManager(storage_path=temp_checkpoint_dir)
    ctx = PipelineContext(novel_id="n1", status=PipelineStatus.RUNNING)

    mgr.save_checkpoint(ctx, pipeline_name="generation")
    assert mgr.can_resume("n1", pipeline_name="generation") is True


def test_checkpoint_can_resume_not_exists(temp_checkpoint_dir):
    """无检查点时 can_resume 返回 False."""
    mgr = PipelineRecoveryManager(storage_path=temp_checkpoint_dir)
    assert mgr.can_resume("nonexistent_novel") is False


def test_checkpoint_load_nonexistent(temp_checkpoint_dir):
    """加载不存在的检查点返回 None."""
    mgr = PipelineRecoveryManager(storage_path=temp_checkpoint_dir)
    loaded = mgr.load_checkpoint("ghost_novel")
    assert loaded is None


def test_checkpoint_overwrite(temp_checkpoint_dir):
    """覆盖写检查点后加载最新内容."""
    mgr = PipelineRecoveryManager(storage_path=temp_checkpoint_dir)

    ctx1 = PipelineContext(novel_id="n1", chapter_id="ch_1")
    ctx1.set("version", 1)
    mgr.save_checkpoint(ctx1)

    ctx2 = PipelineContext(novel_id="n1", chapter_id="ch_2")
    ctx2.set("version", 2)
    mgr.save_checkpoint(ctx2)

    loaded = mgr.load_checkpoint("n1")
    assert loaded.chapter_id == "ch_2"
    assert loaded.get("version") == 2


def test_checkpoint_composite_id(temp_checkpoint_dir):
    """load_checkpoint 支持 composite id 格式 (pipeline_name_novel_id)."""
    mgr = PipelineRecoveryManager(storage_path=temp_checkpoint_dir)
    ctx = PipelineContext(novel_id="n1", chapter_id="ch_1")
    mgr.save_checkpoint(ctx, pipeline_name="generation")

    loaded = mgr.load_checkpoint("generation_n1", pipeline_name="generation")
    assert loaded is not None
    assert loaded.novel_id == "n1"


def test_checkpoint_can_resume_composite_id(temp_checkpoint_dir):
    """can_resume 支持 composite id 格式."""
    mgr = PipelineRecoveryManager(storage_path=temp_checkpoint_dir)
    ctx = PipelineContext(novel_id="n2")
    mgr.save_checkpoint(ctx, pipeline_name="aftermath")

    assert mgr.can_resume("aftermath_n2", pipeline_name="aftermath") is True


def test_checkpoint_corrupted_file(temp_checkpoint_dir):
    """损坏的检查点文件加载返回 None."""
    mgr = PipelineRecoveryManager(storage_path=temp_checkpoint_dir)
    filepath = mgr._get_checkpoint_path("generation", "corrupt")
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("this is not valid json {{{")

    loaded = mgr.load_checkpoint("corrupt")
    assert loaded is None


# ====================================================================
# GenerationPipeline 子方法测试 (_run_step* / _run_aftermath)
# ====================================================================


@pytest.fixture
def pipeline_fixture():
    """创建 GenerationPipeline 实例，所有依赖皆为 Mock."""
    from application.engine.generation_pipeline import GenerationPipeline
    llm = MagicMock()
    pm = MagicMock()
    cb = MagicMock()
    cr = MagicMock()
    rr = MagicMock()
    ap = MagicMock()
    pipe = GenerationPipeline(
        llm_client=llm,
        prompt_manager=pm,
        context_builder=cb,
        chapter_repo=cr,
        review_repo=rr,
        aftermath_pipeline=ap,
        max_retries=2,
    )
    # Mock 内部步骤实例
    pipe._step1 = MagicMock()
    pipe._step2 = MagicMock()
    pipe._step3 = MagicMock()
    pipe._step4 = MagicMock()
    return pipe


def _async_step_result(success: bool, result: dict = None, error: str = ""):
    """返回 _retry_step 风格的 (success, result, error) 异步协程."""
    if result is None:
        result = {}
    return AsyncMock(return_value=(success, result, error))()


class _AsyncGenMock:
    """将列表包装为异步生成器，用于模拟 execute_stream."""

    def __init__(self, items: list):
        self._items = items

    def __aiter__(self):
        return self._aiter()

    async def _aiter(self):
        for item in self._items:
            yield item


# ====================================================================
# _run_step1_build_context
# ====================================================================


@pytest.mark.asyncio
async def test_run_step1_build_context_success(pipeline_fixture):
    """Step1 成功：应更新 pipeline_context 并返回 (True, '')."""
    pipe = pipeline_fixture
    pipe._step1.execute = AsyncMock(return_value=(True, {"generation_context": {"novel_title": "星渊"}}, ""))

    ctx: dict = {}
    success, error = await pipe._run_step1_build_context("ch_1", ctx)

    assert success is True
    assert error == ""
    assert ctx.get("generation_context") == {"novel_title": "星渊"}
    pipe._step1.execute.assert_awaited_once_with("ch_1", ctx)


@pytest.mark.asyncio
async def test_run_step1_build_context_failure(pipeline_fixture):
    """Step1 失败：不应更新 pipeline_context 并返回 (False, error)."""
    pipe = pipeline_fixture
    pipe._step1.execute = AsyncMock(return_value=(False, {}, "小说数据缺失"))

    ctx: dict = {"existing": "val"}
    success, error = await pipe._run_step1_build_context("ch_1", ctx)

    assert success is False
    assert error == "小说数据缺失"
    # context 不应被更新
    assert ctx == {"existing": "val"}


# ====================================================================
# _run_step2_generate_content_stream
# ====================================================================


@pytest.mark.asyncio
async def test_run_step2_generate_content_stream_events(pipeline_fixture):
    """流式生成：应正确转发 outline / token / content_complete / progress 事件."""
    pipe = pipeline_fixture
    pipe._step2.execute_stream = MagicMock(return_value=_AsyncGenMock([
        ("outline", "第一章：相遇"),
        ("token", "林渊推开门，"),
        ("token", "走进了庭院。"),
        ("content_complete", "林渊推开门，走进了庭院。"),
    ]))

    ctx: dict = {}
    events = []
    async for event in pipe._run_step2_generate_content_stream("ch_1", ctx):
        events.append(event)

    # 验证 pipeline_context 被更新
    assert ctx.get("outline") == "第一章：相遇"
    assert ctx.get("content") == "林渊推开门，走进了庭院。"
    assert ctx.get("word_count") == len("林渊推开门，走进了庭院。")

    # 验证 progress 事件
    progress_events = [e for e in events if e[0] == "progress"]
    assert len(progress_events) >= 1

    # 验证 token 事件
    token_events = [e for e in events if e[0] == "token"]
    assert len(token_events) == 2


@pytest.mark.asyncio
async def test_run_step2_generate_content_stream_cancel(pipeline_fixture):
    """流式生成被取消：应返回 error 事件."""
    pipe = pipeline_fixture
    pipe._cancel_flags["ch_1"] = True  # 设置取消标志

    events = []
    async for event in pipe._run_step2_generate_content_stream("ch_1", {}):
        events.append(event)

    assert len(events) == 1
    assert events[0][0] == "error"


@pytest.mark.asyncio
async def test_run_step2_generate_content_stream_error(pipeline_fixture):
    """流式生成遇到 error 事件：应转发 error 并返回."""
    pipe = pipeline_fixture
    pipe._step2.execute_stream = MagicMock(return_value=_AsyncGenMock([
        ("error", "LLM API 调用失败"),
    ]))

    events = []
    async for event in pipe._run_step2_generate_content_stream("ch_1", {}):
        events.append(event)

    assert len(events) == 1
    assert events[0][0] == "error"
    assert events[0][1] == "LLM API 调用失败"


# ====================================================================
# _run_step3_review
# ====================================================================


@pytest.mark.asyncio
async def test_run_step3_review_success(pipeline_fixture):
    """审查成功：应更新 pipeline_context 并返回 (True, '')."""
    pipe = pipeline_fixture
    pipe._step3.execute = AsyncMock(return_value=(
        True,
        {"review_result": {"total_score": 85, "grade": "A"}},
        "",
    ))

    ctx: dict = {}
    success, error = await pipe._run_step3_review("ch_1", ctx)

    assert success is True
    assert error == ""
    assert ctx.get("review_result") == {"total_score": 85, "grade": "A"}


@pytest.mark.asyncio
async def test_run_step3_review_skip(pipeline_fixture):
    """审查失败（可跳过）：应返回 (False, error)，context 中 review_result 为空."""
    pipe = pipeline_fixture
    pipe._step3.execute = AsyncMock(return_value=(False, {}, "LLM 超时"))

    ctx: dict = {"content": "test"}
    success, error = await pipe._run_step3_review("ch_1", ctx)

    assert success is False
    assert error == "LLM 超时"
    assert ctx.get("review_result") == {}


# ====================================================================
# _run_step4_save
# ====================================================================


@pytest.mark.asyncio
async def test_run_step4_save_success(pipeline_fixture):
    """保存成功：应返回 (True, result_data, '')."""
    pipe = pipeline_fixture
    pipe._step4.execute = AsyncMock(return_value=(
        True,
        {"chapter_id": "ch_1", "word_count": 500, "score": 0.85},
        "",
    ))

    success, save_result, error = await pipe._run_step4_save("ch_1", {})

    assert success is True
    assert error == ""
    assert save_result["chapter_id"] == "ch_1"
    assert save_result["word_count"] == 500


@pytest.mark.asyncio
async def test_run_step4_save_failure(pipeline_fixture):
    """保存失败：应返回 (False, {}, error)."""
    pipe = pipeline_fixture
    pipe._step4.execute = AsyncMock(return_value=(False, {}, "保存章节失败: 数据库错误"))

    success, save_result, error = await pipe._run_step4_save("ch_1", {})

    assert success is False
    assert error == "保存章节失败: 数据库错误"
    assert save_result == {}


# ====================================================================
# _run_aftermath
# ====================================================================


@pytest.mark.asyncio
async def test_run_aftermath_success(pipeline_fixture):
    """章后处理成功：应调用 aftermath_pipeline.run."""
    pipe = pipeline_fixture
    pipe.aftermath_pipeline.run = AsyncMock()

    chapter = MagicMock()
    chapter.novel_id = "novel_1"
    chapter.number = 5

    await pipe._run_aftermath("ch_1", {"content": "正文", "extra": "data"}, chapter)

    pipe.aftermath_pipeline.run.assert_awaited_once()
    call_args = pipe.aftermath_pipeline.run.call_args
    ctx_arg, content_arg = call_args[0]
    assert ctx_arg.novel_id == "novel_1"
    assert ctx_arg.chapter_id == "ch_1"
    assert ctx_arg.chapter_index == 5
    assert content_arg == "正文"
    assert ctx_arg.data.get("extra") == "data"


@pytest.mark.asyncio
async def test_run_aftermath_nonblocking_error(pipeline_fixture):
    """章后处理异常不应阻塞主流程."""
    pipe = pipeline_fixture
    pipe.aftermath_pipeline.run = AsyncMock(side_effect=RuntimeError("网络中断"))

    chapter = MagicMock()
    chapter.novel_id = "novel_1"
    chapter.number = 5

    # 不应抛出异常
    await pipe._run_aftermath("ch_1", {"content": "正文"}, chapter)

    pipe.aftermath_pipeline.run.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_aftermath_no_pipeline(pipeline_fixture):
    """aftermath_pipeline 为 None 时，应直接返回."""
    pipe = pipeline_fixture
    pipe.aftermath_pipeline = None

    chapter = MagicMock()
    chapter.novel_id = "novel_1"

    # 不应报错
    await pipe._run_aftermath("ch_1", {"content": "正文"}, chapter)
