from dataclasses import dataclass, field

from .shared.base import BaseEntity


@dataclass
class Foreshadow(BaseEntity):
    novel_id: str = ""
    title: str = ""
    description: str = ""
    priority: str = "P2"
    status: str = "planted"
    planted_chapter_id: str | None = None
    planted_chapter_index: int | None = None
    resolved_chapter_id: str | None = None
    resolved_chapter_index: int | None = None
    related_characters: list = field(default_factory=list)
    related_locations: list = field(default_factory=list)
    urgency: str = "normal"
    tags: list = field(default_factory=list)
    notes: str | None = None
