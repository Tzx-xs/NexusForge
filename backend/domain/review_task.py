from dataclasses import dataclass, field

from domain.shared.base import BaseEntity


@dataclass
class ReviewTask(BaseEntity):
    title: str = ""
    novel_id: str | None = None
    status: str = "pending"
    result: str = ""
