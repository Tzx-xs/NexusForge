import json

from domain.foreshadow import Foreshadow
from infrastructure.persistence.database import Database


class ForeshadowRepository:
    def __init__(self, db: Database):
        self.db = db

    def list_foreshadows(
        self, novel_id: str, status: str | None = None, priority: str | None = None
    ) -> list[Foreshadow]:
        with self.db.get_connection() as conn:
            query = "SELECT * FROM foreshadows WHERE novel_id = ?"
            params = [novel_id]
            if status:
                query += " AND status = ?"
                params.append(status)
            if priority:
                query += " AND priority = ?"
                params.append(priority)
            query += " ORDER BY created_at"
            rows = conn.execute(query, tuple(params)).fetchall()
            result = []
            for row in rows:
                data = dict(row)
                data["related_characters"] = (
                    json.loads(data["related_characters"]) if data["related_characters"] else []
                )
                data["related_locations"] = json.loads(data["related_locations"]) if data["related_locations"] else []
                data["tags"] = json.loads(data["tags"]) if data["tags"] else []
                result.append(Foreshadow(**data))
            return result

    def get_foreshadow(self, foreshadow_id: str) -> Foreshadow | None:
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT * FROM foreshadows WHERE id = ?", (foreshadow_id,)).fetchone()
            if not row:
                return None
            data = dict(row)
            data["related_characters"] = json.loads(data["related_characters"]) if data["related_characters"] else []
            data["related_locations"] = json.loads(data["related_locations"]) if data["related_locations"] else []
            data["tags"] = json.loads(data["tags"]) if data["tags"] else []
            return Foreshadow(**data)

    def create_foreshadow(self, foreshadow: Foreshadow) -> Foreshadow:
        with self.db.get_connection() as conn:
            conn.execute(
                """INSERT INTO foreshadows
                   (id, novel_id, title, description, priority, status,
                    planted_chapter_id, planted_chapter_index, resolved_chapter_id, resolved_chapter_index,
                    related_characters, related_locations, urgency, tags, notes, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    foreshadow.id,
                    foreshadow.novel_id,
                    foreshadow.title,
                    foreshadow.description,
                    foreshadow.priority,
                    foreshadow.status,
                    foreshadow.planted_chapter_id,
                    foreshadow.planted_chapter_index,
                    foreshadow.resolved_chapter_id,
                    foreshadow.resolved_chapter_index,
                    json.dumps(foreshadow.related_characters, ensure_ascii=False),
                    json.dumps(foreshadow.related_locations, ensure_ascii=False),
                    foreshadow.urgency,
                    json.dumps(foreshadow.tags, ensure_ascii=False),
                    foreshadow.notes,
                    foreshadow.created_at,
                    foreshadow.updated_at,
                ),
            )
        return foreshadow

    def update_foreshadow(self, foreshadow_id: str, data: dict) -> Foreshadow | None:
        foreshadow = self.get_foreshadow(foreshadow_id)
        if not foreshadow:
            return None
        for key, value in data.items():
            if hasattr(foreshadow, key):
                setattr(foreshadow, key, value)
        foreshadow.updated_at = Foreshadow.timestamps()
        with self.db.get_connection() as conn:
            conn.execute(
                """UPDATE foreshadows SET title = ?, description = ?, priority = ?, status = ?,
                   planted_chapter_id = ?, planted_chapter_index = ?, resolved_chapter_id = ?, resolved_chapter_index = ?,
                   related_characters = ?, related_locations = ?, urgency = ?, tags = ?, notes = ?, updated_at = ?
                   WHERE id = ?""",
                (
                    foreshadow.title,
                    foreshadow.description,
                    foreshadow.priority,
                    foreshadow.status,
                    foreshadow.planted_chapter_id,
                    foreshadow.planted_chapter_index,
                    foreshadow.resolved_chapter_id,
                    foreshadow.resolved_chapter_index,
                    json.dumps(foreshadow.related_characters, ensure_ascii=False),
                    json.dumps(foreshadow.related_locations, ensure_ascii=False),
                    foreshadow.urgency,
                    json.dumps(foreshadow.tags, ensure_ascii=False),
                    foreshadow.notes,
                    foreshadow.updated_at,
                    foreshadow_id,
                ),
            )
        return foreshadow

    def delete_foreshadow(self, foreshadow_id: str) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.execute("DELETE FROM foreshadows WHERE id = ?", (foreshadow_id,))
            return cursor.rowcount > 0

    def get_pending_report(self, novel_id: str) -> dict:
        with self.db.get_connection() as conn:
            planted = conn.execute(
                "SELECT COUNT(*) as cnt FROM foreshadows WHERE novel_id = ? AND status = 'planted'", (novel_id,)
            ).fetchone()["cnt"]
            resolving = conn.execute(
                "SELECT COUNT(*) as cnt FROM foreshadows WHERE novel_id = ? AND status = 'resolving'", (novel_id,)
            ).fetchone()["cnt"]
            resolved = conn.execute(
                "SELECT COUNT(*) as cnt FROM foreshadows WHERE novel_id = ? AND status = 'resolved'", (novel_id,)
            ).fetchone()["cnt"]
            p1_count = conn.execute(
                "SELECT COUNT(*) as cnt FROM foreshadows WHERE novel_id = ? AND priority = 'P1' AND status != 'resolved'",
                (novel_id,),
            ).fetchone()["cnt"]
            return {
                "total": planted + resolving + resolved,
                "planted": planted,
                "resolving": resolving,
                "resolved": resolved,
                "p1_pending": p1_count,
            }
