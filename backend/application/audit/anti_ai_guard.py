import re
from typing import Any

from .base_guard import BaseGuard, GuardIssue, GuardResult, GuardSeverity


class AntiAIGuard(BaseGuard):
    """反 AI 审计护栏

    检测 AI 写作常见特征：
    - 元话语/模板化表达
    - 句式套路
    - 陈词滥调
    - 过度形容词堆砌
    """

    name = "anti_ai"
    description = "反 AI 味检测"
    weight = 2.0

    AI_PHRASES = [
        "值得一提的是",
        "不得不说",
        "众所周知",
        "总而言之",
        "由此可见",
        "综上所述",
        "不难看出",
        "可以说",
        "也就是说",
        "事实上",
        "实际上",
        "从某种意义上来说",
        "在很大程度上",
        "不可否认",
        "毫无疑问",
        "显而易见",
        "不难发现",
        "可以预见",
        "可想而知",
    ]

    CLICHES = [
        "眼中闪过一丝",
        "嘴角微微上扬",
        "心中一动",
        "眉头微皱",
        "瞳孔骤缩",
        "倒吸一口凉气",
        "沉默了片刻",
        "缓缓开口",
        "轻轻点头",
        "暗自思忖",
        "心中暗想",
        "脸色一变",
        "身形一晃",
        "话音刚落",
        "此言一出",
        "此话一出",
    ]

    ADJ_PATTERN = r"(?:十分|非常|特别|格外|相当|极其|无比|异常)[\u4e00-\u9fa5]{2,4}"

    async def check(self, content: str, context: dict[str, Any]) -> GuardResult:
        issues: list[GuardIssue] = []
        paragraphs = self._split_paragraphs(content)
        full_text = content

        ai_phrase_count = 0
        for phrase in self.AI_PHRASES:
            count = full_text.count(phrase)
            ai_phrase_count += count
            if count > 0:
                for match in re.finditer(re.escape(phrase), full_text):
                    para_idx = self._find_paragraph_index(full_text, match.start(), paragraphs)
                    issues.append(
                        GuardIssue(
                            guard_name=self.name,
                            severity=GuardSeverity.INFO,
                            category="meta_discourse",
                            message=f"元话语表达：'{phrase}'",
                            paragraph_index=para_idx,
                            char_offset=match.start(),
                            char_length=len(phrase),
                            suggestion="考虑删除或改写为更自然的表达",
                        )
                    )

        cliche_count = 0
        for cliche in self.CLICHES:
            count = full_text.count(cliche)
            cliche_count += count
            if count > 0:
                for match in re.finditer(re.escape(cliche), full_text):
                    para_idx = self._find_paragraph_index(full_text, match.start(), paragraphs)
                    issues.append(
                        GuardIssue(
                            guard_name=self.name,
                            severity=GuardSeverity.WARNING,
                            category="cliche",
                            message=f"陈词滥调：'{cliche}'",
                            paragraph_index=para_idx,
                            char_offset=match.start(),
                            char_length=len(cliche),
                            suggestion="尝试用更具原创性的描写",
                        )
                    )

        adj_matches = list(re.finditer(self.ADJ_PATTERN, full_text))
        if len(adj_matches) > len(paragraphs) * 0.3:
            for match in adj_matches[:10]:
                para_idx = self._find_paragraph_index(full_text, match.start(), paragraphs)
                issues.append(
                    GuardIssue(
                        guard_name=self.name,
                        severity=GuardSeverity.INFO,
                        category="adj_overuse",
                        message=f"副词+形容词堆砌：'{match.group()}'",
                        paragraph_index=para_idx,
                        char_offset=match.start(),
                        char_length=len(match.group()),
                        suggestion="减少程度副词，用具体动作表现",
                    )
                )

        sentence_pattern_score = self._analyze_sentence_pattern(paragraphs)

        base_score = 100.0
        base_score -= ai_phrase_count * 1.5
        base_score -= cliche_count * 2.0
        base_score -= (100 - sentence_pattern_score) * 0.3

        score = max(20.0, min(100.0, base_score))

        return self._create_result(
            score=score,
            issues=issues[:50],
            metadata={
                "ai_phrase_count": ai_phrase_count,
                "cliche_count": cliche_count,
                "adj_count": len(adj_matches),
                "sentence_pattern_score": sentence_pattern_score,
            },
        )

    def _find_paragraph_index(self, full_text: str, char_pos: int, paragraphs: list[str]) -> int:
        current_pos = 0
        for i, para in enumerate(paragraphs):
            para_start = full_text.find(para, current_pos)
            if para_start <= char_pos < para_start + len(para):
                return i
            current_pos = para_start + len(para) if para_start >= 0 else current_pos
        return 0

    def _analyze_sentence_pattern(self, paragraphs: list[str]) -> float:
        if not paragraphs:
            return 100.0

        sentence_lengths = []
        for para in paragraphs:
            sentences = re.split(r"[。！？!?]", para)
            for s in sentences:
                s = s.strip()
                if s:
                    sentence_lengths.append(len(s))

        if len(sentence_lengths) < 3:
            return 80.0

        avg_len = sum(sentence_lengths) / len(sentence_lengths)
        variance = sum((x - avg_len) ** 2 for x in sentence_lengths) / len(sentence_lengths)
        std_dev = variance**0.5

        cv = std_dev / avg_len if avg_len > 0 else 0

        if cv > 0.5:
            return 90.0
        elif cv > 0.3:
            return 75.0
        elif cv > 0.15:
            return 60.0
        else:
            return 40.0
