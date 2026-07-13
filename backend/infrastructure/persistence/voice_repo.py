import json
from datetime import datetime

from application.voice.voice_models import VoiceFingerprint
from infrastructure.persistence.database import Database


class VoiceRepository:
    """文风指纹持久化仓库

    完整指纹以 JSON 形式存入 fingerprint_vector 列；
    同时填充 avg_sentence_length / vocab_richness / sentence_pattern /
    favorite_words 等便捷列以便快速查询。
    """

    def __init__(self, db: Database):
        self.db = db
        self._ensure_table()

    def _ensure_table(self) -> None:
        """确保 voice_fingerprints 表存在且 schema 正确。

        处理三种情况：
        1. 表不存在：直接创建（无 UNIQUE 约束）
        2. 表存在但含 UNIQUE(novel_id) 旧约束：迁移为无 UNIQUE
        3. 表存在且 schema 正确：跳过
        """
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='voice_fingerprints'"
            ).fetchone()
            current_sql = row["sql"] if row else ""
            if not current_sql:
                conn.execute(
                    """
                    CREATE TABLE voice_fingerprints (
                        id TEXT PRIMARY KEY,
                        novel_id TEXT NOT NULL,
                        fingerprint_vector TEXT NOT NULL,
                        baseline_chapters TEXT DEFAULT '[]',
                        avg_sentence_length REAL,
                        vocab_richness REAL,
                        sentence_pattern TEXT DEFAULT '{}',
                        favorite_words TEXT DEFAULT '[]',
                        created_at TEXT,
                        updated_at TEXT
                    )
                    """
                )
                conn.execute("CREATE INDEX IF NOT EXISTS idx_voice_fingerprints_novel ON voice_fingerprints(novel_id)")
            elif "UNIQUE" in current_sql.upper():
                conn.execute("ALTER TABLE voice_fingerprints RENAME TO voice_fingerprints_old")
                conn.execute(
                    """
                    CREATE TABLE voice_fingerprints (
                        id TEXT PRIMARY KEY,
                        novel_id TEXT NOT NULL,
                        fingerprint_vector TEXT NOT NULL,
                        baseline_chapters TEXT DEFAULT '[]',
                        avg_sentence_length REAL,
                        vocab_richness REAL,
                        sentence_pattern TEXT DEFAULT '{}',
                        favorite_words TEXT DEFAULT '[]',
                        created_at TEXT,
                        updated_at TEXT
                    )
                    """
                )
                conn.execute("INSERT INTO voice_fingerprints SELECT * FROM voice_fingerprints_old")
                conn.execute("DROP TABLE voice_fingerprints_old")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_voice_fingerprints_novel ON voice_fingerprints(novel_id)")

    def save(self, fp: VoiceFingerprint) -> VoiceFingerprint:
        """保存指纹（INSERT OR REPLACE，按 id 主键 upsert）。"""
        now = datetime.now().isoformat()
        if not fp.created_at:
            fp.created_at = now
        fp.updated_at = now

        vector = json.dumps(fp.to_dict(), ensure_ascii=False)
        sentence_pattern = json.dumps(
            {
                "paragraph_starts": fp.paragraph_starts[:10],
                "diversity": fp.sentence_structure_diversity,
            },
            ensure_ascii=False,
        )
        favorite_words = json.dumps(fp.signature_phrases[:10], ensure_ascii=False)

        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO voice_fingerprints
                    (id, novel_id, fingerprint_vector, baseline_chapters,
                     avg_sentence_length, vocab_richness, sentence_pattern,
                     favorite_words, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fp.fingerprint_id,
                    fp.novel_id,
                    vector,
                    "[]",
                    fp.sentence_length_mean,
                    fp.lexical_richness,
                    sentence_pattern,
                    favorite_words,
                    fp.created_at,
                    fp.updated_at,
                ),
            )
        return fp

    def get_by_id(self, fp_id: str) -> VoiceFingerprint | None:
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT fingerprint_vector FROM voice_fingerprints WHERE id = ?",
                (fp_id,),
            ).fetchone()
            if not row:
                return None
            return VoiceFingerprint.from_dict(json.loads(row["fingerprint_vector"]))

    def list_all(self) -> list[VoiceFingerprint]:
        with self.db.get_connection() as conn:
            rows = conn.execute("SELECT fingerprint_vector FROM voice_fingerprints").fetchall()
            return [VoiceFingerprint.from_dict(json.loads(r["fingerprint_vector"])) for r in rows]

    def delete(self, fp_id: str) -> None:
        with self.db.get_connection() as conn:
            conn.execute("DELETE FROM voice_fingerprints WHERE id = ?", (fp_id,))
