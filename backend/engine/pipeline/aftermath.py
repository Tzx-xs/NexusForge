import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from domain.knowledge.chapter_summary import ChapterSummary
from domain.knowledge.knowledge_triple import KnowledgeTriple
from domain.memory.beat_lock import BeatLock
from domain.memory.clue_lock import ClueLock
from domain.memory.fact_lock import FactLock

from .base import PipelineStep
from .context import PipelineContext, StepResult

logger = logging.getLogger(__name__)


class AftermathStep(ABC):
    name: str = ""

    @abstractmethod
    async def execute(self, ctx: PipelineContext, chapter_content: str) -> StepResult:
        pass


class ExtractSummaryStep(AftermathStep):
    name = "extract_summary"

    def __init__(self, knowledge_repo, llm_client, prompt_manager):
        self.knowledge_repo = knowledge_repo
        self.llm_client = llm_client
        self.prompt_manager = prompt_manager

    async def execute(self, ctx: PipelineContext, chapter_content: str) -> StepResult:
        try:
            if not chapter_content:
                return StepResult(step_name=self.name, status="success", output={"summary": None})

            prompt = self.prompt_manager.get_prompt(
                "aftermath/summary_extraction", {"content": chapter_content, "chapter_number": ctx.chapter_index}
            )

            response = await self.llm_client.generate(prompt)

            try:
                result = json.loads(response)
            except json.JSONDecodeError:
                result = {
                    "summary": response,
                    "key_events": [],
                    "characters_involved": [],
                    "locations": [],
                    "timeline_position": "",
                }

            summary = ChapterSummary(
                novel_id=ctx.novel_id,
                chapter_id=ctx.chapter_id or "",
                chapter_index=ctx.chapter_index or 0,
                summary=result.get("summary", ""),
                key_events=result.get("key_events", []),
                characters_involved=result.get("characters_involved", []),
                locations=result.get("locations", []),
                timeline_position=result.get("timeline_position", ""),
            )

            self.knowledge_repo.upsert_summary(summary)
            ctx.summary = summary

            return StepResult(
                step_name=self.name,
                status="success",
                output={"summary": summary.summary, "key_events": summary.key_events},
            )
        except Exception as e:
            logger.exception("Summary extraction failed")
            return StepResult(step_name=self.name, status="failed", error=str(e))


class ExtractTriplesStep(AftermathStep):
    name = "extract_triples"

    def __init__(self, knowledge_repo, llm_client, prompt_manager):
        self.knowledge_repo = knowledge_repo
        self.llm_client = llm_client
        self.prompt_manager = prompt_manager

    async def execute(self, ctx: PipelineContext, chapter_content: str) -> StepResult:
        try:
            if not chapter_content:
                return StepResult(step_name=self.name, status="success", output={"triples": []})

            prompt = self.prompt_manager.get_prompt("aftermath/triple_extraction", {"content": chapter_content})

            response = await self.llm_client.generate(prompt)

            try:
                triples_data = json.loads(response)
            except json.JSONDecodeError:
                triples_data = []

            triples = []
            for triple_data in triples_data:
                triples.append(
                    KnowledgeTriple(
                        novel_id=ctx.novel_id,
                        subject=triple_data.get("subject", ""),
                        predicate=triple_data.get("predicate", ""),
                        object=triple_data.get("object", ""),
                        confidence=triple_data.get("confidence", 0.8),
                        source_chapter_id=ctx.chapter_id,
                    )
                )

            if triples:
                self.knowledge_repo.bulk_upsert_triples(triples)
                ctx.knowledge_triples = triples

            return StepResult(step_name=self.name, status="success", output={"triples_count": len(triples)})
        except Exception as e:
            logger.exception("Triple extraction failed")
            return StepResult(step_name=self.name, status="failed", error=str(e))


class UpdateForeshadowingStep(AftermathStep):
    name = "update_foreshadowing"

    def __init__(self, memory_repo, llm_client, prompt_manager):
        self.memory_repo = memory_repo
        self.llm_client = llm_client
        self.prompt_manager = prompt_manager

    async def execute(self, ctx: PipelineContext, chapter_content: str) -> StepResult:
        try:
            if not chapter_content:
                return StepResult(step_name=self.name, status="success", output={"updated": 0})

            pending_clues = self.memory_repo.get_clue_locks(ctx.novel_id, statuses=["planted", "developing"])

            if not pending_clues:
                return StepResult(step_name=self.name, status="success", output={"updated": 0})

            clues_text = "\n".join([f"{c.title}: {c.description} (Status: {c.status})" for c in pending_clues])

            prompt = self.prompt_manager.get_prompt(
                "aftermath/foreshadowing_update",
                {"content": chapter_content, "clues": clues_text, "chapter_number": ctx.chapter_index},
            )

            response = await self.llm_client.generate(prompt)

            try:
                updates = json.loads(response)
            except json.JSONDecodeError:
                updates = []

            updated_count = 0
            for update in updates:
                clue_id = update.get("clue_id")
                if clue_id:
                    clue = next((c for c in pending_clues if c.id == clue_id), None)
                    if clue:
                        clue.status = update.get("new_status", clue.status)
                        clue.description = update.get("new_description", clue.description)
                        clue.revealed_chapter = update.get("revealed_chapter")
                        self.memory_repo.bulk_upsert_clues([clue])
                        updated_count += 1

            prompt_new = self.prompt_manager.get_prompt(
                "aftermath/foreshadowing_discovery", {"content": chapter_content, "chapter_number": ctx.chapter_index}
            )

            response_new = await self.llm_client.generate(prompt_new)

            try:
                new_clues = json.loads(response_new)
            except json.JSONDecodeError:
                new_clues = []

            for clue_data in new_clues:
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
                updated_count += 1

            return StepResult(step_name=self.name, status="success", output={"updated": updated_count})
        except Exception as e:
            logger.exception("Foreshadowing update failed")
            return StepResult(step_name=self.name, status="failed", error=str(e))


class UpdateMemoryStep(AftermathStep):
    name = "update_memory"

    def __init__(self, memory_repo, llm_client, prompt_manager):
        self.memory_repo = memory_repo
        self.llm_client = llm_client
        self.prompt_manager = prompt_manager

    async def execute(self, ctx: PipelineContext, chapter_content: str) -> StepResult:
        try:
            if not chapter_content:
                return StepResult(step_name=self.name, status="success", output={"updated": 0})

            prompt = self.prompt_manager.get_prompt(
                "aftermath/memory_extraction", {"content": chapter_content, "chapter_number": ctx.chapter_index}
            )

            response = await self.llm_client.generate(prompt)

            try:
                memory_data = json.loads(response)
            except json.JSONDecodeError:
                memory_data = {"facts": [], "beats": []}

            facts = []
            for fact_data in memory_data.get("facts", []):
                facts.append(
                    FactLock(
                        novel_id=ctx.novel_id,
                        fact_type=fact_data.get("fact_type", "character"),
                        key=fact_data.get("key", ""),
                        value=fact_data.get("value", ""),
                        locked_at_chapter=ctx.chapter_index,
                        is_immutable=True,
                        source=f"chapter_{ctx.chapter_index}",
                    )
                )

            beats = []
            for beat_data in memory_data.get("beats", []):
                beats.append(
                    BeatLock(
                        novel_id=ctx.novel_id,
                        chapter_id=ctx.chapter_id or "",
                        chapter_index=ctx.chapter_index or 0,
                        beat_type=beat_data.get("beat_type", "action"),
                        description=beat_data.get("description", ""),
                        significance=beat_data.get("significance", "major"),
                        characters=beat_data.get("characters", []),
                    )
                )

            if facts:
                self.memory_repo.bulk_upsert_facts(facts)

            if beats:
                self.memory_repo.bulk_upsert_beats(beats)

            ctx.fact_locks = facts
            ctx.beat_locks = beats

            return StepResult(
                step_name=self.name, status="success", output={"facts_added": len(facts), "beats_added": len(beats)}
            )
        except Exception as e:
            logger.exception("Memory update failed")
            return StepResult(step_name=self.name, status="failed", error=str(e))


class IndexVectorStep(AftermathStep):
    name = "index_vector"

    def __init__(self, vector_store):
        self.vector_store = vector_store

    async def execute(self, ctx: PipelineContext, chapter_content: str) -> StepResult:
        try:
            if not chapter_content or not ctx.chapter_id:
                return StepResult(step_name=self.name, status="success", output={"indexed": False})

            if self.vector_store:
                await self.vector_store.add_document(
                    doc_id=ctx.chapter_id,
                    content=chapter_content,
                    metadata={
                        "novel_id": ctx.novel_id,
                        "chapter_id": ctx.chapter_id,
                        "chapter_index": ctx.chapter_index,
                    },
                )

            return StepResult(step_name=self.name, status="success", output={"indexed": True})
        except Exception as e:
            logger.exception("Vector indexing failed")
            return StepResult(step_name=self.name, status="failed", error=str(e))


class CreateSnapshotStep(AftermathStep):
    name = "create_snapshot"

    def __init__(self, knowledge_repo, memory_repo, chapter_repo=None, snapshot_repo=None):
        self.knowledge_repo = knowledge_repo
        self.memory_repo = memory_repo
        self.chapter_repo = chapter_repo
        self.snapshot_repo = snapshot_repo

    async def execute(self, ctx: PipelineContext, chapter_content: str) -> StepResult:
        try:
            import hashlib

            snapshot: dict[str, Any] = {
                "chapter_index": ctx.chapter_index,
                "chapter_id": ctx.chapter_id,
                "facts": [],
                "beats": [],
                "clues": [],
                "triples": [],
                "summary": None,
                "content": chapter_content or "",  # BLOCK-09: 保存完整章节内容
            }

            if ctx.fact_locks:
                snapshot["facts"] = [f.to_dict() for f in ctx.fact_locks]

            if ctx.beat_locks:
                snapshot["beats"] = [b.to_dict() for b in ctx.beat_locks]

            if ctx.clue_locks:
                snapshot["clues"] = [c.to_dict() for c in ctx.clue_locks]

            if ctx.knowledge_triples:
                snapshot["triples"] = [t.to_dict() for t in ctx.knowledge_triples]

            if ctx.summary:
                snapshot["summary"] = ctx.summary.summary

            ctx.snapshot = snapshot

            # BLOCK-09: 将快照持久化到数据库（含完整内容）
            if self.snapshot_repo and ctx.chapter_id:
                content = chapter_content or ""
                content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
                chapter_num = ctx.chapter_index or 0

                from domain.evolution.snapshot import Snapshot

                snapshot_entity = Snapshot(
                    novel_id=ctx.novel_id,
                    chapter_id=ctx.chapter_id,
                    snapshot_type="auto",
                    name=f"第{chapter_num}章·自动快照",
                    description=f"第{chapter_num}章生成后的自动快照",
                    content_hash=content_hash,
                    content=content,
                    created_by="system",
                )
                self.snapshot_repo.create(snapshot_entity)

            return StepResult(
                step_name=self.name,
                status="success",
                output={"snapshot_created": True, "chapter_index": ctx.chapter_index},
            )
        except Exception as e:
            logger.exception("Snapshot creation failed")
            return StepResult(step_name=self.name, status="failed", error=str(e))


class AftermathPipeline:
    """章后管线 - 六章处理

    1. extract_summary      摘要抽取
    2. extract_triples      三元组抽取
    3. update_foreshadowing 伏笔更新
    4. update_memory        记忆更新
    5. index_vector         向量索引
    6. create_snapshot      快照
    """

    def __init__(self, knowledge_repo, memory_repo, llm_client, prompt_manager, vector_store=None, chapter_repo=None, snapshot_repo=None):
        self.steps: list[AftermathStep] = [
            ExtractSummaryStep(knowledge_repo, llm_client, prompt_manager),
            ExtractTriplesStep(knowledge_repo, llm_client, prompt_manager),
            UpdateForeshadowingStep(memory_repo, llm_client, prompt_manager),
            UpdateMemoryStep(memory_repo, llm_client, prompt_manager),
            IndexVectorStep(vector_store),
            CreateSnapshotStep(knowledge_repo, memory_repo, chapter_repo, snapshot_repo),
        ]

    async def run(self, ctx: PipelineContext, chapter_content: str) -> PipelineContext:
        logger.info("Aftermath pipeline started for chapter %s", ctx.chapter_index)

        for step in self.steps:
            try:
                result = await step.execute(ctx, chapter_content)
                ctx.add_step_result(result)

                if result.status == "failed":
                    logger.warning("Aftermath step failed: %s, continuing...", step.name)
            except Exception as e:
                logger.exception("Aftermath step exception: %s", step.name)
                ctx.add_step_result(StepResult(step_name=step.name, status="failed", error=str(e)))

        logger.info("Aftermath pipeline completed for chapter %s", ctx.chapter_index)
        return ctx


class AftermathPipelineStep(PipelineStep):
    """将 AftermathPipeline 包装为标准的 PipelineStep。

    不改动 AftermathStep + AftermathPipeline 的内部实现（execute(ctx, chapter_content)），
    通过适配器将 execute(ctx, chapter_content) 包装为 PipelineStep.execute(ctx) → StepResult。

    该适配器供 StoryPipeline 或其他基于 PipelineStep 的管线集成使用。
    RunPostCommitStep（steps.py）仍保持原样，不受影响。
    """

    name = "aftermath_pipeline"

    def __init__(self, aftermath_pipeline: AftermathPipeline):
        self._inner = aftermath_pipeline

    async def execute(self, ctx: PipelineContext) -> StepResult:
        # 从 PipelineContext 中提取 Aftermath 需要的参数
        chapter_content: str = ctx.get("generated_content", "")
        chapter_id: str | None = ctx.get("chapter_id") or ctx.chapter_id

        if not chapter_content or not chapter_id:
            return StepResult(
                step_name=self.name,
                status="skipped",
                output={"reason": "missing chapter_content or chapter_id"},
            )

        try:
            # 创建 AftermathPipeline 使用的上下文
            aftermath_ctx = PipelineContext(
                novel_id=ctx.novel_id,
                chapter_id=chapter_id,
                chapter_index=ctx.chapter_index,
            )
            aftermath_ctx.data = dict(ctx.data)

            # 执行 AftermathPipeline（run 内部遍历 6 个 AftermathStep）
            await self._inner.run(aftermath_ctx, chapter_content)

            return StepResult(
                step_name=self.name,
                status="success",
                output={
                    "executed": True,
                    "chapter_id": chapter_id,
                    "step_count": len(aftermath_ctx.step_results),
                },
            )
        except Exception as e:
            # Aftermath 失败不阻塞主流程，记录日志即可
            logger.warning("AftermathPipelineStep failed: %s", e)
            return StepResult(
                step_name=self.name,
                status="success",  # 即使内部失败也标记成功，不阻塞管线
                output={"executed": False, "error": str(e)},
            )

    async def rollback(self, ctx: PipelineContext) -> None:
        """Aftermath 的 rollback 是 no-op（操作已提交到数据库/向量存储）。"""
        logger.info("AftermathPipelineStep.rollback: no-op for chapter %s", ctx.chapter_id)
