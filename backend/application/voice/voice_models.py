import hashlib
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class VoiceFingerprint:
    """文风指纹

    多维度量化作者写作风格，用于检测文风漂移和风格一致性。
    """

    fingerprint_id: str = ""
    novel_id: str = ""
    name: str = "default"

    lexical_richness: float = 0.0
    sentence_length_mean: float = 0.0
    sentence_length_std: float = 0.0
    paragraph_length_mean: float = 0.0
    paragraph_length_std: float = 0.0

    unique_char_ratio: float = 0.0
    function_word_ratio: float = 0.0
    content_word_ratio: float = 0.0

    dialogue_ratio: float = 0.0
    narration_ratio: float = 0.0
    description_ratio: float = 0.0

    punctuation_density: dict[str, float] = field(default_factory=dict)

    common_ngrams: list[str] = field(default_factory=list)
    signature_phrases: list[str] = field(default_factory=list)

    sentence_structure_diversity: float = 0.0
    paragraph_starts: list[str] = field(default_factory=list)

    avg_word_per_sentence: float = 0.0
    clause_density: float = 0.0

    source_sample_count: int = 0
    source_char_count: int = 0
    version: int = 1

    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VoiceFingerprint":
        fp = cls()
        for key, value in data.items():
            if hasattr(fp, key):
                setattr(fp, key, value)
        return fp

    def compute_hash(self) -> str:
        data_str = "|".join(
            [
                f"{self.lexical_richness:.4f}",
                f"{self.sentence_length_mean:.2f}",
                f"{self.sentence_length_std:.2f}",
                f"{self.dialogue_ratio:.4f}",
                f"{self.unique_char_ratio:.4f}",
                str(self.source_char_count),
            ]
        )
        return hashlib.md5(data_str.encode()).hexdigest()


@dataclass
class VoiceDriftResult:
    """文风漂移检测结果"""

    drifted: bool
    overall_similarity: float
    dimension_scores: dict[str, float] = field(default_factory=dict)
    drift_dimensions: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "drifted": self.drifted,
            "overall_similarity": self.overall_similarity,
            "dimension_scores": self.dimension_scores,
            "drift_dimensions": self.drift_dimensions,
            "details": self.details,
        }
