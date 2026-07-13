"""008: 故事线 DAG 表

Revision ID: 008
Revises: 007
Create Date: 2026-07-13

新增表：
- story_dag_nodes: 故事线 DAG 节点（章节/支线/转折点）
- story_dag_edges: DAG 边（因果/时序/汇合）

扩展表：
- storylines: 添加 kind/status/start_chapter/end_chapter 列（PlotPilot 风格）
  注意：StellarScribe 已有 storylines 表，此处用 ALTER 扩展而非重建
"""
import logging
from collections.abc import Sequence

from alembic import op
from sqlalchemy import text

logger = logging.getLogger(__name__)

revision: str = "008"
down_revision: str | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_exists(conn, table: str, column: str) -> bool:
    """检查列是否已存在（SQLite PRAGMA table_info）"""
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return any(r[1] == column for r in rows)


def upgrade() -> None:
    """创建故事线 DAG 表并扩展 storylines。"""
    # 扩展现有 storylines 表（StellarScribe 已有，添加 PlotPilot 风格列）
    try:
        bind = op.get_bind()
        # kind: 故事线类型（main/subplot/hidden）
        if not _column_exists(bind, "storylines", "kind"):
            op.execute("ALTER TABLE storylines ADD COLUMN kind TEXT DEFAULT 'main'")
        # status: 状态（active/completed/archived）
        if not _column_exists(bind, "storylines", "status"):
            op.execute("ALTER TABLE storylines ADD COLUMN status TEXT DEFAULT 'active'")
        # start_chapter / end_chapter: 起止章节
        if not _column_exists(bind, "storylines", "start_chapter"):
            op.execute("ALTER TABLE storylines ADD COLUMN start_chapter INTEGER")
        if not _column_exists(bind, "storylines", "end_chapter"):
            op.execute("ALTER TABLE storylines ADD COLUMN end_chapter INTEGER")
        # 创建索引（kind 列已确保存在）
        op.execute("CREATE INDEX IF NOT EXISTS idx_storylines_kind ON storylines(kind)")
        op.execute("CREATE INDEX IF NOT EXISTS idx_storylines_status ON storylines(status)")
        logger.info("storylines table extended with kind/status/start_chapter/end_chapter")
    except Exception:
        logger.error("Migration 008 failed: ALTER TABLE storylines", exc_info=True)

    # DAG 节点表
    try:
        op.execute("""
            CREATE TABLE IF NOT EXISTS story_dag_nodes (
                id TEXT PRIMARY KEY,
                novel_id TEXT NOT NULL,
                storyline_id TEXT,
                node_type TEXT NOT NULL,
                title TEXT DEFAULT '',
                description TEXT DEFAULT '',
                chapter_number INTEGER,
                outline TEXT DEFAULT '',
                status TEXT DEFAULT 'pending',
                metadata TEXT DEFAULT '{}',
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (novel_id) REFERENCES novels(id) ON DELETE CASCADE,
                FOREIGN KEY (storyline_id) REFERENCES storylines(id) ON DELETE SET NULL
            )
        """)
        op.execute("CREATE INDEX IF NOT EXISTS idx_dag_nodes_novel ON story_dag_nodes(novel_id)")
        op.execute("CREATE INDEX IF NOT EXISTS idx_dag_nodes_type ON story_dag_nodes(node_type)")
        op.execute("CREATE INDEX IF NOT EXISTS idx_dag_nodes_chapter ON story_dag_nodes(chapter_number)")
        logger.info("story_dag_nodes table created")
    except Exception:
        logger.error("Migration 008 failed: CREATE TABLE story_dag_nodes", exc_info=True)

    # DAG 边表
    try:
        op.execute("""
            CREATE TABLE IF NOT EXISTS story_dag_edges (
                id TEXT PRIMARY KEY,
                novel_id TEXT NOT NULL,
                source_node_id TEXT NOT NULL,
                target_node_id TEXT NOT NULL,
                edge_type TEXT DEFAULT 'causal',
                weight REAL DEFAULT 1.0,
                metadata TEXT DEFAULT '{}',
                created_at TEXT,
                FOREIGN KEY (novel_id) REFERENCES novels(id) ON DELETE CASCADE,
                FOREIGN KEY (source_node_id) REFERENCES story_dag_nodes(id) ON DELETE CASCADE,
                FOREIGN KEY (target_node_id) REFERENCES story_dag_nodes(id) ON DELETE CASCADE
            )
        """)
        op.execute("CREATE INDEX IF NOT EXISTS idx_dag_edges_novel ON story_dag_edges(novel_id)")
        op.execute("CREATE INDEX IF NOT EXISTS idx_dag_edges_source ON story_dag_edges(source_node_id)")
        op.execute("CREATE INDEX IF NOT EXISTS idx_dag_edges_target ON story_dag_edges(target_node_id)")
        logger.info("story_dag_edges table created")
    except Exception:
        logger.error("Migration 008 failed: CREATE TABLE story_dag_edges", exc_info=True)


def downgrade() -> None:
    """回滚：删除 DAG 表与 storylines 扩展列。

    注意：SQLite 不支持 DROP COLUMN（3.35+ 支持但 alembic 兼容性差），
    故 downgrade 只删除新增表，保留 storylines 扩展列（无害）。
    """
    for stmt in [
        "DROP INDEX IF EXISTS idx_dag_edges_target",
        "DROP INDEX IF EXISTS idx_dag_edges_source",
        "DROP INDEX IF EXISTS idx_dag_edges_novel",
        "DROP TABLE IF EXISTS story_dag_edges",
        "DROP INDEX IF EXISTS idx_dag_nodes_chapter",
        "DROP INDEX IF EXISTS idx_dag_nodes_type",
        "DROP INDEX IF EXISTS idx_dag_nodes_novel",
        "DROP TABLE IF EXISTS story_dag_nodes",
        "DROP INDEX IF EXISTS idx_storylines_status",
        "DROP INDEX IF EXISTS idx_storylines_kind",
    ]:
        try:
            op.execute(stmt)
        except Exception as e:
            logger.warning("Migration 008 downgrade skipped: %s", e)
