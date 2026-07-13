import re
from typing import Any

from .base_guard import BaseGuard, GuardIssue, GuardResult, GuardSeverity


class NamingConsistencyGuard(BaseGuard):
    """命名一致性护栏

    检测人名、地名等专有名词的写法不一致问题
    """

    name = "naming_consistency"
    description = "命名一致性检测"
    weight = 0.5

    NAME_PATTERNS = [
        r"[\u4e00-\u9fa5]{2,4}(?:先生|小姐|公子|姑娘|长老|掌门)",
        r"[\u4e00-\u9fa5]{2,3}(?:城|村|山|河|海|岛|谷|峰|阁|殿|府)",
    ]

    async def check(self, content: str, context: dict[str, Any]) -> GuardResult:
        issues: list[GuardIssue] = []
        paragraphs = self._split_paragraphs(content)

        character_names = context.get("character_names", [])
        location_names = context.get("location_names", [])

        known_names = set(character_names + location_names)

        name_variants: dict[str, list[str]] = {}

        for para_idx, para in enumerate(paragraphs):
            for pattern in self.NAME_PATTERNS:
                for match in re.finditer(pattern, para):
                    name = match.group()
                    for known in known_names:
                        if self._is_similar_name(name, known) and name != known:
                            if known not in name_variants:
                                name_variants[known] = []
                            if name not in name_variants[known]:
                                name_variants[known].append(name)
                                issues.append(
                                    GuardIssue(
                                        guard_name=self.name,
                                        severity=GuardSeverity.WARNING,
                                        category="naming_inconsistency",
                                        message=f"可能的命名不一致：'{name}' 与标准名 '{known}' 相似",
                                        paragraph_index=para_idx,
                                        char_offset=match.start(),
                                        char_length=len(name),
                                        suggestion=f"建议统一使用 '{known}'",
                                    )
                                )

        score = self._calculate_score(len(issues), len(paragraphs))
        return self._create_result(
            score=score,
            issues=issues,
            metadata={"variant_count": len(name_variants)},
        )

    def _is_similar_name(self, name1: str, name2: str) -> bool:
        if name1 == name2:
            return False
        if len(name1) != len(name2):
            return False
        diff = sum(1 for a, b in zip(name1, name2, strict=False) if a != b)
        return diff == 1

    def _calculate_score(self, issue_count: int, para_count: int) -> float:
        if para_count == 0:
            return 100.0
        density = issue_count / max(para_count, 1)
        if density == 0:
            return 100.0
        elif density < 0.02:
            return 90.0
        elif density < 0.05:
            return 75.0
        elif density < 0.1:
            return 60.0
        else:
            return max(30.0, 100 - density * 500)
