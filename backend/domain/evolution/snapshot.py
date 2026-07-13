from dataclasses import dataclass

from ..shared.base import BaseEntity


@dataclass
class Snapshot(BaseEntity):
    novel_id: str = ""
    chapter_id: str = ""
    snapshot_type: str = ""
    name: str = ""
    description: str | None = None
    content_hash: str | None = None
    diff_data: dict | None = None
    parent_snapshot_id: str | None = None
    created_by: str = "system"
    content: str = ""  # 快照时的完整章节内容（>10KB 时 gzip 压缩后 base64 存储）
