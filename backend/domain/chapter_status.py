"""Sprint 1.2 GREEN：章节状态枚举。

集中定义章节状态字段的所有合法取值，删除散落在 6 个文件中的字符串字面量。
关键决策：
- 删除 "generated" 死状态（被立刻覆盖为 completed，永不持久化）
- 保留 "planned" 而非 "outlined"（已是当前实际行为，更通用）
- 兼容现有 SQLite TEXT 字段（enum 值即字符串）
"""
from __future__ import annotations

from enum import Enum


class InvalidStatusTransitionError(ValueError):
    """非法状态流转时抛出。"""


class ChapterStatus(Enum):
    """章节状态枚举。

    状态流转图：
        draft (创建)
          ↓ generate_outline
        planned (已生成章纲)
          ↓ generate_content_stream / generate_chapter
        completed (已完成正文)

    历史存在的 "generated" 中间态已被删除：它在 StoryPipeline 中被
    SaveChapterStep 设置后立刻被 FinalizeStep 覆盖为 "completed"，
    在 GenerationPipeline 中被 ChapterService 覆盖，永不持久化。
    """

    DRAFT = "draft"
    PLANNED = "planned"
    COMPLETED = "completed"

    @classmethod
    def is_valid(cls, value: str | None) -> bool:
        """判断字符串是否为合法状态值。"""
        if not value:
            return False
        return any(value == member.value for member in cls)

    @classmethod
    def from_string(cls, value: str) -> ChapterStatus:
        """从字符串构造枚举，未知值抛 ValueError。"""
        if not isinstance(value, str):
            raise ValueError(f"status must be str, got {type(value).__name__}")
        for member in cls:
            if member.value == value:
                return member
        raise ValueError(f"unknown chapter status: {value!r}")

    @classmethod
    def transition(cls, current: str, target: str) -> None:
        """校验状态流转合法性。

        合法流转：
          draft -> planned
          draft -> completed  (允许跳过 planned)
          planned -> completed

        非法流转（抛 InvalidStatusTransitionError）：
          completed -> *  (终态不可回退)
          planned -> draft  (不可回退)
          * -> generated   (死状态)
          * -> unknown
        """
        if not cls.is_valid(current):
            raise InvalidStatusTransitionError(
                f"invalid current status: {current!r}"
            )
        if not cls.is_valid(target):
            raise InvalidStatusTransitionError(
                f"invalid target status: {target!r}"
            )

        cur = cls.from_string(current)
        tgt = cls.from_string(target)

        legal_transitions = {
            (cls.DRAFT, cls.PLANNED),
            (cls.DRAFT, cls.COMPLETED),
            (cls.PLANNED, cls.COMPLETED),
            # 同状态无变化也合法（幂等）
            (cls.DRAFT, cls.DRAFT),
            (cls.PLANNED, cls.PLANNED),
            (cls.COMPLETED, cls.COMPLETED),
        }

        if (cur, tgt) not in legal_transitions:
            raise InvalidStatusTransitionError(
                f"illegal transition: {current!r} -> {target!r}"
            )
