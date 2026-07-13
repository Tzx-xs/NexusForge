from dataclasses import dataclass, field

from ..shared.base import BaseEntity


@dataclass
class StoryNode(BaseEntity):
    novel_id: str = ""
    node_type: str = ""
    title: str = ""
    position: int = 0
    parent_id: str | None = None
    children_ids: list = field(default_factory=list)
    description: str | None = None
