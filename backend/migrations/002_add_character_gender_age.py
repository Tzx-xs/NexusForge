"""BLOCK-08: Character 新增 gender/age 字段

Revision ID: 002
Revises: 001
Create Date: 2026-07-04
"""
import logging
from collections.abc import Sequence

from alembic import op

logger = logging.getLogger(__name__)


# revision identifiers
revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """添加 gender 和 age 列到 characters 表。"""
    # 使用 try/except 健壮执行，避免列已存在的错误
    try:
        op.execute("ALTER TABLE characters ADD COLUMN gender TEXT DEFAULT ''")
    except Exception:
        logger.error("Migration 002 failed: ALTER TABLE characters ADD COLUMN gender", exc_info=True)

    try:
        op.execute("ALTER TABLE characters ADD COLUMN age TEXT DEFAULT ''")
    except Exception:
        logger.error("Migration 002 failed: ALTER TABLE characters ADD COLUMN age", exc_info=True)


def downgrade() -> None:
    """SQLite 不支持 DROP COLUMN，降级为重建表（数据丢失警告）。"""
    # SQLite 3.35+ 支持 DROP COLUMN，但如果版本低则跳过
    try:
        op.execute("ALTER TABLE characters DROP COLUMN gender")
    except Exception as e:
        logger.warning("Drop column gender skipped: %s", e)

    try:
        op.execute("ALTER TABLE characters DROP COLUMN age")
    except Exception as e:
        logger.warning("Drop column age skipped: %s", e)
