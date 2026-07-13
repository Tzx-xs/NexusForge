"""叙事治理服务

借鉴 PlotPilot application/governance/service.py，简化为：
- 预算分配（allocate_budget）
- 债务登记/回收（register_debt / resolve_debt）
- 写前校验（check_gate）：不通过返回 violations

不依赖 narrative_promise / storyline_registry，保持轻量。
"""
from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from typing import Any

from .models import (
    ChapterBudget,
    DebtKind,
    DebtStatus,
    GateResult,
    NarrativeDebt,
    RevealLevel,
    reveal_level_value,
)

logger = logging.getLogger(__name__)


class GovernanceViolation(Exception):
    """治理校验未通过（严格模式时抛出）"""


class GovernanceRepo(ABC):
    """治理仓储接口"""

    @abstractmethod
    async def upsert_budget(self, budget: ChapterBudget) -> None: ...

    @abstractmethod
    async def get_budget(self, novel_id: str, chapter_number: int) -> ChapterBudget | None: ...

    @abstractmethod
    async def insert_debt(self, debt: NarrativeDebt) -> None: ...

    @abstractmethod
    async def update_debt(self, debt: NarrativeDebt) -> None: ...

    @abstractmethod
    async def get_debt(self, debt_id: str) -> NarrativeDebt | None: ...

    @abstractmethod
    async def list_open_debts(self, novel_id: str) -> list[NarrativeDebt]: ...

    @abstractmethod
    async def list_all_debts(self, novel_id: str) -> list[NarrativeDebt]: ...


class InMemoryGovernanceRepo(GovernanceRepo):
    """内存仓储（测试用 + 开发期默认）"""

    def __init__(self):
        self._budgets: dict[tuple[str, int], ChapterBudget] = {}
        self._debts: dict[str, NarrativeDebt] = {}

    async def upsert_budget(self, budget: ChapterBudget) -> None:
        self._budgets[(budget.novel_id, budget.chapter_number)] = budget

    async def get_budget(self, novel_id: str, chapter_number: int) -> ChapterBudget | None:
        return self._budgets.get((novel_id, chapter_number))

    async def insert_debt(self, debt: NarrativeDebt) -> None:
        self._debts[debt.id] = debt

    async def update_debt(self, debt: NarrativeDebt) -> None:
        self._debts[debt.id] = debt

    async def get_debt(self, debt_id: str) -> NarrativeDebt | None:
        return self._debts.get(debt_id)

    async def list_open_debts(self, novel_id: str) -> list[NarrativeDebt]:
        return [d for d in self._debts.values() if d.novel_id == novel_id and d.status == DebtStatus.OPEN]

    async def list_all_debts(self, novel_id: str) -> list[NarrativeDebt]:
        return [d for d in self._debts.values() if d.novel_id == novel_id]


class GovernanceService:
    """叙事治理应用服务"""

    def __init__(self, repo: GovernanceRepo):
        self.repo = repo

    # ─── 预算 ───
    async def allocate_budget(
        self,
        novel_id: str,
        chapter_number: int,
        max_new_storylines: int = 0,
        max_debt_closures: int = 1,
        allowed_reveal_level: RevealLevel = RevealLevel.HINT,
        must_serve_promise_tags: list[str] | None = None,
        carry_over_debt_ids: list[str] | None = None,
    ) -> ChapterBudget:
        budget = ChapterBudget(
            novel_id=novel_id,
            chapter_number=chapter_number,
            max_new_storylines=max_new_storylines,
            max_debt_closures=max_debt_closures,
            allowed_reveal_level=allowed_reveal_level,
            must_serve_promise_tags=must_serve_promise_tags or [],
            carry_over_debt_ids=carry_over_debt_ids or [],
        )
        await self.repo.upsert_budget(budget)
        logger.info("预算分配: novel=%s chapter=%d", novel_id, chapter_number)
        return budget

    async def get_budget(self, novel_id: str, chapter_number: int) -> ChapterBudget | None:
        return await self.repo.get_budget(novel_id, chapter_number)

    async def mark_budget_completed(self, novel_id: str, chapter_number: int) -> None:
        budget = await self.repo.get_budget(novel_id, chapter_number)
        if budget:
            budget.status = "completed"
            await self.repo.upsert_budget(budget)

    # ─── 债务 ───
    async def register_debt(
        self,
        novel_id: str,
        description: str,
        kind: DebtKind = DebtKind.FORESHADOW,
        raised_chapter: int | None = None,
        suggested_resolve_chapter: int | None = None,
        importance: str = "medium",
    ) -> NarrativeDebt:
        debt = NarrativeDebt(
            id=str(uuid.uuid4()),
            novel_id=novel_id,
            kind=kind,
            description=description,
            raised_chapter=raised_chapter,
            suggested_resolve_chapter=suggested_resolve_chapter,
            importance=importance,
        )
        await self.repo.insert_debt(debt)
        logger.info("债务登记: novel=%s kind=%s", novel_id, kind.value)
        return debt

    async def resolve_debt(self, debt_id: str, resolve_chapter: int) -> None:
        debt = await self.repo.get_debt(debt_id)
        if debt is None:
            logger.warning("债务未找到: %s", debt_id)
            return
        debt.status = DebtStatus.RESOLVED
        debt.actual_resolve_chapter = resolve_chapter
        await self.repo.update_debt(debt)

    async def list_open_debts(self, novel_id: str) -> list[NarrativeDebt]:
        return await self.repo.list_open_debts(novel_id)

    async def list_all_debts(self, novel_id: str) -> list[NarrativeDebt]:
        return await self.repo.list_all_debts(novel_id)

    # ─── 写前校验（Gate）───
    async def check_gate(
        self,
        novel_id: str,
        chapter_number: int,
        new_storylines_count: int = 0,
        debt_closures_count: int = 0,
        reveal_level: RevealLevel = RevealLevel.NONE,
    ) -> GateResult:
        """写前校验：不通过返回 violations

        无预算时默认通过（向后兼容）。
        """
        budget = await self.repo.get_budget(novel_id, chapter_number)
        if budget is None:
            return GateResult(passed=True)

        violations: list[str] = []

        if new_storylines_count > budget.max_new_storylines:
            violations.append(
                f"新增故事线数 {new_storylines_count} 超过预算 {budget.max_new_storylines}"
            )

        if debt_closures_count > budget.max_debt_closures:
            violations.append(
                f"债务回收数 {debt_closures_count} 超过预算 {budget.max_debt_closures}"
            )

        if reveal_level_value(reveal_level) > reveal_level_value(budget.allowed_reveal_level):
            violations.append(
                f"揭秘等级 {reveal_level.value} 超过预算 {budget.allowed_reveal_level.value}"
            )

        return GateResult(
            passed=len(violations) == 0,
            violations=violations,
            budget=budget,
        )
