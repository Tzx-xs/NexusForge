import asyncio
import time
from dataclasses import dataclass, field
from typing import Any

from .base_guard import BaseGuard, GuardIssue, GuardResult


@dataclass
class AuditReport:
    overall_score: float
    passed: bool
    guard_results: list[GuardResult] = field(default_factory=list)
    total_issues: int = 0
    critical_issues: int = 0
    duration_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_score": self.overall_score,
            "passed": self.passed,
            "total_issues": self.total_issues,
            "critical_issues": self.critical_issues,
            "duration_ms": self.duration_ms,
            "guard_results": [
                {
                    "guard_name": r.guard_name,
                    "passed": r.passed,
                    "score": r.score,
                    "issues": [
                        {
                            "guard_name": i.guard_name,
                            "severity": i.severity,
                            "category": i.category,
                            "message": i.message,
                            "paragraph_index": i.paragraph_index,
                            "char_offset": i.char_offset,
                            "char_length": i.char_length,
                            "suggestion": i.suggestion,
                            "location": i.location,
                        }
                        for i in r.issues
                    ],
                    "duration_ms": r.duration_ms,
                    "metadata": r.metadata,
                }
                for r in self.guard_results
            ],
            "metadata": self.metadata,
        }


class QualityAuditService:
    """质量审计服务 - 编排所有质量护栏"""

    def __init__(self, guards: list[BaseGuard] | None = None):
        self._guards: dict[str, BaseGuard] = {}
        if guards:
            for guard in guards:
                self._guards[guard.name] = guard

    def register_guard(self, guard: BaseGuard) -> None:
        self._guards[guard.name] = guard

    def unregister_guard(self, guard_name: str) -> None:
        self._guards.pop(guard_name, None)

    def list_guards(self) -> list[dict[str, Any]]:
        return [{"name": g.name, "description": g.description, "weight": g.weight} for g in self._guards.values()]

    async def run_audit(
        self, content: str, context: dict[str, Any] | None = None, enabled_guards: list[str] | None = None
    ) -> AuditReport:
        start_time = time.time()
        context = context or {}

        total_weight = 0.0
        weighted_score = 0.0
        total_issues = 0
        critical_issues = 0

        guards_to_run = []
        if enabled_guards:
            for name in enabled_guards:
                if name in self._guards:
                    guards_to_run.append(self._guards[name])
        else:
            guards_to_run = list(self._guards.values())

        # M-08: 护栏相互独立，使用 asyncio.gather 并行执行
        async def _run_single_guard(guard: BaseGuard) -> GuardResult:
            guard_start = time.time()
            try:
                result = await guard.check(content, context)
            except Exception as e:
                result = GuardResult(
                    guard_name=guard.name,
                    passed=False,
                    score=0.0,
                    issues=[
                        GuardIssue(
                            guard_name=guard.name,
                            severity="error",
                            category="guard_error",
                            message=f"护栏执行异常: {e}",
                        )
                    ],
                    metadata={"error": str(e)},
                )
            guard_end = time.time()
            result.duration_ms = int((guard_end - guard_start) * 1000)
            return result

        results: list[GuardResult | BaseException] = await asyncio.gather(
            *[_run_single_guard(g) for g in guards_to_run],
            return_exceptions=True,
        )

        # 处理 gather 层异常（极端情况），包装为失败 GuardResult
        safe_results: list[GuardResult] = []
        for i, item in enumerate(results):
            if isinstance(item, BaseException):
                guard = guards_to_run[i]
                safe_results.append(
                    GuardResult(
                        guard_name=guard.name,
                        passed=False,
                        score=0.0,
                        issues=[
                            GuardIssue(
                                guard_name=guard.name,
                                severity="critical",
                                category="guard_error",
                                message=f"护栏并行执行崩溃: {item}",
                            )
                        ],
                        metadata={"error": str(item)},
                    )
                )
            else:
                safe_results.append(item)

        for idx, result in enumerate(safe_results):
            guard = guards_to_run[idx]
            weighted_score += result.score * guard.weight
            total_weight += guard.weight
            total_issues += len(result.issues)
            critical_issues += sum(1 for i in result.issues if i.severity in ("error", "critical"))

        overall_score = weighted_score / total_weight if total_weight > 0 else 0
        passed = overall_score >= 60.0 and critical_issues == 0

        end_time = time.time()
        duration_ms = int((end_time - start_time) * 1000)

        return AuditReport(
            overall_score=round(overall_score, 1),
            passed=passed,
            guard_results=safe_results,
            total_issues=total_issues,
            critical_issues=critical_issues,
            duration_ms=duration_ms,
        )

    @classmethod
    def with_default_guards(cls) -> "QualityAuditService":
        from .anti_ai_guard import AntiAIGuard
        from .character_consistency_guard import CharacterConsistencyGuard
        from .language_style_guard import LanguageStyleGuard
        from .macro_rhythm_guard import MacroRhythmGuard
        from .naming_consistency_guard import NamingConsistencyGuard
        from .plot_density_guard import PlotDensityGuard
        from .pov_guard import POVGuard
        from .rhythm_guard import RhythmGuard

        service = cls()
        service.register_guard(CharacterConsistencyGuard())
        service.register_guard(PlotDensityGuard())
        service.register_guard(LanguageStyleGuard())
        service.register_guard(RhythmGuard())
        service.register_guard(POVGuard())
        service.register_guard(NamingConsistencyGuard())
        service.register_guard(AntiAIGuard())
        service.register_guard(MacroRhythmGuard())
        return service
