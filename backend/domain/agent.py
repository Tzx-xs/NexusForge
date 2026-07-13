from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Conversation:
    """Agent 对话会话"""

    id: str
    novel_id: str | None = None
    title: str = ""
    created_at: float | None = None
    updated_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "novel_id": self.novel_id,
            "title": self.title,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class Message:
    """Agent 对话消息"""

    id: str
    conversation_id: str
    role: str  # "user" / "assistant" / "tool"
    content: str = ""
    tool_calls: str | None = None  # JSON 字符串，记录 LLM 的 tool_call 决策
    tool_name: str | None = None  # role="tool" 时记录工具名
    created_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "tool_calls": self.tool_calls,
            "tool_name": self.tool_name,
            "created_at": self.created_at,
        }
