from __future__ import annotations

from typing import Any

from application.services.bible_service import BibleService

from .base import Tool, ToolResult


class QueryCharactersTool(Tool):
    name = "query_characters"
    description = "查询小说人物列表，可选传入 character_id 查询单个人物详情。"

    def __init__(self, bible_service: BibleService):
        self.bible_service = bible_service

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "novel_id": {"type": "string", "description": "小说ID"},
                "character_id": {
                    "type": "string",
                    "description": "人物ID（可选，传入则返回该人物详情）",
                },
            },
            "required": ["novel_id"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            novel_id = kwargs["novel_id"]
            character_id = kwargs.get("character_id")

            characters = self.bible_service.list_characters(novel_id)
            items = [
                {
                    "id": c.id,
                    "name": c.name,
                    "role": c.role,
                    "description": c.description,
                    "personality": c.personality,
                    "appearance": c.appearance,
                    "background": c.background,
                }
                for c in characters
            ]

            if character_id:
                target = next((it for it in items if it["id"] == character_id), None)
                if target is None:
                    return ToolResult(
                        success=False,
                        error=f"未找到人物：character_id={character_id}",
                    )
                return ToolResult(
                    success=True,
                    data={"character": target},
                )

            return ToolResult(
                success=True,
                data={"novel_id": novel_id, "total": len(items), "characters": items},
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
