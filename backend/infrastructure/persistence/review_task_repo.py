from domain.review_task import ReviewTask
from infrastructure.persistence.database import Database


class ReviewTaskRepository:
    def __init__(self, db: Database):
        self.db = db

    def list(self, page: int, page_size: int) -> tuple[list[ReviewTask], int]:
        offset = (page - 1) * page_size
        with self.db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM review_tasks ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (page_size, offset),
            ).fetchall()
            total_row = conn.execute("SELECT COUNT(*) FROM review_tasks").fetchone()
            total = total_row[0] if total_row else 0
            return [ReviewTask(**dict(row)) for row in rows], total

    def get_by_id(self, task_id: str) -> ReviewTask | None:
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT * FROM review_tasks WHERE id = ?", (task_id,)).fetchone()
            return ReviewTask(**dict(row)) if row else None

    def create(self, task: ReviewTask) -> ReviewTask:
        db_dict = task.to_db_dict()
        with self.db.get_connection() as conn:
            conn.execute(
                """INSERT INTO review_tasks (id, title, novel_id, status, result, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    db_dict["id"],
                    db_dict["title"],
                    db_dict["novel_id"],
                    db_dict["status"],
                    db_dict["result"],
                    db_dict["created_at"],
                    db_dict["updated_at"],
                ),
            )
        return task

    def update(self, task: ReviewTask) -> ReviewTask:
        db_dict = task.to_db_dict()
        with self.db.get_connection() as conn:
            conn.execute(
                """UPDATE review_tasks SET title = ?, novel_id = ?, status = ?, result = ?, updated_at = ?
                   WHERE id = ?""",
                (
                    db_dict["title"],
                    db_dict["novel_id"],
                    db_dict["status"],
                    db_dict["result"],
                    db_dict["updated_at"],
                    db_dict["id"],
                ),
            )
        return task

    def delete(self, task_id: str) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.execute("DELETE FROM review_tasks WHERE id = ?", (task_id,))
            return cursor.rowcount > 0
