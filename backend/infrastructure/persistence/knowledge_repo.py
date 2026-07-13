from domain.knowledge.chapter_summary import ChapterSummary
from domain.knowledge.knowledge_triple import KnowledgeTriple
from infrastructure.persistence.database import Database


class KnowledgeRepository:
    def __init__(self, db: Database):
        self.db = db

    def get_triples(
        self, novel_id: str, subject: str | None = None, predicate: str | None = None
    ) -> list[KnowledgeTriple]:
        with self.db.get_connection() as conn:
            query = "SELECT * FROM triples WHERE novel_id = ?"
            params = [novel_id]
            if subject:
                query += " AND subject = ?"
                params.append(subject)
            if predicate:
                query += " AND predicate = ?"
                params.append(predicate)
            query += " ORDER BY created_at"
            rows = conn.execute(query, tuple(params)).fetchall()
            return [KnowledgeTriple(**dict(row)) for row in rows]

    def bulk_upsert_triples(self, triples: list[KnowledgeTriple]) -> None:
        with self.db.get_connection() as conn:
            for triple in triples:
                conn.execute(
                    """INSERT OR REPLACE INTO triples
                       (id, novel_id, subject, predicate, object, confidence, source_chapter_id, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        triple.id,
                        triple.novel_id,
                        triple.subject,
                        triple.predicate,
                        triple.object,
                        triple.confidence,
                        triple.source_chapter_id,
                        triple.created_at,
                        triple.updated_at,
                    ),
                )

    def get_summaries(self, novel_id: str, limit: int = 10) -> list[ChapterSummary]:
        with self.db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM chapter_summaries WHERE novel_id = ? ORDER BY chapter_index DESC LIMIT ?",
                (novel_id, limit),
            ).fetchall()
            import json

            result = []
            for row in rows:
                data = dict(row)
                data["key_events"] = json.loads(data["key_events"]) if data["key_events"] else []
                data["characters_involved"] = (
                    json.loads(data["characters_involved"]) if data["characters_involved"] else []
                )
                data["locations"] = json.loads(data["locations"]) if data["locations"] else []
                result.append(ChapterSummary(**data))
            return list(reversed(result))

    def get_summary_by_chapter(self, chapter_id: str) -> ChapterSummary | None:
        with self.db.get_connection() as conn:
            row = conn.execute("SELECT * FROM chapter_summaries WHERE chapter_id = ?", (chapter_id,)).fetchone()
            if not row:
                return None
            import json

            data = dict(row)
            data["key_events"] = json.loads(data["key_events"]) if data["key_events"] else []
            data["characters_involved"] = json.loads(data["characters_involved"]) if data["characters_involved"] else []
            data["locations"] = json.loads(data["locations"]) if data["locations"] else []
            return ChapterSummary(**data)

    def upsert_summary(self, summary: ChapterSummary) -> ChapterSummary:
        import json

        with self.db.get_connection() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO chapter_summaries
                   (id, novel_id, chapter_id, chapter_index, summary, key_events, characters_involved, locations, timeline_position, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    summary.id,
                    summary.novel_id,
                    summary.chapter_id,
                    summary.chapter_index,
                    summary.summary,
                    json.dumps(summary.key_events, ensure_ascii=False),
                    json.dumps(summary.characters_involved, ensure_ascii=False),
                    json.dumps(summary.locations, ensure_ascii=False),
                    summary.timeline_position,
                    summary.created_at,
                    summary.updated_at,
                ),
            )
        return summary

    def search(self, novel_id: str, query: str, limit: int = 20) -> list[dict]:
        """基于 LIKE 模糊匹配搜索知识条目（三元组 + 章节摘要）"""
        import json

        results: list[dict] = []
        like = f"%{query}%"
        with self.db.get_connection() as conn:
            triple_rows = conn.execute(
                """SELECT * FROM triples
                   WHERE novel_id = ? AND (subject LIKE ? OR predicate LIKE ? OR object LIKE ?)
                   ORDER BY created_at DESC LIMIT ?""",
                (novel_id, like, like, like, limit),
            ).fetchall()
            for row in triple_rows:
                data = dict(row)
                data["source"] = "triple"
                results.append(data)

            summary_rows = conn.execute(
                """SELECT * FROM chapter_summaries
                   WHERE novel_id = ? AND summary LIKE ?
                   ORDER BY chapter_index DESC LIMIT ?""",
                (novel_id, like, limit),
            ).fetchall()
            for row in summary_rows:
                data = dict(row)
                data["key_events"] = json.loads(data["key_events"]) if data["key_events"] else []
                data["characters_involved"] = (
                    json.loads(data["characters_involved"]) if data["characters_involved"] else []
                )
                data["locations"] = json.loads(data["locations"]) if data["locations"] else []
                data["source"] = "summary"
                results.append(data)
        return results
