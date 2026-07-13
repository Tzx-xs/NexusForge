"""AI Invocation 数据模型"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class InvocationStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class InvocationRecord:
    """LLM 调用记录（可观测/可审计/可重放）"""
    id: str
    stage: str                          # 阶段（generate/aftermath/review/...）
    operation: str                      # 操作（chapter_content/extract_summary/...）
    prompt_key: str                     # 提示词键
    novel_id: str | None = None
    chapter_number: int | None = None
    session_id: str | None = None
    prompt_text: str = ""
    prompt_variables: dict[str, Any] = field(default_factory=dict)
    model: str = ""
    provider: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    output_text: str = ""
    output_metadata: dict[str, Any] = field(default_factory=dict)
    tokens_input: int = 0
    tokens_output: int = 0
    duration_ms: int = 0
    status: InvocationStatus = InvocationStatus.SUCCESS
    error: str = ""
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "stage": self.stage,
            "operation": self.operation,
            "prompt_key": self.prompt_key,
            "novel_id": self.novel_id,
            "chapter_number": self.chapter_number,
            "session_id": self.session_id,
            "model": self.model,
            "provider": self.provider,
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "error": self.error,
            "created_at": self.created_at,
        }
