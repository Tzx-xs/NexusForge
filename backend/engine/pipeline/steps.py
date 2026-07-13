import logging
import time

from domain.chapter_status import ChapterStatus

from .base import PipelineStep
from .context import PipelineContext, PipelineStatus, StepResult

logger = logging.getLogger(__name__)


class FindNextChapterStep(PipelineStep):
    name = "find_next_chapter"

    def __init__(self, chapter_repo, novel_repo):
        self.chapter_repo = chapter_repo
        self.novel_repo = novel_repo

    async def execute(self, ctx: PipelineContext) -> StepResult:
        novel_id = ctx.novel_id
        try:
            chapters = self.chapter_repo.list_by_novel(novel_id)
            chapters.sort(key=lambda c: c.number or 0)

            if ctx.chapter_id:
                current_chapter = self.chapter_repo.get_by_id(ctx.chapter_id)
                if current_chapter:
                    ctx.chapter_index = current_chapter.number
                    return StepResult(
                        step_name=self.name,
                        status="success",
                        output={"chapter_id": ctx.chapter_id, "chapter_index": current_chapter.number},
                    )

            if chapters:
                last_chapter = chapters[-1]
                next_index = last_chapter.number + 1 if last_chapter.number else 1
                ctx.chapter_index = next_index
                return StepResult(
                    step_name=self.name,
                    status="success",
                    output={"chapter_id": None, "chapter_index": next_index, "next_chapter_number": next_index},
                )

            ctx.chapter_index = 1
            return StepResult(step_name=self.name, status="success", output={"chapter_id": None, "chapter_index": 1})
        except Exception as e:
            return StepResult(step_name=self.name, status="failed", error=str(e))


class BuildContextStep(PipelineStep):
    name = "build_context"

    def __init__(self, context_builder, memory_engine):
        self.context_builder = context_builder
        self.memory_engine = memory_engine

    async def execute(self, ctx: PipelineContext) -> StepResult:
        novel_id = ctx.novel_id
        chapter_id = ctx.data.get("chapter_id") or ctx.chapter_id
        chapter_index = ctx.chapter_index

        try:
            base_context = self.context_builder.build_generation_context(novel_id, chapter_id)

            if self.memory_engine and chapter_index:
                iron_lock = self.memory_engine.build_t0_iron_lock(novel_id, chapter_index - 1)
                base_context["iron_lock"] = iron_lock

            ctx.set("generation_context", base_context)
            return StepResult(
                step_name=self.name,
                status="success",
                output={
                    "context_size": len(str(base_context)),
                    "has_iron_lock": bool(iron_lock) if "iron_lock" in locals() else False,
                },
            )
        except Exception as e:
            return StepResult(step_name=self.name, status="failed", error=str(e))


class PrepareChapterPlanStep(PipelineStep):
    name = "prepare_chapter_plan"

    def __init__(self, prompt_manager, llm_client, chapter_repo):
        self.prompt_manager = prompt_manager
        self.llm_client = llm_client
        self.chapter_repo = chapter_repo

    async def execute(self, ctx: PipelineContext) -> StepResult:
        generation_context = ctx.get("generation_context")

        try:
            if generation_context:
                prompt = self.prompt_manager.render("chapter-outline", generation_context)
                outline_response = await self.llm_client.chat(prompt)

                ctx.set("chapter_outline", outline_response.strip())
                ctx.set("beat_sheet", [])

                if ctx.chapter_id:
                    chapter = self.chapter_repo.get_by_id(ctx.chapter_id)
                    if chapter:
                        chapter.outline = ctx.get("chapter_outline")
                        self.chapter_repo.update(chapter)

                return StepResult(
                    step_name=self.name,
                    status="success",
                    output={"outline_length": len(ctx.get("chapter_outline", ""))},
                )

            ctx.set("chapter_outline", "")
            return StepResult(
                step_name=self.name, status="success", output={"outline_length": 0, "note": "Using empty outline"}
            )
        except Exception as e:
            logger.warning("PrepareChapterPlanStep failed: %s", e)
            ctx.set("chapter_outline", "")
            return StepResult(
                step_name=self.name,
                status="success",
                output={"outline_length": 0, "note": f"Outline generation failed: {str(e)}"},
            )


class GenerateStep(PipelineStep):
    name = "generate"

    def __init__(self, llm_client, prompt_manager, context_builder):
        self.llm_client = llm_client
        self.prompt_manager = prompt_manager
        self.context_builder = context_builder

    async def execute(self, ctx: PipelineContext) -> StepResult:
        novel_id = ctx.novel_id
        chapter_id = ctx.data.get("chapter_id") or ctx.chapter_id
        outline = ctx.get("chapter_outline", "")
        generation_context = ctx.get("generation_context")
        audit_feedback = ctx.get("audit_feedback", "")  # BLOCK-02: 审计反馈注入

        try:
            if not generation_context:
                generation_context = self.context_builder.build_generation_context(novel_id, chapter_id)
                ctx.set("generation_context", generation_context)

            if outline:
                generation_context["outline"] = outline

            # BLOCK-02: 注入审计反馈到生成上下文
            if audit_feedback:
                generation_context["audit_feedback"] = audit_feedback

            prompt = self.prompt_manager.render("chapter-content", generation_context)
            response = await self.llm_client.chat(prompt)

            ctx.set("generated_content", response.strip())
            ctx.set("word_count", len(response.strip()))

            return StepResult(
                step_name=self.name,
                status="success",
                output={"word_count": len(response.strip()), "content_length": len(response)},
            )
        except Exception as e:
            return StepResult(step_name=self.name, status="failed", error=str(e))


class ValidateContentStep(PipelineStep):
    name = "validate_content"

    def __init__(self, quality_service):
        self.quality_service = quality_service

    async def execute(self, ctx: PipelineContext) -> StepResult:
        content = ctx.get("generated_content", "")

        if not content:
            return StepResult(step_name=self.name, status="skipped", output={"reason": "No content to validate"})

        try:
            report = await self.quality_service.run_audit(content, context={"novel_id": ctx.novel_id})

            ctx.set("quality_report", report.to_dict())
            ctx.set("quality_score", report.overall_score)
            ctx.set("quality_passed", report.passed)

            if report.passed:
                return StepResult(
                    step_name=self.name,
                    status="success",
                    output={
                        "score": report.overall_score,
                        "total_issues": report.total_issues,
                        "passed": report.passed,
                    },
                )
            else:
                # BLOCK-03: 质量门禁阻断 — 审计不通过时返回 status="failed"
                issues_summary = (
                    f"质量审计不通过: score={report.overall_score:.1f}, "
                    f"issues={report.total_issues}"
                )
                return StepResult(
                    step_name=self.name,
                    status="failed",
                    error=issues_summary,
                    output={
                        "score": report.overall_score,
                        "total_issues": report.total_issues,
                        "passed": report.passed,
                    },
                )
        except Exception as e:
            logger.warning("ValidateContentStep failed: %s", e)
            return StepResult(
                step_name=self.name,
                status="failed",
                error=str(e),
                output={"note": f"Validation failed: {str(e)}"},
            )


class SaveChapterStep(PipelineStep):
    name = "save_chapter"

    def __init__(self, chapter_repo, novel_repo):
        self.chapter_repo = chapter_repo
        self.novel_repo = novel_repo

    async def execute(self, ctx: PipelineContext) -> StepResult:
        novel_id = ctx.novel_id
        content = ctx.get("generated_content", "")
        chapter_index = ctx.chapter_index

        try:
            chapter = self.chapter_repo.get_by_number(novel_id, chapter_index)

            if not chapter:
                from domain.chapter import Chapter

                chapter = Chapter(novel_id=novel_id, number=chapter_index or 0, title=f"第{chapter_index}章")
                chapter = self.chapter_repo.create(chapter)

            chapter.content = content
            chapter.word_count = len(content)
            # Sprint 1：删除 "generated" 死状态，由 FinalizeStep 统一设为 COMPLETED
            chapter.outline = ctx.get("chapter_outline", "")

            quality_report = ctx.get("quality_report")
            if quality_report:
                chapter.tension_score = quality_report.get("overall_score", 50.0)

            updated_chapter = self.chapter_repo.update(chapter)
            ctx.chapter_id = updated_chapter.id
            ctx.set("chapter_id", updated_chapter.id)

            novel = self.novel_repo.get_by_id(novel_id)
            if novel and chapter_index > novel.current_chapter:
                novel.current_chapter = chapter_index
                self.novel_repo.update(novel)

            return StepResult(
                step_name=self.name,
                status="success",
                output={"chapter_id": updated_chapter.id, "word_count": updated_chapter.word_count, "saved": True},
            )
        except Exception as e:
            return StepResult(step_name=self.name, status="failed", error=str(e))


class ValidateVoiceStep(PipelineStep):
    name = "validate_voice"

    def __init__(self, voice_service, voice_repo=None):
        self.voice_service = voice_service
        self.voice_repo = voice_repo

    async def execute(self, ctx: PipelineContext) -> StepResult:
        content = ctx.get("generated_content", "")

        if not content:
            return StepResult(step_name=self.name, status="skipped", output={"reason": "No content to check"})

        try:
            fingerprints = self.voice_service.list_fingerprints()
            if fingerprints:
                fp = fingerprints[0]
                drift_result = self.voice_service.detect_drift(fp.fingerprint_id, content)
                ctx.set("voice_drift_result", drift_result)

                if drift_result and hasattr(drift_result, "drifted") and drift_result.drifted:
                    logger.warning("Voice drift detected for chapter %s", ctx.chapter_index)
                    return StepResult(
                        step_name=self.name,
                        status="success",
                        output={
                            "drifted": True,
                            "similarity": drift_result.overall_similarity,
                            "note": "Voice drift detected",
                        },
                    )
                else:
                    return StepResult(
                        step_name=self.name,
                        status="success",
                        output={"drifted": False, "similarity": drift_result.overall_similarity if drift_result else 0},
                    )
            else:
                return StepResult(
                    step_name=self.name,
                    status="success",
                    output={"note": "No baseline fingerprint, skipping voice validation"},
                )
        except Exception as e:
            logger.warning("ValidateVoiceStep failed: %s", e)
            return StepResult(
                step_name=self.name, status="success", output={"note": f"Voice validation failed: {str(e)}"}
            )


class RunPostCommitStep(PipelineStep):
    name = "run_post_commit"

    def __init__(self, aftermath_pipeline):
        self.aftermath_pipeline = aftermath_pipeline

    async def execute(self, ctx: PipelineContext) -> StepResult:
        novel_id = ctx.novel_id
        chapter_id = ctx.get("chapter_id") or ctx.chapter_id
        chapter_index = ctx.chapter_index
        content = ctx.get("generated_content", "")

        if not chapter_id or not content:
            return StepResult(step_name=self.name, status="skipped", output={"reason": "Missing chapter_id or content"})

        try:
            if self.aftermath_pipeline:
                aftermath_ctx = PipelineContext(
                    novel_id=novel_id,
                    chapter_id=chapter_id,
                    chapter_index=chapter_index,
                )
                await self.aftermath_pipeline.run(aftermath_ctx, content)
                results = {"executed": True, "chapter_id": chapter_id, "chapter_index": chapter_index}
                ctx.set("aftermath_results", results)
                return StepResult(step_name=self.name, status="success", output=results)
            else:
                return StepResult(
                    step_name=self.name, status="skipped", output={"reason": "Aftermath pipeline not configured"}
                )
        except Exception as e:
            logger.warning("RunPostCommitStep failed: %s", e)
            return StepResult(step_name=self.name, status="success", output={"note": f"Post-commit failed: {str(e)}"})


class ScoreTensionStep(PipelineStep):
    name = "score_tension"

    def __init__(self, chapter_repo):
        self.chapter_repo = chapter_repo

    async def execute(self, ctx: PipelineContext) -> StepResult:
        chapter_id = ctx.get("chapter_id") or ctx.chapter_id
        content = ctx.get("generated_content", "")

        try:
            score = self._calculate_tension_score(content)

            if chapter_id:
                chapter = self.chapter_repo.get_by_id(chapter_id)
                if chapter:
                    chapter.tension_score = score
                    self.chapter_repo.update(chapter)

            ctx.set("tension_score", score)
            return StepResult(step_name=self.name, status="success", output={"tension_score": score})
        except Exception as e:
            logger.warning("ScoreTensionStep failed: %s", e)
            return StepResult(
                step_name=self.name,
                status="success",
                output={"tension_score": 50.0, "note": f"Scoring failed: {str(e)}"},
            )

    def _calculate_tension_score(self, content: str) -> float:
        if not content:
            return 50.0

        tension_keywords = [
            "突然",
            "猛地",
            "惊",
            "恐",
            "急",
            "慌",
            "险",
            "危",
            "杀",
            "死",
            "战",
            "斗",
            "冲突",
            "危机",
            "紧张",
            "激烈",
            "震撼",
            "震惊",
            "愤怒",
        ]

        sentence_count = max(len(content.split("。")), 1)
        keyword_count = sum(content.count(kw) for kw in tension_keywords)

        base_score = 50.0
        keyword_bonus = min(keyword_count * 2, 30)
        sentence_penalty = 0

        if sentence_count < 5:
            sentence_penalty = 10
        elif sentence_count > 50:
            sentence_penalty = -10

        score = base_score + keyword_bonus + sentence_penalty
        return max(0, min(100, score))


class FinalizeStep(PipelineStep):
    name = "finalize"

    def __init__(self, novel_repo, chapter_repo):
        self.novel_repo = novel_repo
        self.chapter_repo = chapter_repo

    async def execute(self, ctx: PipelineContext) -> StepResult:
        chapter_index = ctx.chapter_index
        chapter_id = ctx.get("chapter_id") or ctx.chapter_id

        try:
            chapter = self.chapter_repo.get_by_id(chapter_id) if chapter_id else None
            if chapter:
                chapter.status = ChapterStatus.COMPLETED.value
                self.chapter_repo.update(chapter)

            ctx.status = PipelineStatus.COMPLETED
            ctx.completed_at = time.time()

            return StepResult(
                step_name=self.name,
                status="success",
                output={
                    "chapter_id": chapter_id,
                    "chapter_index": chapter_index,
                    "status": ChapterStatus.COMPLETED.value,
                    "total_steps": len(ctx.step_results),
                },
            )
        except Exception as e:
            return StepResult(step_name=self.name, status="failed", error=str(e))
