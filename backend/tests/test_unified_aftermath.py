"""章后管线统一抽取测试

验证 UnifiedExtractionStep 单次 LLM 调用产出 8 类结构化数据：
1. summary 章节摘要
2. key_events 关键事件
3. knowledge_triples 知识三元组
4. foreshadows 伏笔（新增+更新）
5. memory_facts 记忆事实
6. memory_beats 记忆节拍
7. causal_edges 因果边
8. character_mutations 人物状态突变
9. narrative_debts 叙事债务
"""
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from engine.pipeline.context import PipelineContext
from engine.pipeline.unified_aftermath import (
    UnifiedExtractionStep,
    UnifiedAftermathPipeline,
)


# ─── 测试 fixtures ──────────────────────────────────────────────────
MOCK_LLM_RESPONSE = json.dumps({
    "summary": "林墨在密室中发现古卷，触发了血脉觉醒。",
    "key_events": [
        "林墨进入密室",
        "发现古卷",
        "血脉觉醒",
    ],
    "characters_involved": ["林墨"],
    "locations": ["密室"],
    "timeline_position": "第三日黄昏",
    "knowledge_triples": [
        {"subject": "林墨", "predicate": "拥有", "object": "古卷", "confidence": 0.9},
        {"subject": "古卷", "predicate": "触发", "object": "血脉觉醒", "confidence": 0.95},
    ],
    "foreshadows": {
        "new": [
            {
                "clue_type": "subtle",
                "title": "古卷上的未知符号",
                "description": "古卷边缘有未辨认的符号",
                "related_characters": ["林墨"],
                "urgency": 2,
            },
        ],
        "updates": [
            {
                "clue_id": "clue_001",
                "new_status": "developing",
                "new_description": "血脉觉醒初步显现",
            },
        ],
    },
    "memory_facts": [
        {"fact_type": "character", "key": "林墨.血脉", "value": "已觉醒"},
    ],
    "memory_beats": [
        {"beat_type": "revelation", "description": "血脉觉醒", "significance": "major", "characters": ["林墨"]},
    ],
    "causal_edges": [
        {"source": "进入密室", "target": "发现古卷", "edge_type": "causal"},
        {"source": "发现古卷", "target": "血脉觉醒", "edge_type": "causal"},
    ],
    "character_mutations": [
        {"character": "林墨", "field": "血脉状态", "old": "未觉醒", "new": "已觉醒"},
    ],
    "narrative_debts": [
        {"kind": "foreshadow", "description": "古卷符号含义未解", "importance": "high"},
    ],
    "tension_composite": 78,
})


@pytest.fixture
def mock_repos():
    """模拟所有仓储"""
    return {
        "knowledge_repo": MagicMock(),
        "memory_repo": MagicMock(),
        "llm_client": AsyncMock(),
        "prompt_manager": MagicMock(),
        "vector_store": AsyncMock(),
        "chapter_repo": MagicMock(),
        "snapshot_repo": MagicMock(),
    }


@pytest.fixture
def pipeline_ctx():
    return PipelineContext(
        novel_id="novel_001",
        chapter_id="chap_001",
        chapter_index=5,
    )


# ═══════════════════════════════════════════════════════════════════
# 测试用例
# ═══════════════════════════════════════════════════════════════════
class TestUnifiedExtractionStep:
    """单次 LLM 调用产出 8 类数据"""

    @pytest.mark.asyncio
    async def test_single_llm_call_produces_all_outputs(self, mock_repos, pipeline_ctx):
        """单次 LLM 调用应产出全部 8 类结构化数据"""
        mock_repos["llm_client"].generate.return_value = MOCK_LLM_RESPONSE

        step = UnifiedExtractionStep(
            knowledge_repo=mock_repos["knowledge_repo"],
            memory_repo=mock_repos["memory_repo"],
            llm_client=mock_repos["llm_client"],
            prompt_manager=mock_repos["prompt_manager"],
        )

        result = await step.execute(pipeline_ctx, "林墨走进密室...")

        assert result.status == "success"
        # 验证 LLM 只被调用一次
        assert mock_repos["llm_client"].generate.call_count == 1

        # 验证 8 类产出都存在
        output = result.output
        assert "summary" in output
        assert "key_events" in output
        assert "knowledge_triples" in output
        assert "foreshadows" in output
        assert "memory_facts" in output
        assert "memory_beats" in output
        assert "causal_edges" in output
        assert "character_mutations" in output
        assert "narrative_debts" in output
        assert "tension_composite" in output

    @pytest.mark.asyncio
    async def test_persists_summary_to_knowledge_repo(self, mock_repos, pipeline_ctx):
        """摘要应持久化到 knowledge_repo"""
        mock_repos["llm_client"].generate.return_value = MOCK_LLM_RESPONSE

        step = UnifiedExtractionStep(
            knowledge_repo=mock_repos["knowledge_repo"],
            memory_repo=mock_repos["memory_repo"],
            llm_client=mock_repos["llm_client"],
            prompt_manager=mock_repos["prompt_manager"],
        )

        await step.execute(pipeline_ctx, "内容...")

        mock_repos["knowledge_repo"].upsert_summary.assert_called_once()
        summary = mock_repos["knowledge_repo"].upsert_summary.call_args[0][0]
        assert summary.summary == "林墨在密室中发现古卷，触发了血脉觉醒。"

    @pytest.mark.asyncio
    async def test_persists_triples(self, mock_repos, pipeline_ctx):
        """三元组应批量持久化"""
        mock_repos["llm_client"].generate.return_value = MOCK_LLM_RESPONSE

        step = UnifiedExtractionStep(
            knowledge_repo=mock_repos["knowledge_repo"],
            memory_repo=mock_repos["memory_repo"],
            llm_client=mock_repos["llm_client"],
            prompt_manager=mock_repos["prompt_manager"],
        )

        await step.execute(pipeline_ctx, "内容...")

        mock_repos["knowledge_repo"].bulk_upsert_triples.assert_called_once()
        triples = mock_repos["knowledge_repo"].bulk_upsert_triples.call_args[0][0]
        assert len(triples) == 2

    @pytest.mark.asyncio
    async def test_persists_facts_and_beats(self, mock_repos, pipeline_ctx):
        """记忆事实与节拍应持久化"""
        mock_repos["llm_client"].generate.return_value = MOCK_LLM_RESPONSE

        step = UnifiedExtractionStep(
            knowledge_repo=mock_repos["knowledge_repo"],
            memory_repo=mock_repos["memory_repo"],
            llm_client=mock_repos["llm_client"],
            prompt_manager=mock_repos["prompt_manager"],
        )

        await step.execute(pipeline_ctx, "内容...")

        mock_repos["memory_repo"].bulk_upsert_facts.assert_called_once()
        mock_repos["memory_repo"].bulk_upsert_beats.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_malformed_json(self, mock_repos, pipeline_ctx):
        """LLM 返回非 JSON 时应降级为空结果，不抛异常"""
        mock_repos["llm_client"].generate.return_value = "这不是JSON"

        step = UnifiedExtractionStep(
            knowledge_repo=mock_repos["knowledge_repo"],
            memory_repo=mock_repos["memory_repo"],
            llm_client=mock_repos["llm_client"],
            prompt_manager=mock_repos["prompt_manager"],
        )

        result = await step.execute(pipeline_ctx, "内容...")

        # 应返回 success 但产出为空
        assert result.status == "success"
        assert result.output["summary"] is None
        assert result.output["knowledge_triples"] == []

    @pytest.mark.asyncio
    async def test_empty_content_skips(self, mock_repos, pipeline_ctx):
        """空内容应跳过 LLM 调用"""
        step = UnifiedExtractionStep(
            knowledge_repo=mock_repos["knowledge_repo"],
            memory_repo=mock_repos["memory_repo"],
            llm_client=mock_repos["llm_client"],
            prompt_manager=mock_repos["prompt_manager"],
        )

        result = await step.execute(pipeline_ctx, "")

        assert result.status == "skipped"
        mock_repos["llm_client"].generate.assert_not_called()


class TestUnifiedAftermathPipeline:
    """统一章后管线整体测试"""

    @pytest.mark.asyncio
    async def test_pipeline_uses_single_llm_call(self, mock_repos, pipeline_ctx):
        """整个管线应只调用 LLM 一次（vs 旧的 5 次）"""
        mock_repos["llm_client"].generate.return_value = MOCK_LLM_RESPONSE

        pipeline = UnifiedAftermathPipeline(
            knowledge_repo=mock_repos["knowledge_repo"],
            memory_repo=mock_repos["memory_repo"],
            llm_client=mock_repos["llm_client"],
            prompt_manager=mock_repos["prompt_manager"],
            vector_store=mock_repos["vector_store"],
            chapter_repo=mock_repos["chapter_repo"],
            snapshot_repo=mock_repos["snapshot_repo"],
        )

        await pipeline.run(pipeline_ctx, "章节内容...")

        # 核心：LLM 只调用一次
        assert mock_repos["llm_client"].generate.call_count == 1

    @pytest.mark.asyncio
    async def test_pipeline_still_indexes_vector(self, mock_repos, pipeline_ctx):
        """向量索引仍应执行"""
        mock_repos["llm_client"].generate.return_value = MOCK_LLM_RESPONSE

        pipeline = UnifiedAftermathPipeline(
            knowledge_repo=mock_repos["knowledge_repo"],
            memory_repo=mock_repos["memory_repo"],
            llm_client=mock_repos["llm_client"],
            prompt_manager=mock_repos["prompt_manager"],
            vector_store=mock_repos["vector_store"],
        )

        await pipeline.run(pipeline_ctx, "章节内容...")

        mock_repos["vector_store"].add_document.assert_called_once()

    @pytest.mark.asyncio
    async def test_pipeline_creates_snapshot(self, mock_repos, pipeline_ctx):
        """快照仍应创建"""
        mock_repos["llm_client"].generate.return_value = MOCK_LLM_RESPONSE

        pipeline = UnifiedAftermathPipeline(
            knowledge_repo=mock_repos["knowledge_repo"],
            memory_repo=mock_repos["memory_repo"],
            llm_client=mock_repos["llm_client"],
            prompt_manager=mock_repos["prompt_manager"],
            snapshot_repo=mock_repos["snapshot_repo"],
        )

        await pipeline.run(pipeline_ctx, "章节内容...")

        mock_repos["snapshot_repo"].create.assert_called_once()

    @pytest.mark.asyncio
    async def test_pipeline_step_count(self, mock_repos, pipeline_ctx):
        """管线应有 3 步：unified_extract + index_vector + create_snapshot"""
        mock_repos["llm_client"].generate.return_value = MOCK_LLM_RESPONSE

        pipeline = UnifiedAftermathPipeline(
            knowledge_repo=mock_repos["knowledge_repo"],
            memory_repo=mock_repos["memory_repo"],
            llm_client=mock_repos["llm_client"],
            prompt_manager=mock_repos["prompt_manager"],
        )

        await pipeline.run(pipeline_ctx, "内容...")

        # 3 步：unified_extract + index_vector + create_snapshot
        assert len(pipeline_ctx.step_results) == 3
        step_names = [r.step_name for r in pipeline_ctx.step_results]
        assert "unified_extract" in step_names
        assert "index_vector" in step_names
        assert "create_snapshot" in step_names
