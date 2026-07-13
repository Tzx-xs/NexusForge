from typing import Any

from .base_guard import BaseGuard, GuardIssue, GuardResult, GuardSeverity


class POVGuard(BaseGuard):
    """视角护栏

    检测：
    - POV 视角一致性
    - 信息越界（角色不应知道的信息）
    - 人称混用
    """

    name = "pov"
    description = "视角统一检测"
    weight = 1.0

    FIRST_PERSON = ["我", "我们", "咱", "咱们", "我的", "我们的"]
    THIRD_PERSON = ["他", "她", "它", "他们", "她们", "它们", "他的", "她的"]
    SECOND_PERSON = ["你", "你们", "你的", "你们的", "阁下", "君"]

    THOUGHT_INDICATORS = [
        "心想",
        "暗想",
        "暗道",
        "暗自思量",
        "心中暗道",
        "想道",
        "想到",
        "心中暗想",
        "心里想",
    ]

    async def check(self, content: str, context: dict[str, Any]) -> GuardResult:
        issues: list[GuardIssue] = []
        paragraphs = self._split_paragraphs(content)

        if not paragraphs:
            return self._create_result(score=0, issues=[])

        pov_type = self._detect_pov(content)
        pov_consistency = self._check_pov_consistency(paragraphs, issues)
        info_leak = self._check_info_leakage(content, context, issues)

        score = pov_consistency * 0.6 + info_leak * 0.4

        return self._create_result(
            score=round(score, 1),
            issues=issues[:20],
            metadata={
                "pov_type": pov_type,
                "pov_consistency": round(pov_consistency, 1),
                "info_leak_score": round(info_leak, 1),
            },
        )

    def _detect_pov(self, content: str) -> str:
        first_count = sum(content.count(p) for p in self.FIRST_PERSON)
        third_count = sum(content.count(p) for p in self.THIRD_PERSON)
        second_count = sum(content.count(p) for p in self.SECOND_PERSON)

        total = first_count + third_count + second_count
        if total == 0:
            return "unknown"

        if first_count / total > 0.5:
            return "first_person"
        elif third_count / total > 0.5:
            return "third_person"
        elif second_count / total > 0.3:
            return "second_person"
        else:
            return "mixed"

    def _check_pov_consistency(self, paragraphs: list[str], issues: list[GuardIssue]) -> float:
        score = 100.0
        pov_shifts = 0

        prev_pov = None
        for i, para in enumerate(paragraphs):
            has_first = any(p in para for p in self.FIRST_PERSON)
            has_third = any(p in para for p in self.THIRD_PERSON)
            has_second = any(p in para for p in self.SECOND_PERSON)

            current_pov = self._dominant_pov(has_first, has_third, has_second)

            if prev_pov and current_pov and prev_pov != current_pov and current_pov != "unknown":
                pov_shifts += 1
                if pov_shifts <= 5:
                    issues.append(
                        GuardIssue(
                            guard_name=self.name,
                            severity=GuardSeverity.WARNING,
                            category="pov_shift",
                            message=f"第 {i + 1} 段视角可能发生切换",
                            paragraph_index=i,
                            suggestion="确认是否为有意的视角切换，避免频繁跳脱",
                        )
                    )

            if current_pov:
                prev_pov = current_pov

        if pov_shifts > 3:
            score -= (pov_shifts - 3) * 10

        return max(40.0, score)

    def _dominant_pov(self, first: bool, third: bool, second: bool) -> str | None:
        if first and not third and not second:
            return "first"
        if third and not first and not second:
            return "third"
        if second and not first and not third:
            return "second"
        if first and third:
            return "mixed"
        return None

    def _check_info_leakage(self, content: str, context: dict[str, Any], issues: list[GuardIssue]) -> float:
        score = 100.0

        pov_character = context.get("pov_character", "")
        if not pov_character:
            return 80.0

        leak_indicators = [
            "殊不知",
            "岂知",
            "哪里知道",
            "他不知道",
            "她不知道",
        ]

        for ind in leak_indicators:
            count = content.count(ind)
            if count > 2:
                issues.append(
                    GuardIssue(
                        guard_name=self.name,
                        severity=GuardSeverity.INFO,
                        category="info_leak_warning",
                        message=f"视角外信息提示 '{ind}' 出现 {count} 次",
                        suggestion="确认是否在有限视角中泄露了角色不应知道的信息",
                    )
                )
                score -= count * 2

        return max(50.0, score)
