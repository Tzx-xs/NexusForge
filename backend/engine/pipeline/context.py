from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class PipelineStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class StepResult:
    step_name: str
    status: str
    duration_ms: int = 0
    output: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StepResult":
        return cls(**data)


@dataclass
class PipelineContext:
    novel_id: str
    chapter_id: str | None = None
    chapter_index: int | None = None

    status: PipelineStatus = PipelineStatus.PENDING
    current_step: str = ""

    data: dict[str, Any] = field(default_factory=dict)
    step_results: list[StepResult] = field(default_factory=list)

    started_at: float | None = None
    completed_at: float | None = None
    total_tokens_used: int = 0
    retry_count: dict[str, int] = field(default_factory=dict)

    # Aftermath step outputs (dynamically populated)
    summary: Any = None
    knowledge_triples: list[Any] = field(default_factory=list)
    fact_locks: list[Any] = field(default_factory=list)
    beat_locks: list[Any] = field(default_factory=list)
    clue_locks: list[Any] = field(default_factory=list)
    snapshot: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    def set(self, key: str, value: Any):
        self.data[key] = value

    def add_step_result(self, result: StepResult):
        self.step_results.append(result)

    def to_dict(self) -> dict[str, Any]:
        """将 PipelineContext 序列化为字典用于持久化。"""
        return {
            "novel_id": self.novel_id,
            "chapter_id": self.chapter_id,
            "chapter_index": self.chapter_index,
            "status": self.status.value,
            "current_step": self.current_step,
            "data": self.data,
            "step_results": [sr.to_dict() for sr in self.step_results],
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_tokens_used": self.total_tokens_used,
            "retry_count": self.retry_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PipelineContext":
        """从字典反序列化还原 PipelineContext。"""
        ctx = cls(
            novel_id=data.get("novel_id", ""),
            chapter_id=data.get("chapter_id"),
            chapter_index=data.get("chapter_index"),
        )
        ctx.status = PipelineStatus(data.get("status", "pending"))
        ctx.current_step = data.get("current_step", "")
        ctx.data = data.get("data", {})
        ctx.step_results = [
            StepResult.from_dict(sr) for sr in data.get("step_results", [])
        ]
        ctx.started_at = data.get("started_at")
        ctx.completed_at = data.get("completed_at")
        ctx.total_tokens_used = data.get("total_tokens_used", 0)
        ctx.retry_count = data.get("retry_count", {})
        return ctx
