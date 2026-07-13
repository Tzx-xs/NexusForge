from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from application.engine.autonomous_writer import AutonomousWritingEngine, AutoWriteConfig
from interfaces.dependencies import get_autonomous_writer
from interfaces.utils.response import success_response

router = APIRouter(prefix="/api/v1", tags=["autonomous"])


class CreateSessionRequest(BaseModel):
    model_config = {"extra": "forbid"}

    novel_id: str
    target_chapters: int = 1
    min_quality_score: float = 60.0
    max_retries_per_chapter: int = 2
    pause_between_chapters: bool = False
    auto_rewrite_on_fail: bool = True
    mode: str = "single"
    enabled_guards: list[str] | None = None


@router.post("/autonomous/sessions")
async def create_session(
    request: CreateSessionRequest,
    engine: AutonomousWritingEngine = Depends(get_autonomous_writer),
):
    config = AutoWriteConfig.from_dict(request.model_dump())
    session = engine.create_session(request.novel_id, config)
    return success_response(session.to_dict())


@router.get("/autonomous/sessions")
def list_sessions(
    novel_id: str | None = None,
    engine: AutonomousWritingEngine = Depends(get_autonomous_writer),
):
    sessions = engine.list_sessions(novel_id)
    return success_response([s.to_dict() for s in sessions])


@router.get("/autonomous/sessions/{session_id}")
def get_session(
    session_id: str,
    engine: AutonomousWritingEngine = Depends(get_autonomous_writer),
):
    session = engine.get_status(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return success_response(session.to_dict())


@router.post("/autonomous/sessions/{session_id}/start")
async def start_session(
    session_id: str,
    engine: AutonomousWritingEngine = Depends(get_autonomous_writer),
):
    success = await engine.start(session_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot start session")
    session = engine.get_status(session_id)
    return success_response(session.to_dict() if session else None)


@router.post("/autonomous/sessions/{session_id}/pause")
async def pause_session(
    session_id: str,
    engine: AutonomousWritingEngine = Depends(get_autonomous_writer),
):
    success = await engine.pause(session_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot pause session")
    session = engine.get_status(session_id)
    return success_response(session.to_dict() if session else None)


@router.post("/autonomous/sessions/{session_id}/resume")
async def resume_session(
    session_id: str,
    engine: AutonomousWritingEngine = Depends(get_autonomous_writer),
):
    success = await engine.resume(session_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot resume session")
    session = engine.get_status(session_id)
    return success_response(session.to_dict() if session else None)


@router.post("/autonomous/sessions/{session_id}/cancel")
async def cancel_session(
    session_id: str,
    engine: AutonomousWritingEngine = Depends(get_autonomous_writer),
):
    success = await engine.cancel(session_id)
    if not success:
        raise HTTPException(status_code=400, detail="Cannot cancel session")
    return success_response({"cancelled": True})
