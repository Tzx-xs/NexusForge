import re
from collections import Counter

from .voice_models import VoiceFingerprint

FUNCTION_WORDS = set(
    list("的了是在不我有和就人都一而为以于与及也又但却并")
    + ["之", "其", "此", "那", "这", "何", "孰", "焉", "乎", "哉"]
)


class VoiceExtractor:
    """文风指纹提取器"""

    def extract(self, texts: list[str], name: str = "default", novel_id: str = "") -> VoiceFingerprint:
        if not texts:
            return VoiceFingerprint(name=name, novel_id=novel_id)

        combined = "\n".join(texts)
        paragraphs = self._split_paragraphs(combined)
        sentences = self._split_sentences(combined)
        chars = self._extract_chars(combined)

        fp = VoiceFingerprint()
        fp.name = name
        fp.novel_id = novel_id

        fp.lexical_richness = self._calc_lexical_richness(chars)
        fp.unique_char_ratio = len(set(chars)) / max(len(chars), 1)

        sent_lengths = [len(s) for s in sentences if s.strip()]
        if sent_lengths:
            fp.sentence_length_mean = sum(sent_lengths) / len(sent_lengths)
            variance = sum((x - fp.sentence_length_mean) ** 2 for x in sent_lengths) / len(sent_lengths)
            fp.sentence_length_std = variance**0.5

        para_lengths = [len(p) for p in paragraphs if p.strip()]
        if para_lengths:
            fp.paragraph_length_mean = sum(para_lengths) / len(para_lengths)
            variance = sum((x - fp.paragraph_length_mean) ** 2 for x in para_lengths) / len(para_lengths)
            fp.paragraph_length_std = variance**0.5

        fp.function_word_ratio = self._calc_function_word_ratio(combined)
        fp.content_word_ratio = 1.0 - fp.function_word_ratio

        fp.dialogue_ratio = self._calc_dialogue_ratio(combined)
        fp.narration_ratio = 1.0 - fp.dialogue_ratio
        fp.description_ratio = self._calc_description_ratio(combined)

        fp.punctuation_density = self._calc_punctuation_density(combined)

        fp.common_ngrams = self._extract_ngrams(combined, n=4, top_k=20)
        fp.signature_phrases = self._extract_signature_phrases(combined)

        fp.sentence_structure_diversity = self._calc_sentence_structure_diversity(sentences)

        fp.paragraph_starts = self._extract_paragraph_starts(paragraphs, top_k=10)

        fp.clause_density = self._calc_clause_density(combined)

        fp.source_sample_count = len(texts)
        fp.source_char_count = len(combined)

        fp.fingerprint_id = fp.compute_hash()

        return fp

    def _split_paragraphs(self, text: str) -> list[str]:
        return [p.strip() for p in text.split("\n") if p.strip()]

    def _split_sentences(self, text: str) -> list[str]:
        sentences = re.split(r"[。！？!?；;]", text)
        return [s.strip() for s in sentences if s.strip()]

    def _extract_chars(self, text: str) -> list[str]:
        return [c for c in text if "\u4e00" <= c <= "\u9fff"]

    def _calc_lexical_richness(self, chars: list[str]) -> float:
        if not chars:
            return 0.0
        return len(set(chars)) / len(chars)

    def _calc_function_word_ratio(self, text: str) -> float:
        chars = [c for c in text if "\u4e00" <= c <= "\u9fff"]
        if not chars:
            return 0.0
        func_count = sum(1 for c in chars if c in FUNCTION_WORDS)
        return func_count / len(chars)

    def _calc_dialogue_ratio(self, text: str) -> float:
        if not text:
            return 0.0
        dialogue_chars = 0
        in_quotes = False
        for c in text:
            if c == '"':
                in_quotes = not in_quotes
            elif in_quotes and c.strip():
                dialogue_chars += 1
        return dialogue_chars / len(text)

    def _calc_description_ratio(self, text: str) -> float:
        desc_indicators = [
            "像",
            "如",
            "似",
            "仿佛",
            "犹如",
            "美丽",
            "壮观",
            "雄伟",
            "华丽",
        ]
        desc_count = sum(text.count(ind) for ind in desc_indicators)
        return min(1.0, desc_count / max(len(text) / 100, 1))

    def _calc_punctuation_density(self, text: str) -> dict[str, float]:
        punctuations = ["，", "。", "！", "？", "、", "；", "：", '"', "（", "）"]
        total = len(text) or 1
        return {p: text.count(p) / total for p in punctuations}

    def _extract_ngrams(self, text: str, n: int = 4, top_k: int = 20) -> list[str]:
        ngrams = []
        for i in range(len(text) - n + 1):
            gram = text[i : i + n]
            if all("\u4e00" <= c <= "\u9fff" for c in gram):
                ngrams.append(gram)

        counter = Counter(ngrams)
        return [gram for gram, _ in counter.most_common(top_k)]

    def _extract_signature_phrases(self, text: str) -> list[str]:
        patterns = [
            r"[\u4e00-\u9fa5]{2,4}地[\u4e00-\u9fa5]{1,2}",
            r"[\u4e00-\u9fa5]{2,4}的[\u4e00-\u9fa5]{2,4}",
        ]
        phrases = []
        for pattern in patterns:
            phrases.extend(re.findall(pattern, text))

        counter = Counter(phrases)
        return [p for p, c in counter.most_common(10) if c >= 2]

    def _calc_sentence_structure_diversity(self, sentences: list[str]) -> float:
        if not sentences:
            return 0.0

        patterns = []
        for s in sentences:
            length_bucket = len(s) // 10
            end_char = s[-1] if s else ""
            patterns.append(f"{length_bucket}_{end_char}")

        unique = len(set(patterns))
        return unique / max(len(patterns), 1)

    def _extract_paragraph_starts(self, paragraphs: list[str], top_k: int = 10) -> list[str]:
        starts = []
        for p in paragraphs:
            if len(p) >= 2:
                starts.append(p[:2])
        counter = Counter(starts)
        return [s for s, _ in counter.most_common(top_k)]

    def _calc_clause_density(self, text: str) -> float:
        if not text:
            return 0.0
        commas = text.count("，") + text.count(",")
        periods = text.count("。") + text.count(".")
        total_sentences = max(periods, 1)
        return commas / total_sentences
