from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from domain.foreshadow import Foreshadow
from infrastructure.persistence.foreshadow_repo import ForeshadowRepository
from interfaces.dependencies import get_foreshadow_repo

router = APIRouter(prefix="/api/v1", tags=["foreshadows"])


class ForeshadowCreateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    title: str = Field(..., min_length=1)
    description: str = ""
    priority: str = "P2"
    status: str = "planted"
    planted_chapter_index: int | None = None
    related_characters: list[str] = Field(default_factory=list)
    related_locations: list[str] = Field(default_factory=list)
    urgency: str = "normal"
    tags: list[str] = Field(default_factory=list)
    notes: str | None = None


class ForeshadowUpdateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    title: str | None = None
    description: str | None = None
    priority: str | None = None
    status: str | None = None
    urgency: str | None = None
    notes: str | None = None
    planted_chapter_index: int | None = None
    related_characters: list[str] | None = None
    related_locations: list[str] | None = None
    tags: list[str] | None = None


def success_response(data):
    return {"code": 0, "message": "success", "data": data}


def foreshadow_to_response(f: Foreshadow) -> dict:
    return {
        "id": f.id,
        "novel_id": f.novel_id,
        "title": f.title,
        "description": f.description,
        "priority": f.priority,
        "status": f.status,
        "planted_chapter_id": f.planted_chapter_id,
        "planted_chapter_index": f.planted_chapter_index,
        "resolved_chapter_id": f.resolved_chapter_id,
        "resolved_chapter_index": f.resolved_chapter_index,
        "related_characters": f.related_characters,
        "related_locations": f.related_locations,
        "urgency": f.urgency,
        "tags": f.tags,
        "notes": f.notes,
        "created_at": f.created_at,
        "updated_at": f.updated_at,
    }


@router.get("/novels/{novel_id}/foreshadows")
def list_foreshadows(
    novel_id: str,
    status: str | None = Query(None),
    priority: str | None = Query(None),
    repo: ForeshadowRepository = Depends(get_foreshadow_repo),
):
    items = repo.list_foreshadows(novel_id, status=status, priority=priority)
    return success_response([foreshadow_to_response(f) for f in items])


@router.get("/foreshadows/{foreshadow_id}")
def get_foreshadow(
    foreshadow_id: str,
    repo: ForeshadowRepository = Depends(get_foreshadow_repo),
):
    item = repo.get_foreshadow(foreshadow_id)
    if not item:
        return {"code": 404, "message": "not found", "data": None}
    return success_response(foreshadow_to_response(item))


@router.post("/novels/{novel_id}/foreshadows")
def create_foreshadow(
    novel_id: str,
    req: ForeshadowCreateRequest,
    repo: ForeshadowRepository = Depends(get_foreshadow_repo),
):
    foreshadow = Foreshadow(
        novel_id=novel_id,
        title=req.title,
        description=req.description,
        priority=req.priority,
        status=req.status,
        planted_chapter_index=req.planted_chapter_index,
        related_characters=req.related_characters,
        related_locations=req.related_locations,
        urgency=req.urgency,
        tags=req.tags,
        notes=req.notes,
    )
    created = repo.create_foreshadow(foreshadow)
    return success_response(foreshadow_to_response(created))


@router.put("/foreshadows/{foreshadow_id}")
def update_foreshadow(
    foreshadow_id: str,
    req: ForeshadowUpdateRequest,
    repo: ForeshadowRepository = Depends(get_foreshadow_repo),
):
    update_data = req.model_dump(exclude_none=True)
    updated = repo.update_foreshadow(foreshadow_id, update_data)
    if updated is None:
        raise HTTPException(status_code=404, detail="Foreshadow not found")
    return success_response(foreshadow_to_response(updated))


@router.delete("/foreshadows/{foreshadow_id}")
def delete_foreshadow(
    foreshadow_id: str,
    repo: ForeshadowRepository = Depends(get_foreshadow_repo),
):
    result = repo.delete_foreshadow(foreshadow_id)
    return success_response({"deleted": result})


@router.get("/novels/{novel_id}/foreshadows/pending-report")
def get_pending_report(
    novel_id: str,
    repo: ForeshadowRepository = Depends(get_foreshadow_repo),
):
    report = repo.get_pending_report(novel_id)
    return success_response(report)
