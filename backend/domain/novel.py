from dataclasses import dataclass, field

from .shared.base import BaseEntity


@dataclass
class Novel(BaseEntity):
    title: str = ""
    premise: str = ""
    genre: str = ""
    target_chapters: int = 0
    current_chapter: int = 0
    cover_url: str = ""
    style_tags: list = field(default_factory=list)
    perspective: str = ""
