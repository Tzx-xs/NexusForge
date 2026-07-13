"""Add style_tags and perspective columns to novels table.

Revision ID: 005
Revises: 004
Create Date: 2026-07-06
"""
import logging
from collections.abc import Sequence

from alembic import op

logger = logging.getLogger(__name__)


# revision identifiers
revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """添加 style_tags 和 perspective 列到 novels 表。"""
    try:
        op.execute("ALTER TABLE novels ADD COLUMN style_tags TEXT DEFAULT '[]'")
    except Exception:
        logger.error("Migration 005 failed: ALTER TABLE novels ADD COLUMN style_tags", exc_info=True)

    try:
        op.execute("ALTER TABLE novels ADD COLUMN perspective TEXT DEFAULT ''")
    except Exception:
        logger.error("Migration 005 failed: ALTER TABLE novels ADD COLUMN perspective", exc_info=True)


def downgrade() -> None:
    """SQLite 不支持 DROP COLUMN，降级时尝试删除。"""
    try:
        op.execute("ALTER TABLE novels DROP COLUMN style_tags")
    except Exception as e:
        logger.warning("Drop column style_tags skipped: %s", e)

    try:
        op.execute("ALTER TABLE novels DROP COLUMN perspective")
    except Exception as e:
        logger.warning("Drop column perspective skipped: %s", e)
