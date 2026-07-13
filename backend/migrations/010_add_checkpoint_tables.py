"""010: 检查点表

Revision ID: 010
Revises: 009
Create Date: 2026-07-13

新增表：
- engine_checkpoints: 引擎检查点快照（崩溃恢复用）
"""
import logging
from collections.abc import Sequence

from alembic import op

logger = logging.getLogger(__name__)

revision: str = "010"
down_revision: str | None = "009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建检查点表。"""
    try:
        op.execute("""
            CREATE TABLE IF NOT EXISTS engine_checkpoints (
                id TEXT PRIMARY KEY,
                novel_id TEXT NOT NULL,
                chapter_number INTEGER,
                pipeline_run_id TEXT,
                step_name TEXT,
                step_status TEXT,
                context_snapshot TEXT DEFAULT '{}',
                audit_snapshot TEXT DEFAULT '{}',
                status TEXT DEFAULT 'active',
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (novel_id) REFERENCES novels(id) ON DELETE CASCADE
            )
        """)
        op.execute("CREATE INDEX IF NOT EXISTS idx_checkpoints_novel ON engine_checkpoints(novel_id)")
        op.execute("CREATE INDEX IF NOT EXISTS idx_checkpoints_status ON engine_checkpoints(status)")
        op.execute("CREATE INDEX IF NOT EXISTS idx_checkpoints_run ON engine_checkpoints(pipeline_run_id)")
        op.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_checkpoints_active ON engine_checkpoints(novel_id, status) WHERE status = 'active'")
        logger.info("engine_checkpoints table created")
    except Exception:
        logger.error("Migration 010 failed: CREATE TABLE engine_checkpoints", exc_info=True)


def downgrade() -> None:
    """删除检查点表。"""
    for stmt in [
        "DROP INDEX IF EXISTS idx_checkpoints_active",
        "DROP INDEX IF EXISTS idx_checkpoints_run",
        "DROP INDEX IF EXISTS idx_checkpoints_status",
        "DROP INDEX IF EXISTS idx_checkpoints_novel",
        "DROP TABLE IF EXISTS engine_checkpoints",
    ]:
        try:
            op.execute(stmt)
        except Exception as e:
            logger.warning("Migration 010 downgrade skipped: %s", e)
