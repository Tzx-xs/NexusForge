from __future__ import annotations

from domain.novel import Novel, VALID_STAGES, STAGE_PREPARING
from domain.shared.exceptions import NovelNotFoundException
from infrastructure.persistence.chapter_repo import ChapterRepository
from infrastructure.persistence.character_repo import CharacterRepository
from infrastructure.persistence.novel_repo import NovelRepository


class NovelService:
    def __init__(
        self, novel_repo: NovelRepository, chapter_repo: ChapterRepository, character_repo: CharacterRepository
    ):
        self.novel_repo = novel_repo
        self.chapter_repo = chapter_repo
        self.character_repo = character_repo

    def list_novels(self, page: int | None = None, page_size: int | None = None) -> tuple[list[Novel], int]:
        return self.novel_repo.list(page=page, page_size=page_size)

    def get_novel(self, novel_id: str) -> Novel:
        novel = self.novel_repo.get_by_id(novel_id)
        if not novel:
            raise NovelNotFoundException()
        return novel

    def create_novel(
        self,
        title: str,
        premise: str = "",
        genre: str = "",
        target_chapters: int = 0,
        cover_url: str = "",
        style_tags: list | None = None,
        perspective: str = "",
        # NexusForge Phase 3.5：对齐 PlotPilot 前端建档字段
        novel_id: str | None = None,
        author: str = "",
        stage: str = STAGE_PREPARING,
        auto_approve_mode: bool = False,
        target_words_per_chapter: int = 2500,
        generation_prefs: dict | None = None,
        world_preset: str = "",
        story_structure: str = "",
        pacing_control: str = "",
        writing_style: str = "",
        special_requirements: str = "",
    ) -> Novel:
        novel = Novel(
            title=title,
            premise=premise,
            genre=genre,
            target_chapters=target_chapters,
            cover_url=cover_url,
            style_tags=style_tags or [],
            perspective=perspective,
            author=author,
            stage=stage if stage in VALID_STAGES else STAGE_PREPARING,
            auto_approve_mode=auto_approve_mode,
            target_words_per_chapter=target_words_per_chapter,
            generation_prefs=generation_prefs or {},
            world_preset=world_preset,
            story_structure=story_structure,
            pacing_control=pacing_control,
            writing_style=writing_style,
            special_requirements=special_requirements,
        )
        # 允许前端自定义 ID（PlotPilot 用 novel-{timestamp} 风格）
        if novel_id:
            novel.id = novel_id
        return self.novel_repo.create(novel)

    def update_novel(self, novel_id: str, **kwargs) -> Novel:
        novel = self.get_novel(novel_id)
        # stage 合法性校验
        if "stage" in kwargs and kwargs["stage"] is not None:
            if kwargs["stage"] not in VALID_STAGES:
                kwargs.pop("stage")
        # auto_approve_mode 强制 bool
        if "auto_approve_mode" in kwargs and kwargs["auto_approve_mode"] is not None:
            kwargs["auto_approve_mode"] = bool(kwargs["auto_approve_mode"])
        for key, value in kwargs.items():
            if hasattr(novel, key):
                setattr(novel, key, value)
        novel.updated_at = Novel.timestamps()
        return self.novel_repo.update(novel)

    def delete_novel(self, novel_id: str) -> bool:
        return self.novel_repo.delete(novel_id)

    def update_stage(self, novel_id: str, stage: str) -> Novel:
        """更新小说阶段（PlotPilot 前端 PUT /novels/{id}/stage 调用）。"""
        if stage not in VALID_STAGES:
            raise ValueError(f"无效阶段: {stage}")
        return self.update_novel(novel_id, stage=stage)

    def update_auto_approve_mode(self, novel_id: str, auto_approve_mode: bool) -> Novel:
        """更新自动审核模式（PlotPilot 前端 PATCH /novels/{id}/auto-approve-mode 调用）。"""
        return self.update_novel(novel_id, auto_approve_mode=auto_approve_mode)

    def get_novel_stats(self, novel_id: str) -> dict:
        novel = self.get_novel(novel_id)
        chapters = self.chapter_repo.list_by_novel(novel_id)
        total_words = sum(ch.word_count for ch in chapters)
        chapter_count = len(chapters)
        completion_rate = 0.0
        if novel.target_chapters > 0:
            completion_rate = round(chapter_count / novel.target_chapters * 100, 2)
        completed_chapters = sum(1 for ch in chapters if ch.status == "completed")
        return {
            "novel_id": novel.id,
            "title": novel.title,
            "chapter_count": chapter_count,
            "completed_chapters": completed_chapters,
            "total_words": total_words,
            "target_chapters": novel.target_chapters,
            "completion_rate": completion_rate,
            "today_words": 0,
            "streak_days": 0,
            "total_chapters": chapter_count,
        }

    def get_novel_statistics(self, novel_id: str) -> dict:
        """PlotPilot 风格统计（GET /novels/{id}/statistics）。

        字段对齐前端 toBookStatsFromStatisticsPayload 期望：
        total_chapters / completed_chapters / total_words / avg_chapter_words /
        completion_rate / last_updated / slug / title
        """
        novel = self.get_novel(novel_id)
        chapters = self.chapter_repo.list_by_novel(novel_id)
        total_words = sum(ch.word_count for ch in chapters)
        total_chapters = len(chapters)
        completed_chapters = sum(1 for ch in chapters if ch.status == "completed")
        avg_chapter_words = round(total_words / total_chapters) if total_chapters > 0 else 0
        completion_rate = (
            round(completed_chapters / total_chapters, 4) if total_chapters > 0 else 0.0
        )
        last_updated = novel.updated_at.isoformat() if hasattr(novel.updated_at, "isoformat") else str(novel.updated_at)
        return {
            "slug": novel.id,
            "title": novel.title,
            "total_chapters": total_chapters,
            "completed_chapters": completed_chapters,
            "total_words": total_words,
            "avg_chapter_words": avg_chapter_words,
            "completion_rate": completion_rate,
            "last_updated": last_updated,
        }
