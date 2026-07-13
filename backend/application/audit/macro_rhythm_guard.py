from typing import Any

from .base_guard import BaseGuard, GuardIssue, GuardResult, GuardSeverity


class MacroRhythmGuard(BaseGuard):
    """宏观节奏护栏

    检测：
    - 章节整体节奏曲线（起-承-转-合）
    - 高潮位置是否合理
    - 情绪起伏度
    - 悬念设置密度
    """

    name = "macro_rhythm"
    description = "宏观节奏把控"
    weight = 1.5

    TENSION_WORDS = [
        "突然",
        "紧急",
        "危机",
        "危险",
        "惊",
        "恐",
        "惧",
        "杀",
        "死",
        "血",
        "战斗",
        "决战",
        "生死",
        "怒吼",
        "咆哮",
        "爆发",
        "崩溃",
        "绝望",
    ]

    RELIEF_WORDS = [
        "松了口气",
        "放下心来",
        "终于",
        "安全",
        "平静",
        "安宁",
        "温暖",
        "希望",
        "光明",
    ]

    SUSPENSE_WORDS = [
        "竟然",
        "居然",
        "难道",
        "莫非",
        "真相",
        "秘密",
        "谜",
        "未解",
        "下一章",
        "欲知后事",
    ]

    async def check(self, content: str, context: dict[str, Any]) -> GuardResult:
        issues: list[GuardIssue] = []
        paragraphs = self._split_paragraphs(content)

        if not paragraphs:
            return self._create_result(score=0, issues=[])

        rhythm_curve = self._build_rhythm_curve(paragraphs)
        climax_position = self._find_climax_position(rhythm_curve)
        emotional_range = self._calculate_emotional_range(rhythm_curve)
        suspense_density = self._calculate_suspense_density(content)

        rhythm_score = self._calculate_macro_score(climax_position, emotional_range, suspense_density, len(paragraphs))

        if emotional_range < 0.2:
            issues.append(
                GuardIssue(
                    guard_name=self.name,
                    severity=GuardSeverity.WARNING,
                    category="flat_emotion",
                    message="情绪起伏度过低，叙事偏平淡",
                    suggestion="增加冲突和情绪波动，让读者有代入感",
                )
            )

        if suspense_density < 0.005 and len(paragraphs) > 10:
            issues.append(
                GuardIssue(
                    guard_name=self.name,
                    severity=GuardSeverity.INFO,
                    category="low_suspense",
                    message="悬念设置较少",
                    suggestion="适当设置悬念，勾起读者好奇心",
                )
            )

        return self._create_result(
            score=round(rhythm_score, 1),
            issues=issues,
            metadata={
                "climax_position_percent": round(climax_position * 100, 1),
                "emotional_range": round(emotional_range, 3),
                "suspense_density": round(suspense_density, 4),
                "rhythm_curve_length": len(rhythm_curve),
            },
        )

    def _build_rhythm_curve(self, paragraphs: list[str]) -> list[float]:
        curve = []
        for para in paragraphs:
            tension_score = sum(para.count(w) for w in self.TENSION_WORDS)
            relief_score = sum(para.count(w) for w in self.RELIEF_WORDS)
            intensity = tension_score * 2 - relief_score
            curve.append(intensity)

        if not curve:
            return [0]

        max_val = max(abs(v) for v in curve) or 1
        normalized = [v / max_val for v in curve]
        return normalized

    def _find_climax_position(self, curve: list[float]) -> float:
        if not curve:
            return 0.5
        max_idx = max(range(len(curve)), key=lambda i: curve[i])
        return max_idx / len(curve) if curve else 0.5

    def _calculate_emotional_range(self, curve: list[float]) -> float:
        if not curve:
            return 0
        max_val = max(curve)
        min_val = min(curve)
        return max_val - min_val

    def _calculate_suspense_density(self, content: str) -> float:
        if not content:
            return 0
        count = sum(content.count(w) for w in self.SUSPENSE_WORDS)
        return count / len(content)

    def _calculate_macro_score(
        self, climax_pos: float, emotional_range: float, suspense_density: float, para_count: int
    ) -> float:
        score = 100.0

        if 0.5 <= climax_pos <= 0.85:
            score += 5
        elif climax_pos < 0.2:
            score -= 15
        elif climax_pos > 0.95:
            score -= 10

        if emotional_range < 0.2:
            score -= 30
        elif emotional_range < 0.4:
            score -= 15
        elif emotional_range > 0.8:
            score += 5

        if suspense_density < 0.003:
            score -= 10
        elif suspense_density > 0.02:
            score += 5

        return max(20.0, min(100.0, score))
