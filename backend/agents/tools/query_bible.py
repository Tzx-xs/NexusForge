from __future__ import annotations

from typing import Any

from application.services.bible_service import BibleService

from .base import Tool, ToolResult


class QueryBibleTool(Tool):
    name = "query_bible"
    description = "查询小说设定库（世界观/地点/势力等设定）。可选按设定类型过滤。"

    def __init__(self, bible_service: BibleService):
        self.bible_service = bible_service

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "novel_id": {"type": "string", "description": "小说ID"},
                "setting_type": {
                    "type": "string",
                    "description": "设定类型（可选，如 world/character/location/other）",
                },
            },
            "required": ["novel_id"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            novel_id = kwargs["novel_id"]
            setting_type = kwargs.get("setting_type")

            settings = self.bible_service.list_settings(novel_id, setting_type=setting_type)
            items = []
            for s in settings:
                items.append(
                    {
                        "id": s.id,
                        "name": s.name,
                        "setting_type": s.setting_type,
                        "description": s.description,
                        "parent_id": s.parent_id,
                    }
                )

            return ToolResult(
                success=True,
                data={
                    "novel_id": novel_id,
                    "setting_type": setting_type,
                    "total": len(items),
                    "settings": items,
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
