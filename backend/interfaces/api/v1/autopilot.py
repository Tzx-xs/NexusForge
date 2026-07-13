"""Autopilot 适配层 — 对齐 PlotPilot 前端 per-novel 风格端点。

PlotPilot 前端期望：
- GET    /api/v1/autopilot/{novelId}/status
- POST   /api/v1/autopilot/{novelId}/start
- POST   /api/v1/autopilot/{novelId}/stop
- POST   /api/v1/autopilot/{novelId}/resume
- GET    /api/v1/autopilot/{novelId}/stream          (SSE)
- GET    /api/v1/autopilot/{novelId}/log-stream      (SSE)
- GET    /api/v1/autopilot/{novelId}/circuit-breaker
- POST   /api/v1/autopilot/{novelId}/circuit-breaker/reset

NexusForge 后端 AutonomousWritingEngine 是 per-session 范式：
- 需先 create_session 拿 session_id，再 start/pause/resume/cancel session_id。

适配策略：
- 每个 novel 维持一个 active session（最新非失败的那个）
- 前端 start → 后端 create_session + start
- 前端 stop → 后端 cancel active session
- 前端 status → 后端查 active session 状态，找不到返回 stopped 占位
- circuit-breaker 占位返回 closed（与 PlotPilot 前端 AutopilotCircuitBreakerData 对齐）
- stream/log-stream 暂返回 200 空流（PlotPilot 的 SSE 实际由 chapterStream + dag/events 替代）
"""
import asyncio
import json
import time
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from application.engine.autonomous_writer import (
    AutoWriteConfig,
    AutoWriteState,
    AutonomousWritingEngine,
)
from interfaces.dependencies import get_autonomous_writer
from interfaces.utils.response import success_response

router = APIRouter(prefix="/api/v1/autopilot", tags=["autopilot"])


# ─── 请求模型 ───────────────────────────────────────────────────────────────

class AutopilotStartRequest(BaseModel):
    """对齐 PlotPilot 前端 autopilotApi.start 入参。"""
    model_config = {"extra": "ignore"}

    max_auto_chapters: int = 1
    target_chapters: int = 1
    target_words_per_chapter: int = 3000
    mode: str = "single"
    min_quality_score: float = 60.0
    max_retries_per_chapter: int = 2
    pause_between_chapters: bool = False
    auto_rewrite_on_fail: bool = True


# ─── 辅助函数 ───────────────────────────────────────────────────────────────

# 内存级 novel_id → session_id 映射（进程内有效；与 engine._sessions 同生命周期）
_novel_active_session: dict[str, str] = {}


def _find_active_session_id(engine: AutonomousWritingEngine, novel_id: str) -> str | None:
    """查找 novel 的 active session_id。

    优先内存映射；其次查 engine.list_sessions 找最新非 failed/completed 的。
    """
    sid = _novel_active_session.get(novel_id)
    if sid and engine.get_status(sid):
        return sid
    # 兜底：list_sessions 查 novel 的最新会话
    sessions = engine.list_sessions(novel_id)
    if not sessions:
        return None
    # 取 updated_at 最大的、且非 failed/completed 的
    candidates = [
        s for s in sessions
        if s.state not in (AutoWriteState.FAILED, AutoWriteState.COMPLETED)
    ]
    if not candidates:
        candidates = sessions
    latest = max(candidates, key=lambda s: s.updated_at or 0)
    _novel_active_session[novel_id] = latest.session_id
    return latest.session_id


def _status_to_payload(status: Any | None, novel_id: str) -> dict:
    """将 AutoWriteStatus 转为 PlotPilot 前端 AutopilotStatus 期望格式。"""
    if status is None:
        return {
            "novel_id": novel_id,
            "autopilot_status": "stopped",
            "status": "stopped",
            "state": "idle",
            "current_stage": "idle",
            "active_pipeline_step": None,
            "active_pipeline_run_id": None,
            "last_stable_stage": None,
            "autopilot_run_epoch": 0,
            "autopilot_recovery_reason": None,
            "current_chapter_index": 0,
            "total_chapters_completed": 0,
            "total_words_generated": 0,
            "current_progress": 0.0,
            "started_at": None,
            "updated_at": None,
            "error": None,
            "mode": "single",
            "target_chapters": 0,
            "failed_chapters": [],
        }
    # PlotPilot 前端 autopilotStatus.ts: status.autopilot_status ?? status.status ?? 'stopped'
    # state 映射：engine 的 state 转 PlotPilot 习惯字符串
    state_str = str(status.state) if status.state else "idle"
    # PlotPilot 用 "running"/"paused"/"stopped"/"completed"/"failed" 五态
    ap_status_map = {
        AutoWriteState.IDLE: "stopped",
        AutoWriteState.PLANNING: "running",
        AutoWriteState.GENERATING: "running",
        AutoWriteState.AUDITING: "running",
        AutoWriteState.REWRITING: "running",
        AutoWriteState.AFTERMATH: "running",
        AutoWriteState.PAUSED: "paused",
        AutoWriteState.COMPLETED: "completed",
        AutoWriteState.FAILED: "failed",
    }
    ap_status = ap_status_map.get(status.state, "stopped")
    return {
        "novel_id": novel_id,
        "session_id": status.session_id,
        "autopilot_status": ap_status,
        "status": ap_status,
        "state": state_str,
        "current_stage": state_str,
        "active_pipeline_step": state_str if ap_status == "running" else None,
        "active_pipeline_run_id": status.session_id if ap_status == "running" else None,
        "last_stable_stage": None,
        "autopilot_run_epoch": int(status.started_at or 0),
        "autopilot_recovery_reason": status.error,
        "current_chapter_index": status.current_chapter_index,
        "total_chapters_completed": status.total_chapters_completed,
        "total_words_generated": status.total_words_generated,
        "current_progress": status.current_progress,
        "started_at": status.started_at,
        "updated_at": status.updated_at,
        "error": status.error,
        "mode": str(status.config.mode) if status.config else "single",
        "target_chapters": status.config.target_chapters if status.config else 0,
        "failed_chapters": status.failed_chapters,
    }


# ─── 端点 ───────────────────────────────────────────────────────────────────

@router.get("/{novel_id}/status")
def get_autopilot_status(
    novel_id: str,
    engine: AutonomousWritingEngine = Depends(get_autonomous_writer),
):
    """获取 novel 的自动驾驶状态。"""
    sid = _find_active_session_id(engine, novel_id)
    status = engine.get_status(sid) if sid else None
    return success_response(_status_to_payload(status, novel_id))


@router.post("/{novel_id}/start")
async def start_autopilot(
    novel_id: str,
    req: AutopilotStartRequest | None = None,
    engine: AutonomousWritingEngine = Depends(get_autonomous_writer),
):
    """启动 novel 自动驾驶。

    若已有 active session 且在 running/paused 状态，返回当前状态（幂等）。
    否则新建 session 并启动。
    """
    req = req or AutopilotStartRequest()
    sid = _find_active_session_id(engine, novel_id)
    if sid:
        existing = engine.get_status(sid)
        if existing and existing.state in (
            AutoWriteState.PLANNING, AutoWriteState.GENERATING,
            AutoWriteState.AUDITING, AutoWriteState.REWRITING,
            AutoWriteState.AFTERMATH, AutoWriteState.PAUSED,
        ):
            return success_response(_status_to_payload(existing, novel_id))

    config = AutoWriteConfig(
        mode=req.mode,
        target_chapters=req.target_chapters,
        min_quality_score=req.min_quality_score,
        max_retries_per_chapter=req.max_retries_per_chapter,
        pause_between_chapters=req.pause_between_chapters,
        auto_rewrite_on_fail=req.auto_rewrite_on_fail,
        target_words_per_chapter=req.target_words_per_chapter,
    )
    status = engine.create_session(novel_id, config)
    _novel_active_session[novel_id] = status.session_id
    started = await engine.start(status.session_id)
    if not started:
        raise HTTPException(status_code=400, detail="无法启动自动驾驶（会话状态非 IDLE/PAUSED）")
    refreshed = engine.get_status(status.session_id)
    return success_response(_status_to_payload(refreshed, novel_id))


@router.post("/{novel_id}/stop")
async def stop_autopilot(
    novel_id: str,
    engine: AutonomousWritingEngine = Depends(get_autonomous_writer),
):
    """停止 novel 自动驾驶（cancel active session）。"""
    sid = _find_active_session_id(engine, novel_id)
    if not sid:
        return success_response(_status_to_payload(None, novel_id))
    await engine.cancel(sid)
    status = engine.get_status(sid)
    # 清除映射，下次 status 查询会回落到 stopped 占位
    _novel_active_session.pop(novel_id, None)
    return success_response(_status_to_payload(status, novel_id))


@router.post("/{novel_id}/resume")
async def resume_autopilot(
    novel_id: str,
    engine: AutonomousWritingEngine = Depends(get_autonomous_writer),
):
    """恢复 novel 自动驾驶（resume paused session）。"""
    sid = _find_active_session_id(engine, novel_id)
    if not sid:
        raise HTTPException(status_code=404, detail="无 active session 可恢复")
    ok = await engine.resume(sid)
    if not ok:
        raise HTTPException(status_code=400, detail="会话非 paused 状态，无法恢复")
    status = engine.get_status(sid)
    return success_response(_status_to_payload(status, novel_id))


@router.get("/{novel_id}/circuit-breaker")
def get_circuit_breaker(
    novel_id: str,
    engine: AutonomousWritingEngine = Depends(get_autonomous_writer),
):
    """获取熔断器状态（占位实现，对齐 PlotPilot 前端 AutopilotCircuitBreakerData）。"""
    sid = _find_active_session_id(engine, novel_id)
    status = engine.get_status(sid) if sid else None
    error_count = len(status.failed_chapters) if status else 0
    return success_response({
        "status": "closed",
        "error_count": error_count,
        "max_errors": 5,
        "last_error": None,
        "error_history": [],
    })


@router.post("/{novel_id}/circuit-breaker/reset")
def reset_circuit_breaker(
    novel_id: str,
    engine: AutonomousWritingEngine = Depends(get_autonomous_writer),
):
    """重置熔断器（占位实现）。"""
    return success_response({
        "status": "closed",
        "error_count": 0,
        "max_errors": 5,
        "reset": True,
    })


# ─── SSE 流（占位实现） ────────────────────────────────────────────────────
# PlotPilot 前端 autopilotApi.streamUrl/logStreamUrl 主要用于实时日志。
# NexusForge 实际日志由 chapters/{id}/generate-content 的 SSE 流 +
# dag/events SSE 流覆盖。本端点返回 200 心跳流，避免前端 404。

@router.get("/{novel_id}/stream")
async def autopilot_stream(
    novel_id: str,
    after_seq: int | None = Query(default=None, ge=0),
    engine: AutonomousWritingEngine = Depends(get_autonomous_writer),
):
    """自动驾驶事件流（占位心跳）。"""
    async def heartbeat() -> Any:
        keepalive = 15
        while True:
            payload = json.dumps({
                "type": "heartbeat",
                "message": "ok",
                "timestamp": time.time(),
            }, ensure_ascii=False)
            yield f"data: {payload}\n\n"
            await asyncio.sleep(keepalive)

    return StreamingResponse(
        heartbeat(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{novel_id}/log-stream")
async def autopilot_log_stream(
    novel_id: str,
    engine: AutonomousWritingEngine = Depends(get_autonomous_writer),
):
    """自动驾驶日志流（占位心跳）。"""
    async def heartbeat() -> Any:
        keepalive = 15
        while True:
            payload = json.dumps({
                "type": "heartbeat",
                "message": "ok",
                "timestamp": time.time(),
            }, ensure_ascii=False)
            yield f"data: {payload}\n\n"
            await asyncio.sleep(keepalive)

    return StreamingResponse(
        heartbeat(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{novel_id}/chapter-stream")
async def chapter_stream(
    novel_id: str,
    engine: AutonomousWritingEngine = Depends(get_autonomous_writer),
):
    """章节生成流（占位心跳，对齐 PlotPilot 前端 chapterStream 路径）。"""
    async def heartbeat() -> Any:
        keepalive = 15
        while True:
            payload = json.dumps({
                "type": "heartbeat",
                "message": "ok",
                "timestamp": time.time(),
            }, ensure_ascii=False)
            yield f"data: {payload}\n\n"
            await asyncio.sleep(keepalive)

    return StreamingResponse(
        heartbeat(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
