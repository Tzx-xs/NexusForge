from dataclasses import dataclass, field
from typing import Any

from ..shared.base import BaseEntity


@dataclass
class Storyline(BaseEntity):
    """故事线 - DAG 的顶层结构"""

    novel_id: str = ""
    name: str = ""
    description: str = ""
    color: str = "#2080f0"
    node_count: int = 0
    is_active: bool = True
    order: int = 0


@dataclass
class StorylineNode(BaseEntity):
    """故事线节点 - DAG 节点"""

    novel_id: str = ""
    storyline_id: str = ""
    title: str = ""
    description: str = ""
    node_type: str = "scene"
    status: str = "draft"
    chapter_index: int | None = None
    chapter_id: str | None = None

    x: float = 0
    y: float = 0
    width: float = 180
    height: float = 80

    parent_ids: list[str] = field(default_factory=list)
    child_ids: list[str] = field(default_factory=list)

    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
