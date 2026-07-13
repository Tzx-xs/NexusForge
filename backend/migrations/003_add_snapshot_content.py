"""BLOCK-09: Snapshot 新增 content 列

Revision ID: 003
Revises: 002
Create Date: 2026-07-04
"""
import logging
from collections.abc import Sequence

from alembic import op

logger = logging.getLogger(__name__)


# revision identifiers
revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """添加 content 列到 snapshots 表。"""
    try:
        op.execute("ALTER TABLE snapshots ADD COLUMN content TEXT DEFAULT ''")
    except Exception:
        logger.error("Migration 003 failed: ALTER TABLE snapshots ADD COLUMN content", exc_info=True)


def downgrade() -> None:
    """SQLite 不支持 DROP COLUMN，降级时尝试删除。"""
    try:
        op.execute("ALTER TABLE snapshots DROP COLUMN content")
    except Exception as e:
        logger.warning("Drop column content skipped: %s", e)
