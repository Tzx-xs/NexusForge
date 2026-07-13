from __future__ import annotations

from typing import Any

from application.services.export_service import ExportFormat, ExportOptions, ExportService

from .base import Tool, ToolResult


class ExportNovelTool(Tool):
    name = "export_novel"
    description = "导出小说为指定格式（txt/md/html/docx/epub），返回导出文件名与字节数。"

    def __init__(self, export_service: ExportService):
        self.export_service = export_service

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "novel_id": {"type": "string", "description": "小说ID"},
                "format": {
                    "type": "string",
                    "enum": ["txt", "md", "html", "docx", "epub"],
                    "description": "导出格式，默认 txt",
                },
                "title": {"type": "string", "description": "自定义标题（可选）"},
                "author": {"type": "string", "description": "自定义作者（可选）"},
            },
            "required": ["novel_id"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            novel_id = kwargs["novel_id"]
            fmt_str = kwargs.get("format", "txt")

            try:
                fmt = ExportFormat(fmt_str)
            except ValueError:
                fmt = ExportFormat.TXT

            options = ExportOptions(format=fmt)
            if "title" in kwargs and kwargs["title"]:
                options.title = kwargs["title"]
            if "author" in kwargs and kwargs["author"]:
                options.author = kwargs["author"]

            content_bytes = self.export_service.export_novel(novel_id, options)
            filename = self.export_service.get_export_filename(novel_id, options)

            return ToolResult(
                success=True,
                data={
                    "novel_id": novel_id,
                    "format": fmt.value,
                    "filename": filename,
                    "byte_size": len(content_bytes),
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
