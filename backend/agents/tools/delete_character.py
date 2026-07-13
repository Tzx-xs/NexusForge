from __future__ import annotations

from typing import Any

from application.services.bible_service import BibleService

from .base import Tool, ToolResult


class DeleteCharacterTool(Tool):
    name = "delete_character"
    description = "软删除指定小说中的角色（名称前添加 [已删除] 标记），需显式确认 confirm=true 才执行。"
    requires_confirmation = True

    def __init__(self, bible_service: BibleService):
        self.bible_service = bible_service

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "novel_id": {"type": "string", "description": "小说ID"},
                "character_id": {"type": "string", "description": "要删除的角色ID"},
                "confirm": {
                    "type": "boolean",
                    "description": "确认删除（必须显式传 true 才会执行软删除）",
                },
            },
            "required": ["novel_id", "character_id"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            novel_id = kwargs["novel_id"]
            character_id = kwargs["character_id"]
            confirm = kwargs.get("confirm", False)

            # 通过小说查找角色
            characters = self.bible_service.list_characters(novel_id)
            target = next((c for c in characters if c.id == character_id), None)

            if target is None:
                return ToolResult(
                    success=False,
                    error=f"未找到角色：character_id={character_id}（在小说 {novel_id} 中）",
                )

            if not confirm:
                return ToolResult(
                    success=True,
                    data={
                        "character_id": target.id,
                        "novel_id": novel_id,
                        "name": target.name,
                        "role": target.role,
                        "action": "preview",
                        "message": f"角色「{target.name}」将被标记为已删除。请将 confirm 设为 true 以确认执行。",
                    },
                )

            # 执行软删除：名称前添加标记，描述中追加标记记录
            new_name = f"[已删除] {target.name}"
            updated = self.bible_service.update_character(
                character_id,
                name=new_name,
                description=f"{target.description or ''}\n[软删除标记] 此角色已被标记为删除。".strip(),
            )

            return ToolResult(
                success=True,
                data={
                    "character_id": updated.id,
                    "novel_id": novel_id,
                    "name": updated.name,
                    "role": updated.role,
                    "action": "soft_deleted",
                    "message": f"角色「{target.name}」已标记为软删除。",
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
