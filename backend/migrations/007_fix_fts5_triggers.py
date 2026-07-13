"""BLOCK-FTS5-FIX: 修复 FTS5 触发器兼容性

Revision ID: 007
Revises: 006
Create Date: 2026-07-07

Windows 官方 Python 绑定中的 SQLite 对 FTS5 的
"INSERT INTO fts(tbl, rowid, ...) VALUES ('delete', ...)" 特殊语法
返回 SQL logic error，导致源表 UPDATE/DELETE 失败。

本迁移将已存在的 *_ad / *_au 触发器替换为等价的
DELETE FROM fts WHERE rowid = old.rowid 语法。
"""
import logging
from collections.abc import Sequence

from alembic import op

logger = logging.getLogger(__name__)

revision: str = "007"
down_revision: str | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FTS_TABLES: list[dict[str, str]] = [
    {"fts_name": "chapters_fts", "source_table": "chapters", "columns": "title, outline, content"},
    {"fts_name": "characters_fts", "source_table": "characters", "columns": "name, description"},
    {"fts_name": "foreshadows_fts", "source_table": "foreshadows", "columns": "title, description"},
    {"fts_name": "world_settings_fts", "source_table": "world_settings", "columns": "name, description"},
    {"fts_name": "memory_facts_fts", "source_table": "memory_facts", "columns": "key, value"},
]


def _replace_trigger(fts_name: str, source_table: str, columns: str) -> None:
    col_list = [c.strip() for c in columns.split(",")]
    insert_cols = ", ".join(col_list)
    insert_new_cols = ", ".join(f"new.{c}" for c in col_list)

    # 删除旧的 DELETE/UPDATE 触发器（INSERT 触发器无需修改）
    op.execute(f"DROP TRIGGER IF EXISTS {fts_name}_ad")
    op.execute(f"DROP TRIGGER IF EXISTS {fts_name}_au")

    # 使用兼容语法的 DELETE 触发器
    op.execute(f"""
        CREATE TRIGGER IF NOT EXISTS {fts_name}_ad AFTER DELETE ON {source_table}
        BEGIN
            DELETE FROM {fts_name} WHERE rowid = old.rowid;
        END;
    """)

    # 使用兼容语法的 UPDATE 触发器
    op.execute(f"""
        CREATE TRIGGER IF NOT EXISTS {fts_name}_au AFTER UPDATE ON {source_table}
        BEGIN
            DELETE FROM {fts_name} WHERE rowid = old.rowid;
            INSERT INTO {fts_name}(rowid, {insert_cols})
            VALUES (new.rowid, {insert_new_cols});
        END;
    """)

    logger.info("FTS5 triggers replaced for %s", fts_name)


def upgrade() -> None:
    """替换已存在的 FTS5 DELETE/UPDATE 触发器。"""
    for table_def in _FTS_TABLES:
        try:
            _replace_trigger(table_def["fts_name"], table_def["source_table"], table_def["columns"])
        except Exception:
            logger.error("Failed to replace FTS5 triggers for %s", table_def["fts_name"], exc_info=True)


def downgrade() -> None:
    """回退为使用 FTS5 'delete' 特殊语法的触发器（不推荐在生产环境使用）。"""
    for table_def in _FTS_TABLES:
        fts_name = table_def["fts_name"]
        source_table = table_def["source_table"]
        columns = table_def["columns"]
        col_list = [c.strip() for c in columns.split(",")]
        insert_cols = ", ".join(col_list)
        insert_old_cols = ", ".join(f"old.{c}" for c in col_list)
        insert_new_cols = ", ".join(f"new.{c}" for c in col_list)

        try:
            op.execute(f"DROP TRIGGER IF EXISTS {fts_name}_ad")
            op.execute(f"DROP TRIGGER IF EXISTS {fts_name}_au")
            op.execute(f"""
                CREATE TRIGGER IF NOT EXISTS {fts_name}_ad AFTER DELETE ON {source_table}
                BEGIN
                    INSERT INTO {fts_name}({fts_name}, rowid, {insert_cols})
                    VALUES ('delete', old.rowid, {insert_old_cols});
                END;
            """)
            op.execute(f"""
                CREATE TRIGGER IF NOT EXISTS {fts_name}_au AFTER UPDATE ON {source_table}
                BEGIN
                    INSERT INTO {fts_name}({fts_name}, rowid, {insert_cols})
                    VALUES ('delete', old.rowid, {insert_old_cols});
                    INSERT INTO {fts_name}(rowid, {insert_cols})
                    VALUES (new.rowid, {insert_new_cols});
                END;
            """)
        except Exception as e:
            logger.warning("Downgrade FTS5 triggers for %s skipped: %s", fts_name, e)
