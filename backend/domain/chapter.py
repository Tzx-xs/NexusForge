from dataclasses import dataclass

from .chapter_status import ChapterStatus
from .shared.base import BaseEntity


@dataclass
class Chapter(BaseEntity):
    novel_id: str = ""
    number: int = 0
    title: str = ""
    outline: str = ""
    content: str = ""
    status: str = ChapterStatus.DRAFT.value
    word_count: int = 0
    tension_score: float = 50.0
