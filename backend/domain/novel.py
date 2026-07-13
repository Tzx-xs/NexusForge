from dataclasses import dataclass, field

from .shared.base import BaseEntity


# 小说阶段常量（对齐 PlotPilot 前端 stage 字段）
STAGE_PREPARING = "preparing"
STAGE_OUTLINING = "outlining"
STAGE_WRITING = "writing"
STAGE_REVISING = "revising"
STAGE_COMPLETED = "completed"

VALID_STAGES: frozenset[str] = frozenset({
    STAGE_PREPARING, STAGE_OUTLINING, STAGE_WRITING, STAGE_REVISING, STAGE_COMPLETED,
})


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
    # NexusForge Phase 3.5：对齐 PlotPilot 前端 NovelDTO 字段
    author: str = ""
    stage: str = STAGE_PREPARING
    auto_approve_mode: bool = False
    target_words_per_chapter: int = 2500
    generation_prefs: dict = field(default_factory=dict)
    world_preset: str = ""
    story_structure: str = ""
    pacing_control: str = ""
    writing_style: str = ""
    special_requirements: str = ""
