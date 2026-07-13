"""Sprint 4.2: 补全 AftermathPipeline 测试。

为 backend/engine/pipeline/aftermath.py 的 6 个 step + AftermathPipeline.run 补测试。
策略:步骤级单元测试为主 + 端到端 happy path + 容错性测试。
"""

import json
import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.pipeline.aftermath import (  # noqa: E402
    AftermathPipeline,
    CreateSnapshotStep,
    ExtractSummaryStep,
    ExtractTriplesStep,
    IndexVectorStep,
    UpdateForeshadowingStep,
    UpdateMemoryStep,
)
from engine.pipeline.context import PipelineContext  # noqa: E402

# ====================================================================
# Fixtures
# ====================================================================


@pytest.fixture
def ctx():
    return PipelineContext(novel_id="n1", chapter_id="c1", chapter_index=1)


@pytest.fixture
def llm_client():
    client = MagicMock()
    client.generate = AsyncMock(
        return_value=json.dumps(
            {
                "summary": "测试摘要",
                "key_events": ["事件A"],
                "characters_involved": ["角色A"],
                "locations": ["地点A"],
                "timeline_position": "第1章",
            },
            ensure_ascii=False,
        )
    )
    return client


@pytest.fixture
def prompt_manager():
    pm = MagicMock()
    pm.get_prompt = MagicMock(return_value="prompt")
    return pm


@pytest.fixture
def knowledge_repo():
    repo = MagicMock()
    repo.upsert_summary = MagicMock()
    repo.bulk_upsert_triples = MagicMock()
    return repo


@pytest.fixture
def memory_repo():
    repo = MagicMock()
    repo.get_clue_locks = MagicMock(return_value=[])
    repo.bulk_upsert_clues = MagicMock()
    repo.bulk_upsert_facts = MagicMock()
    repo.bulk_upsert_beats = MagicMock()
    return repo


@pytest.fixture
def vector_store():
    vs = MagicMock()
    vs.add_document = AsyncMock()
    return vs


# ====================================================================
# 1. ExtractSummaryStep 成功路径
# ====================================================================


async def test_extract_summary_step_success(llm_client, prompt_manager, knowledge_repo, ctx):
    step = ExtractSummaryStep(knowledge_repo, llm_client, prompt_manager)

    result = await step.execute(ctx, "章节正文")

    assert result.status == "success"
    assert result.output["summary"] == "测试摘要"
    assert "事件A" in result.output["key_events"]
    knowledge_repo.upsert_summary.assert_called_once()
    assert ctx.summary is not None
    assert ctx.summary.summary == "测试摘要"


# ====================================================================
# 2. ExtractSummaryStep 空 chapter_content
# ====================================================================


async def test_extract_summary_step_empty_content_skips_llm(llm_client, prompt_manager, knowledge_repo, ctx):
    step = ExtractSummaryStep(knowledge_repo, llm_client, prompt_manager)

    result = await step.execute(ctx, "")

    assert result.status == "success"
    assert result.output["summary"] is None
    llm_client.generate.assert_not_called()
    knowledge_repo.upsert_summary.assert_not_called()


# ====================================================================
# 3. ExtractSummaryStep LLM 返回非 JSON 降级
# ====================================================================


async def test_extract_summary_step_non_json_response_degrades(llm_client, prompt_manager, knowledge_repo, ctx):
    llm_client.generate = AsyncMock(return_value="这是一段纯文本摘要,不是 JSON")
    step = ExtractSummaryStep(knowledge_repo, llm_client, prompt_manager)

    result = await step.execute(ctx, "章节正文")

    assert result.status == "success"
    # 降级:用文本作为 summary,其他字段为空
    assert ctx.summary is not None
    assert ctx.summary.summary == "这是一段纯文本摘要,不是 JSON"
    assert ctx.summary.key_events == []


# ====================================================================
# 4. ExtractTriplesStep 成功路径
# ====================================================================


async def test_extract_triples_step_success(llm_client, prompt_manager, knowledge_repo, ctx):
    llm_client.generate = AsyncMock(
        return_value=json.dumps(
            [{"subject": "A", "predicate": "是", "object": "B", "confidence": 0.9}],
            ensure_ascii=False,
        )
    )
    step = ExtractTriplesStep(knowledge_repo, llm_client, prompt_manager)

    result = await step.execute(ctx, "章节正文")

    assert result.status == "success"
    assert result.output["triples_count"] == 1
    knowledge_repo.bulk_upsert_triples.assert_called_once()
    assert len(ctx.knowledge_triples) == 1
    assert ctx.knowledge_triples[0].subject == "A"


# ====================================================================
# 5. UpdateForeshadowingStep 无待处理 clue
# ====================================================================


async def test_update_foreshadowing_step_no_pending_clues(llm_client, prompt_manager, memory_repo, ctx):
    memory_repo.get_clue_locks = MagicMock(return_value=[])
    step = UpdateForeshadowingStep(memory_repo, llm_client, prompt_manager)

    result = await step.execute(ctx, "章节正文")

    assert result.status == "success"
    assert result.output["updated"] == 0
    llm_client.generate.assert_not_called()


# ====================================================================
# 6. UpdateMemoryStep 成功路径
# ====================================================================


async def test_update_memory_step_success(llm_client, prompt_manager, memory_repo, ctx):
    llm_client.generate = AsyncMock(
        return_value=json.dumps(
            {
                "facts": [
                    {"fact_type": "character", "key": "主角", "value": "唐凌轩"},
                ],
                "beats": [
                    {"beat_type": "action", "description": "战斗", "characters": ["主角"]},
                ],
            },
            ensure_ascii=False,
        )
    )
    step = UpdateMemoryStep(memory_repo, llm_client, prompt_manager)

    result = await step.execute(ctx, "章节正文")

    assert result.status == "success"
    assert result.output["facts_added"] == 1
    assert result.output["beats_added"] == 1
    memory_repo.bulk_upsert_facts.assert_called_once()
    memory_repo.bulk_upsert_beats.assert_called_once()
    assert len(ctx.fact_locks) == 1
    assert ctx.fact_locks[0].key == "主角"
    assert len(ctx.beat_locks) == 1


# ====================================================================
# 7. IndexVectorStep:chapter_content 或 chapter_id 为空时返回 indexed=False
# ====================================================================


async def test_index_vector_step_empty_content_returns_not_indexed(vector_store, ctx):
    step = IndexVectorStep(vector_store=vector_store)

    result = await step.execute(ctx, "")

    assert result.status == "success"
    assert result.output["indexed"] is False
    vector_store.add_document.assert_not_called()


async def test_index_vector_step_no_chapter_id_returns_not_indexed(vector_store):
    from engine.pipeline.context import PipelineContext

    ctx_no_id = PipelineContext(novel_id="n1", chapter_id=None, chapter_index=1)
    step = IndexVectorStep(vector_store=vector_store)

    result = await step.execute(ctx_no_id, "章节正文")

    assert result.status == "success"
    assert result.output["indexed"] is False


async def test_index_vector_step_with_vector_store(vector_store, ctx):
    step = IndexVectorStep(vector_store=vector_store)

    result = await step.execute(ctx, "章节正文")

    assert result.status == "success"
    assert result.output["indexed"] is True
    vector_store.add_document.assert_awaited_once()


# ====================================================================
# 8. CreateSnapshotStep 成功路径
# ====================================================================


async def test_create_snapshot_step_success(knowledge_repo, memory_repo, ctx):
    # 预设 ctx 中的 step 输出
    from domain.knowledge.chapter_summary import ChapterSummary
    from domain.knowledge.knowledge_triple import KnowledgeTriple
    from domain.memory.beat_lock import BeatLock
    from domain.memory.fact_lock import FactLock

    ctx.summary = ChapterSummary(novel_id="n1", chapter_id="c1", chapter_index=1, summary="摘要")
    ctx.fact_locks = [FactLock(novel_id="n1", key="主角", value="唐凌轩")]
    ctx.beat_locks = [BeatLock(novel_id="n1", chapter_id="c1", beat_type="action", description="战斗")]
    ctx.knowledge_triples = [KnowledgeTriple(novel_id="n1", subject="A", predicate="是", object="B")]

    step = CreateSnapshotStep(knowledge_repo, memory_repo)

    result = await step.execute(ctx, "章节正文")

    assert result.status == "success"
    assert result.output["snapshot_created"] is True
    assert ctx.snapshot is not None
    assert ctx.snapshot["summary"] == "摘要"
    assert len(ctx.snapshot["facts"]) == 1
    assert len(ctx.snapshot["beats"]) == 1
    assert len(ctx.snapshot["triples"]) == 1


# ====================================================================
# 9. AftermathPipeline.run 端到端 happy path
# ====================================================================


async def test_aftermath_pipeline_run_happy_path(llm_client, prompt_manager, knowledge_repo, memory_repo, vector_store, ctx):
    # LLM 调用顺序(UpdateForeshadowingStep 因无 pending_clues 提前返回,不调用 generate):
    # 1. ExtractSummary → summary_json
    # 2. ExtractTriples → triples_json
    # 3. UpdateMemory → memory_json
    summary_json = json.dumps(
        {"summary": "摘要", "key_events": [], "characters_involved": [], "locations": [], "timeline_position": ""},
        ensure_ascii=False,
    )
    triples_json = json.dumps([{"subject": "A", "predicate": "是", "object": "B"}], ensure_ascii=False)
    memory_json = json.dumps({"facts": [], "beats": []}, ensure_ascii=False)

    responses = [summary_json, triples_json, memory_json]
    call_count = [0]

    async def _mock_generate(prompt):
        idx = min(call_count[0], len(responses) - 1)
        result = responses[idx]
        call_count[0] += 1
        return result

    llm_client.generate = AsyncMock(side_effect=_mock_generate)

    pipeline = AftermathPipeline(
        knowledge_repo=knowledge_repo,
        memory_repo=memory_repo,
        llm_client=llm_client,
        prompt_manager=prompt_manager,
        vector_store=vector_store,
    )

    result_ctx = await pipeline.run(ctx, "章节正文")

    assert len(result_ctx.step_results) == 6
    for sr in result_ctx.step_results:
        assert sr.status == "success", f"step {sr.step_name} failed: {sr.error}"


# ====================================================================
# 10. AftermathPipeline.run 容错性:某步骤失败不阻塞后续
# ====================================================================


async def test_aftermath_pipeline_run_step_failure_does_not_block_subsequent(llm_client, prompt_manager, knowledge_repo, memory_repo, vector_store, ctx):
    # 让 ExtractSummaryStep 抛异常
    llm_client.generate = AsyncMock(side_effect=RuntimeError("LLM 服务不可用"))

    pipeline = AftermathPipeline(
        knowledge_repo=knowledge_repo,
        memory_repo=memory_repo,
        llm_client=llm_client,
        prompt_manager=prompt_manager,
        vector_store=vector_store,
    )

    result_ctx = await pipeline.run(ctx, "章节正文")

    assert len(result_ctx.step_results) == 6
    # 第一个步骤(ExtractSummaryStep)应该失败
    assert result_ctx.step_results[0].status == "failed"
    assert "LLM 服务不可用" in result_ctx.step_results[0].error
    # 后续步骤仍执行(不阻塞)
    # 注意:ExtractTriplesStep/UpdateForeshadowingStep/UpdateMemoryStep 也调用 llm_client.generate 会失败
    # 但 IndexVectorStep 与 CreateSnapshotStep 不依赖 LLM,应成功
    last_step = result_ctx.step_results[-1]
    assert last_step.status == "success"
    assert last_step.output["snapshot_created"] is True
