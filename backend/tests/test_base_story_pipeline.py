"""BaseStoryPipeline 软失败机制测试

PlotPilot 语义：validate_content / validate_voice / run_post_commit / score_tension
失败时不阻断管线，转为 warning 记录，继续执行后续步骤。
仅 find_next_chapter / build_context / prepare_chapter_plan / generate / save_chapter / finalize
这类步骤失败才短路。

本测试验证 StellarScribe 的注册式管线也能支持这种软失败语义。
"""
import pytest

from engine.pipeline.base import BaseStoryPipeline, PipelineStep
from engine.pipeline.context import PipelineContext, PipelineStatus, StepResult


# ─── 测试用 Step 桩 ────────────────────────────────────────────────
class _StubStep(PipelineStep):
    """可配置返回结果的测试步骤"""

    def __init__(self, name: str, result: StepResult):
        self.name = name
        self._result = result
        self.executed = False

    async def execute(self, ctx: PipelineContext) -> StepResult:
        self.executed = True
        ctx.set(f"{self.name}_executed", True)
        return self._result


def _ok(name: str) -> StepResult:
    return StepResult(step_name=name, status="success")


def _fail(name: str, err: str = "boom") -> StepResult:
    return StepResult(step_name=name, status="failed", error=err)


def _skip(name: str, reason: str = "n/a") -> StepResult:
    return StepResult.skip_step(step_name=name, reason=reason)


# ─── 测试用 Pipeline ───────────────────────────────────────────────
class _TestPipeline(BaseStoryPipeline):
    """测试管线：允许注入步骤列表与软失败配置"""

    def __init__(self, steps, soft_fail_steps=None):
        self._injected_steps = steps
        super().__init__()
        # 父类 __init__ 设置了默认 _soft_fail_steps，此处覆盖
        if soft_fail_steps is not None:
            self._soft_fail_steps = set(soft_fail_steps)

    def _register_steps(self):
        self.steps = self._injected_steps


# ═══════════════════════════════════════════════════════════════════
# 测试用例
# ═══════════════════════════════════════════════════════════════════
class TestSoftFailSemantics:
    """软失败语义：配置的步骤失败不阻断管线"""

    @pytest.mark.asyncio
    async def test_hard_fail_short_circuits(self):
        """硬失败步骤（如 generate）失败时短路管线"""
        s1 = _StubStep("build_context", _ok("build_context"))
        s2 = _StubStep("generate", _fail("generate", "LLM 超时"))
        s3 = _StubStep("save_chapter", _ok("save_chapter"))

        pipe = _TestPipeline([s1, s2, s3], soft_fail_steps=["validate_content"])
        ctx = PipelineContext(novel_id="n1")

        await pipe.run(ctx)

        assert ctx.status == PipelineStatus.FAILED
        assert s1.executed is True
        assert s2.executed is True
        assert s3.executed is False  # generate 失败后短路

    @pytest.mark.asyncio
    async def test_soft_fail_continues_pipeline(self):
        """软失败步骤（validate_content）失败时继续后续步骤"""
        s1 = _StubStep("generate", _ok("generate"))
        s2 = _StubStep("validate_content", _fail("validate_content", "score=0.4"))
        s3 = _StubStep("save_chapter", _ok("save_chapter"))

        pipe = _TestPipeline(
            [s1, s2, s3],
            soft_fail_steps=["validate_content", "validate_voice", "run_post_commit", "score_tension"],
        )
        ctx = PipelineContext(novel_id="n1")

        await pipe.run(ctx)

        # 软失败不阻断：管线最终 COMPLETED
        assert ctx.status == PipelineStatus.COMPLETED
        assert s1.executed is True
        assert s2.executed is True
        assert s3.executed is True  # validate_content 软失败后继续

    @pytest.mark.asyncio
    async def test_soft_fail_records_warning(self):
        """软失败步骤的失败结果仍记录在 step_results 中"""
        s1 = _StubStep("generate", _ok("generate"))
        s2 = _StubStep("validate_content", _fail("validate_content", "score=0.4"))
        s3 = _StubStep("finalize", _ok("finalize"))

        pipe = _TestPipeline([s1, s2, s3], soft_fail_steps=["validate_content"])
        ctx = PipelineContext(novel_id="n1")

        await pipe.run(ctx)

        assert ctx.status == PipelineStatus.COMPLETED
        # 失败结果仍在记录中
        validate_result = next(r for r in ctx.step_results if r.step_name == "validate_content")
        assert validate_result.failed is True
        assert validate_result.error == "score=0.4"

    @pytest.mark.asyncio
    async def test_default_soft_fail_steps_includes_audit_family(self):
        """BaseStoryPipeline 默认软失败集合应包含审计族步骤"""
        # 默认实例的 soft_fail_steps 应包含 PlotPilot 风格的 4 个审计步骤
        from engine.pipeline.base import DEFAULT_SOFT_FAIL_STEPS
        expected = {"validate_content", "validate_voice", "run_post_commit", "score_tension"}
        assert expected.issubset(DEFAULT_SOFT_FAIL_STEPS)


class TestSkipSemantics:
    """跳过语义（Task 1.1 已实现，此处回归验证）"""

    @pytest.mark.asyncio
    async def test_skip_does_not_block(self):
        """skipped 步骤不阻断管线"""
        s1 = _StubStep("validate_voice", _skip("validate_voice", "无基线指纹"))
        s2 = _StubStep("finalize", _ok("finalize"))

        pipe = _TestPipeline([s1, s2])
        ctx = PipelineContext(novel_id="n1")

        await pipe.run(ctx)

        assert ctx.status == PipelineStatus.COMPLETED
        assert s1.executed is True
        assert s2.executed is True
        assert ctx.step_results[0].skipped is True


class TestPipelineCompletes:
    """全成功场景"""

    @pytest.mark.asyncio
    async def test_all_success_completes(self):
        steps = [
            _StubStep("find_next_chapter", _ok("find_next_chapter")),
            _StubStep("build_context", _ok("build_context")),
            _StubStep("generate", _ok("generate")),
            _StubStep("validate_content", _ok("validate_content")),
            _StubStep("save_chapter", _ok("save_chapter")),
            _StubStep("finalize", _ok("finalize")),
        ]
        pipe = _TestPipeline(steps)
        ctx = PipelineContext(novel_id="n1")

        await pipe.run(ctx)

        assert ctx.status == PipelineStatus.COMPLETED
        assert all(s.executed for s in steps)
        assert len(ctx.step_results) == 6
