import logging
import time

from domain.chapter_status import ChapterStatus

from .base import PipelineStep
from .context import PipelineContext, PipelineStatus, StepResult

logger = logging.getLogger(__name__)


# Phase 5 Task 5.2：文风漂移定向改写最大尝试轮数
# 每轮都会调用一次 LLM 改写 + 一次漂移复检，超过轮数仍漂移则保留最后一次结果。
VOICE_REWRITE_MAX_ATTEMPTS = 2


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
            # Phase 5 Task 5.1：把管线上下文传给 audit，让 character/naming 类 guard 能读到角色信息
            audit_context = {
                "novel_id": ctx.novel_id,
                "chapter_id": ctx.get("chapter_id") or ctx.chapter_id,
                "chapter_index": ctx.chapter_index,
            }
            # 透传 generation_context 中可能包含的角色/伏笔信息（供 character_consistency_guard 使用）
            generation_context = ctx.get("generation_context")
            if isinstance(generation_context, dict):
                for key in ("characters", "dead_characters", "character_traits", "foreshadows"):
                    if key in generation_context:
                        audit_context[key] = generation_context[key]

            report = await self.quality_service.run_audit(content, context=audit_context)

            # Phase 5 Task 5.1：将所有 guard 的 issues 展平为 violations 列表
            # 结构：[{guard_name, severity, category, message, paragraph_index, char_offset, char_length, suggestion, location}]
            violations: list[dict] = []
            for guard_result in report.guard_results:
                for issue in guard_result.issues:
                    violations.append({
                        "guard_name": issue.guard_name,
                        "severity": issue.severity,
                        "category": issue.category,
                        "message": issue.message,
                        "paragraph_index": issue.paragraph_index,
                        "char_offset": issue.char_offset,
                        "char_length": issue.char_length,
                        "suggestion": issue.suggestion,
                        "location": issue.location,
                    })

            # guard 名称列表，便于下游诊断"哪些 guard 被执行了"
            executed_guards = [gr.guard_name for gr in report.guard_results]

            ctx.set("quality_report", report.to_dict())
            ctx.set("quality_score", report.overall_score)
            ctx.set("quality_passed", report.passed)
            ctx.set("quality_violations", violations)

            common_output = {
                "score": report.overall_score,
                "total_issues": report.total_issues,
                "critical_issues": report.critical_issues,
                "passed": report.passed,
                "executed_guards": executed_guards,
                "violations_count": len(violations),
            }
            common_metadata = {
                "guard_results_count": len(report.guard_results),
                "duration_ms": report.duration_ms,
            }

            if report.passed:
                return StepResult(
                    step_name=self.name,
                    status="success",
                    output=common_output,
                    violations=violations,
                    score=report.overall_score,
                    metadata=common_metadata,
                )
            else:
                # 软失败语义：返回 failed 状态，但 validate_content 在 DEFAULT_SOFT_FAIL_STEPS
                # 中，管线不会短路，仅记录 warning。violations 供下游诊断与 SSE 上报。
                issues_summary = (
                    f"质量审计不通过: score={report.overall_score:.1f}, "
                    f"issues={report.total_issues}, critical={report.critical_issues}"
                )
                return StepResult(
                    step_name=self.name,
                    status="failed",
                    error=issues_summary,
                    output=common_output,
                    violations=violations,
                    score=report.overall_score,
                    metadata=common_metadata,
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

    def __init__(
        self,
        voice_service,
        voice_repo=None,
        llm_client=None,
        chapter_repo=None,
        max_attempts: int = VOICE_REWRITE_MAX_ATTEMPTS,
    ):
        """Phase 5 Task 5.2：注入 llm_client + chapter_repo 启用文风漂移定向改写闭环。

        Args:
            voice_service: VoiceService 实例
            voice_repo: 文风指纹持久层（保留原参数，向后兼容）
            llm_client: LLMClient 实例。为 None 时跳过改写循环（仅检测漂移）。
            chapter_repo: ChapterRepository 实例。为 None 时改写结果只写入 ctx，不回写章节。
            max_attempts: 文风改写最大尝试轮数
        """
        self.voice_service = voice_service
        self.voice_repo = voice_repo
        self.llm_client = llm_client
        self.chapter_repo = chapter_repo
        self.max_attempts = max_attempts

    async def execute(self, ctx: PipelineContext) -> StepResult:
        content = ctx.get("generated_content", "")

        if not content:
            return StepResult(step_name=self.name, status="skipped", output={"reason": "No content to check"})

        try:
            fingerprints = self.voice_service.list_fingerprints()
            if not fingerprints:
                return StepResult(
                    step_name=self.name,
                    status="success",
                    output={"note": "No baseline fingerprint, skipping voice validation"},
                )

            fp = fingerprints[0]
            fp_id = fp.get("id", "") if isinstance(fp, dict) else getattr(fp, "fingerprint_id", "")
            drift_result = self.voice_service.detect_drift(fp_id, content)
            ctx.set("voice_drift_result", drift_result.to_dict() if drift_result else None)

            if not (drift_result and getattr(drift_result, "drifted", False)):
                return StepResult(
                    step_name=self.name,
                    status="success",
                    output={
                        "drifted": False,
                        "similarity": drift_result.overall_similarity if drift_result else 0,
                    },
                )

            # 检测到漂移
            logger.warning(
                "Voice drift detected for chapter %s (similarity=%.3f, dims=%s)",
                ctx.chapter_index,
                drift_result.overall_similarity,
                drift_result.drift_dimensions,
            )

            # Phase 5 Task 5.2：若注入了 llm_client，触发定向改写闭环
            rewrite_summary: dict = {"applied": False, "attempts": 0, "final_drifted": True}
            if self.llm_client is not None:
                rewrite_summary = await self._apply_voice_rewrite_loop(
                    ctx, fp_id, content, drift_result
                )
            else:
                logger.info("Voice rewrite skipped (no llm_client injected)")

            return StepResult(
                step_name=self.name,
                status="success",
                output={
                    "drifted": rewrite_summary["final_drifted"],
                    "similarity": drift_result.overall_similarity,
                    "rewrite": rewrite_summary,
                    "note": "Voice drift detected" if rewrite_summary["final_drifted"] else "Drift resolved by rewrite",
                },
            )
        except Exception as e:
            logger.warning("ValidateVoiceStep failed: %s", e)
            return StepResult(
                step_name=self.name, status="success", output={"note": f"Voice validation failed: {str(e)}"}
            )

    async def _apply_voice_rewrite_loop(
        self,
        ctx: PipelineContext,
        baseline_fp_id: str,
        initial_content: str,
        initial_drift,
    ) -> dict:
        """Phase 5 Task 5.2：文风漂移定向改写闭环。

        最多 ``max_attempts`` 轮：每轮调用 LLM 改写 → 用改写后文本复检漂移 →
        若仍漂移则继续，若不再漂移则提前终止。改写后的文本覆盖 ctx.generated_content，
        并在 chapter_repo 可用时回写到章节。

        Returns:
            改写摘要 dict：{applied, attempts, final_drifted, final_similarity, rounds}
        """
        rounds: list[dict] = []
        current_content = initial_content
        current_drift = initial_drift
        final_drifted = True

        # 保留原始内容供诊断
        ctx.set("original_content_before_voice_rewrite", initial_content)

        for attempt in range(1, self.max_attempts + 1):
            # 调用 LLM 改写
            try:
                rewritten = await self.voice_service.rewrite_content(
                    baseline_fp_id,
                    current_content,
                    current_drift.drift_dimensions,
                    self.llm_client,
                )
            except Exception as e:
                logger.warning("Voice rewrite attempt %d failed: %s", attempt, e)
                rounds.append({"attempt": attempt, "error": str(e), "drifted": True})
                break

            if not rewritten or rewritten == current_content:
                # LLM 回退了原文本或返回空，停止改写
                logger.info("Voice rewrite attempt %d returned unchanged content, stopping", attempt)
                rounds.append({
                    "attempt": attempt,
                    "drifted": True,
                    "unchanged": True,
                })
                break

            current_content = rewritten

            # 复检漂移
            current_drift = self.voice_service.detect_drift(baseline_fp_id, current_content)
            final_drifted = bool(current_drift and getattr(current_drift, "drifted", False))
            similarity = current_drift.overall_similarity if current_drift else 0.0

            rounds.append({
                "attempt": attempt,
                "drifted": final_drifted,
                "similarity": similarity,
                "content_length": len(current_content),
            })

            logger.info(
                "Voice rewrite attempt %d: drifted=%s similarity=%.3f",
                attempt, final_drifted, similarity,
            )

            if not final_drifted:
                break

        # 用改写后的内容覆盖 ctx.generated_content（后续 ScoreTensionStep 等会读到新内容）
        if current_content != initial_content:
            ctx.set("generated_content", current_content)
            ctx.set("word_count", len(current_content))
            ctx.set("voice_rewrite_applied", True)

            # 若提供了 chapter_repo，回写到已保存的章节
            chapter_id = ctx.get("chapter_id") or ctx.chapter_id
            if self.chapter_repo and chapter_id:
                try:
                    chapter = self.chapter_repo.get_by_id(chapter_id)
                    if chapter:
                        chapter.content = current_content
                        chapter.word_count = len(current_content)
                        self.chapter_repo.update(chapter)
                except Exception as e:
                    logger.warning("Failed to persist voice-rewritten chapter %s: %s", chapter_id, e)

        ctx.set("voice_rewrite_rounds", rounds)

        return {
            "applied": current_content != initial_content,
            "attempts": len(rounds),
            "final_drifted": final_drifted,
            "final_similarity": current_drift.overall_similarity if current_drift else 0.0,
            "rounds": rounds,
        }


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
