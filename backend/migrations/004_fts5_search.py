"""BLOCK-FTS5: 全文搜索虚拟表

Revision ID: 004
Revises: 003
Create Date: 2026-07-04

创建 5 个 FTS5 虚拟表 + 初始索引 + 触发器自动同步。
"""
import logging
from collections.abc import Sequence

from alembic import op

logger = logging.getLogger(__name__)

# revision identifiers
revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# FTS5 虚拟表定义
_FTS_TABLES: list[dict[str, str]] = [
    {
        "fts_name": "chapters_fts",
        "source_table": "chapters",
        "columns": "title, outline, content",
    },
    {
        "fts_name": "characters_fts",
        "source_table": "characters",
        "columns": "name, description",
    },
    {
        "fts_name": "foreshadows_fts",
        "source_table": "foreshadows",
        "columns": "title, description",
    },
    {
        "fts_name": "world_settings_fts",
        "source_table": "world_settings",
        "columns": "name, description",
    },
    {
        "fts_name": "memory_facts_fts",
        "source_table": "memory_facts",
        "columns": "key, value",
    },
]


def _create_triggers(fts_name: str, source_table: str, columns: str) -> None:
    """为 FTS5 虚拟表创建 INSERT/UPDATE/DELETE 触发器。

    触发器在源表变更后自动同步 FTS5 索引，保持全文搜索数据一致。
    """
    col_list = [c.strip() for c in columns.split(",")]

    # INSERT 触发器：新行写入后同步到 FTS5
    insert_cols = ", ".join(col_list)
    insert_new_cols = ", ".join(f"new.{c}" for c in col_list)
    op.execute(f"""
        CREATE TRIGGER IF NOT EXISTS {fts_name}_ai AFTER INSERT ON {source_table}
        BEGIN
            INSERT INTO {fts_name}(rowid, {insert_cols})
            VALUES (new.rowid, {insert_new_cols});
        END;
    """)

    # DELETE 触发器：行删除后从 FTS5 移除
    # 注意：某些 SQLite 编译版本（如 Windows 官方 Python 绑定）不支持
    # FTS5 的 "INSERT ... VALUES ('delete', ...)" 特殊语法，因此使用普通 DELETE。
    op.execute(f"""
        CREATE TRIGGER IF NOT EXISTS {fts_name}_ad AFTER DELETE ON {source_table}
        BEGIN
            DELETE FROM {fts_name} WHERE rowid = old.rowid;
        END;
    """)

    # UPDATE 触发器：行更新后同步 FTS5
    op.execute(f"""
        CREATE TRIGGER IF NOT EXISTS {fts_name}_au AFTER UPDATE ON {source_table}
        BEGIN
            DELETE FROM {fts_name} WHERE rowid = old.rowid;
            INSERT INTO {fts_name}(rowid, {insert_cols})
            VALUES (new.rowid, {insert_new_cols});
        END;
    """)


def upgrade() -> None:
    """创建 FTS5 虚拟表、初始索引和同步触发器。"""
    for table_def in _FTS_TABLES:
        fts_name = table_def["fts_name"]
        source_table = table_def["source_table"]
        columns = table_def["columns"]

        try:
            # 创建 FTS5 虚拟表（使用 unicode61 tokenizer 支持中文单字分词）
            op.execute(f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS {fts_name}
                USING fts5({columns}, tokenize='unicode61');
            """)
            logger.info("FTS5 virtual table %s created", fts_name)
        except Exception:
            logger.error("Failed to create FTS5 table %s", fts_name, exc_info=True)
            continue

        try:
            # 初始索引：从源表导入已有数据
            col_list = ", ".join(c.strip() for c in columns.split(","))
            op.execute(f"""
                INSERT INTO {fts_name}(rowid, {col_list})
                SELECT rowid, {col_list} FROM {source_table};
            """)
            logger.info("FTS5 initial index populated for %s", fts_name)
        except Exception:
            logger.error(
                "Failed to populate initial index for %s", fts_name, exc_info=True
            )

        try:
            # 创建触发器自动同步
            _create_triggers(fts_name, source_table, columns)
            logger.info("FTS5 triggers created for %s", fts_name)
        except Exception:
            logger.error("Failed to create triggers for %s", fts_name, exc_info=True)


def downgrade() -> None:
    """删除 FTS5 虚拟表和所有触发器。"""
    for table_def in _FTS_TABLES:
        fts_name = table_def["fts_name"]

        try:
            op.execute(f"DROP TRIGGER IF EXISTS {fts_name}_ai")
        except Exception as e:
            logger.warning("Drop trigger %s_ai skipped: %s", fts_name, e)
        try:
            op.execute(f"DROP TRIGGER IF EXISTS {fts_name}_ad")
        except Exception as e:
            logger.warning("Drop trigger %s_ad skipped: %s", fts_name, e)
        try:
            op.execute(f"DROP TRIGGER IF EXISTS {fts_name}_au")
        except Exception as e:
            logger.warning("Drop trigger %s_au skipped: %s", fts_name, e)
        try:
            op.execute(f"DROP TABLE IF EXISTS {fts_name}")
        except Exception as e:
            logger.warning("Drop table %s skipped: %s", fts_name, e)

    logger.info("FTS5 migration downgraded")
