from dataclasses import dataclass, field

from ..shared.base import BaseEntity


@dataclass
class ClueLock(BaseEntity):
    novel_id: str = ""
    clue_type: str = ""
    title: str = ""
    description: str = ""
    status: str = "planted"
    planted_chapter: int | None = None
    revealed_chapter: int | None = None
    related_characters: list = field(default_factory=list)
    urgency: str = "normal"
