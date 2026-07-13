import re
from typing import Any

from .base_guard import BaseGuard, GuardIssue, GuardResult, GuardSeverity


class PlotDensityGuard(BaseGuard):
    """情节密度护栏

    检测每千字的事件密度、对话占比、场景转换频率
    """

    name = "plot_density"
    description = "情节密度检测"
    weight = 1.5

    EVENT_INDICATORS = [
        "突然",
        "就在这时",
        "然而",
        "但是",
        "不料",
        "没想到",
        "紧接着",
        "下一刻",
        "刹那间",
        "瞬间",
        "猛然",
        "决定",
        "宣布",
        "发现",
        "得知",
        "意识到",
    ]

    async def check(self, content: str, context: dict[str, Any]) -> GuardResult:
        issues: list[GuardIssue] = []
        paragraphs = self._split_paragraphs(content)
        char_count = len(content)
        word_count = char_count  # 中文近似字数

        if word_count == 0:
            return self._create_result(score=0, issues=[])

        event_count = 0
        for indicator in self.EVENT_INDICATORS:
            event_count += content.count(indicator)

        dialogue_count = len(re.findall(r'"[^"]*"', content))
        dialogue_count += len(re.findall(r'"[^"]*"', content))

        scene_changes = 0
        location_indicators = [
            "来到",
            "到达",
            "进入",
            "走出",
            "离开",
            "前往",
            "在.*里",
            "在.*中",
            "在.*上",
        ]
        for ind in location_indicators:
            scene_changes += len(re.findall(ind, content))

        events_per_k = (event_count / max(word_count, 1)) * 1000
        dialogue_ratio = dialogue_count / max(len(paragraphs), 1)
        scenes_per_k = (scene_changes / max(word_count, 1)) * 1000

        density_score = self._calculate_density_score(events_per_k, dialogue_ratio, scenes_per_k)

        if events_per_k < 2:
            issues.append(
                GuardIssue(
                    guard_name=self.name,
                    severity=GuardSeverity.WARNING,
                    category="low_density",
                    message=f"情节密度偏低：每千字 {events_per_k:.1f} 个事件点",
                    suggestion="建议增加冲突点或转折点，提升叙事张力",
                )
            )
        elif events_per_k > 15:
            issues.append(
                GuardIssue(
                    guard_name=self.name,
                    severity=GuardSeverity.INFO,
                    category="high_density",
                    message=f"情节密度偏高：每千字 {events_per_k:.1f} 个事件点",
                    suggestion="建议适当增加过渡描写，给读者喘息空间",
                )
            )

        if dialogue_ratio > 0.8:
            issues.append(
                GuardIssue(
                    guard_name=self.name,
                    severity=GuardSeverity.INFO,
                    category="too_much_dialogue",
                    message=f"对话占比过高：{dialogue_ratio:.1%}",
                    suggestion="建议增加动作、环境和心理描写",
                )
            )
        elif dialogue_ratio < 0.1 and len(paragraphs) > 10:
            issues.append(
                GuardIssue(
                    guard_name=self.name,
                    severity=GuardSeverity.WARNING,
                    category="too_little_dialogue",
                    message=f"对话占比过低：{dialogue_ratio:.1%}",
                    suggestion="建议增加人物对话，让角色更生动",
                )
            )

        return self._create_result(
            score=density_score,
            issues=issues,
            metadata={
                "events_per_k": round(events_per_k, 2),
                "dialogue_ratio": round(dialogue_ratio, 3),
                "scenes_per_k": round(scenes_per_k, 2),
                "event_count": event_count,
                "dialogue_count": dialogue_count,
                "word_count": word_count,
            },
        )

    def _calculate_density_score(self, events_per_k: float, dialogue_ratio: float, scenes_per_k: float) -> float:
        score = 100.0

        if events_per_k < 2:
            score -= (2 - events_per_k) * 15
        elif events_per_k > 15:
            score -= (events_per_k - 15) * 3

        if dialogue_ratio < 0.1:
            score -= (0.1 - dialogue_ratio) * 100
        elif dialogue_ratio > 0.8:
            score -= (dialogue_ratio - 0.8) * 50

        if scenes_per_k > 5:
            score -= (scenes_per_k - 5) * 5

        return max(30.0, min(100.0, score))
