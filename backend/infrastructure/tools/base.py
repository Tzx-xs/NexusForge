from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class Violation:
    rule_id: int
    rule_name: str
    description: str
    severity: str = "medium"
    position: dict | None = field(default_factory=dict)


@dataclass
class TextStats:
    chinese_chars: int = 0
    total_chars: int = 0
    paragraphs: int = 0
    dialogues: int = 0
    sentences: int = 0
    avg_paragraph_length: float = 0.0
    dialogue_ratio: float = 0.0


@dataclass
class QualityScore:
    total_score: float = 0.0
    grade: str = ""
    dimension_scores: dict = field(default_factory=dict)
    issues: list = field(default_factory=list)
    suggestions: list = field(default_factory=list)
    overall_comment: str = ""


class BaseTool(ABC):
    name: str = "base_tool"
    description: str = ""

    @abstractmethod
    def run(self, *args, **kwargs): ...

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(name={self.name})>"
