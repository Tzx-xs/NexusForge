"""扩展 novels 表 — 对齐 PlotPilot 前端 NovelDTO 字段

Revision ID: 012
Revises: 011
Create Date: 2026-07-13

新增字段：
- author                 作者
- stage                  小说阶段（preparing/outlining/writing/revising/completed）
- auto_approve_mode      自动审核模式（0/1）
- target_words_per_chapter 每章目标字数
- generation_prefs       生成偏好（JSON 字符串）
- world_preset           世界观基调
- story_structure        故事结构
- pacing_control         节拍控制
- writing_style          写作风格
- special_requirements   特殊要求

StellarScribe 原 novels 表仅 9 字段，PlotPilot 前端 NovelDTO 期望 ~20 字段。
本迁移在不动旧字段的前提下增量补齐，后端 Domain/Service/Repo/Response 同步支持。
"""
from collections.abc import Sequence

from alembic import op

revision: str = "012"
down_revision: str | None = "011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(conn, table: str, column: str) -> bool:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return any(r[1] == column for r in rows)


def _add_column_if_missing(conn, table: str, column: str, ddl_type: str) -> None:
    if not _column_exists(conn, table, column):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl_type}")


def upgrade() -> None:
    bind = op.get_bind()
    # author
    _add_column_if_missing(bind, "novels", "author", "TEXT DEFAULT ''")
    # stage
    _add_column_if_missing(bind, "novels", "stage", "TEXT DEFAULT 'preparing'")
    # auto_approve_mode（SQLite 用 INTEGER 表 bool）
    _add_column_if_missing(bind, "novels", "auto_approve_mode", "INTEGER DEFAULT 0")
    # target_words_per_chapter
    _add_column_if_missing(bind, "novels", "target_words_per_chapter", "INTEGER DEFAULT 2500")
    # generation_prefs（JSON 字符串）
    _add_column_if_missing(bind, "novels", "generation_prefs", "TEXT DEFAULT '{}'")
    # PlotPilot 建档字段
    _add_column_if_missing(bind, "novels", "world_preset", "TEXT DEFAULT ''")
    _add_column_if_missing(bind, "novels", "story_structure", "TEXT DEFAULT ''")
    _add_column_if_missing(bind, "novels", "pacing_control", "TEXT DEFAULT ''")
    _add_column_if_missing(bind, "novels", "writing_style", "TEXT DEFAULT ''")
    _add_column_if_missing(bind, "novels", "special_requirements", "TEXT DEFAULT ''")


def downgrade() -> None:
    # SQLite 不支持 DROP COLUMN（3.35+ 支持，但生产兼容性差），downgrade 留空
    pass
