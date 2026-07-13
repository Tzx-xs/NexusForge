from dataclasses import dataclass, field

from ..shared.base import BaseEntity


@dataclass
class ChapterSummary(BaseEntity):
    novel_id: str = ""
    chapter_id: str = ""
    chapter_index: int = 0
    summary: str = ""
    key_events: list = field(default_factory=list)
    characters_involved: list = field(default_factory=list)
    locations: list = field(default_factory=list)
    timeline_position: str | None = None
