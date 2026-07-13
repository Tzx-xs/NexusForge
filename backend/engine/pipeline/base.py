import logging
import time
from abc import ABC, abstractmethod

from .context import PipelineContext, PipelineStatus, StepResult

logger = logging.getLogger(__name__)


class PipelineStep(ABC):
    name: str = ""

    @abstractmethod
    async def execute(self, ctx: PipelineContext) -> StepResult:
        pass

    async def rollback(self, ctx: PipelineContext) -> None:
        return None


class BaseStoryPipeline(ABC):
    """十步故事生成管线基类（批处理路径）

    职责边界：
        StoryPipeline 负责 Agent 自动调用场景下的完整十步章节生成，
        入口为 ``generate_chapter``（一次性返回 PipelineContext）。
        与之并存的 ``GenerationPipeline``（``application.engine.generation_pipeline``）
        负责用户交互场景下的 SSE 流式生成（已存在 chapter_id），入口为
        ``generate_content_stream`` / ``generate_ai_suggest``。
        两者不可互相替代，本基类仅服务批处理路径。

    十步流程：
    1. find_next_chapter     定位下一章
    2. build_context         四层洋葱上下文装配
    3. prepare_chapter_plan  章纲/Beat Sheet 准备
    4. generate              LLM 正文生成
    5. validate_content      策略验证
    6. save_chapter          保存章节
    7. validate_voice        文风审计
    8. run_post_commit       章后管线
    9. score_tension         张力打分
    10. finalize             收尾
    """

    def __init__(self):
        self.steps: list[PipelineStep] = []
        self._register_steps()

    @abstractmethod
    def _register_steps(self):
        pass

    async def run(self, ctx: PipelineContext) -> PipelineContext:
        ctx.status = PipelineStatus.RUNNING
        ctx.started_at = time.time()

        for step in self.steps:
            ctx.current_step = step.name
            logger.info("Pipeline step started: %s", step.name)

            try:
                result = await step.execute(ctx)
                ctx.add_step_result(result)

                # 三态语义：
                #   failed  → 短路：停止管线（已完成步骤副作用不回滚）
                #   skipped → 跳过本步，继续管线
                #   success → 继续
                if result.failed:
                    ctx.status = PipelineStatus.FAILED
                    logger.error("Pipeline step failed: %s: %s", step.name, result.error)
                    break

                if result.skipped:
                    logger.info("Pipeline step skipped: %s: %s", step.name, result.metadata.get("reason", ""))

            except Exception as e:
                logger.exception("Pipeline step exception: %s", step.name)
                ctx.add_step_result(StepResult(step_name=step.name, status="failed", error=str(e)))
                ctx.status = PipelineStatus.FAILED
                break

        if ctx.status == PipelineStatus.RUNNING:
            ctx.status = PipelineStatus.COMPLETED

        ctx.completed_at = time.time()
        return ctx

    async def resume_from(self, ctx: PipelineContext, step_name: str) -> PipelineContext:
        step_index = next((i for i, s in enumerate(self.steps) if s.name == step_name), 0)
        self.steps = self.steps[step_index:]
        return await self.run(ctx)


class StoryPipeline(BaseStoryPipeline):
    """十步故事生成管线 - 完整实现"""

    def __init__(
        self,
        chapter_repo,
        novel_repo,
        context_builder,
        memory_engine,
        prompt_manager,
        llm_client,
        quality_service,
        voice_service,
        aftermath_pipeline=None,
    ):
        self.chapter_repo = chapter_repo
        self.novel_repo = novel_repo
        self.context_builder = context_builder
        self.memory_engine = memory_engine
        self.prompt_manager = prompt_manager
        self.llm_client = llm_client
        self.quality_service = quality_service
        self.voice_service = voice_service
        self.aftermath_pipeline = aftermath_pipeline
        super().__init__()

    def _register_steps(self):
        from .steps import (
            BuildContextStep,
            FinalizeStep,
            FindNextChapterStep,
            GenerateStep,
            PrepareChapterPlanStep,
            RunPostCommitStep,
            SaveChapterStep,
            ScoreTensionStep,
            ValidateContentStep,
            ValidateVoiceStep,
        )

        self.steps = [
            FindNextChapterStep(self.chapter_repo, self.novel_repo),
            BuildContextStep(self.context_builder, self.memory_engine),
            PrepareChapterPlanStep(self.prompt_manager, self.llm_client, self.chapter_repo),
            GenerateStep(self.llm_client, self.prompt_manager, self.context_builder),
            ValidateContentStep(self.quality_service),
            SaveChapterStep(self.chapter_repo, self.novel_repo),
            ValidateVoiceStep(self.voice_service),
            RunPostCommitStep(self.aftermath_pipeline),
            ScoreTensionStep(self.chapter_repo),
            FinalizeStep(self.novel_repo, self.chapter_repo),
        ]

    async def generate_chapter(
        self,
        novel_id: str,
        chapter_id: str = None,
        audit_feedback: str = "",
        chapter_number: int | None = None,
        outline: str | None = None,
    ) -> PipelineContext:
        """生成章节。

        Args:
            novel_id: 小说ID
            chapter_id: 章节ID（可选）
            audit_feedback: 审计反馈文本（BLOCK-02），注入到生成上下文以针对性重写
            chapter_number: 目标章节号（可选，M-15）
            outline: 章纲内容（可选，M-15）
        """
        ctx = PipelineContext(novel_id=novel_id, chapter_id=chapter_id)
        # 将审计反馈注入管线上下文
        if audit_feedback:
            ctx.set("audit_feedback", audit_feedback)
        # M-15: 将 chapter_number 和 outline 注入管线上下文
        if chapter_number is not None:
            ctx.set("target_chapter_number", chapter_number)
        if outline:
            ctx.set("target_outline", outline)
        return await self.run(ctx)
