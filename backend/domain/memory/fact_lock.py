from dataclasses import dataclass

from ..shared.base import BaseEntity


@dataclass
class FactLock(BaseEntity):
    novel_id: str = ""
    fact_type: str = ""
    key: str = ""
    value: str = ""
    locked_at_chapter: int | None = None
    is_immutable: bool = False
    source: str = "extracted"
