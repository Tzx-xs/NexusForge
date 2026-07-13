from __future__ import annotations

from typing import Any

from application.services.chapter_service import ChapterService
from infrastructure.ai.llm_client import LLMClient

from .base import Tool, ToolResult


class PolishContentTool(Tool):
    name = "polish_content"
    description = "对指定章节进行润色，去除 AI 写作痕迹，提升文笔自然度。可选指定润色强度。"

    def __init__(self, chapter_service: ChapterService, llm_client: LLMClient):
        self.chapter_service = chapter_service
        self.llm_client = llm_client

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "chapter_id": {"type": "string", "description": "章节ID"},
                "intensity": {
                    "type": "string",
                    "enum": ["light", "medium", "heavy"],
                    "description": "润色强度：light 轻度（保留原文结构），medium 中度（优化句式），heavy 重度（深度改写）。默认 medium",
                },
                "focus": {
                    "type": "string",
                    "description": "润色侧重点（可选，如 '去AI味'/'增强文学性'/'对话优化'）",
                },
            },
            "required": ["chapter_id"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            chapter_id = kwargs["chapter_id"]
            intensity = kwargs.get("intensity", "medium")
            focus = kwargs.get("focus", "去AI味，增强文学性和可读性")

            chapter = self.chapter_service.get_chapter(chapter_id)
            original_content = chapter.content or ""
            if not original_content.strip():
                return ToolResult(success=False, error="章节内容为空，无法润色")

            intensity_map = {
                "light": "轻度润色，仅修正明显的 AI 痕迹和生硬表达，保留绝大部分原文结构和用词",
                "medium": "中度润色，优化句式结构，丰富词汇，让行文更接近人类写作风格",
                "heavy": "重度润色，深度改写以消除所有 AI 痕迹，在保留原意前提下追求文学品质",
            }
            intensity_desc = intensity_map.get(intensity, intensity_map["medium"])

            polish_prompt = f"""请对以下章节内容进行润色。
润色强度：{intensity_desc}
侧重点：{focus}

润色要求：
1. 去除 AI 写作痕迹（如过于规整的句式、机械的过渡词、生硬的比喻等）
2. 增强语言的文学性和可读性
3. 保持原文的核心内容、情节和人物性格不变
4. 保留对话的自然感
5. 不要添加原文没有的情节

原始内容：
{original_content}

请返回润色后的完整内容（不要加任何解释性文字）。"""

            polished = await self.llm_client.chat(polish_prompt)

            # 更新章节内容
            updated = self.chapter_service.update_chapter(chapter_id, content=polished)

            return ToolResult(
                success=True,
                data={
                    "chapter_id": updated.id,
                    "chapter_number": updated.number,
                    "title": updated.title,
                    "intensity": intensity,
                    "original_word_count": len(original_content),
                    "polished_word_count": updated.word_count,
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
