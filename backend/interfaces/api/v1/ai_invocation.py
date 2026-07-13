"""AI Invocation API 端点"""
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from application.ai_invocation.models import InvocationStatus
from application.ai_invocation.service import InMemoryInvocationRepo, InvocationService

router = APIRouter(prefix="/api/v1/ai-invocations", tags=["ai-invocations"])

_service = InvocationService(InMemoryInvocationRepo())


def _success(data: Any) -> dict:
    return {"code": 0, "message": "success", "data": data}


class InvocationRecordRequest(BaseModel):
    stage: str
    operation: str
    prompt_key: str
    novel_id: str | None = None
    chapter_number: int | None = None
    session_id: str | None = None
    model: str = ""
    provider: str = ""
    tokens_input: int = 0
    tokens_output: int = 0
    duration_ms: int = 0
    status: str = "success"
    error: str = ""


@router.post("")
async def record_invocation(req: InvocationRecordRequest):
    record = await _service.record(
        stage=req.stage,
        operation=req.operation,
        prompt_key=req.prompt_key,
        novel_id=req.novel_id,
        chapter_number=req.chapter_number,
        session_id=req.session_id,
        model=req.model,
        provider=req.provider,
        tokens_input=req.tokens_input,
        tokens_output=req.tokens_output,
        duration_ms=req.duration_ms,
        status=InvocationStatus(req.status),
        error=req.error,
    )
    return _success(record.to_dict())


@router.get("/novel/{novel_id}")
async def list_by_novel(novel_id: str):
    records = await _service.list_by_novel(novel_id)
    return _success([r.to_dict() for r in records])


@router.get("/session/{session_id}")
async def list_by_session(session_id: str):
    records = await _service.list_by_session(session_id)
    return _success([r.to_dict() for r in records])


@router.get("/novel/{novel_id}/stats")
async def stats_by_novel(novel_id: str):
    stats = await _service.stats_by_novel(novel_id)
    return _success(stats)
