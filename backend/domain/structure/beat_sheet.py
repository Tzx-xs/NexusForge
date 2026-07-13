from dataclasses import dataclass, field

from ..shared.base import BaseEntity


@dataclass
class Beat(BaseEntity):
    chapter_id: str = ""
    beat_index: int = 0
    scene_type: str = ""
    location: str | None = None
    characters: list = field(default_factory=list)
    goal: str | None = None
    conflict: str | None = None
    turning_point: str | None = None
    emotion_arc: str | None = None
    word_count_estimate: int = 0


@dataclass
class BeatSheet(BaseEntity):
    chapter_id: str = ""
    beats: list = field(default_factory=list)
