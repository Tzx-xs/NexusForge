import re
from collections import Counter
from typing import Any

from .base_guard import BaseGuard, GuardIssue, GuardResult, GuardSeverity


class LanguageStyleGuard(BaseGuard):
    """语言风格护栏

    检测：
    - 词汇丰富度
    - 句式多样性
    - 重复用词
    - 语病/不通顺
    """

    name = "language_style"
    description = "语言风格检测"
    weight = 2.0

    COMMON_WORDS = set("的了一是不人在有他这我来们到说大要去也就和那你都要而")

    async def check(self, content: str, context: dict[str, Any]) -> GuardResult:
        issues: list[GuardIssue] = []
        paragraphs = self._split_paragraphs(content)

        if not paragraphs:
            return self._create_result(score=0, issues=[])

        vocab_richness = self._calculate_vocab_richness(content)
        sentence_diversity = self._calculate_sentence_diversity(paragraphs)
        repetition_score = self._check_repetition(content, paragraphs, issues)
        filler_score = self._check_filler_words(content, issues)

        overall_score = vocab_richness * 0.3 + sentence_diversity * 0.3 + repetition_score * 0.2 + filler_score * 0.2

        return self._create_result(
            score=round(overall_score, 1),
            issues=issues[:30],
            metadata={
                "vocab_richness": round(vocab_richness, 1),
                "sentence_diversity": round(sentence_diversity, 1),
                "repetition_score": round(repetition_score, 1),
                "filler_score": round(filler_score, 1),
            },
        )

    def _calculate_vocab_richness(self, text: str) -> float:
        chars = [c for c in text if "\u4e00" <= c <= "\u9fff"]
        if not chars:
            return 50.0

        unique_chars = set(chars)
        ttr = len(unique_chars) / len(chars)

        if ttr > 0.6:
            return 95.0
        elif ttr > 0.5:
            return 85.0
        elif ttr > 0.4:
            return 70.0
        elif ttr > 0.3:
            return 55.0
        else:
            return 40.0

    def _calculate_sentence_diversity(self, paragraphs: list[str]) -> float:
        sentence_lengths = []
        for para in paragraphs:
            sentences = re.split(r"[。！？!?；;]", para)
            for s in sentences:
                s = s.strip()
                if s:
                    sentence_lengths.append(len(s))

        if len(sentence_lengths) < 5:
            return 70.0

        avg_len = sum(sentence_lengths) / len(sentence_lengths)
        variance = sum((x - avg_len) ** 2 for x in sentence_lengths) / len(sentence_lengths)
        std_dev = variance**0.5
        cv = std_dev / avg_len if avg_len > 0 else 0

        if cv > 0.6:
            return 90.0
        elif cv > 0.4:
            return 75.0
        elif cv > 0.25:
            return 60.0
        else:
            return 45.0

    def _check_repetition(self, content: str, paragraphs: list[str], issues: list[GuardIssue]) -> float:
        score = 100.0

        char_ngrams = []
        for i in range(len(content) - 3):
            gram = content[i : i + 4]
            if all("\u4e00" <= c <= "\u9fff" for c in gram):
                char_ngrams.append(gram)

        ngram_counts = Counter(char_ngrams)
        repeated = [(g, c) for g, c in ngram_counts.most_common(10) if c >= 3]

        for gram, count in repeated[:5]:
            para_idx = self._find_para_of_ngram(content, gram, paragraphs)
            issues.append(
                GuardIssue(
                    guard_name=self.name,
                    severity=GuardSeverity.WARNING,
                    category="word_repetition",
                    message=f"词语重复：'{gram}' 出现 {count} 次",
                    paragraph_index=para_idx,
                    suggestion="考虑使用同义词或改写",
                )
            )
            score -= count * 2

        para_starts = [p[:2] for p in paragraphs if len(p) >= 2]
        start_counts = Counter(para_starts)
        for start, count in start_counts.most_common(5):
            if count >= 3:
                issues.append(
                    GuardIssue(
                        guard_name=self.name,
                        severity=GuardSeverity.INFO,
                        category="paragraph_start_repetition",
                        message=f"段落开头重复：'{start}...' 出现 {count} 次",
                        suggestion="变换段落开头方式，增加句式变化",
                    )
                )
                score -= count * 3

        return max(30.0, score)

    def _check_filler_words(self, content: str, issues: list[GuardIssue]) -> float:
        score = 100.0
        fillers = [
            "然后",
            "就是",
            "其实",
            "反正",
            "总之",
            "那个",
            "这个",
            "嗯",
            "啊",
            "哦",
        ]

        total_fillers = 0
        for filler in fillers:
            count = content.count(filler)
            total_fillers += count
            if count > 5:
                issues.append(
                    GuardIssue(
                        guard_name=self.name,
                        severity=GuardSeverity.INFO,
                        category="filler_word",
                        message=f"口头禅/填充词：'{filler}' 出现 {count} 次",
                        suggestion="减少填充词，让语言更精炼",
                    )
                )

        if total_fillers > 20:
            score -= total_fillers * 0.5

        return max(50.0, score)

    def _find_para_of_ngram(self, content: str, gram: str, paragraphs: list[str]) -> int:
        pos = content.find(gram)
        if pos < 0:
            return 0
        current = 0
        for i, p in enumerate(paragraphs):
            p_start = content.find(p, current)
            if p_start >= 0 and p_start <= pos < p_start + len(p):
                return i
            if p_start >= 0:
                current = p_start + len(p)
        return 0
