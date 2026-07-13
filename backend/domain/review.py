from dataclasses import dataclass, field
from datetime import datetime

from .shared.base import BaseEntity


@dataclass
class ReviewResult:
    id: str = field(default_factory=lambda: BaseEntity.generate_id())
    chapter_id: str = ""
    total_score: float = 0.0
    grade: str = ""
    red_line_violations: list = field(default_factory=list)
    dimension_scores: dict = field(default_factory=dict)
    review_details: str = ""
    created_at: datetime = field(default_factory=lambda: BaseEntity.now())
