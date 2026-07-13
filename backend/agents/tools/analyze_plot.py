from __future__ import annotations

from typing import Any

from application.services.chapter_service import ChapterService
from application.services.novel_service import NovelService
from infrastructure.ai.llm_client import LLMClient

from .base import Tool, ToolResult


class AnalyzePlotTool(Tool):
    name = "analyze_plot"
    description = "分析小说整体情节结构（起承转合/三幕式），识别节奏问题与结构缺陷。"

    def __init__(
        self,
        chapter_service: ChapterService,
        novel_service: NovelService,
        llm_client: LLMClient,
    ):
        self.chapter_service = chapter_service
        self.novel_service = novel_service
        self.llm_client = llm_client

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "novel_id": {"type": "string", "description": "小说ID"},
                "analysis_type": {
                    "type": "string",
                    "enum": ["structure", "pacing", "full"],
                    "description": "分析类型：structure 情节结构，pacing 节奏分析，full 完整分析。默认 full",
                },
            },
            "required": ["novel_id"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        try:
            novel_id = kwargs["novel_id"]
            analysis_type = kwargs.get("analysis_type", "full")

            novel = self.novel_service.get_novel(novel_id)
            chapters = self.chapter_service.list_chapters(novel_id)

            if not chapters:
                return ToolResult(
                    success=False,
                    error=f"小说「{novel.title}」尚无章节，无法分析情节结构",
                )

            # 构建章节摘要
            chapter_summaries = []
            for ch in chapters:
                content_preview = (ch.content or "")[:500].replace("\n", " ")
                chapter_summaries.append(
                    f"第{ch.number}章「{ch.title}」({ch.word_count}字) | {ch.status}\n"
                    f"内容预览：{content_preview}..."
                )

            chapters_text = "\n\n".join(chapter_summaries)

            analysis_prompt = ""
            if analysis_type == "structure":
                analysis_prompt = f"""请分析以下小说的情节结构。

小说：{novel.title}
类型：{novel.genre or '未指定'}
总章节数：{len(chapters)}

各章节信息：
{chapters_text}

请以 JSON 格式返回分析结果：
{{
    "structure_type": "三幕式/起承转合/多线并进等",
    "acts": [
        {{"name": "第一幕/起", "chapters": "第1-3章", "description": "..."}},
        ...
    ],
    "turning_points": [
        {{"chapter": 3, "name": "激励事件", "description": "..."}}
    ],
    "structure_score": 80,
    "issues": ["..."],
    "suggestions": ["..."]
}}"""
            elif analysis_type == "pacing":
                analysis_prompt = f"""请分析以下小说的叙事节奏。

小说：{novel.title}
总章节数：{len(chapters)}

各章节信息：
{chapters_text}

请以 JSON 格式返回分析结果：
{{
    "pacing_curve": [
        {{"chapter": 1, "tension": 50, "description": "..."}},
        ...
    ],
    "avg_chapter_length": 0,
    "pacing_score": 80,
    "slow_sections": ["..."],
    "rushed_sections": ["..."],
    "suggestions": ["..."]
}}"""
            else:
                analysis_prompt = f"""请完整分析以下小说的情节结构与叙事节奏。

小说：{novel.title}
类型：{novel.genre or '未指定'}
总章节数：{len(chapters)}

各章节信息：
{chapters_text}

请以 JSON 格式返回完整分析结果：
{{
    "structure_type": "三幕式/起承转合/多线并进等",
    "acts": [
        {{"name": "第一幕/起", "chapters": "第1-3章", "description": "..."}}
    ],
    "turning_points": [
        {{"chapter": 3, "name": "激励事件", "description": "..."}}
    ],
    "pacing_curve": [
        {{"chapter": 1, "tension": 50, "description": "..."}}
    ],
    "structure_score": 80,
    "pacing_score": 75,
    "overall_score": 78,
    "issues": ["..."],
    "suggestions": ["..."]
}}"""

            result = await self.llm_client.chat_json(analysis_prompt)

            return ToolResult(
                success=True,
                data={
                    "novel_id": novel_id,
                    "title": novel.title,
                    "total_chapters": len(chapters),
                    "analysis_type": analysis_type,
                    **result,
                },
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
