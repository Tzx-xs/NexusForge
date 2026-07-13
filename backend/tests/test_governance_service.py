"""叙事治理测试

验证：
1. ChapterBudget 预算模型
2. NarrativeDebt 债务模型（open/resolved/closed）
3. GovernanceService 预算分配 + 债务登记 + 债务回收
4. GovernanceGate 写前校验（不通过抛 GovernanceViolation）
"""
import pytest

from application.governance.models import (
    ChapterBudget,
    NarrativeDebt,
    DebtStatus,
    DebtKind,
    RevealLevel,
)
from application.governance.service import GovernanceService, GovernanceViolation


# ─── 模型测试 ───────────────────────────────────────────────────────
class TestModels:
    def test_chapter_budget_defaults(self):
        b = ChapterBudget(novel_id="n1", chapter_number=5)
        assert b.max_new_storylines == 0
        assert b.max_debt_closures == 1
        assert b.allowed_reveal_level == RevealLevel.HINT
        assert b.status == "pending"

    def test_narrative_debt_defaults(self):
        d = NarrativeDebt(id="d1", novel_id="n1", description="古卷符号未解")
        assert d.kind == DebtKind.FORESHADOW
        assert d.status == DebtStatus.OPEN
        assert d.importance == "medium"

    def test_debt_kinds(self):
        assert DebtKind.FORESHADOW.value == "foreshadow"
        assert DebtKind.PROMISE.value == "promise"
        assert DebtKind.SUSPENSE.value == "suspense"

    def test_reveal_levels(self):
        assert RevealLevel.NONE.value == "none"
        assert RevealLevel.HINT.value == "hint"
        assert RevealLevel.PARTIAL.value == "partial"
        assert RevealLevel.FULL.value == "full"


# ─── GovernanceService 测试 ────────────────────────────────────────
class TestGovernanceService:
    @pytest.fixture
    def service(self):
        from application.governance.service import InMemoryGovernanceRepo
        return GovernanceService(InMemoryGovernanceRepo())

    @pytest.mark.asyncio
    async def test_allocate_budget(self, service):
        """分配章节预算"""
        budget = await service.allocate_budget(
            novel_id="n1",
            chapter_number=5,
            max_new_storylines=1,
            max_debt_closures=2,
            allowed_reveal_level=RevealLevel.PARTIAL,
        )
        assert budget.chapter_number == 5
        assert budget.max_new_storylines == 1
        assert budget.status == "pending"

    @pytest.mark.asyncio
    async def test_get_budget(self, service):
        """查询章节预算"""
        await service.allocate_budget(
            novel_id="n1", chapter_number=5, max_new_storylines=2,
        )
        budget = await service.get_budget("n1", 5)
        assert budget is not None
        assert budget.max_new_storylines == 2

    @pytest.mark.asyncio
    async def test_register_debt(self, service):
        """登记叙事债务"""
        debt = await service.register_debt(
            novel_id="n1",
            description="古卷符号含义未解",
            kind=DebtKind.FORESHADOW,
            raised_chapter=3,
            suggested_resolve_chapter=10,
            importance="high",
        )
        assert debt.id is not None
        assert debt.status == DebtStatus.OPEN
        assert debt.raised_chapter == 3

    @pytest.mark.asyncio
    async def test_list_open_debts(self, service):
        """列出未回收债务"""
        await service.register_debt(novel_id="n1", description="d1", raised_chapter=1)
        await service.register_debt(novel_id="n1", description="d2", raised_chapter=2)
        await service.register_debt(novel_id="n2", description="other", raised_chapter=1)

        debts = await service.list_open_debts("n1")
        assert len(debts) == 2

    @pytest.mark.asyncio
    async def test_resolve_debt(self, service):
        """回收债务"""
        debt = await service.register_debt(
            novel_id="n1", description="d1", raised_chapter=1,
        )
        await service.resolve_debt(debt.id, resolve_chapter=5)

        debts = await service.list_open_debts("n1")
        assert len(debts) == 0
        all_debts = await service.list_all_debts("n1")
        assert all_debts[0].status == DebtStatus.RESOLVED
        assert all_debts[0].actual_resolve_chapter == 5


# ─── GovernanceGate 写前校验 ──────────────────────────────────────
class TestGovernanceGate:
    @pytest.fixture
    def service(self):
        from application.governance.service import InMemoryGovernanceRepo
        return GovernanceService(InMemoryGovernanceRepo())

    @pytest.mark.asyncio
    async def test_gate_passes_when_no_budget_set(self, service):
        """无预算时默认通过（向后兼容）"""
        result = await service.check_gate(
            novel_id="n1",
            chapter_number=5,
            new_storylines_count=99,
            debt_closures_count=99,
            reveal_level=RevealLevel.FULL,
        )
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_gate_passes_when_within_budget(self, service):
        """在预算内通过"""
        await service.allocate_budget(
            novel_id="n1",
            chapter_number=5,
            max_new_storylines=2,
            max_debt_closures=1,
            allowed_reveal_level=RevealLevel.PARTIAL,
        )

        result = await service.check_gate(
            novel_id="n1",
            chapter_number=5,
            new_storylines_count=1,
            debt_closures_count=1,
            reveal_level=RevealLevel.HINT,
        )
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_gate_fails_when_new_storylines_exceed(self, service):
        """新增故事线超预算"""
        await service.allocate_budget(
            novel_id="n1", chapter_number=5, max_new_storylines=0,
        )

        result = await service.check_gate(
            novel_id="n1",
            chapter_number=5,
            new_storylines_count=1,
            debt_closures_count=0,
            reveal_level=RevealLevel.NONE,
        )
        assert result.passed is False
        assert any("故事线" in v for v in result.violations)

    @pytest.mark.asyncio
    async def test_gate_fails_when_reveal_level_exceeds(self, service):
        """揭秘等级超预算"""
        await service.allocate_budget(
            novel_id="n1",
            chapter_number=5,
            max_new_storylines=99,
            max_debt_closures=99,
            allowed_reveal_level=RevealLevel.HINT,
        )

        result = await service.check_gate(
            novel_id="n1",
            chapter_number=5,
            new_storylines_count=0,
            debt_closures_count=0,
            reveal_level=RevealLevel.FULL,
        )
        assert result.passed is False
        assert any("揭秘" in v for v in result.violations)

    @pytest.mark.asyncio
    async def test_gate_fails_when_debt_closures_exceed(self, service):
        """债务回收超预算"""
        await service.allocate_budget(
            novel_id="n1",
            chapter_number=5,
            max_new_storylines=99,
            max_debt_closures=0,
            allowed_reveal_level=RevealLevel.FULL,
        )

        result = await service.check_gate(
            novel_id="n1",
            chapter_number=5,
            new_storylines_count=0,
            debt_closures_count=1,
            reveal_level=RevealLevel.NONE,
        )
        assert result.passed is False
        assert any("债务" in v for v in result.violations)


# ─── 章节预算完成 ──────────────────────────────────────────────────
class TestBudgetCompletion:
    @pytest.fixture
    def service(self):
        from application.governance.service import InMemoryGovernanceRepo
        return GovernanceService(InMemoryGovernanceRepo())

    @pytest.mark.asyncio
    async def test_mark_budget_completed(self, service):
        """标记预算完成"""
        await service.allocate_budget(novel_id="n1", chapter_number=5)
        await service.mark_budget_completed("n1", 5)

        budget = await service.get_budget("n1", 5)
        assert budget.status == "completed"
