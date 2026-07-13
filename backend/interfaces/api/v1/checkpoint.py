"""Checkpoint API 端点"""
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from application.checkpoint.service import CheckpointService, InMemoryCheckpointRepo

router = APIRouter(prefix="/api/v1/checkpoint", tags=["checkpoint"])

_service = CheckpointService(InMemoryCheckpointRepo())


def _success(data: Any) -> dict:
    return {"code": 0, "message": "success", "data": data}


class CheckpointCreateRequest(BaseModel):
    novel_id: str
    chapter_number: int | None = None
    pipeline_run_id: str | None = None
    step_name: str = ""
    step_status: str = "success"
    context_snapshot: dict = {}
    audit_snapshot: dict = {}


@router.post("")
async def create_checkpoint(req: CheckpointCreateRequest):
    cp = await _service.create_checkpoint(
        novel_id=req.novel_id,
        chapter_number=req.chapter_number,
        pipeline_run_id=req.pipeline_run_id,
        step_name=req.step_name,
        step_status=req.step_status,
        context_snapshot=req.context_snapshot,
        audit_snapshot=req.audit_snapshot,
    )
    return _success(cp.to_dict())


@router.get("/{novel_id}/active")
async def get_active_checkpoint(novel_id: str):
    cp = await _service.get_active_checkpoint(novel_id)
    return _success(cp.to_dict() if cp else None)


@router.delete("/{novel_id}/active")
async def clear_active(novel_id: str):
    await _service.clear_active(novel_id)
    return _success({"cleared": novel_id})


@router.get("/{novel_id}/resume")
async def resume_from(novel_id: str):
    snapshot = await _service.resume_from(novel_id)
    return _success(snapshot)
