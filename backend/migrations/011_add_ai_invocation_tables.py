"""011: AI Invocation 调用记录表

Revision ID: 011
Revises: 010
Create Date: 2026-07-13

新增表：
- ai_invocations: LLM 调用记录（可观测/可审计/可重放）
"""
import logging
from collections.abc import Sequence

from alembic import op

logger = logging.getLogger(__name__)

revision: str = "011"
down_revision: str | None = "010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建 AI Invocation 记录表。"""
    try:
        op.execute("""
            CREATE TABLE IF NOT EXISTS ai_invocations (
                id TEXT PRIMARY KEY,
                novel_id TEXT,
                chapter_number INTEGER,
                session_id TEXT,
                stage TEXT,
                operation TEXT,
                prompt_key TEXT,
                prompt_text TEXT DEFAULT '',
                prompt_variables TEXT DEFAULT '{}',
                model TEXT DEFAULT '',
                provider TEXT DEFAULT '',
                config TEXT DEFAULT '{}',
                output_text TEXT DEFAULT '',
                output_metadata TEXT DEFAULT '{}',
                tokens_input INTEGER DEFAULT 0,
                tokens_output INTEGER DEFAULT 0,
                duration_ms INTEGER DEFAULT 0,
                status TEXT DEFAULT 'success',
                error TEXT DEFAULT '',
                created_at TEXT,
                FOREIGN KEY (novel_id) REFERENCES novels(id) ON DELETE SET NULL
            )
        """)
        op.execute("CREATE INDEX IF NOT EXISTS idx_invocations_novel ON ai_invocations(novel_id)")
        op.execute("CREATE INDEX IF NOT EXISTS idx_invocations_session ON ai_invocations(session_id)")
        op.execute("CREATE INDEX IF NOT EXISTS idx_invocations_stage ON ai_invocations(stage)")
        op.execute("CREATE INDEX IF NOT EXISTS idx_invocations_created ON ai_invocations(created_at DESC)")
        logger.info("ai_invocations table created")
    except Exception:
        logger.error("Migration 011 failed: CREATE TABLE ai_invocations", exc_info=True)


def downgrade() -> None:
    """删除 AI Invocation 记录表。"""
    for stmt in [
        "DROP INDEX IF EXISTS idx_invocations_created",
        "DROP INDEX IF EXISTS idx_invocations_stage",
        "DROP INDEX IF EXISTS idx_invocations_session",
        "DROP INDEX IF EXISTS idx_invocations_novel",
        "DROP TABLE IF EXISTS ai_invocations",
    ]:
        try:
            op.execute(stmt)
        except Exception as e:
            logger.warning("Migration 011 downgrade skipped: %s", e)
