from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from application.engine.generation_pipeline import GenerationPipeline
from domain.chapter import Chapter
from domain.chapter_status import ChapterStatus
from domain.novel import Novel
from domain.shared.exceptions import (
    ChapterNotFoundException,
    NovelNotFoundException,
    SnapshotNotFoundException,
)
from engine.pipeline.base import StoryPipeline
from infrastructure.persistence.chapter_repo import ChapterRepository
from infrastructure.persistence.novel_repo import NovelRepository


class ChapterService:
    def __init__(
        self,
        chapter_repo: ChapterRepository,
        novel_repo: NovelRepository,
        generation_pipeline: GenerationPipeline,
        story_pipeline: StoryPipeline,
    ) -> None:
        self.chapter_repo = chapter_repo
        self.novel_repo = novel_repo
        self.generation_pipeline = generation_pipeline
        self.story_pipeline = story_pipeline

    def list_chapters(self, novel_id: str) -> list[Chapter]:
        return self.chapter_repo.list_by_novel(novel_id)

    def get_chapter(self, chapter_id: str) -> Chapter:
        chapter = self.chapter_repo.get_by_id(chapter_id)
        if not chapter:
            raise ChapterNotFoundException()
        return chapter

    def create_chapter(self, novel_id: str, title: str = "", number: int | None = None) -> Chapter:
        novel = self.novel_repo.get_by_id(novel_id)
        if not novel:
            raise NovelNotFoundException()

        if number is None:
            chapters = self.chapter_repo.list_by_novel(novel_id)
            number = len(chapters) + 1

        chapter = Chapter(novel_id=novel_id, title=title, number=number)
        created = self.chapter_repo.create(chapter)

        if number > novel.current_chapter:
            novel.current_chapter = number
            novel.updated_at = Novel.timestamps()
            self.novel_repo.update(novel)

        return created

    def update_chapter(self, chapter_id: str, **kwargs) -> Chapter:
        chapter = self.get_chapter(chapter_id)
        for key, value in kwargs.items():
            if hasattr(chapter, key):
                setattr(chapter, key, value)
        if "content" in kwargs:
            chapter.word_count = self._calculate_word_count(kwargs["content"])
        chapter.updated_at = Chapter.timestamps()
        return self.chapter_repo.update(chapter)

    def delete_chapter(self, chapter_id: str) -> bool:
        return self.chapter_repo.delete(chapter_id)

    async def generate_outline(self, chapter_id: str) -> Chapter:
        chapter = self.get_chapter(chapter_id)
        outline = await self.generation_pipeline.generate_outline(chapter_id)
        chapter.outline = outline
        chapter.status = ChapterStatus.PLANNED.value
        chapter.updated_at = Chapter.timestamps()
        return self.chapter_repo.update(chapter)

    async def generate_content_stream(
        self, chapter_id: str, options: dict[str, Any] | None = None
    ) -> AsyncGenerator[tuple[str, Any], None]:
        chapter = self.get_chapter(chapter_id)
        full_content = ""
        async for event_type, data in self.generation_pipeline.generate_content_stream(chapter_id, options=options):
            if event_type == "token":
                full_content += data
            yield event_type, data

        chapter.content = full_content
        chapter.word_count = self._calculate_word_count(full_content)
        chapter.status = ChapterStatus.COMPLETED.value
        chapter.updated_at = Chapter.timestamps()
        self.chapter_repo.update(chapter)

    def _calculate_word_count(self, content: str) -> int:
        if not content:
            return 0
        # 去除 HTML 标签后再统计字数，避免自动保存 HTML 导致字数虚高（审查报告 1.7）
        import re

        text = re.sub(r"<[^>]+>", "", content)
        return len(text.strip())

    async def generate_chapter(
        self,
        novel_id: str,
        audit_feedback: str = "",
        chapter_number: int | None = None,
        outline: str | None = None,
    ):
        """生成章节。

        通过 StoryPipeline 执行十步生成管线。
        支持可选的 audit_feedback 参数（BLOCK-02），用于在重写时注入上次审计的问题。
        支持可选的 chapter_number 和 outline 参数（M-15），用于 Agent 工具精确指定。
        """
        # M-15: 如果指定了 chapter_number 且该章节已有内容，则返回错误
        if chapter_number is not None:
            existing_chapters = self.chapter_repo.list_by_novel(novel_id)
            for ch in existing_chapters:
                if ch.number == chapter_number and ch.content:
                    from domain.shared.exceptions import DomainException
                    raise DomainException("E3003", f"第 {chapter_number} 章已有内容，不可覆盖生成")

        ctx = await self.story_pipeline.generate_chapter(
            novel_id,
            audit_feedback=audit_feedback,
            chapter_number=chapter_number,
            outline=outline,
        )
        chapter_id = ctx.chapter_id
        if chapter_id:
            return self.chapter_repo.get_by_id(chapter_id)
        chapters = self.chapter_repo.list_by_novel(novel_id)
        return chapters[-1] if chapters else None

    def restore_from_snapshot(self, chapter_id: str, snapshot_id: str) -> Chapter:
        """从快照恢复章节内容（BLOCK-09）。

        将章节的 content 替换为快照中的完整内容版本。
        """
        from infrastructure.persistence.snapshot_repo import SnapshotRepository

        # 获取快照内容
        snapshot_repo = SnapshotRepository(self.chapter_repo.db)
        content = snapshot_repo.get_content(snapshot_id)
        if content is None:
            raise SnapshotNotFoundException()

        # 获取章节并替换内容
        chapter = self.get_chapter(chapter_id)
        chapter.content = content
        chapter.word_count = self._calculate_word_count(content)
        chapter.updated_at = Chapter.timestamps()
        return self.chapter_repo.update(chapter)

    async def generate_ai_suggest_stream(
        self, chapter_id: str
    ) -> AsyncGenerator[tuple[str, Any], None]:
        """Sprint 5.1: 流式生成 AI 写作建议。

        前置校验(章节存在/内容非空)由端点完成,此处仅负责流式产出。
        """
        async for event_type, data in self.generation_pipeline.generate_ai_suggest(chapter_id):
            yield event_type, data
