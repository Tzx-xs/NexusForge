import re
from typing import Any

from .base_guard import BaseGuard, GuardIssue, GuardResult, GuardSeverity


class RhythmGuard(BaseGuard):
    """节奏护栏

    检测：
    - 场景切换频率
    - 长短句分布
    - 段落长度分布
    - 起承转合节奏
    """

    name = "rhythm"
    description = "节奏把控检测"
    weight = 1.5

    async def check(self, content: str, context: dict[str, Any]) -> GuardResult:
        issues: list[GuardIssue] = []
        paragraphs = self._split_paragraphs(content)

        if not paragraphs:
            return self._create_result(score=0, issues=[])

        sentence_stats = self._analyze_sentences(paragraphs)
        paragraph_stats = self._analyze_paragraphs(paragraphs)
        scene_flow = self._analyze_scene_flow(paragraphs)

        rhythm_score = self._calculate_rhythm_score(sentence_stats, paragraph_stats, scene_flow)

        if sentence_stats.get("cv", 0) < 0.2:
            issues.append(
                GuardIssue(
                    guard_name=self.name,
                    severity=GuardSeverity.WARNING,
                    category="monotonous_sentence",
                    message="句式节奏单调，句子长度过于均匀",
                    suggestion="尝试混合使用长短句，制造节奏感",
                )
            )

        if paragraph_stats.get("cv", 0) < 0.2:
            issues.append(
                GuardIssue(
                    guard_name=self.name,
                    severity=GuardSeverity.INFO,
                    category="monotonous_paragraph",
                    message="段落长度过于均匀",
                    suggestion="长短段落交替，重要内容用短段落强调",
                )
            )

        if scene_flow.get("scene_changes", 0) > len(paragraphs) * 0.3:
            issues.append(
                GuardIssue(
                    guard_name=self.name,
                    severity=GuardSeverity.WARNING,
                    category="too_fast_scene",
                    message="场景切换过于频繁",
                    suggestion="适当放慢节奏，让读者有时间消化场景",
                )
            )

        return self._create_result(
            score=rhythm_score,
            issues=issues,
            metadata={
                "sentence_cv": round(sentence_stats.get("cv", 0), 3),
                "paragraph_cv": round(paragraph_stats.get("cv", 0), 3),
                "scene_changes": scene_flow.get("scene_changes", 0),
                "avg_sentence_len": round(sentence_stats.get("avg_len", 0), 1),
                "avg_paragraph_len": round(paragraph_stats.get("avg_len", 0), 1),
            },
        )

    def _analyze_sentences(self, paragraphs: list[str]) -> dict[str, Any]:
        lengths = []
        for para in paragraphs:
            sentences = re.split(r"[。！？!?；;]", para)
            for s in sentences:
                s = s.strip()
                if s:
                    lengths.append(len(s))

        if not lengths:
            return {"avg_len": 0, "cv": 0, "min_len": 0, "max_len": 0}

        avg_len = sum(lengths) / len(lengths)
        variance = sum((x - avg_len) ** 2 for x in lengths) / len(lengths)
        std_dev = variance**0.5
        cv = std_dev / avg_len if avg_len > 0 else 0

        return {
            "avg_len": avg_len,
            "cv": cv,
            "min_len": min(lengths),
            "max_len": max(lengths),
            "count": len(lengths),
        }

    def _analyze_paragraphs(self, paragraphs: list[str]) -> dict[str, Any]:
        lengths = [len(p) for p in paragraphs]

        if not lengths:
            return {"avg_len": 0, "cv": 0}

        avg_len = sum(lengths) / len(lengths)
        variance = sum((x - avg_len) ** 2 for x in lengths) / len(lengths)
        std_dev = variance**0.5
        cv = std_dev / avg_len if avg_len > 0 else 0

        return {
            "avg_len": avg_len,
            "cv": cv,
            "min_len": min(lengths),
            "max_len": max(lengths),
        }

    def _analyze_scene_flow(self, paragraphs: list[str]) -> dict[str, Any]:
        scene_indicators = [
            "转瞬间",
            "转眼间",
            "下一刻",
            "与此同时",
            "画面一转",
            "镜头",
            "视角转到",
        ]

        scene_changes = 0
        for para in paragraphs:
            for ind in scene_indicators:
                if ind in para:
                    scene_changes += 1
                    break

        return {"scene_changes": scene_changes}

    def _calculate_rhythm_score(self, sentence_stats: dict, paragraph_stats: dict, scene_flow: dict) -> float:
        score = 100.0

        sent_cv = sentence_stats.get("cv", 0)
        if sent_cv < 0.2:
            score -= (0.2 - sent_cv) * 150
        elif sent_cv > 0.8:
            score -= (sent_cv - 0.8) * 80

        para_cv = paragraph_stats.get("cv", 0)
        if para_cv < 0.2:
            score -= (0.2 - para_cv) * 80
        elif para_cv > 1.2:
            score -= (para_cv - 1.2) * 40

        avg_sent = sentence_stats.get("avg_len", 0)
        if avg_sent < 10:
            score -= (10 - avg_sent) * 2
        elif avg_sent > 50:
            score -= (avg_sent - 50) * 0.5

        return max(30.0, min(100.0, score))
