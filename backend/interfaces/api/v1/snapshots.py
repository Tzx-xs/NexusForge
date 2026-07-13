import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from application.services.chapter_service import ChapterService
from domain.evolution.snapshot import Snapshot
from infrastructure.persistence.snapshot_repo import SnapshotRepository
from interfaces.dependencies import get_chapter_service, get_snapshot_repo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["snapshots"])


def success_response(data):
    return {"code": 0, "message": "success", "data": data}


class SnapshotCreateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    novel_id: str
    chapter_id: str = ""
    snapshot_type: str = "manual"
    name: str
    description: str = ""
    content_hash: str | None = None
    diff_data: dict[str, Any] | None = None
    parent_snapshot_id: str | None = None
    created_by: str = "user"


class SnapshotRestoreRequest(BaseModel):
    model_config = {"extra": "forbid"}

    snapshot_id: str


def snapshot_to_response(s: Snapshot) -> dict:
    return {
        "id": s.id,
        "novel_id": s.novel_id,
        "chapter_id": s.chapter_id,
        "snapshot_type": s.snapshot_type,
        "name": s.name,
        "description": s.description,
        "content_hash": s.content_hash,
        "diff_data": s.diff_data,
        "parent_snapshot_id": s.parent_snapshot_id,
        "created_by": s.created_by,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
    }


@router.get("/novels/{novel_id}/snapshots")
def list_snapshots(
    novel_id: str,
    limit: int = 50,
    chapter_id: str | None = None,
    repo: SnapshotRepository = Depends(get_snapshot_repo),
):
    items = repo.list_by_novel(novel_id, limit=limit, chapter_id=chapter_id)
    return success_response([snapshot_to_response(s) for s in items])


@router.get("/chapters/{chapter_id}/snapshots")
def list_chapter_snapshots(
    chapter_id: str,
    repo: SnapshotRepository = Depends(get_snapshot_repo),
):
    items = repo.list_by_chapter(chapter_id)
    return success_response([snapshot_to_response(s) for s in items])


@router.post("/snapshots")
def create_snapshot(
    req: SnapshotCreateRequest,
    repo: SnapshotRepository = Depends(get_snapshot_repo),
):
    snapshot = Snapshot(
        novel_id=req.novel_id,
        chapter_id=req.chapter_id,
        snapshot_type=req.snapshot_type,
        name=req.name,
        description=req.description,
        content_hash=req.content_hash,
        diff_data=req.diff_data,
        parent_snapshot_id=req.parent_snapshot_id,
        created_by=req.created_by,
    )
    created = repo.create(snapshot)
    return success_response(snapshot_to_response(created))


@router.get("/snapshots/{snapshot_id}")
def get_snapshot(
    snapshot_id: str,
    repo: SnapshotRepository = Depends(get_snapshot_repo),
):
    item = repo.get(snapshot_id)
    if not item:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return success_response(snapshot_to_response(item))


@router.delete("/snapshots/{snapshot_id}")
def delete_snapshot(
    snapshot_id: str,
    repo: SnapshotRepository = Depends(get_snapshot_repo),
):
    result = repo.delete(snapshot_id)
    return success_response({"deleted": result})


# ========== BLOCK-09: 版本管理新增端点 ==========


@router.get("/snapshots/{snapshot_id}/content")
def get_snapshot_content(
    snapshot_id: str,
    repo: SnapshotRepository = Depends(get_snapshot_repo),
):
    """获取快照的完整章节内容。"""
    content = repo.get_content(snapshot_id)
    if content is None:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return success_response({
        "snapshot_id": snapshot_id,
        "content": content,
    })


@router.post("/chapters/{chapter_id}/restore/{snapshot_id}")
def restore_chapter_from_snapshot(
    chapter_id: str,
    snapshot_id: str,
    chapter_service: ChapterService = Depends(get_chapter_service),
):
    """从指定快照恢复章节内容。"""
    try:
        chapter = chapter_service.restore_from_snapshot(chapter_id, snapshot_id)
        return success_response({
            "id": chapter.id,
            "number": chapter.number,
            "word_count": chapter.word_count,
            "restored": True,
        })
    except Exception:
        logger.exception("快照恢复失败")
        raise HTTPException(status_code=400, detail="恢复失败，请稍后重试")
