import json
from typing import Any

from domain.memory.beat_lock import BeatLock
from domain.memory.clue_lock import ClueLock
from domain.memory.fact_lock import FactLock
from infrastructure.persistence.database import Database


class MemoryRepository:
    def __init__(self, db: Database):
        self.db = db

    def get_fact_locks(
        self, novel_id: str, fact_type: str | None = None, immutable_only: bool = False
    ) -> list[FactLock]:
        with self.db.get_connection() as conn:
            query = "SELECT * FROM memory_facts WHERE novel_id = ?"
            params = [novel_id]
            if fact_type:
                query += " AND fact_type = ?"
                params.append(fact_type)
            if immutable_only:
                query += " AND is_immutable = 1"
            query += " ORDER BY created_at"
            rows = conn.execute(query, tuple(params)).fetchall()
            result = []
            for row in rows:
                data = dict(row)
                data["is_immutable"] = bool(data["is_immutable"])
                result.append(FactLock(**data))
            return result

    def bulk_upsert_facts(self, facts: list[FactLock]) -> None:
        with self.db.get_connection() as conn:
            for fact in facts:
                conn.execute(
                    """INSERT OR REPLACE INTO memory_facts
                       (id, novel_id, fact_type, key, value, locked_at_chapter, is_immutable, source, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        fact.id,
                        fact.novel_id,
                        fact.fact_type,
                        fact.key,
                        fact.value,
                        fact.locked_at_chapter,
                        1 if fact.is_immutable else 0,
                        fact.source,
                        fact.created_at,
                        fact.updated_at,
                    ),
                )

    def get_beat_locks(self, novel_id: str, up_to_chapter: int | None = None) -> list[BeatLock]:
        with self.db.get_connection() as conn:
            query = "SELECT * FROM memory_beats WHERE novel_id = ?"
            params: list[Any] = [novel_id]
            if up_to_chapter is not None:
                query += " AND chapter_index <= ?"
                params.append(up_to_chapter)
            query += " ORDER BY chapter_index, created_at"
            rows = conn.execute(query, tuple(params)).fetchall()
            result = []
            for row in rows:
                data = dict(row)
                data["characters"] = json.loads(data["characters"]) if data["characters"] else []
                result.append(BeatLock(**data))
            return result

    def bulk_upsert_beats(self, beats: list[BeatLock]) -> None:
        with self.db.get_connection() as conn:
            for beat in beats:
                conn.execute(
                    """INSERT OR REPLACE INTO memory_beats
                       (id, novel_id, chapter_id, chapter_index, beat_type, description, significance, characters, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        beat.id,
                        beat.novel_id,
                        beat.chapter_id,
                        beat.chapter_index,
                        beat.beat_type,
                        beat.description,
                        beat.significance,
                        json.dumps(beat.characters, ensure_ascii=False),
                        beat.created_at,
                    ),
                )

    def get_clue_locks(self, novel_id: str, statuses: list[str] | None = None) -> list[ClueLock]:
        with self.db.get_connection() as conn:
            query = "SELECT * FROM memory_clues WHERE novel_id = ?"
            params = [novel_id]
            if statuses:
                placeholders = ",".join(["?"] * len(statuses))
                query += f" AND status IN ({placeholders})"
                params.extend(statuses)
            query += " ORDER BY created_at"
            rows = conn.execute(query, tuple(params)).fetchall()
            result = []
            for row in rows:
                data = dict(row)
                data["related_characters"] = (
                    json.loads(data["related_characters"]) if data["related_characters"] else []
                )
                result.append(ClueLock(**data))
            return result

    def bulk_upsert_clues(self, clues: list[ClueLock]) -> None:
        with self.db.get_connection() as conn:
            for clue in clues:
                conn.execute(
                    """INSERT OR REPLACE INTO memory_clues
                       (id, novel_id, clue_type, title, description, status, planted_chapter, revealed_chapter, related_characters, urgency, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        clue.id,
                        clue.novel_id,
                        clue.clue_type,
                        clue.title,
                        clue.description,
                        clue.status,
                        clue.planted_chapter,
                        clue.revealed_chapter,
                        json.dumps(clue.related_characters, ensure_ascii=False),
                        clue.urgency,
                        clue.created_at,
                        clue.updated_at,
                    ),
                )
