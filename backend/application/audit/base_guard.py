from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class GuardSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class GuardIssue:
    guard_name: str
    severity: str
    category: str
    message: str
    location: dict[str, Any] = field(default_factory=dict)
    suggestion: str = ""
    paragraph_index: int | None = None
    char_offset: int | None = None
    char_length: int | None = None


@dataclass
class GuardResult:
    guard_name: str
    passed: bool
    score: float
    issues: list[GuardIssue] = field(default_factory=list)
    duration_ms: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseGuard(ABC):
    """质量护栏基类"""

    name: str = ""
    description: str = ""
    weight: float = 1.0

    @abstractmethod
    async def check(self, content: str, context: dict[str, Any]) -> GuardResult:
        pass

    def _create_result(
        self, score: float, issues: list[GuardIssue], passed: bool | None = None, metadata: dict[str, Any] | None = None
    ) -> GuardResult:
        if passed is None:
            passed = score >= 60.0
        return GuardResult(
            guard_name=self.name,
            passed=passed,
            score=score,
            issues=issues,
            metadata=metadata or {},
        )

    def _split_paragraphs(self, content: str) -> list[str]:
        return [p.strip() for p in content.split("\n") if p.strip()]
