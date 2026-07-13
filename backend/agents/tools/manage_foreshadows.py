from __future__ import annotations

from typing import Any

from infrastructure.persistence.foreshadow_repo import ForeshadowRepository

from .base import Tool, ToolResult


class ManageForeshadowsTool(Tool):
    name = "manage_foreshadows"
    description = "管理小说伏笔：list 查询伏笔列表（可按状态/优先级过滤），update 更新伏笔状态。"

    def __init__(self, foreshadow_repo: ForeshadowRepository):
        self.foreshadow_repo = foreshadow_repo

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "novel_id": {"type": "string", "description": "小说ID"},
                "action": {
                    "type": "string",
                    "enum": ["list", "update"],
                    "description": "操作类型，默认 list",
                },
                "status": {
                    "type": "string",
                    "description": "list 时按状态过滤（planted/resolving/resolved）；update 时为新的状态值",
                },
                "priority": {
                    "type": "string",
                    "description": "list 时按优先级过滤（P1/P2/P3）",
                },
                "foreshadow_id": {
                    "type": "string",
                    "description": "update 操作必填，指定要更新的伏笔ID",
                },
            },
            "required": ["novel_id"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            novel_id = kwargs["novel_id"]
            action = kwargs.get("action", "list")

            if action == "list":
                status = kwargs.get("status")
                priority = kwargs.get("priority")
                foreshadows = self.foreshadow_repo.list_foreshadows(novel_id, status=status, priority=priority)
                items = [
                    {
                        "id": f.id,
                        "title": f.title,
                        "description": f.description,
                        "priority": f.priority,
                        "status": f.status,
                        "planted_chapter_id": f.planted_chapter_id,
                        "planted_chapter_index": f.planted_chapter_index,
                        "resolved_chapter_id": f.resolved_chapter_id,
                        "resolved_chapter_index": f.resolved_chapter_index,
                        "urgency": f.urgency,
                        "tags": f.tags,
                        "notes": f.notes,
                    }
                    for f in foreshadows
                ]
                return ToolResult(
                    success=True,
                    data={
                        "novel_id": novel_id,
                        "total": len(items),
                        "foreshadows": items,
                    },
                )

            if action == "update":
                foreshadow_id = kwargs.get("foreshadow_id")
                if not foreshadow_id:
                    return ToolResult(
                        success=False,
                        error="update 操作需要提供 foreshadow_id",
                    )
                data: dict[str, Any] = {}
                if "status" in kwargs and kwargs["status"] is not None:
                    data["status"] = kwargs["status"]
                # 允许透传其他可更新字段
                for field_name in ("priority", "urgency", "notes", "title", "description"):
                    if field_name in kwargs and kwargs[field_name] is not None:
                        data[field_name] = kwargs[field_name]
                if not data:
                    return ToolResult(
                        success=False,
                        error="update 操作未提供任何可更新字段",
                    )
                updated = self.foreshadow_repo.update_foreshadow(foreshadow_id, data)
                if updated is None:
                    return ToolResult(
                        success=False,
                        error=f"未找到伏笔：foreshadow_id={foreshadow_id}",
                    )
                return ToolResult(
                    success=True,
                    data={
                        "foreshadow_id": updated.id,
                        "title": updated.title,
                        "status": updated.status,
                        "priority": updated.priority,
                    },
                )

            return ToolResult(
                success=False,
                error=f"不支持的操作类型：{action}（仅支持 list / update）",
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
