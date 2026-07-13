from __future__ import annotations

from typing import Any

from application.services.chapter_service import ChapterService

from .base import Tool, ToolResult


class GenerateChapterTool(Tool):
    name = "generate_chapter"
    description = "生成一章节的小说正文。需指定小说ID，可选指定章节号和章纲。"

    def __init__(self, chapter_service: ChapterService):
        self.chapter_service = chapter_service

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "novel_id": {"type": "string", "description": "小说ID"},
                "chapter_number": {
                    "type": "integer",
                    "description": "章节号（可选，默认下一章）",
                },
                "outline": {"type": "string", "description": "章纲内容（可选）"},
            },
            "required": ["novel_id"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            novel_id = kwargs["novel_id"]
            chapter_number = kwargs.get("chapter_number")
            outline = kwargs.get("outline")
            # M-15: 传递 chapter_number 和 outline 参数到 chapter_service
            chapter = await self.chapter_service.generate_chapter(
                novel_id,
                chapter_number=chapter_number,
                outline=outline,
            )
            if chapter is None:
                return ToolResult(success=False, error="生成章节失败：service 返回 None")
            return ToolResult(
                success=True,
                data={
                    "chapter_id": chapter.id,
                    "chapter_number": chapter.number,
                    "word_count": chapter.word_count or 0,
                    "title": chapter.title,
                    "status": chapter.status,
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
