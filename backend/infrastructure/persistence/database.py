import logging
import os
import sqlite3
import threading
from typing import cast

from config.defaults import SQLITE_BUSY_TIMEOUT

logger = logging.getLogger(__name__)


class Database:
    """数据库访问层。

    使用原生 sqlite3 进行数据访问，通过 Alembic 管理 DDL 迁移。
    """

    def __init__(self, db_path: str):
        self.db_path = self._normalize_path(db_path)
        self._local = threading.local()

    def _normalize_path(self, path: str) -> str:
        if path.startswith("sqlite:///"):
            return path[10:]
        return path

    def get_connection(self) -> sqlite3.Connection:
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=-64000")
            conn.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT}")
            self._local.connection = conn
            return conn
        return cast("sqlite3.Connection", self._local.connection)

    def close_connection(self) -> None:
        if hasattr(self._local, 'connection') and self._local.connection is not None:
            self._local.connection.close()
            self._local.connection = None

    def init_db(self) -> None:
        """初始化数据库：通过 Alembic 执行所有未应用的迁移。

        替代原来的 schema.sql 直接执行方式，支持版本化迁移管理。
        schema.sql 保留作为参考文档。
        """
        try:
            from alembic.config import Config as AlembicConfig

            from alembic import command

            # 设置数据库路径到环境变量供 alembic/env.py 使用
            os.environ["XINGYUANBI_DB_PATH"] = self.db_path

            # 定位 alembic.ini 和 migrations 目录
            backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            alembic_ini = os.path.join(backend_dir, "alembic.ini")

            if not os.path.exists(alembic_ini):
                logger.warning(
                    "alembic.ini 未找到，降级为 schema.sql 直接执行: %s", alembic_ini
                )
                self._init_db_fallback()
                return

            alembic_cfg = AlembicConfig(alembic_ini)
            # 确保 Alembic 使用正确的脚本目录
            alembic_cfg.set_main_option("script_location", os.path.join(backend_dir, "alembic"))

            command.upgrade(alembic_cfg, "head")
            with self.get_connection() as conn:
                self._ensure_cover_url_column(conn)
                self._ensure_style_tags_column(conn)
                self._ensure_perspective_column(conn)
                # BLOCK-08/09 兼容：Alembic 迁移理论上已加这些列，
                # 但旧库/异常中断场景下补检，避免 repo 读写崩溃
                self._ensure_gender_age_columns(conn)
                self._ensure_snapshot_content_column(conn)
            logger.info("数据库迁移完成（Alembic upgrade head）")
        except ImportError:
            logger.warning(
                "Alembic 未安装，降级为 schema.sql 直接执行。"
                "请运行: pip install alembic sqlalchemy"
            )
            self._init_db_fallback()
        except Exception as e:
            logger.error("Alembic 迁移失败: %s，降级为 schema.sql 直接执行", e, exc_info=True)
            self._init_db_fallback()

    def _init_db_fallback(self) -> None:
        """降级方案：直接执行 schema.sql（兼容 alembic 不可用的情况）。

        将 schema.sql 拆分为「表结构」与「FTS5 全文搜索」两段执行：
        表结构段必须成功；FTS5 段单独 try（SQLite 未编译 FTS5 模块时跳过，
        SearchService 会回退到 LIKE 查询），避免 FTS5 不可用导致整体初始化失败。
        """
        schema = self._load_schema()
        base_schema, fts5_schema = self._split_fts5_section(schema)
        with self.get_connection() as conn:
            # 1. 表结构（含索引/触发器以外的 DDL）必须成功
            conn.executescript(base_schema)
            self._ensure_cover_url_column(conn)
            self._ensure_style_tags_column(conn)
            self._ensure_perspective_column(conn)
            self._ensure_gender_age_columns(conn)
            self._ensure_snapshot_content_column(conn)
            # 2. FTS5 段单独容错执行
            if fts5_schema:
                try:
                    conn.executescript(fts5_schema)
                    logger.info("FTS5 全文搜索表已初始化（降级方案）")
                except Exception as e:
                    logger.warning(
                        "FTS5 初始化失败，全文搜索将回退到 LIKE 查询: %s", e
                    )
        logger.info("数据库初始化完成（schema.sql 降级方案）")

    @staticmethod
    def _split_fts5_section(schema: str) -> tuple[str, str]:
        """将 schema.sql 拆为 (表结构段, FTS5 段)。

        以 FTS5 段落标记注释为分隔。无标记时全部归入表结构段。
        """
        marker = "-- ==================== FTS5"
        idx = schema.find(marker)
        if idx == -1:
            return schema, ""
        return schema[:idx], schema[idx:]

    def _ensure_cover_url_column(self, conn: sqlite3.Connection) -> None:
        """确保 novels 表包含 cover_url 列（兼容旧数据库）。"""
        rows = conn.execute("PRAGMA table_info(novels)").fetchall()
        columns = [row[1] for row in rows]
        if 'cover_url' not in columns:
            conn.execute("ALTER TABLE novels ADD COLUMN cover_url TEXT DEFAULT ''")
            logger.info("已添加 cover_url 列到 novels 表")

    def _ensure_style_tags_column(self, conn: sqlite3.Connection) -> None:
        """确保 novels 表包含 style_tags 列（兼容旧数据库）。"""
        rows = conn.execute("PRAGMA table_info(novels)").fetchall()
        columns = [row[1] for row in rows]
        if 'style_tags' not in columns:
            conn.execute("ALTER TABLE novels ADD COLUMN style_tags TEXT DEFAULT '[]'")
            logger.info("已添加 style_tags 列到 novels 表")

    def _ensure_perspective_column(self, conn: sqlite3.Connection) -> None:
        """确保 novels 表包含 perspective 列（兼容旧数据库）。"""
        rows = conn.execute("PRAGMA table_info(novels)").fetchall()
        columns = [row[1] for row in rows]
        if 'perspective' not in columns:
            conn.execute("ALTER TABLE novels ADD COLUMN perspective TEXT DEFAULT ''")
            logger.info("已添加 perspective 列到 novels 表")

    def _ensure_gender_age_columns(self, conn: sqlite3.Connection) -> None:
        """确保 characters 表包含 gender/age 列（BLOCK-08 兼容旧数据库）。

        CharacterRepository.create/update 会读写这两列，缺失会导致 INSERT/UPDATE 崩溃。
        """
        rows = conn.execute("PRAGMA table_info(characters)").fetchall()
        columns = [row[1] for row in rows]
        if 'gender' not in columns:
            conn.execute("ALTER TABLE characters ADD COLUMN gender TEXT DEFAULT ''")
            logger.info("已添加 gender 列到 characters 表")
        if 'age' not in columns:
            conn.execute("ALTER TABLE characters ADD COLUMN age TEXT DEFAULT ''")
            logger.info("已添加 age 列到 characters 表")

    def _ensure_snapshot_content_column(self, conn: sqlite3.Connection) -> None:
        """确保 snapshots 表包含 content 列（BLOCK-09 兼容旧数据库）。

        SnapshotRepository.create 会写入 content 列，缺失会导致 INSERT 崩溃。
        """
        rows = conn.execute("PRAGMA table_info(snapshots)").fetchall()
        columns = [row[1] for row in rows]
        if 'content' not in columns:
            conn.execute("ALTER TABLE snapshots ADD COLUMN content TEXT DEFAULT ''")
            logger.info("已添加 content 列到 snapshots 表")

    def query(self, sql: str, params: tuple = ()) -> list:
        # L-02 修复：删除空 try/finally: pass 死代码。
        conn = self.get_connection()
        rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def query_one(self, sql: str, params: tuple = ()) -> dict | None:
        conn = self.get_connection()
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    def execute(self, sql: str, params: tuple = ()) -> int:
        conn = self.get_connection()
        try:
            cursor = conn.execute(sql, params)
            conn.commit()
            return cursor.rowcount
        except Exception:
            conn.rollback()
            raise

    def _load_schema(self) -> str:
        schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
        with open(schema_path, encoding="utf-8") as f:
            return f.read()
