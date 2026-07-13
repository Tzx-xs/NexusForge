"""检查点数据模型"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class CheckpointStatus(StrEnum):
    ACTIVE = "active"      # 活跃（当前可恢复）
    ARCHIVED = "archived"  # 已归档（被新检查点替代）


@dataclass
class Checkpoint:
    """引擎检查点快照（崩溃恢复用）"""
    id: str
    novel_id: str
    chapter_number: int | None = None
    pipeline_run_id: str | None = None
    step_name: str = ""
    step_status: str = "success"
    context_snapshot: dict[str, Any] = field(default_factory=dict)
    audit_snapshot: dict[str, Any] = field(default_factory=dict)
    status: CheckpointStatus = CheckpointStatus.ACTIVE
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "novel_id": self.novel_id,
            "chapter_number": self.chapter_number,
            "pipeline_run_id": self.pipeline_run_id,
            "step_name": self.step_name,
            "step_status": self.step_status,
            "context_snapshot": self.context_snapshot,
            "audit_snapshot": self.audit_snapshot,
            "status": self.status.value,
        }
