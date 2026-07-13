from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    """工具执行结果"""

    success: bool
    data: dict[str, Any] = field(default_factory=dict)
    error: str = ""


class Tool(ABC):
    """Tool 基类，所有 Agent 工具继承此类"""

    name: str = ""
    description: str = ""
    depends_on: list[str] = []
    requires_confirmation: bool = False

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """返回 JSON Schema 格式的参数定义（OpenAI Function Calling 兼容）"""
        ...

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """执行工具，返回 ToolResult"""
        ...

    def validate_args(self, tool_args: dict) -> tuple[bool, str | None]:
        """校验工具参数是否符合 parameters schema.

        Returns:
            (is_valid, error_message) — is_valid 为 True 表示通过；
            False 时 error_message 说明原因。
        """
        params = self.parameters
        if not params or params.get("type") != "object":
            return True, None
        try:
            import jsonschema
            jsonschema.validate(tool_args, params)
            return True, None
        except jsonschema.ValidationError as e:
            return False, str(e.message)
        except ImportError:
            return True, None

    def to_openai_schema(self) -> dict[str, Any]:
        """转换为 OpenAI Function Calling 的 tool schema 格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
