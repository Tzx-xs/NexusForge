from datetime import UTC, datetime

from domain.chapter import Chapter
from infrastructure.persistence.database import Database


class ChapterRepository:
    def __init__(self, db: Database):
        self.db = db

    def try_acquire_generation_lock(self, novel_id: str, chapter_num: int) -> bool:
        """尝试获取章节生成锁。仅当章节状态为 draft/planned 时才能获取。

        通过 SQL 原子 UPDATE 实现乐观锁，防止并发生成同一章节。
        """
        allowed_statuses = ("draft", "planned")
        placeholders = ",".join("?" * len(allowed_statuses))
        sql = (
            f"UPDATE chapters "
            f"SET status = 'generating', updated_at = ? "
            f"WHERE novel_id = ? AND number = ? "
            f"AND status IN ({placeholders})"
        )
        cursor = self.db.execute(
            sql,
            (datetime.now(UTC).isoformat(), novel_id, chapter_num, *allowed_statuses),
        )
        return cursor > 0

    def list_by_novel(self, novel_id: str) -> list[Chapter]:
        with self.db.get_connection() as conn:
            rows = conn.execute("SELECT * FROM chapters WHERE novel_id = ? ORDER BY number", (novel_id,)).fetchall()
            return [Chapter(**dict(row)) for row in rows]

    def get_by_id(self, chapter_id: str) -> Chapter | None:
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT * FROM chapters WHERE id = ?", (chapter_id,)).fetchone()
            return Chapter(**dict(row)) if row else None

    def create(self, chapter: Chapter) -> Chapter:
        with self.db.get_connection() as conn:
            conn.execute(
                """INSERT INTO chapters (id, novel_id, number, title, outline, content, status,
                   word_count, tension_score, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    chapter.id,
                    chapter.novel_id,
                    chapter.number,
                    chapter.title,
                    chapter.outline,
                    chapter.content,
                    chapter.status,
                    chapter.word_count,
                    chapter.tension_score,
                    chapter.created_at,
                    chapter.updated_at,
                ),
            )
        return chapter

    def update(self, chapter: Chapter) -> Chapter:
        with self.db.get_connection() as conn:
            conn.execute(
                """UPDATE chapters SET number = ?, title = ?, outline = ?, content = ?,
                   status = ?, word_count = ?, tension_score = ?, updated_at = ? WHERE id = ?""",
                (
                    chapter.number,
                    chapter.title,
                    chapter.outline,
                    chapter.content,
                    chapter.status,
                    chapter.word_count,
                    chapter.tension_score,
                    chapter.updated_at,
                    chapter.id,
                ),
            )
        return chapter

    def delete(self, chapter_id: str) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.execute("DELETE FROM chapters WHERE id = ?", (chapter_id,))
            return cursor.rowcount > 0

    def get_by_novel_and_number(self, novel_id: str, number: int) -> Chapter | None:
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM chapters WHERE novel_id = ? AND number = ?", (novel_id, number)
            ).fetchone()
            return Chapter(**dict(row)) if row else None
