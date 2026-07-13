import json

from domain.novel import Novel
from infrastructure.persistence.database import Database


class NovelRepository:
    def __init__(self, db: Database):
        self.db = db

    def _row_to_novel(self, row: dict) -> Novel:
        data = dict(row)
        data["style_tags"] = json.loads(data["style_tags"]) if data.get("style_tags") else []
        # NexusForge Phase 3.5：兼容旧库未迁移列（None 时回落默认）
        data["generation_prefs"] = (
            json.loads(data["generation_prefs"])
            if data.get("generation_prefs")
            else {}
        )
        # SQLite 用 INTEGER 表 bool，转 Python bool
        if "auto_approve_mode" in data:
            data["auto_approve_mode"] = bool(data["auto_approve_mode"])
        # 过滤掉未知键（避免 Novel 构造函数报错）
        valid_fields = {f for f in Novel.__dataclass_fields__}  # type: ignore[attr-defined]
        data = {k: v for k, v in data.items() if k in valid_fields}
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
                """INSERT INTO novels (
                    id, title, premise, genre, target_chapters, current_chapter,
                    cover_url, style_tags, perspective, created_at, updated_at,
                    author, stage, auto_approve_mode, target_words_per_chapter,
                    generation_prefs, world_preset, story_structure, pacing_control,
                    writing_style, special_requirements
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                    novel.author,
                    novel.stage,
                    int(novel.auto_approve_mode),
                    novel.target_words_per_chapter,
                    json.dumps(novel.generation_prefs, ensure_ascii=False),
                    novel.world_preset,
                    novel.story_structure,
                    novel.pacing_control,
                    novel.writing_style,
                    novel.special_requirements,
                ),
            )
        return novel

    def update(self, novel: Novel) -> Novel:
        with self.db.get_connection() as conn:
            conn.execute(
                """UPDATE novels SET
                   title = ?, premise = ?, genre = ?, target_chapters = ?,
                   current_chapter = ?, cover_url = ?, style_tags = ?, perspective = ?,
                   author = ?, stage = ?, auto_approve_mode = ?, target_words_per_chapter = ?,
                   generation_prefs = ?, world_preset = ?, story_structure = ?,
                   pacing_control = ?, writing_style = ?, special_requirements = ?,
                   updated_at = ?
                   WHERE id = ?""",
                (
                    novel.title,
                    novel.premise,
                    novel.genre,
                    novel.target_chapters,
                    novel.current_chapter,
                    novel.cover_url,
                    json.dumps(novel.style_tags, ensure_ascii=False),
                    novel.perspective,
                    novel.author,
                    novel.stage,
                    int(novel.auto_approve_mode),
                    novel.target_words_per_chapter,
                    json.dumps(novel.generation_prefs, ensure_ascii=False),
                    novel.world_preset,
                    novel.story_structure,
                    novel.pacing_control,
                    novel.writing_style,
                    novel.special_requirements,
                    novel.updated_at,
                    novel.id,
                ),
            )
        return novel

    def delete(self, novel_id: str) -> bool:
        with self.db.get_connection() as conn:
            cursor = conn.execute("DELETE FROM novels WHERE id = ?", (novel_id,))
            return cursor.rowcount > 0
