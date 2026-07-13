"""叙事治理数据模型

借鉴 PlotPilot application/governance/models.py，简化为：
- ChapterBudget: 章节叙事预算
- NarrativeDebt: 叙事债务
- GovernanceReport: 治理报告（占位，后续扩展）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class DebtKind(StrEnum):
    """债务类型"""
    FORESHADOW = "foreshadow"  # 伏笔
    PROMISE = "promise"        # 承诺
    SUSPENSE = "suspense"      # 悬念


class DebtStatus(StrEnum):
    """债务状态"""
    OPEN = "open"          # 未回收
    RESOLVED = "resolved"  # 已回收
    CLOSED = "closed"      # 已关闭（放弃回收）


class RevealLevel(StrEnum):
    """揭秘等级（递增）"""
    NONE = "none"        # 不揭秘
    HINT = "hint"        # 暗示
    PARTIAL = "partial"  # 部分揭秘
    FULL = "full"        # 完全揭秘


# 揭秘等级排序（用于 gate 比较）
_REVEAL_ORDER = {
    RevealLevel.NONE: 0,
    RevealLevel.HINT: 1,
    RevealLevel.PARTIAL: 2,
    RevealLevel.FULL: 3,
}


def reveal_level_value(level: RevealLevel) -> int:
    """获取揭秘等级的数值（越大揭秘越多）"""
    return _REVEAL_ORDER.get(level, 0)


@dataclass
class ChapterBudget:
    """章节叙事预算

    写前分配，约束本章不能：
    - 新增超过 max_new_storylines 条故事线
    - 回收超过 max_debt_closures 条叙事债务
    - 揭秘等级超过 allowed_reveal_level
    """
    novel_id: str
    chapter_number: int
    max_new_storylines: int = 0
    max_debt_closures: int = 1
    allowed_reveal_level: RevealLevel = RevealLevel.HINT
    must_serve_promise_tags: list[str] = field(default_factory=list)
    carry_over_debt_ids: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    status: str = "pending"  # pending / completed
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "novel_id": self.novel_id,
            "chapter_number": self.chapter_number,
            "max_new_storylines": self.max_new_storylines,
            "max_debt_closures": self.max_debt_closures,
            "allowed_reveal_level": self.allowed_reveal_level.value,
            "must_serve_promise_tags": self.must_serve_promise_tags,
            "carry_over_debt_ids": self.carry_over_debt_ids,
            "notes": self.notes,
            "status": self.status,
        }


@dataclass
class NarrativeDebt:
    """叙事债务

    伏笔/承诺/悬念的待回收项。
    raised_chapter: 提出章节
    suggested_resolve_chapter: 建议回收章节
    actual_resolve_chapter: 实际回收章节
    """
    id: str
    novel_id: str
    kind: DebtKind = DebtKind.FORESHADOW
    description: str = ""
    raised_chapter: int | None = None
    suggested_resolve_chapter: int | None = None
    actual_resolve_chapter: int | None = None
    importance: str = "medium"  # low / medium / high / critical
    status: DebtStatus = DebtStatus.OPEN
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "novel_id": self.novel_id,
            "kind": self.kind.value,
            "description": self.description,
            "raised_chapter": self.raised_chapter,
            "suggested_resolve_chapter": self.suggested_resolve_chapter,
            "actual_resolve_chapter": self.actual_resolve_chapter,
            "importance": self.importance,
            "status": self.status.value,
            "metadata": self.metadata,
        }


@dataclass
class GateResult:
    """写前校验结果"""
    passed: bool
    violations: list[str] = field(default_factory=list)
    budget: ChapterBudget | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "violations": self.violations,
            "budget": self.budget.to_dict() if self.budget else None,
        }
