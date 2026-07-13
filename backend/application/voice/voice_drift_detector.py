from .voice_models import VoiceDriftResult, VoiceFingerprint


class VoiceDriftDetector:
    """文风漂移检测器"""

    DEFAULT_THRESHOLDS = {
        "lexical_richness": 0.8,
        "sentence_length_mean": 0.7,
        "sentence_length_std": 0.6,
        "paragraph_length_mean": 0.6,
        "dialogue_ratio": 0.7,
        "function_word_ratio": 0.8,
        "punctuation_density": 0.7,
        "ngram_overlap": 0.5,
    }

    def detect(
        self, baseline: VoiceFingerprint, sample: VoiceFingerprint, thresholds: dict[str, float] | None = None
    ) -> VoiceDriftResult:
        thresholds = thresholds or self.DEFAULT_THRESHOLDS

        dimension_scores: dict[str, float] = {}

        dimension_scores["lexical_richness"] = self._similarity(baseline.lexical_richness, sample.lexical_richness)

        dimension_scores["sentence_length_mean"] = self._similarity(
            baseline.sentence_length_mean, sample.sentence_length_mean
        )

        dimension_scores["sentence_length_std"] = self._similarity(
            baseline.sentence_length_std, sample.sentence_length_std
        )

        dimension_scores["paragraph_length_mean"] = self._similarity(
            baseline.paragraph_length_mean, sample.paragraph_length_mean
        )

        dimension_scores["dialogue_ratio"] = self._similarity(baseline.dialogue_ratio, sample.dialogue_ratio)

        dimension_scores["function_word_ratio"] = self._similarity(
            baseline.function_word_ratio, sample.function_word_ratio
        )

        dimension_scores["punctuation_density"] = self._dict_similarity(
            baseline.punctuation_density, sample.punctuation_density
        )

        dimension_scores["ngram_overlap"] = self._list_overlap(baseline.common_ngrams, sample.common_ngrams)

        weights = {
            "lexical_richness": 0.15,
            "sentence_length_mean": 0.15,
            "sentence_length_std": 0.1,
            "paragraph_length_mean": 0.1,
            "dialogue_ratio": 0.15,
            "function_word_ratio": 0.15,
            "punctuation_density": 0.1,
            "ngram_overlap": 0.1,
        }

        overall = sum(dimension_scores.get(d, 0) * weights.get(d, 0) for d in weights)

        drift_dimensions = []
        for dim, score in dimension_scores.items():
            threshold = thresholds.get(dim, 0.7)
            if score < threshold:
                drift_dimensions.append(dim)

        drifted = len(drift_dimensions) >= 2 or overall < 0.7

        return VoiceDriftResult(
            drifted=drifted,
            overall_similarity=round(overall, 4),
            dimension_scores={k: round(v, 4) for k, v in dimension_scores.items()},
            drift_dimensions=drift_dimensions,
            details={
                "baseline_sample_count": baseline.source_sample_count,
                "sample_sample_count": sample.source_sample_count,
                "baseline_char_count": baseline.source_char_count,
                "sample_char_count": sample.source_char_count,
            },
        )

    def _similarity(self, a: float, b: float) -> float:
        if a == 0 and b == 0:
            return 1.0
        if a == 0 or b == 0:
            return 0.5
        diff = abs(a - b) / max(abs(a), abs(b))
        return max(0.0, 1.0 - diff)

    def _dict_similarity(self, a: dict[str, float], b: dict[str, float]) -> float:
        if not a and not b:
            return 1.0
        keys = set(a.keys()) | set(b.keys())
        if not keys:
            return 1.0
        total_sim = 0.0
        for k in keys:
            va = a.get(k, 0.0)
            vb = b.get(k, 0.0)
            total_sim += self._similarity(va, vb)
        return total_sim / len(keys)

    def _list_overlap(self, a: list[str], b: list[str]) -> float:
        if not a and not b:
            return 1.0
        if not a or not b:
            return 0.0
        set_a = set(a)
        set_b = set(b)
        intersection = set_a & set_b
        union = set_a | set_b
        return len(intersection) / len(union) if union else 1.0
