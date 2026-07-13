"""BLOCK-10: 新增 review_tasks 表

Revision ID: 006
Revises: 005
Create Date: 2026-07-06

用于内容审查模块的轻量级审查任务。
"""
import logging
from collections.abc import Sequence

from alembic import op

logger = logging.getLogger(__name__)

# revision identifiers
revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """创建 review_tasks 表及索引。"""
    try:
        op.execute("""
            CREATE TABLE IF NOT EXISTS review_tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                novel_id TEXT,
                status TEXT DEFAULT 'pending',
                result TEXT DEFAULT '',
                created_at TEXT,
                updated_at TEXT
            )
        """)
        logger.info("review_tasks table created")
    except Exception:
        logger.error("Migration 006 failed: CREATE TABLE review_tasks", exc_info=True)

    try:
        op.execute("CREATE INDEX IF NOT EXISTS idx_review_tasks_created_at ON review_tasks(created_at DESC)")
    except Exception:
        logger.error("Migration 006 failed: CREATE INDEX idx_review_tasks_created_at", exc_info=True)

    try:
        op.execute("CREATE INDEX IF NOT EXISTS idx_review_tasks_novel ON review_tasks(novel_id)")
    except Exception:
        logger.error("Migration 006 failed: CREATE INDEX idx_review_tasks_novel", exc_info=True)


def downgrade() -> None:
    """删除 review_tasks 表及索引。"""
    try:
        op.execute("DROP INDEX IF EXISTS idx_review_tasks_novel")
    except Exception as e:
        logger.warning("Drop index idx_review_tasks_novel skipped: %s", e)

    try:
        op.execute("DROP INDEX IF EXISTS idx_review_tasks_created_at")
    except Exception as e:
        logger.warning("Drop index idx_review_tasks_created_at skipped: %s", e)

    try:
        op.execute("DROP TABLE IF EXISTS review_tasks")
    except Exception as e:
        logger.warning("Drop table review_tasks skipped: %s", e)
