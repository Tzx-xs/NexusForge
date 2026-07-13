import gzip
import json
import logging
from base64 import b64decode, b64encode

from domain.evolution.snapshot import Snapshot
from domain.shared.base import BaseEntity

from .database import Database

logger = logging.getLogger(__name__)

# BLOCK-09: 快照内容压缩阈值（字节数）
CONTENT_COMPRESS_THRESHOLD = 10 * 1024  # 10KB


class SnapshotRepository:
    """快照仓储 - 章节级增量快照，支持内容版本管理"""

    def __init__(self, db: Database):
        self.db = db

    def create(self, snapshot: Snapshot) -> Snapshot:
        """创建快照，content > 10KB 时自动 gzip 压缩后 base64 编码存储。"""
        content = snapshot.content or ""
        if len(content.encode("utf-8")) > CONTENT_COMPRESS_THRESHOLD:
            content = "GZIP:" + b64encode(gzip.compress(content.encode("utf-8"))).decode("ascii")

        self.db.execute(
            """
            INSERT INTO snapshots (id, novel_id, chapter_id, snapshot_type, name,
                description, content_hash, diff_data, parent_snapshot_id, created_by,
                content, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot.id,
                snapshot.novel_id,
                snapshot.chapter_id,
                snapshot.snapshot_type,
                snapshot.name,
                snapshot.description,
                snapshot.content_hash,
                snapshot.diff_data and json.dumps(snapshot.diff_data, ensure_ascii=False),
                snapshot.parent_snapshot_id,
                snapshot.created_by,
                content,
                snapshot.created_at,
                snapshot.updated_at,
            ),
        )
        return snapshot

    def get(self, snapshot_id: str) -> Snapshot | None:
        row = self.db.query_one(
            "SELECT * FROM snapshots WHERE id = ?",
            (snapshot_id,),
        )
        if not row:
            return None
        return self._row_to_snapshot(row)

    def list_by_novel(self, novel_id: str, limit: int = 50, chapter_id: str | None = None) -> list:
        if chapter_id:
            rows = self.db.query(
                "SELECT * FROM snapshots WHERE novel_id = ? AND chapter_id = ? ORDER BY created_at DESC LIMIT ?",
                (novel_id, chapter_id, limit),
            )
        else:
            rows = self.db.query(
                "SELECT * FROM snapshots WHERE novel_id = ? ORDER BY created_at DESC LIMIT ?",
                (novel_id, limit),
            )
        return [self._row_to_snapshot(r) for r in rows]

    def list_by_chapter(self, chapter_id: str, limit: int = 50) -> list:
        """按章节ID列出快照，按时间倒序。"""
        rows = self.db.query(
            "SELECT * FROM snapshots WHERE chapter_id = ? ORDER BY created_at DESC LIMIT ?",
            (chapter_id, limit),
        )
        return [self._row_to_snapshot(r) for r in rows]

    def get_latest_by_chapter(self, chapter_id: str) -> Snapshot | None:
        """获取某章节的最新快照。"""
        row = self.db.query_one(
            "SELECT * FROM snapshots WHERE chapter_id = ? ORDER BY created_at DESC LIMIT 1",
            (chapter_id,),
        )
        if not row:
            return None
        return self._row_to_snapshot(row)

    def get_content(self, snapshot_id: str) -> str | None:
        """获取快照的完整内容（自动解压 gzip）。"""
        row = self.db.query_one(
            "SELECT content FROM snapshots WHERE id = ?",
            (snapshot_id,),
        )
        if not row:
            return None
        content = row.get("content", "")
        return self._decompress_content(content)

    def delete(self, snapshot_id: str) -> bool:
        self.db.execute("DELETE FROM snapshots WHERE id = ?", (snapshot_id,))
        return True

    def _row_to_snapshot(self, row: dict) -> Snapshot:
        diff_data = json.loads(row["diff_data"]) if row.get("diff_data") else None
        content_raw = row.get("content", "")
        # 返回时不包含完整 content，减少内存占用
        # 需要完整内容时使用 get_content()
        return Snapshot(
            id=row["id"],
            novel_id=row["novel_id"],
            chapter_id=row["chapter_id"],
            snapshot_type=row["snapshot_type"],
            name=row["name"],
            description=row.get("description"),
            content_hash=row.get("content_hash"),
            diff_data=diff_data,
            parent_snapshot_id=row.get("parent_snapshot_id"),
            created_by=row.get("created_by", "system"),
            created_at=row.get("created_at") or BaseEntity.now(),
            updated_at=row.get("updated_at") or BaseEntity.now(),
            content="" if content_raw and len(content_raw) > 200 else content_raw,
        )

    @staticmethod
    def _decompress_content(stored: str) -> str:
        """解压以 'GZIP:' 前缀标记的压缩内容。"""
        if stored.startswith("GZIP:"):
            try:
                compressed = b64decode(stored[5:])
                return gzip.decompress(compressed).decode("utf-8")
            except Exception as e:
                logger.warning("快照内容解压失败: %s", e)
                return stored
        return stored
