from __future__ import annotations

from typing import Any

from application.services.chapter_service import ChapterService

from .base import Tool, ToolResult


class EditParagraphTool(Tool):
    name = "edit_paragraph"
    description = "编辑指定章节的指定段落，支持替换段落内容或插入新段落。"

    def __init__(self, chapter_service: ChapterService):
        self.chapter_service = chapter_service

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "chapter_id": {"type": "string", "description": "章节ID"},
                "paragraph_index": {
                    "type": "integer",
                    "description": "段落序号（从 0 开始，传入 -1 表示追加到末尾）",
                },
                "new_content": {
                    "type": "string",
                    "description": "新的段落内容",
                },
                "mode": {
                    "type": "string",
                    "enum": ["replace", "insert_after"],
                    "description": "编辑模式：replace 替换指定段落，insert_after 在指定段落后插入新段落。默认 replace",
                },
            },
            "required": ["chapter_id", "paragraph_index", "new_content"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            chapter_id = kwargs["chapter_id"]
            paragraph_index = int(kwargs["paragraph_index"])
            new_content = kwargs["new_content"]
            mode = kwargs.get("mode", "replace")

            chapter = self.chapter_service.get_chapter(chapter_id)
            content = chapter.content or ""

            # 按空行分割段落
            paragraphs = [p for p in content.split("\n\n")] if content.strip() else []

            if mode == "replace":
                if paragraph_index < 0 or paragraph_index >= len(paragraphs):
                    return ToolResult(
                        success=False,
                        error=f"段落序号 {paragraph_index} 超出范围（共 {len(paragraphs)} 段）",
                    )
                paragraphs[paragraph_index] = new_content
            elif mode == "insert_after":
                if paragraph_index < -1 or paragraph_index >= len(paragraphs):
                    return ToolResult(
                        success=False,
                        error=f"段落序号 {paragraph_index} 超出范围（共 {len(paragraphs)} 段，-1 表示末尾）",
                    )
                if paragraph_index == -1:
                    paragraphs.append(new_content)
                else:
                    paragraphs.insert(paragraph_index + 1, new_content)
            else:
                return ToolResult(success=False, error=f"不支持的编辑模式：{mode}（仅支持 replace / insert_after）")

            new_full_content = "\n\n".join(paragraphs)
            updated = self.chapter_service.update_chapter(chapter_id, content=new_full_content)

            return ToolResult(
                success=True,
                data={
                    "chapter_id": updated.id,
                    "chapter_number": updated.number,
                    "paragraph_index": paragraph_index,
                    "mode": mode,
                    "word_count": updated.word_count,
                    "total_paragraphs": len(paragraphs),
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
