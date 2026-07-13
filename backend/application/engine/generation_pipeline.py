from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from typing import Any

from application.engine.prompt_manager import PromptManager
from config.logging import get_logger
from engine.pipeline.aftermath import AftermathPipeline
from engine.pipeline.context import PipelineContext, PipelineStatus
from infrastructure.ai.llm_client import LLMClient
from infrastructure.persistence.chapter_repo import ChapterRepository
from infrastructure.persistence.review_repo import ReviewRepository

from .context_builder import ContextBuilder
from .steps.step1_build_context import Step1BuildContext
from .steps.step2_generate_content import Step2GenerateContent
from .steps.step3_run_review import Step3RunReview
from .steps.step4_save_finalize import Step4SaveFinalize

logger = get_logger(__name__)


PIPELINE_STEPS = [
    ("building_context", 0, 10, Step1BuildContext),
    ("generating_outline", 10, 30, None),
    ("generating_content", 30, 90, None),
    ("reviewing", 90, 95, Step3RunReview),
    ("saving", 95, 100, Step4SaveFinalize),
]


class GenerationPipeline:
    """SSE 流式生成管线（用户交互路径）。

    职责边界：
        仅负责用户交互场景下的流式章节生成（已存在 chapter_id），
        入口为 ``generate_content_stream`` / ``generate_ai_suggest``。
        与之并存的 ``StoryPipeline``（``engine.pipeline.base``）负责 Agent 自动
        调用场景下的十步批处理管线（含 find_next_chapter / finalize），入口为
        ``generate_chapter``。两者职责互补但不可合并。
    """

    def __init__(
        self,
        llm_client: LLMClient,
        prompt_manager: PromptManager,
        context_builder: ContextBuilder,
        chapter_repo: ChapterRepository,
        review_repo: ReviewRepository,
        aftermath_pipeline: AftermathPipeline | None = None,
        max_retries: int = 2,
    ):
        self.llm_client = llm_client
        self.prompt_manager = prompt_manager
        self.context_builder = context_builder
        self.chapter_repo = chapter_repo
        self.review_repo = review_repo
        # Sprint 2.2：注入 AftermathPipeline，使 SSE 路径也能产出摘要/伏笔/记忆/快照
        self.aftermath_pipeline = aftermath_pipeline
        self.max_retries = max_retries

        self._step1 = Step1BuildContext(
            llm_client=llm_client,
            prompt_manager=prompt_manager,
            context_builder=context_builder,
            chapter_repo=chapter_repo,
        )
        self._step2 = Step2GenerateContent(
            llm_client=llm_client,
            prompt_manager=prompt_manager,
            context_builder=context_builder,
            chapter_repo=chapter_repo,
        )
        self._step3 = Step3RunReview(
            llm_client=llm_client,
            prompt_manager=prompt_manager,
            context_builder=context_builder,
            chapter_repo=chapter_repo,
            review_repo=review_repo,
        )
        self._step4 = Step4SaveFinalize(
            chapter_repo=chapter_repo,
            review_repo=review_repo,
        )

        self._status: dict[str, dict] = {}
        self._cancel_flags: dict[str, bool] = {}

    def get_status(self, chapter_id: str) -> dict:
        return self._status.get(
            chapter_id,
            {
                "chapter_id": chapter_id,
                "state": "idle",
                "progress": 0,
                "step": None,
                "error": None,
            },
        )

    def is_running(self, chapter_id: str) -> bool:
        state = self.get_status(chapter_id).get("state")
        return state in ("building_context", "generating", "reviewing", "saving")

    def _cleanup_status(self, chapter_id: str) -> None:
        """清理已完成/失败的章节状态，防止内存泄漏。

        根据审查报告 PERF-C1：_status 字典无限增长，completed 和 failed 的
        状态记录永久保留。本章节流程结束后（无论成功、失败或取消），
        立即清理对应的状态和取消标记。
        """
        self._status.pop(chapter_id, None)
        self._cancel_flags.pop(chapter_id, None)

    def cancel(self, chapter_id: str):
        self._cancel_flags[chapter_id] = True
        logger.info("Cancel requested for chapter %s", chapter_id)

    def _set_status(
        self, chapter_id: str, state: str, progress: int = 0, step: str | None = None, error: str | None = None
    ):
        self._status[chapter_id] = {
            "chapter_id": chapter_id,
            "state": state,
            "progress": progress,
            "step": step,
            "error": error,
        }

    def _check_cancel(self, chapter_id: str) -> bool:
        if self._cancel_flags.get(chapter_id, False):
            self._set_status(chapter_id, "failed", error="用户取消")
            return True
        return False

    # ------------------------------------------------------------------
    # T03: 步骤子方法
    # ------------------------------------------------------------------

    async def _run_step1_build_context(
        self,
        chapter_id: str,
        pipeline_context: dict,
    ) -> tuple[bool, str]:
        """构建上下文步骤。Returns (success, error_message)"""
        success, result, error = await self._retry_step(self._step1.execute, chapter_id, pipeline_context)
        if success:
            pipeline_context.update(result)
        return success, error

    async def _run_step2_generate_content_stream(
        self,
        chapter_id: str,
        pipeline_context: dict,
    ) -> AsyncGenerator[tuple[str, str], None]:
        """流式生成步骤。yields SSE 事件 (event, data)"""
        self._set_status(chapter_id, "generating", 30)

        full_content = ""
        outline = ""
        stream_gen = self._step2.execute_stream(chapter_id, pipeline_context)
        async for event, data in stream_gen:
            if self._check_cancel(chapter_id):
                yield "error", "用户取消"
                return

            if event == "outline":
                outline = data
                pipeline_context["outline"] = outline
                yield "progress", "30"
            elif event == "token":
                full_content += data
                progress = 30 + int((len(full_content) / 4000) * 60)
                if progress > 90:
                    progress = 90
                yield "progress", str(progress)
                yield "token", data
            elif event == "content_complete":
                full_content = data
                pipeline_context["content"] = full_content
                pipeline_context["word_count"] = len(full_content)
                self._set_status(chapter_id, "generating", 90)
                yield "progress", "90"
            elif event == "error":
                self._set_status(chapter_id, "failed", error=data)
                yield "error", data
                return

        if self._check_cancel(chapter_id):
            yield "error", "用户取消"
            return

    async def _run_step3_review(
        self,
        chapter_id: str,
        pipeline_context: dict,
    ) -> tuple[bool, str]:
        """质量审查步骤（可跳过）。Returns (success, error_message)"""
        self._set_status(chapter_id, "reviewing", 92)
        success, review_result, error = await self._retry_step(
            self._step3.execute, chapter_id, pipeline_context, skip_on_error=True
        )
        if success:
            pipeline_context["review_result"] = review_result.get("review_result", {})
        else:
            logger.warning("Review skipped: %s", error)
            pipeline_context["review_result"] = {}
        return success, error

    async def _run_step4_save(
        self,
        chapter_id: str,
        pipeline_context: dict,
    ) -> tuple[bool, dict, str]:
        """保存收尾。Returns (success, result_data, error_message)"""
        self._set_status(chapter_id, "saving", 97)
        success, save_result, error = await self._retry_step(
            self._step4.execute, chapter_id, pipeline_context, retries=1
        )
        return success, save_result, error

    async def _run_aftermath(
        self,
        chapter_id: str,
        pipeline_context: dict,
        chapter: Any,
    ) -> None:
        """章后处理。异常不阻塞主流程。"""
        if self.aftermath_pipeline is None:
            return

        try:
            full_content = pipeline_context.get("content", "")
            aftermath_ctx = PipelineContext(
                novel_id=chapter.novel_id,
                chapter_id=chapter_id,
                chapter_index=getattr(chapter, "number", None),
                status=PipelineStatus.RUNNING,
            )
            aftermath_ctx.data = dict(pipeline_context)
            await self.aftermath_pipeline.run(aftermath_ctx, full_content)
        except Exception as aftermath_err:
            # AftermathPipeline 异常不应阻塞主流程，章节正文已保存
            logger.warning(
                f"Aftermath pipeline failed for chapter {chapter_id}: {aftermath_err}",
                exc_info=True,
            )

    # ------------------------------------------------------------------
    # 主入口
    # ------------------------------------------------------------------

    async def generate_content_stream(
        self, chapter_id: str, options: dict | None = None
    ) -> AsyncGenerator[tuple[str, str], None]:
        """生成章节内容并流式返回事件。编排层，调用子方法完成各步骤。"""
        chapter = self.chapter_repo.get_by_id(chapter_id)
        if not chapter:
            yield "error", "章节不存在"
            self._cleanup_status(chapter_id)
            return

        if not self.chapter_repo.try_acquire_generation_lock(chapter.novel_id, chapter.number):
            yield "error", "生成进行中，不可重复触发"
            self._cleanup_status(chapter_id)
            return

        self._set_status(chapter_id, "building_context", 0)

        pipeline_context: dict = {}
        # 注入 AI 控制台生成参数，供 prompt 模板与 step 使用（审查报告 1.2/4.2）
        if options:
            pipeline_context["generation_options"] = options
            generation_context = pipeline_context.setdefault("generation_context", {})
            generation_context["generation_mode"] = options.get("mode", "continue")
            generation_context["target_length"] = options.get("target_length", "medium")
            generation_context["style_strength"] = options.get("style_strength", 70)
            generation_context["creativity"] = options.get("creativity", 50)
            guards = options.get("quality_guards")
            if guards:
                generation_context["quality_guards"] = guards
            user_context = options.get("context")
            if user_context:
                generation_context["user_context"] = user_context

        try:
            yield "progress", "0"

            # Step 1: 构建上下文
            success, error = await self._run_step1_build_context(chapter_id, pipeline_context)
            if not success:
                self._set_status(chapter_id, "failed", error=error)
                yield "error", error
                return
            self._set_status(chapter_id, "building_context", 10)
            yield "progress", "10"

            if self._check_cancel(chapter_id):
                yield "error", "用户取消"
                return

            # Step 2: 流式生成正文
            async for event in self._run_step2_generate_content_stream(chapter_id, pipeline_context):
                yield event

            if self._check_cancel(chapter_id):
                yield "error", "用户取消"
                return

            # Step 3: 质量审查
            success, error = await self._run_step3_review(chapter_id, pipeline_context)
            if not success:
                # review 可跳过，仅记录警告而非直接失败
                logger.warning("Review skipped: %s", error)

            self._set_status(chapter_id, "reviewing", 95)
            yield "progress", "95"

            if self._check_cancel(chapter_id):
                yield "error", "用户取消"
                return

            # Step 4: 保存收尾
            success, save_result, error = await self._run_step4_save(chapter_id, pipeline_context)
            if not success:
                self._set_status(chapter_id, "failed", error=error)
                yield "error", error
                return

            self._set_status(chapter_id, "completed", 100)
            yield "progress", "100"

            # Aftermath（不阻塞主流程）
            try:
                await self._run_aftermath(chapter_id, pipeline_context, chapter)
            except Exception:
                logger.exception("Aftermath 处理异常")

            complete_data = {
                "chapter_id": chapter_id,
                "word_count": save_result.get("word_count", len(pipeline_context.get("content", ""))),
                "score": save_result.get("score", 0.0),
            }
            yield "complete", json.dumps(complete_data, ensure_ascii=False)

        except Exception as e:
            logger.error("Pipeline error: %s", e, exc_info=True)
            self._set_status(chapter_id, "failed", error=str(e))
            yield "error", str(e)
        finally:
            self._cleanup_status(chapter_id)

    async def _retry_step(
        self, step_func, chapter_id: str, context: dict, retries: int | None = None, skip_on_error: bool = False
    ) -> tuple[bool, dict, str]:
        max_tries = (retries if retries is not None else self.max_retries) + 1
        last_error = ""

        for attempt in range(max_tries):
            if self._check_cancel(chapter_id):
                return False, {}, "用户取消"

            try:
                success, result, error = await step_func(chapter_id, context)
                if success:
                    return True, result, ""
                last_error = error
            except Exception as e:
                last_error = str(e)
                logger.warning("Step attempt %s failed: %s", attempt + 1, e)

            if attempt < max_tries - 1:
                await asyncio.sleep(0.5 * (attempt + 1))

        if skip_on_error:
            return False, {}, last_error
        return False, {}, last_error

    async def generate_outline(self, chapter_id: str) -> str:
        """独立生成章节大纲（不触发正文流式生成）。

        复用 Step2GenerateContent 的 outline 生成逻辑：渲染 ``chapter-outline``
        模板并调用 LLM 返回纯文本大纲。供 ChapterService.generate_outline 调用。
        """
        chapter = self.chapter_repo.get_by_id(chapter_id)
        if not chapter:
            raise ValueError(f"章节不存在: {chapter_id}")

        pipeline_context: dict[str, Any] = {
            "generation_context": {
                "novel_id": chapter.novel_id,
                "chapter_id": chapter_id,
                "chapter_number": getattr(chapter, "number", None),
                "title": chapter.title or "",
            }
        }
        outline_prompt = self.prompt_manager.render("chapter-outline", pipeline_context["generation_context"])
        outline_response = await self.llm_client.chat(outline_prompt)
        return str(outline_response).strip()

    async def generate_ai_suggest(
        self, chapter_id: str
    ) -> AsyncGenerator[tuple[str, Any], None]:
        """Sprint 5.1: 流式生成 AI 写作建议。

        复用 LLMClient.chat_stream,基于章节内容构造建议 prompt。
        事件类型:token(str)/ complete(dict)/ error(str)。
        """
        chapter = self.chapter_repo.get_by_id(chapter_id)
        if not chapter:
            yield "error", f"章节不存在: {chapter_id}"
            return

        prompt = self._build_suggest_prompt(chapter.content)
        self._set_status(chapter_id, "generating", 0, "ai_suggest")

        try:
            async for chunk in self.llm_client.chat_stream(prompt):
                if self._check_cancel(chapter_id):
                    yield "error", "用户取消"
                    return
                yield "token", chunk

            self._set_status(chapter_id, "completed", 100, "ai_suggest")
            yield "complete", {"chapter_id": chapter_id}
        except Exception as e:
            logger.error("AI suggest failed for chapter %s: %s", chapter_id, e, exc_info=True)
            self._set_status(chapter_id, "failed", error=str(e))
            yield "error", str(e)
        finally:
            self._cleanup_status(chapter_id)

    def _build_suggest_prompt(self, content: str) -> str:
        """构造 AI 写作建议提示词。"""
        truncated = content[:2000] if len(content) > 2000 else content
        return (
            "你是星渊笔的 AI 写作助手。请基于以下章节内容,给出具体、可操作的写作建议:\n"
            "1. 情节推进是否自然\n"
            "2. 人物塑造是否立体\n"
            "3. 是否存在逻辑漏洞\n"
            "4. 文风改进建议\n\n"
            f"章节内容:\n{truncated}\n\n"
            "请给出 200-400 字的具体建议:"
        )
