"""迁移链测试：验证 008-011 新增表可正常创建

用 importlib 动态加载数字开头的迁移模块。
"""
import importlib.util
import os
import sqlite3
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIGRATIONS_DIR = os.path.join(BACKEND_DIR, "migrations")


def _load_migration_module(filename: str):
    """动态加载迁移模块（文件名以数字开头，不能直接 import）"""
    path = os.path.join(MIGRATIONS_DIR, filename)
    spec = importlib.util.spec_from_file_location(filename.replace(".py", ""), path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_migration(conn, migration_module):
    """手动应用迁移到给定连接（绕过 alembic 上下文）"""

    class FakeBind:
        """模拟 SQLAlchemy Connection，支持 text() SQL 执行"""
        def execute(self, stmt):
            # stmt 可能是 str 或 sqlalchemy text() 对象
            sql = str(stmt) if not isinstance(stmt, str) else stmt
            return conn.execute(sql)

    class FakeOp:
        def execute(self, sql):
            sql_str = str(sql) if not isinstance(sql, str) else sql
            conn.execute(sql_str)

        def get_bind(self):
            return FakeBind()

    with patch.object(migration_module, "op", FakeOp()):
        migration_module.upgrade()


@pytest.fixture
def fresh_db():
    """临时空数据库（含 novels + storylines 表供外键引用）

    storylines 表用 StellarScribe 原始结构（008 会 ALTER 扩展）。
    """
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE novels (
            id TEXT PRIMARY KEY,
            title TEXT,
            status TEXT DEFAULT 'draft'
        )
    """)
    # StellarScribe 原始 storylines 表结构（008 会 ALTER 添加 kind/status 等列）
    conn.execute("""
        CREATE TABLE storylines (
            id TEXT PRIMARY KEY,
            novel_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            color TEXT,
            node_count INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT
        )
    """)
    yield conn
    conn.close()
    os.unlink(path)


class TestMigration008DagTables:
    def test_creates_dag_tables(self, fresh_db):
        m = _load_migration_module("008_add_dag_tables.py")
        _run_migration(fresh_db, m)

        tables = [
            r[0] for r in fresh_db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        assert "storylines" in tables
        assert "story_dag_nodes" in tables
        assert "story_dag_edges" in tables

    def test_storylines_columns(self, fresh_db):
        m = _load_migration_module("008_add_dag_tables.py")
        _run_migration(fresh_db, m)

        cols = [r[1] for r in fresh_db.execute("PRAGMA table_info(storylines)").fetchall()]
        for expected in ["id", "novel_id", "name", "kind", "status", "start_chapter", "end_chapter"]:
            assert expected in cols, f"missing column {expected}"

    def test_dag_nodes_indexes(self, fresh_db):
        m = _load_migration_module("008_add_dag_tables.py")
        _run_migration(fresh_db, m)

        indexes = [
            r[0] for r in fresh_db.execute(
                "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='story_dag_nodes'"
            ).fetchall()
        ]
        assert "idx_dag_nodes_novel" in indexes
        assert "idx_dag_nodes_type" in indexes

    def test_idempotent(self, fresh_db):
        """重复执行不报错（CREATE TABLE IF NOT EXISTS）"""
        m = _load_migration_module("008_add_dag_tables.py")
        _run_migration(fresh_db, m)
        _run_migration(fresh_db, m)


class TestMigration009GovernanceTables:
    def test_creates_governance_tables(self, fresh_db):
        m = _load_migration_module("009_add_governance_tables.py")
        _run_migration(fresh_db, m)

        tables = [
            r[0] for r in fresh_db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        assert "governance_budgets" in tables
        assert "narrative_debts" in tables

    def test_budgets_unique_constraint(self, fresh_db):
        """(novel_id, chapter_number) 唯一约束"""
        m = _load_migration_module("009_add_governance_tables.py")
        _run_migration(fresh_db, m)

        fresh_db.execute(
            "INSERT INTO governance_budgets (id, novel_id, chapter_number) VALUES (?, ?, ?)",
            ("b1", "n1", 1),
        )
        with pytest.raises(sqlite3.IntegrityError):
            fresh_db.execute(
                "INSERT INTO governance_budgets (id, novel_id, chapter_number) VALUES (?, ?, ?)",
                ("b2", "n1", 1),
            )


class TestMigration010CheckpointTables:
    def test_creates_checkpoint_table(self, fresh_db):
        m = _load_migration_module("010_add_checkpoint_tables.py")
        _run_migration(fresh_db, m)

        tables = [
            r[0] for r in fresh_db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        assert "engine_checkpoints" in tables

    def test_checkpoint_columns(self, fresh_db):
        m = _load_migration_module("010_add_checkpoint_tables.py")
        _run_migration(fresh_db, m)

        cols = [r[1] for r in fresh_db.execute("PRAGMA table_info(engine_checkpoints)").fetchall()]
        for expected in ["novel_id", "chapter_number", "pipeline_run_id", "step_name", "context_snapshot", "audit_snapshot"]:
            assert expected in cols


class TestMigration011AiInvocationTables:
    def test_creates_invocation_table(self, fresh_db):
        m = _load_migration_module("011_add_ai_invocation_tables.py")
        _run_migration(fresh_db, m)

        tables = [
            r[0] for r in fresh_db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        assert "ai_invocations" in tables

    def test_invocation_columns(self, fresh_db):
        m = _load_migration_module("011_add_ai_invocation_tables.py")
        _run_migration(fresh_db, m)

        cols = [r[1] for r in fresh_db.execute("PRAGMA table_info(ai_invocations)").fetchall()]
        for expected in ["novel_id", "session_id", "stage", "operation", "prompt_key", "model", "tokens_input", "tokens_output", "status"]:
            assert expected in cols


class TestMigrationChainOrder:
    """迁移链顺序正确"""

    def test_revision_ids(self):
        m8 = _load_migration_module("008_add_dag_tables.py")
        m9 = _load_migration_module("009_add_governance_tables.py")
        m10 = _load_migration_module("010_add_checkpoint_tables.py")
        m11 = _load_migration_module("011_add_ai_invocation_tables.py")

        assert m8.revision == "008"
        assert m9.revision == "009" and m9.down_revision == "008"
        assert m10.revision == "010" and m10.down_revision == "009"
        assert m11.revision == "011" and m11.down_revision == "010"


class TestFullMigrationChain:
    """完整迁移链可顺序执行"""

    def test_all_migrations_apply_sequentially(self, fresh_db):
        for filename in [
            "008_add_dag_tables.py",
            "009_add_governance_tables.py",
            "010_add_checkpoint_tables.py",
            "011_add_ai_invocation_tables.py",
        ]:
            m = _load_migration_module(filename)
            _run_migration(fresh_db, m)

        tables = [
            r[0] for r in fresh_db.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        ]
        for expected in [
            "storylines", "story_dag_nodes", "story_dag_edges",
            "governance_budgets", "narrative_debts",
            "engine_checkpoints", "ai_invocations",
        ]:
            assert expected in tables, f"missing table {expected}"
