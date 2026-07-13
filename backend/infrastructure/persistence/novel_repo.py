import json

from domain.novel import Novel
from infrastructure.persistence.database import Database


class NovelRepository:
    def __init__(self, db: Database):
        self.db = db

    def _row_to_novel(self, row: dict) -> Novel:
        data = dict(row)
        data["style_tags"] = json.loads(data["style_tags"]) if data.get("style_tags") else []
        return Novel(**data)

    def list(self, page: int | None = None, page_size: int | None = None) -> tuple[list[Novel], int]:
        with self.db.get_connection() as conn:
            total = conn.execute("SELECT COUNT(*) FROM novels").fetchone()[0]
            query = "SELECT * FROM novels ORDER BY created_at DESC"
            params: tuple = ()
            if page is not None and page_size is not None:
                query += " LIMIT ? OFFSET ?"
                params = (page_size, (page - 1) * page_size)
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_novel(row) for row in rows], total

    def get_by_id(self, novel_id: str) -> Novel | None:
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT * FROM novels WHERE id = ?", (novel_id,)).fetchone()
            return self._row_to_novel(row) if row else None

    def create(self, novel: Novel) -> Novel:
        with self.db.get_connection() as conn:
            conn.execute(
                """INSERT INTO novels (id, title, premise, genre, target_chapters, current_chapter, cover_url, style_tags, perspective, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    novel.id,
                    novel.title,
                    novel.premise,
                    novel.genre,
                    novel.target_chapters,
                    novel.current_chapter,
                    novel.cover_url,
                    json.dumps(novel.style_tags, ensure_ascii=False),
                    novel.perspective,
                    novel.created_at,
                    novel.updated_at,
                ),
            )
        return novel

    def update(self, novel: Novel) -> Novel:
        with self.db.get_connection() as conn:
            conn.execute(
                """UPDATE novels SET title = ?, premise = ?, genre = ?, target_chapters = ?,
                   current_chapter = ?, cover_url = ?, style_tags = ?, perspective = ?, updated_at = ? WHERE id = ?""",
                (
                    novel.title,
                    novel.premise,
                    novel.genre,
                    novel.target_chapters,
                    novel.current_chapter,
                    novel.cover_url,
                    json.dumps(novel.style_tags, ensure_ascii=False),
                    novel.perspective,
                    novel.updated_at,
                    novel.id,
                ),
            )
        return novel

    def delete(self, novel_id: str) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.execute("DELETE FROM novels WHERE id = ?", (novel_id,))
            return cursor.rowcount > 0
