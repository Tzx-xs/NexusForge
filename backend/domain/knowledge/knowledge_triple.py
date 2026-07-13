from dataclasses import dataclass

from ..shared.base import BaseEntity


@dataclass
class KnowledgeTriple(BaseEntity):
    novel_id: str = ""
    subject: str = ""
    predicate: str = ""
    object: str = ""
    confidence: float = 1.0
    source_chapter_id: str | None = None
