"""unified_aftermath — 章后管线统一抽取（借鉴 PlotPilot 单次多产出）

将原有 4 步独立 LLM 调用合并为单次调用，产出 8 类结构化数据：
1. summary 章节摘要
2. key_events 关键事件
3. knowledge_triples 知识三元组
4. foreshadows 伏笔（新增+更新）
5. memory_facts 记忆事实
6. memory_beats 记忆节拍
7. causal_edges 因果边
8. character_mutations 人物状态突变
9. narrative_debts 叙事债务
10. tension_composite 多维张力

LLM 调用次数：1 次（vs 原 5 次），token 成本降一半以上。
"""
import json
import logging
from typing import Any

from domain.knowledge.chapter_summary import ChapterSummary
from domain.knowledge.knowledge_triple import KnowledgeTriple
from domain.memory.beat_lock import BeatLock
from domain.memory.clue_lock import ClueLock
from domain.memory.fact_lock import FactLock

from .aftermath import AftermathStep, CreateSnapshotStep, IndexVectorStep
from .context import PipelineContext, StepResult

logger = logging.getLogger(__name__)


# 统一抽取的 JSON Schema（用于提示词约束 LLM 输出）
UNIFIED_EXTRACTION_SCHEMA = """{
  "summary": "章节摘要（200字内）",
  "key_events": ["关键事件1", "关键事件2"],
  "characters_involved": ["涉及角色"],
  "locations": ["涉及地点"],
  "timeline_position": "时间线位置",
  "knowledge_triples": [
    {"subject": "", "predicate": "", "object": "", "confidence": 0.9}
  ],
  "foreshadows": {
    "new": [
      {"clue_type": "subtle", "title": "", "description": "", "related_characters": [], "urgency": 1}
    ],
    "updates": [
      {"clue_id": "", "new_status": "developing", "new_description": ""}
    ]
  },
  "memory_facts": [
    {"fact_type": "character", "key": "", "value": ""}
  ],
  "memory_beats": [
    {"beat_type": "action", "description": "", "significance": "major", "characters": []}
  ],
  "causal_edges": [
    {"source": "事件A", "target": "事件B", "edge_type": "causal"}
  ],
  "character_mutations": [
    {"character": "", "field": "", "old": "", "new": ""}
  ],
  "narrative_debts": [
    {"kind": "foreshadow", "description": "", "importance": "medium"}
  ],
  "tension_composite": 75
}"""


class UnifiedExtractionStep(AftermathStep):
    """统一抽取步骤 — 单次 LLM 调用产出 8 类结构化数据

    替代原有的 ExtractSummaryStep + ExtractTriplesStep + UpdateForeshadowingStep + UpdateMemoryStep
    LLM 调用次数：1 次（vs 原 5 次）
    """

    name = "unified_extract"

    def __init__(self, knowledge_repo, memory_repo, llm_client, prompt_manager):
        self.knowledge_repo = knowledge_repo
        self.memory_repo = memory_repo
        self.llm_client = llm_client
        self.prompt_manager = prompt_manager

    async def execute(self, ctx: PipelineContext, chapter_content: str) -> StepResult:
        if not chapter_content:
            return StepResult.skip_step(step_name=self.name, reason="empty content")

        try:
            # 构建提示词：内容 + schema 约束 + 已有待更新伏笔
            pending_clues = []
            try:
                pending_clues = self.memory_repo.get_clue_locks(
                    ctx.novel_id, statuses=["planted", "developing"]
                )
            except Exception:
                pass

            prompt = self._build_prompt(chapter_content, ctx, pending_clues)

            # 单次 LLM 调用
            response = await self.llm_client.generate(prompt)

            # 解析 JSON（容错）
            data = self._parse_json(response)

            # 持久化各产出
            summary = self._persist_summary(data, ctx)
            triples = self._persist_triples(data, ctx)
            facts, beats = self._persist_memory(data, ctx)
            self._persist_foreshadows(data, ctx, pending_clues)

            # 写入 ctx 供后续步骤使用
            ctx.summary = summary
            ctx.knowledge_triples = triples
            ctx.fact_locks = facts
            ctx.beat_locks = beats

            return StepResult(
                step_name=self.name,
                status="success",
                output={
                    "summary": data.get("summary"),
                    "key_events": data.get("key_events", []),
                    "knowledge_triples": data.get("knowledge_triples", []),
                    "foreshadows": data.get("foreshadows", {}),
                    "memory_facts": data.get("memory_facts", []),
                    "memory_beats": data.get("memory_beats", []),
                    "causal_edges": data.get("causal_edges", []),
                    "character_mutations": data.get("character_mutations", []),
                    "narrative_debts": data.get("narrative_debts", []),
                    "tension_composite": data.get("tension_composite"),
                },
            )
        except Exception as e:
            logger.exception("Unified extraction failed")
            return StepResult(step_name=self.name, status="failed", error=str(e))

    def _build_prompt(self, content: str, ctx: PipelineContext, pending_clues: list) -> str:
        """构建统一抽取提示词"""
        clues_text = ""
        if pending_clues:
            clues_text = "\n".join(
                f"- id={c.id} title={c.title} status={c.status}" for c in pending_clues
            )

        # 优先用 prompt_manager 的模板，降级到内联
        try:
            return self.prompt_manager.get_prompt(
                "aftermath/unified_extraction",
                {
                    "content": content,
                    "chapter_number": ctx.chapter_index,
                    "schema": UNIFIED_EXTRACTION_SCHEMA,
                    "pending_clues": clues_text,
                },
            )
        except Exception:
            # 内联提示词（prompt 模板不存在时降级）
            return f"""请分析以下章节内容，按 JSON Schema 返回结构化结果。

章节内容：
{content[:8000]}

待更新伏笔：
{clues_text or "（无）"}

返回 JSON（严格遵循 schema，不要多余说明）：
{UNIFIED_EXTRACTION_SCHEMA}"""

    def _parse_json(self, response: str) -> dict:
        """解析 LLM 返回的 JSON（容错）"""
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            # 尝试提取 JSON 块
            import re
            match = re.search(r'\{[\s\S]*\}', response)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            logger.warning("Unified extraction JSON parse failed, returning empty")
            return {}

    def _persist_summary(self, data: dict, ctx: PipelineContext):
        """持久化摘要"""
        if not data.get("summary"):
            return None
        try:
            summary = ChapterSummary(
                novel_id=ctx.novel_id,
                chapter_id=ctx.chapter_id or "",
                chapter_index=ctx.chapter_index or 0,
                summary=data.get("summary", ""),
                key_events=data.get("key_events", []),
                characters_involved=data.get("characters_involved", []),
                locations=data.get("locations", []),
                timeline_position=data.get("timeline_position", ""),
            )
            self.knowledge_repo.upsert_summary(summary)
            return summary
        except Exception as e:
            logger.warning("Summary persist failed: %s", e)
            return None

    def _persist_triples(self, data: dict, ctx: PipelineContext):
        """持久化三元组"""
        triples_data = data.get("knowledge_triples", [])
        if not triples_data:
            return []
        try:
            triples = [
                KnowledgeTriple(
                    novel_id=ctx.novel_id,
                    subject=t.get("subject", ""),
                    predicate=t.get("predicate", ""),
                    object=t.get("object", ""),
                    confidence=t.get("confidence", 0.8),
                    source_chapter_id=ctx.chapter_id,
                )
                for t in triples_data
            ]
            if triples:
                self.knowledge_repo.bulk_upsert_triples(triples)
            return triples
        except Exception as e:
            logger.warning("Triples persist failed: %s", e)
            return []

    def _persist_memory(self, data: dict, ctx: PipelineContext):
        """持久化记忆事实与节拍"""
        facts = []
        beats = []
        try:
            for fact_data in data.get("memory_facts", []):
                facts.append(FactLock(
                    novel_id=ctx.novel_id,
                    fact_type=fact_data.get("fact_type", "character"),
                    key=fact_data.get("key", ""),
                    value=fact_data.get("value", ""),
                    locked_at_chapter=ctx.chapter_index,
                    is_immutable=True,
                    source=f"chapter_{ctx.chapter_index}",
                ))
            if facts:
                self.memory_repo.bulk_upsert_facts(facts)

            for beat_data in data.get("memory_beats", []):
                beats.append(BeatLock(
                    novel_id=ctx.novel_id,
                    chapter_id=ctx.chapter_id or "",
                    chapter_index=ctx.chapter_index or 0,
                    beat_type=beat_data.get("beat_type", "action"),
                    description=beat_data.get("description", ""),
                    significance=beat_data.get("significance", "major"),
                    characters=beat_data.get("characters", []),
                ))
            if beats:
                self.memory_repo.bulk_upsert_beats(beats)
        except Exception as e:
            logger.warning("Memory persist failed: %s", e)
        return facts, beats

    def _persist_foreshadows(self, data: dict, ctx: PipelineContext, pending_clues: list):
        """持久化伏笔（新增+更新）"""
        try:
            foreshadows = data.get("foreshadows", {})

            # 更新现有伏笔
            for update in foreshadows.get("updates", []):
                clue_id = update.get("clue_id")
                if clue_id:
                    clue = next((c for c in pending_clues if c.id == clue_id), None)
                    if clue:
                        clue.status = update.get("new_status", clue.status)
                        clue.description = update.get("new_description", clue.description)
                        self.memory_repo.bulk_upsert_clues([clue])

            # 新增伏笔
            for clue_data in foreshadows.get("new", []):
                new_clue = ClueLock(
                    novel_id=ctx.novel_id,
                    clue_type=clue_data.get("clue_type", "subtle"),
                    title=clue_data.get("title", ""),
                    description=clue_data.get("description", ""),
                    status="planted",
                    planted_chapter=ctx.chapter_index,
                    related_characters=clue_data.get("related_characters", []),
                    urgency=clue_data.get("urgency", 1),
                )
                self.memory_repo.bulk_upsert_clues([new_clue])
        except Exception as e:
            logger.warning("Foreshadows persist failed: %s", e)


class UnifiedAftermathPipeline:
    """统一章后管线 — 单次 LLM 调用 + 向量索引 + 快照

    LLM 调用次数：1 次（vs 原 AftermathPipeline 的 5 次）

    步骤：
    1. unified_extract  统一抽取（单次 LLM 调用产出 8 类数据）
    2. index_vector     向量索引
    3. create_snapshot  快照
    """

    def __init__(
        self,
        knowledge_repo,
        memory_repo,
        llm_client,
        prompt_manager,
        vector_store=None,
        chapter_repo=None,
        snapshot_repo=None,
    ):
        self.steps: list[AftermathStep] = [
            UnifiedExtractionStep(knowledge_repo, memory_repo, llm_client, prompt_manager),
            IndexVectorStep(vector_store),
            CreateSnapshotStep(knowledge_repo, memory_repo, chapter_repo, snapshot_repo),
        ]

    async def run(self, ctx: PipelineContext, chapter_content: str) -> PipelineContext:
        """执行统一章后管线"""
        logger.info("Unified aftermath pipeline started for chapter %s", ctx.chapter_index)

        for step in self.steps:
            try:
                result = await step.execute(ctx, chapter_content)
                ctx.add_step_result(result)
                if result.failed:
                    logger.warning("Unified aftermath step failed: %s, continuing...", step.name)
            except Exception as e:
                logger.exception("Unified aftermath step exception: %s", step.name)
                ctx.add_step_result(StepResult(step_name=step.name, status="failed", error=str(e)))

        logger.info("Unified aftermath pipeline completed for chapter %s", ctx.chapter_index)
        return ctx
