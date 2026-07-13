"""Phase 5 Task 5.1：8 个 quality guards 接入十步管线 validate_content 步骤

验证点：
1. ValidateContentStep 调用 QualityAuditService.run_audit
2. 全部 8 个默认 guards 均被执行（通过 executed_guards 字段断言）
3. guard issues 被展平为 StepResult.violations
4. report.passed=False 时返回 status="failed"（软失败：管线不短路）
5. report.passed=True 时返回 status="success"
6. 无内容时返回 skipped
"""
import pytest

from application.audit.audit_service import QualityAuditService
from application.audit.base_guard import BaseGuard, GuardIssue, GuardResult
from engine.pipeline.context import PipelineContext
from engine.pipeline.steps import ValidateContentStep


# 8 个默认 guard 的名称（与 with_default_guards() 注册顺序无关）
EXPECTED_GUARD_NAMES = {
    "character_consistency",
    "plot_density",
    "language_style",
    "rhythm",
    "pov",
    "naming_consistency",
    "anti_ai",
    "macro_rhythm",
}


class _RecordingGuard(BaseGuard):
    """记录调用次数的测试 guard 桩，用于验证 run_audit 真的调用了每个 guard"""

    def __init__(self, name: str, score: float = 80.0, issues: list[GuardIssue] | None = None):
        self.name = name
        self.description = f"test guard {name}"
        self.weight = 1.0
        self._score = score
        self._issues = issues or []
        self.call_count = 0
        self.last_content: str | None = None
        self.last_context: dict | None = None

    async def check(self, content: str, context: dict) -> GuardResult:
        self.call_count += 1
        self.last_content = content
        self.last_context = context
        return self._create_result(score=self._score, issues=self._issues, passed=True)


class TestValidateContentStepGuards:
    """ValidateContentStep 与 8 个 guards 的集成"""

    @pytest.mark.asyncio
    async def test_all_eight_default_guards_executed(self):
        """用真实 8 个默认 guards 跑一次 audit，验证全部被执行"""
        service = QualityAuditService.with_default_guards()
        step = ValidateContentStep(service)

        # 一段典型正文，足以触发各 guard 的检测路径
        content = (
            "林逸走出洞府，望着远方连绵的山脉，心中涌起一股豪情。\n"
            "他握紧手中的长剑，剑身泛着冷光。突然，一道黑影从天而降。\n"
            "“来者何人！”林逸喝道。对方没有回答，只是冷冷一笑。\n"
            "剑光一闪，两人在山巅斗在一起，招招致命。"
        )
        ctx = PipelineContext(novel_id="n1", chapter_index=1)
        ctx.set("generated_content", content)

        result = await step.execute(ctx)

        executed = set(result.output.get("executed_guards", []))
        assert executed == EXPECTED_GUARD_NAMES, (
            f"应有 8 个 guard 被执行，实际: {executed}"
        )
        assert result.output["guard_results_count"] if "guard_results_count" in result.output else True
        # metadata 也记录了 guard_results_count
        assert result.metadata.get("guard_results_count") == 8

    @pytest.mark.asyncio
    async def test_violations_populated_from_guard_issues(self):
        """guard 报告的 issues 被展平到 StepResult.violations"""
        # 构造两个会报错的 guard
        issue1 = GuardIssue(
            guard_name="anti_ai",
            severity="warning",
            category="cliche",
            message="检测到 AI 模板化表达",
            paragraph_index=2,
            suggestion="改为更自然的口语",
        )
        issue2 = GuardIssue(
            guard_name="rhythm",
            severity="error",
            category="rhythm",
            message="段落节奏过短",
        )
        g1 = _RecordingGuard("anti_ai", score=40.0, issues=[issue1])
        g2 = _RecordingGuard("rhythm", score=30.0, issues=[issue2])
        # 其余 6 个高分 guard 保证 overall 不至于过低触发不同分支
        others = [_RecordingGuard(n, score=90.0) for n in
                  ("character_consistency", "plot_density", "language_style",
                   "pov", "naming_consistency", "macro_rhythm")]
        service = QualityAuditService([g1, g2, *others])

        step = ValidateContentStep(service)
        ctx = PipelineContext(novel_id="n1", chapter_index=1)
        ctx.set("generated_content", "测试内容\n第二段")

        result = await step.execute(ctx)

        # violations 应包含 issue1 和 issue2 的展平字典
        assert len(result.violations) == 2
        guard_names_in_violations = {v["guard_name"] for v in result.violations}
        assert guard_names_in_violations == {"anti_ai", "rhythm"}

        # 验证 violation 字段完整
        anti_ai_v = next(v for v in result.violations if v["guard_name"] == "anti_ai")
        assert anti_ai_v["severity"] == "warning"
        assert anti_ai_v["category"] == "cliche"
        assert anti_ai_v["message"] == "检测到 AI 模板化表达"
        assert anti_ai_v["paragraph_index"] == 2
        assert anti_ai_v["suggestion"] == "改为更自然的口语"

        # 两个 guard 都被实际调用
        assert g1.call_count == 1
        assert g2.call_count == 1
        assert g1.last_content == "测试内容\n第二段"

    @pytest.mark.asyncio
    async def test_failed_audit_returns_failed_status_with_violations(self):
        """审计不通过时返回 status=failed，但 violations 仍被填充（供软失败诊断）"""
        # 全部低分 guard
        guards = [_RecordingGuard(n, score=20.0) for n in EXPECTED_GUARD_NAMES]
        service = QualityAuditService(guards)

        step = ValidateContentStep(service)
        ctx = PipelineContext(novel_id="n1", chapter_index=1)
        ctx.set("generated_content", "短内容")

        result = await step.execute(ctx)

        assert result.status == "failed"
        assert result.score is not None
        assert result.score < 60.0
        # 8 个 guard 都被调用
        assert set(result.output["executed_guards"]) == EXPECTED_GUARD_NAMES
        # ctx 中也保存了违规列表
        assert ctx.get("quality_violations") == result.violations
        assert ctx.get("quality_passed") is False

    @pytest.mark.asyncio
    async def test_passed_audit_returns_success_with_empty_violations(self):
        """审计通过时返回 status=success，violations 为空"""
        guards = [_RecordingGuard(n, score=95.0) for n in EXPECTED_GUARD_NAMES]
        service = QualityAuditService(guards)

        step = ValidateContentStep(service)
        ctx = PipelineContext(novel_id="n1", chapter_index=1)
        ctx.set("generated_content", "高质量内容")

        result = await step.execute(ctx)

        assert result.status == "success"
        assert result.score == 95.0
        assert result.violations == []
        assert ctx.get("quality_passed") is True
        assert ctx.get("quality_score") == 95.0

    @pytest.mark.asyncio
    async def test_empty_content_skipped(self):
        """无内容时返回 skipped"""
        service = QualityAuditService.with_default_guards()
        step = ValidateContentStep(service)

        ctx = PipelineContext(novel_id="n1", chapter_index=1)
        ctx.set("generated_content", "")

        result = await step.execute(ctx)

        assert result.status == "skipped"
        assert result.violations == []

    @pytest.mark.asyncio
    async def test_audit_context_passes_novel_and_chapter_info(self):
        """ValidateContentStep 应把 novel_id/chapter_id/chapter_index 传给 guard context"""
        captured = {}

        class _CapturingGuard(BaseGuard):
            name = "capturing"
            description = "captures context"
            weight = 1.0

            async def check(self, content: str, context: dict) -> GuardResult:
                captured.update(context)
                return self._create_result(score=90.0, issues=[], passed=True)

        service = QualityAuditService([_CapturingGuard()])
        step = ValidateContentStep(service)

        ctx = PipelineContext(novel_id="novel-xyz", chapter_id="chap-7", chapter_index=7)
        ctx.set("generated_content", "测试")

        await step.execute(ctx)

        assert captured.get("novel_id") == "novel-xyz"
        assert captured.get("chapter_id") == "chap-7"
        assert captured.get("chapter_index") == 7

    @pytest.mark.asyncio
    async def test_generation_context_characters_propagated_to_audit(self):
        """generation_context 中的 characters/dead_characters 应透传给 audit context"""
        captured = {}

        class _CapturingGuard(BaseGuard):
            name = "capturing"
            description = "captures context"
            weight = 1.0

            async def check(self, content: str, context: dict) -> GuardResult:
                captured.update(context)
                return self._create_result(score=90.0, issues=[], passed=True)

        service = QualityAuditService([_CapturingGuard()])
        step = ValidateContentStep(service)

        ctx = PipelineContext(novel_id="n1", chapter_index=1)
        ctx.set("generated_content", "内容")
        ctx.set("generation_context", {
            "characters": [{"name": "林逸"}],
            "dead_characters": ["老怪"],
            "character_traits": {"林逸": ["冷静"]},
            # foreshadows 不在透传白名单的"必填"里但应被透传
            "foreshadows": [{"id": "f1"}],
            # 其它无关字段不应透传
            "irrelevant_field": "should_not_propagate",
        })

        await step.execute(ctx)

        assert captured.get("characters") == [{"name": "林逸"}]
        assert captured.get("dead_characters") == ["老怪"]
        assert captured.get("character_traits") == {"林逸": ["冷静"]}
        assert captured.get("foreshadows") == [{"id": "f1"}]
        assert "irrelevant_field" not in captured


class TestQualityAuditServiceDefaultGuards:
    """直接验证 with_default_guards() 注册的 8 个 guard"""

    def test_with_default_guards_registers_eight(self):
        service = QualityAuditService.with_default_guards()
        guard_names = {g["name"] for g in service.list_guards()}
        assert guard_names == EXPECTED_GUARD_NAMES
        assert len(guard_names) == 8

    @pytest.mark.asyncio
    async def test_run_audit_invokes_all_registered_guards(self):
        """run_audit 默认调用全部注册的 guard（无 enabled_guards 过滤）"""
        service = QualityAuditService.with_default_guards()
        report = await service.run_audit(
            "林逸走出洞府，望着远方连绵的山脉。\n突然一道黑影闪过。",
            context={"novel_id": "n1"},
        )
        executed = {r.guard_name for r in report.guard_results}
        assert executed == EXPECTED_GUARD_NAMES
