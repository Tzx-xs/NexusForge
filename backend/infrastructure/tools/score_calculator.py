from .base import BaseTool, QualityScore, Violation


class ScoreCalculator(BaseTool):
    name = "score_calculator"
    description = "质量评分计算器：从审查结果计算总分和等级"

    GRADE_THRESHOLDS = [
        (90, "S"),
        (75, "A"),
        (60, "B"),
        (40, "C"),
        (0, "D"),
    ]

    DIMENSION_WEIGHTS = {
        "plot_coherence": 0.25,
        "character_consistency": 0.25,
        "setting_consistency": 0.2,
        "writing_quality": 0.3,
    }

    HIGH_SEVERITY_PENALTY = 5.0
    MEDIUM_SEVERITY_PENALTY = 2.0
    LOW_SEVERITY_PENALTY = 0.5

    def get_grade(self, total_score: float) -> str:
        for threshold, grade in self.GRADE_THRESHOLDS:
            if total_score >= threshold:
                return grade
        return "D"

    def calculate_from_llm_result(self, llm_result: dict) -> QualityScore:
        dimension_scores = llm_result.get("dimension_scores", {}) or {}

        if dimension_scores:
            weighted_total = 0.0
            total_weight = 0.0
            for dim, weight in self.DIMENSION_WEIGHTS.items():
                if dim in dimension_scores:
                    score = float(dimension_scores[dim])
                    weighted_total += score * weight
                    total_weight += weight
            if total_weight > 0:
                total_score = weighted_total / total_weight
            else:
                total_score = sum(dimension_scores.values()) / len(dimension_scores)
        else:
            total_score = float(llm_result.get("total_score", 60.0))

        total_score = max(0.0, min(100.0, total_score))
        grade = self.get_grade(total_score)

        return QualityScore(
            total_score=round(total_score, 1),
            grade=grade,
            dimension_scores=dimension_scores,
            issues=llm_result.get("issues", []),
            suggestions=llm_result.get("suggestions", []),
            overall_comment=llm_result.get("overall_comment", ""),
        )

    def apply_red_line_penalty(
        self,
        score: QualityScore,
        violations: list[Violation],
    ) -> QualityScore:
        if not violations:
            return score

        total_penalty = 0.0
        for v in violations:
            if v.severity == "high":
                total_penalty += self.HIGH_SEVERITY_PENALTY
            elif v.severity == "medium":
                total_penalty += self.MEDIUM_SEVERITY_PENALTY
            else:
                total_penalty += self.LOW_SEVERITY_PENALTY

        total_penalty = min(total_penalty, 30.0)

        new_score = max(0.0, score.total_score - total_penalty)
        new_grade = self.get_grade(new_score)

        return QualityScore(
            total_score=round(new_score, 1),
            grade=new_grade,
            dimension_scores=score.dimension_scores,
            issues=score.issues,
            suggestions=score.suggestions,
            overall_comment=score.overall_comment,
        )

    def calculate(self, llm_result: dict, red_line_violations: list[Violation] | None = None) -> QualityScore:
        score = self.calculate_from_llm_result(llm_result)
        if red_line_violations:
            score = self.apply_red_line_penalty(score, red_line_violations)
        return score

    def run(self, llm_result: dict, red_line_violations: list | None = None) -> QualityScore:
        return self.calculate(llm_result, red_line_violations)
