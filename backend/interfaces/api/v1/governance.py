"""Governance API 端点"""
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from application.governance.models import DebtKind, RevealLevel
from application.governance.service import GovernanceService, InMemoryGovernanceRepo

router = APIRouter(prefix="/api/v1/governance", tags=["governance"])

_service = GovernanceService(InMemoryGovernanceRepo())


def _success(data: Any) -> dict:
    return {"code": 0, "message": "success", "data": data}


class BudgetCreateRequest(BaseModel):
    novel_id: str
    chapter_number: int
    max_new_storylines: int = 0
    max_debt_closures: int = 1
    allowed_reveal_level: str = "hint"
    must_serve_promise_tags: list[str] = []


class DebtCreateRequest(BaseModel):
    novel_id: str
    description: str
    kind: str = "foreshadow"
    raised_chapter: int | None = None
    suggested_resolve_chapter: int | None = None
    importance: str = "medium"


class DebtResolveRequest(BaseModel):
    resolve_chapter: int


class GateCheckRequest(BaseModel):
    novel_id: str
    chapter_number: int
    new_storylines_count: int = 0
    debt_closures_count: int = 0
    reveal_level: str = "none"


@router.post("/budgets")
async def allocate_budget(req: BudgetCreateRequest):
    budget = await _service.allocate_budget(
        novel_id=req.novel_id,
        chapter_number=req.chapter_number,
        max_new_storylines=req.max_new_storylines,
        max_debt_closures=req.max_debt_closures,
        allowed_reveal_level=RevealLevel(req.allowed_reveal_level),
        must_serve_promise_tags=req.must_serve_promise_tags,
    )
    return _success(budget.to_dict())


@router.get("/budgets/{novel_id}/{chapter_number}")
async def get_budget(novel_id: str, chapter_number: int):
    budget = await _service.get_budget(novel_id, chapter_number)
    return _success(budget.to_dict() if budget else None)


@router.post("/debts")
async def register_debt(req: DebtCreateRequest):
    debt = await _service.register_debt(
        novel_id=req.novel_id,
        description=req.description,
        kind=DebtKind(req.kind),
        raised_chapter=req.raised_chapter,
        suggested_resolve_chapter=req.suggested_resolve_chapter,
        importance=req.importance,
    )
    return _success(debt.to_dict())


@router.get("/debts/{novel_id}/open")
async def list_open_debts(novel_id: str):
    debts = await _service.list_open_debts(novel_id)
    return _success([d.to_dict() for d in debts])


@router.get("/debts/{novel_id}/all")
async def list_all_debts(novel_id: str):
    debts = await _service.list_all_debts(novel_id)
    return _success([d.to_dict() for d in debts])


@router.post("/debts/{debt_id}/resolve")
async def resolve_debt(debt_id: str, req: DebtResolveRequest):
    await _service.resolve_debt(debt_id, req.resolve_chapter)
    return _success({"resolved": debt_id})


@router.post("/gate/check")
async def check_gate(req: GateCheckRequest):
    result = await _service.check_gate(
        novel_id=req.novel_id,
        chapter_number=req.chapter_number,
        new_storylines_count=req.new_storylines_count,
        debt_closures_count=req.debt_closures_count,
        reveal_level=RevealLevel(req.reveal_level),
    )
    return _success(result.to_dict())
