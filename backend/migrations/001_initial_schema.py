"""基线迁移 — 现有 schema.sql 完整 DDL

Revision ID: 001
Revises: None
Create Date: 2026-07-04

将所有现有表结构作为基线迁移，后续增量变更（BLOCK-08/09）作为增量迁移叠加。
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers
revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ========== 核心表 ==========
    op.execute("""
        CREATE TABLE IF NOT EXISTS novels (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            premise TEXT DEFAULT '',
            genre TEXT DEFAULT '',
            target_chapters INTEGER DEFAULT 0,
            current_chapter INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS chapters (
            id TEXT PRIMARY KEY,
            novel_id TEXT NOT NULL,
            number INTEGER NOT NULL,
            title TEXT DEFAULT '',
            outline TEXT DEFAULT '',
            content TEXT DEFAULT '',
            status TEXT DEFAULT 'draft',
            word_count INTEGER DEFAULT 0,
            tension_score REAL DEFAULT 50.0,
            created_at TEXT,
            updated_at TEXT,
            UNIQUE(novel_id, number),
            FOREIGN KEY (novel_id) REFERENCES novels(id) ON DELETE CASCADE
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS characters (
            id TEXT PRIMARY KEY,
            novel_id TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT DEFAULT '配角',
            description TEXT DEFAULT '',
            personality TEXT DEFAULT '',
            appearance TEXT DEFAULT '',
            background TEXT DEFAULT '',
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (novel_id) REFERENCES novels(id) ON DELETE CASCADE
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS world_settings (
            id TEXT PRIMARY KEY,
            novel_id TEXT NOT NULL,
            name TEXT NOT NULL,
            setting_type TEXT DEFAULT 'other',
            description TEXT DEFAULT '',
            parent_id TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (novel_id) REFERENCES novels(id) ON DELETE CASCADE
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS chapter_reviews (
            id TEXT PRIMARY KEY,
            chapter_id TEXT NOT NULL UNIQUE,
            total_score REAL DEFAULT 0,
            grade TEXT DEFAULT 'C',
            red_line_violations TEXT DEFAULT '[]',
            dimension_scores TEXT DEFAULT '{}',
            review_details TEXT DEFAULT '',
            created_at TEXT,
            FOREIGN KEY (chapter_id) REFERENCES chapters(id) ON DELETE CASCADE
        )
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS system_settings (
            id TEXT PRIMARY KEY,
            key TEXT NOT NULL UNIQUE,
            value TEXT DEFAULT '',
            description TEXT DEFAULT '',
            updated_at TEXT
        )
    """)

    # ========== 索引 ==========
    op.execute("CREATE INDEX IF NOT EXISTS idx_novels_created_at ON novels(created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_chapters_novel_number ON chapters(novel_id, number)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_characters_novel ON characters(novel_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_settings_novel_type ON world_settings(novel_id, setting_type)")

    # ========== M1 新增表：知识三元组 ==========
    op.execute("""
        CREATE TABLE IF NOT EXISTS triples (
            id TEXT PRIMARY KEY,
            novel_id TEXT NOT NULL,
            subject TEXT NOT NULL,
            predicate TEXT NOT NULL,
            object TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            source_chapter_id TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_triples_novel ON triples(novel_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_triples_subject ON triples(subject)")

    # ========== 章节摘要链 ==========
    op.execute("""
        CREATE TABLE IF NOT EXISTS chapter_summaries (
            id TEXT PRIMARY KEY,
            novel_id TEXT NOT NULL,
            chapter_id TEXT NOT NULL UNIQUE,
            chapter_index INTEGER NOT NULL,
            summary TEXT NOT NULL,
            key_events TEXT DEFAULT '[]',
            characters_involved TEXT DEFAULT '[]',
            locations TEXT DEFAULT '[]',
            timeline_position TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_summaries_novel ON chapter_summaries(novel_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_summaries_chapter ON chapter_summaries(chapter_id)")

    # ========== 记忆事实锁 ==========
    op.execute("""
        CREATE TABLE IF NOT EXISTS memory_facts (
            id TEXT PRIMARY KEY,
            novel_id TEXT NOT NULL,
            fact_type TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            locked_at_chapter INTEGER,
            is_immutable INTEGER DEFAULT 0,
            source TEXT DEFAULT 'extracted',
            created_at TEXT,
            updated_at TEXT
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_memory_facts_novel ON memory_facts(novel_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_memory_facts_type ON memory_facts(fact_type)")

    # ========== 记忆节拍锁 ==========
    op.execute("""
        CREATE TABLE IF NOT EXISTS memory_beats (
            id TEXT PRIMARY KEY,
            novel_id TEXT NOT NULL,
            chapter_id TEXT NOT NULL,
            chapter_index INTEGER NOT NULL,
            beat_type TEXT NOT NULL,
            description TEXT NOT NULL,
            significance REAL DEFAULT 0.5,
            characters TEXT DEFAULT '[]',
            created_at TEXT
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_beats_novel ON memory_beats(novel_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_beats_chapter ON memory_beats(chapter_id)")

    # ========== 记忆线索锁 ==========
    op.execute("""
        CREATE TABLE IF NOT EXISTS memory_clues (
            id TEXT PRIMARY KEY,
            novel_id TEXT NOT NULL,
            clue_type TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'planted',
            planted_chapter INTEGER,
            revealed_chapter INTEGER,
            related_characters TEXT DEFAULT '[]',
            urgency TEXT DEFAULT 'normal',
            created_at TEXT,
            updated_at TEXT
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_clues_novel ON memory_clues(novel_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_clues_status ON memory_clues(status)")

    # ========== 伏笔注册表 ==========
    op.execute("""
        CREATE TABLE IF NOT EXISTS foreshadows (
            id TEXT PRIMARY KEY,
            novel_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'P2',
            status TEXT NOT NULL DEFAULT 'planted',
            planted_chapter_id TEXT,
            planted_chapter_index INTEGER,
            resolved_chapter_id TEXT,
            resolved_chapter_index INTEGER,
            related_characters TEXT DEFAULT '[]',
            related_locations TEXT DEFAULT '[]',
            urgency TEXT DEFAULT 'normal',
            tags TEXT DEFAULT '[]',
            notes TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_foreshadows_novel ON foreshadows(novel_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_foreshadows_status ON foreshadows(status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_foreshadows_priority ON foreshadows(priority)")

    # ========== 故事线管理 ==========
    op.execute("""
        CREATE TABLE IF NOT EXISTS storylines (
            id TEXT PRIMARY KEY,
            novel_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            color TEXT,
            node_count INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_storylines_novel ON storylines(novel_id)")

    # ========== 故事线节点 ==========
    op.execute("""
        CREATE TABLE IF NOT EXISTS storyline_nodes (
            id TEXT PRIMARY KEY,
            novel_id TEXT NOT NULL,
            storyline_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            node_type TEXT DEFAULT 'scene',
            status TEXT DEFAULT 'draft',
            chapter_index INTEGER,
            chapter_id TEXT,
            x REAL DEFAULT 0,
            y REAL DEFAULT 0,
            width REAL DEFAULT 180,
            height REAL DEFAULT 80,
            parent_ids TEXT DEFAULT '[]',
            child_ids TEXT DEFAULT '[]',
            tags TEXT DEFAULT '[]',
            metadata TEXT DEFAULT '{}',
            created_at TEXT,
            updated_at TEXT
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_storyline_nodes_storyline ON storyline_nodes(storyline_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_storyline_nodes_novel ON storyline_nodes(novel_id)")

    # ========== 章后快照 ==========
    op.execute("""
        CREATE TABLE IF NOT EXISTS snapshots (
            id TEXT PRIMARY KEY,
            novel_id TEXT NOT NULL,
            chapter_id TEXT NOT NULL,
            snapshot_type TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            content_hash TEXT,
            diff_data TEXT,
            parent_snapshot_id TEXT,
            created_by TEXT DEFAULT 'system',
            created_at TEXT,
            updated_at TEXT
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_novel ON snapshots(novel_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_chapter ON snapshots(chapter_id)")

    # ========== 文风指纹 ==========
    op.execute("""
        CREATE TABLE IF NOT EXISTS voice_fingerprints (
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
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_voice_fingerprints_novel ON voice_fingerprints(novel_id)")

    # ========== 审计日志 ==========
    op.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id TEXT PRIMARY KEY,
            novel_id TEXT,
            chapter_id TEXT,
            audit_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            details TEXT,
            resolved INTEGER DEFAULT 0,
            created_at TEXT
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_novel ON audit_logs(novel_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_audit_logs_type ON audit_logs(audit_type)")

    # ========== 后台任务队列 ==========
    op.execute("""
        CREATE TABLE IF NOT EXISTS background_tasks (
            id TEXT PRIMARY KEY,
            task_type TEXT NOT NULL,
            novel_id TEXT,
            chapter_id TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            progress REAL DEFAULT 0,
            current_step TEXT,
            payload TEXT,
            result TEXT,
            error_message TEXT,
            retry_count INTEGER DEFAULT 0,
            started_at TEXT,
            completed_at TEXT,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_background_tasks_status ON background_tasks(status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_background_tasks_type ON background_tasks(task_type)")

    # ========== Agent 对话 ==========
    op.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id TEXT PRIMARY KEY,
            novel_id TEXT,
            title TEXT DEFAULT '',
            created_at REAL,
            updated_at REAL
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_conversations_novel_id ON conversations(novel_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            conversation_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT DEFAULT '',
            tool_calls TEXT,
            tool_name TEXT,
            created_at REAL,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at)")


def downgrade() -> None:
    """回滚基线迁移：删除所有表（反向顺序）。"""
    tables = [
        "messages", "conversations",
        "background_tasks", "audit_logs",
        "voice_fingerprints", "snapshots",
        "storyline_nodes", "storylines",
        "foreshadows", "memory_clues",
        "memory_beats", "memory_facts",
        "chapter_summaries", "triples",
        "system_settings", "chapter_reviews",
        "world_settings", "characters",
        "chapters", "novels",
    ]
    for table in tables:
        op.execute(f"DROP TABLE IF EXISTS {table}")
