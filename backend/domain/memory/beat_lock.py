from dataclasses import dataclass, field

from ..shared.base import BaseEntity


@dataclass
class BeatLock(BaseEntity):
    novel_id: str = ""
    chapter_id: str = ""
    chapter_index: int = 0
    beat_type: str = ""
    description: str = ""
    significance: str = "major"
    characters: list = field(default_factory=list)
