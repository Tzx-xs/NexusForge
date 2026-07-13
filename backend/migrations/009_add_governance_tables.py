"""009: 叙事治理表

Revision ID: 009
Revises: 008
Create Date: 2026-07-13

新增表：
- governance_budgets: 每章叙事预算（最多新增故事线/回收债务/揭秘等级）
- narrative_debts: 叙事债务（伏笔/承诺/悬念的待回收项）
"""
import logging
from collections.abc import Sequence

from alembic import op

logger = logging.getLogger(__name__)

revision: str = "009"
down_revision: str | None = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建叙事治理表。"""
    # 章节叙事预算
    try:
        op.execute("""
            CREATE TABLE IF NOT EXISTS governance_budgets (
                id TEXT PRIMARY KEY,
                novel_id TEXT NOT NULL,
                chapter_number INTEGER NOT NULL,
                max_new_storylines INTEGER DEFAULT 0,
                max_debt_closures INTEGER DEFAULT 1,
                allowed_reveal_level TEXT DEFAULT 'hint',
                must_serve_promise_tags TEXT DEFAULT '[]',
                notes TEXT DEFAULT '[]',
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                updated_at TEXT,
                UNIQUE(novel_id, chapter_number)
            )
        """)
        op.execute("CREATE INDEX IF NOT EXISTS idx_gov_budgets_novel ON governance_budgets(novel_id)")
        op.execute("CREATE INDEX IF NOT EXISTS idx_gov_budgets_chapter ON governance_budgets(novel_id, chapter_number)")
        logger.info("governance_budgets table created")
    except Exception:
        logger.error("Migration 009 failed: CREATE TABLE governance_budgets", exc_info=True)

    # 叙事债务
    try:
        op.execute("""
            CREATE TABLE IF NOT EXISTS narrative_debts (
                id TEXT PRIMARY KEY,
                novel_id TEXT NOT NULL,
                kind TEXT DEFAULT 'foreshadow',
                description TEXT DEFAULT '',
                raised_chapter INTEGER,
                suggested_resolve_chapter INTEGER,
                actual_resolve_chapter INTEGER,
                importance TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'open',
                metadata TEXT DEFAULT '{}',
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (novel_id) REFERENCES novels(id) ON DELETE CASCADE
            )
        """)
        op.execute("CREATE INDEX IF NOT EXISTS idx_debts_novel ON narrative_debts(novel_id)")
        op.execute("CREATE INDEX IF NOT EXISTS idx_debts_status ON narrative_debts(status)")
        op.execute("CREATE INDEX IF NOT EXISTS idx_debts_resolve ON narrative_debts(suggested_resolve_chapter)")
        logger.info("narrative_debts table created")
    except Exception:
        logger.error("Migration 009 failed: CREATE TABLE narrative_debts", exc_info=True)


def downgrade() -> None:
    """删除叙事治理表。"""
    for stmt in [
        "DROP INDEX IF EXISTS idx_debts_resolve",
        "DROP INDEX IF EXISTS idx_debts_status",
        "DROP INDEX IF EXISTS idx_debts_novel",
        "DROP TABLE IF EXISTS narrative_debts",
        "DROP INDEX IF EXISTS idx_gov_budgets_chapter",
        "DROP INDEX IF EXISTS idx_gov_budgets_novel",
        "DROP TABLE IF EXISTS governance_budgets",
    ]:
        try:
            op.execute(stmt)
        except Exception as e:
            logger.warning("Migration 009 downgrade skipped: %s", e)
