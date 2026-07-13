from __future__ import annotations

from domain.novel import Novel
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
    ) -> Novel:
        novel = Novel(
            title=title,
            premise=premise,
            genre=genre,
            target_chapters=target_chapters,
            cover_url=cover_url,
            style_tags=style_tags or [],
            perspective=perspective,
        )
        return self.novel_repo.create(novel)

    def update_novel(self, novel_id: str, **kwargs) -> Novel:
        novel = self.get_novel(novel_id)
        for key, value in kwargs.items():
            if hasattr(novel, key):
                setattr(novel, key, value)
        novel.updated_at = Novel.timestamps()
        return self.novel_repo.update(novel)

    def delete_novel(self, novel_id: str) -> bool:
        return self.novel_repo.delete(novel_id)

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
