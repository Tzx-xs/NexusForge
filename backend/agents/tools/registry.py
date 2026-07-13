from __future__ import annotations

from typing import Any

from application.services.bible_service import BibleService
from application.services.chapter_service import ChapterService
from application.services.export_service import ExportService
from application.services.novel_service import NovelService
from application.services.review_service import ReviewService
from infrastructure.ai.llm_client import LLMClient
from infrastructure.persistence.foreshadow_repo import ForeshadowRepository

from .analyze_plot import AnalyzePlotTool
from .base import Tool
from .delete_character import DeleteCharacterTool
from .edit_paragraph import EditParagraphTool
from .export_novel import ExportNovelTool
from .generate_chapter import GenerateChapterTool
from .manage_foreshadows import ManageForeshadowsTool
from .polish_content import PolishContentTool
from .query_bible import QueryBibleTool
from .query_characters import QueryCharactersTool
from .review_chapter import ReviewChapterTool


class ToolRegistry:
    """Tool 注册表，管理所有可用工具"""

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if not tool.name:
            raise ValueError("Tool must have a name")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def list_names(self) -> list[str]:
        return list(self._tools.keys())

    def to_openai_schemas(self) -> list[dict[str, Any]]:
        """返回所有工具的 OpenAI Function Calling schema 列表"""
        return [tool.to_openai_schema() for tool in self._tools.values()]

    @classmethod
    def create_default(
        cls,
        chapter_service: ChapterService,
        review_service: ReviewService,
        bible_service: BibleService,
        export_service: ExportService,
        foreshadow_repo: ForeshadowRepository,
        llm_client: LLMClient | None = None,
        novel_service: NovelService | None = None,
    ) -> ToolRegistry:
        """用默认 10 个工具创建注册表"""
        registry = cls()
        # 原有 6 个工具
        registry.register(GenerateChapterTool(chapter_service))
        registry.register(ReviewChapterTool(review_service))
        registry.register(QueryBibleTool(bible_service))
        registry.register(QueryCharactersTool(bible_service))
        registry.register(ManageForeshadowsTool(foreshadow_repo))
        registry.register(ExportNovelTool(export_service))
        # 新增 4 个工具（Sprint 审查优化）
        registry.register(EditParagraphTool(chapter_service))
        registry.register(DeleteCharacterTool(bible_service))
        if llm_client is not None:
            registry.register(PolishContentTool(chapter_service, llm_client))
            if novel_service is not None:
                registry.register(AnalyzePlotTool(chapter_service, novel_service, llm_client))
        return registry
