from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from domain.structure.storyline import Storyline, StorylineNode
from infrastructure.persistence.storyline_repo import StorylineRepository
from interfaces.dependencies import get_storyline_repo

router = APIRouter(prefix="/api/v1", tags=["storylines"])


def success_response(data):
    return {"code": 0, "message": "success", "data": data}


class StorylineCreateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    name: str
    description: str = ""
    color: str = "#2080f0"
    order: int = 0


class StorylineUpdateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    name: str | None = None
    description: str | None = None
    color: str | None = None
    is_active: bool | None = None
    order: int | None = None


class NodeCreateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    title: str
    description: str = ""
    node_type: str = "scene"
    status: str = "draft"
    chapter_index: int | None = None
    chapter_id: str | None = None
    x: float = 0
    y: float = 0
    width: float = 180
    height: float = 80
    parent_ids: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class NodeUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    node_type: str | None = None
    status: str | None = None
    chapter_index: int | None = None
    chapter_id: str | None = None
    x: float | None = None
    y: float | None = None
    width: float | None = None
    height: float | None = None
    parent_ids: list[str] | None = None
    child_ids: list[str] | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = None


class ConnectRequest(BaseModel):
    source_id: str
    target_id: str


def storyline_to_response(s: Storyline) -> dict:
    return {
        "id": s.id,
        "novel_id": s.novel_id,
        "name": s.name,
        "description": s.description,
        "color": s.color,
        "node_count": s.node_count,
        "is_active": s.is_active,
        "order": s.order,
        "created_at": s.created_at,
        "updated_at": s.updated_at,
    }


def node_to_response(n: StorylineNode) -> dict:
    return {
        "id": n.id,
        "novel_id": n.novel_id,
        "storyline_id": n.storyline_id,
        "title": n.title,
        "description": n.description,
        "node_type": n.node_type,
        "status": n.status,
        "chapter_index": n.chapter_index,
        "chapter_id": n.chapter_id,
        "x": n.x,
        "y": n.y,
        "width": n.width,
        "height": n.height,
        "parent_ids": n.parent_ids,
        "child_ids": n.child_ids,
        "tags": n.tags,
        "metadata": n.metadata,
        "created_at": n.created_at,
        "updated_at": n.updated_at,
    }


@router.get("/novels/{novel_id}/storylines")
def list_storylines(
    novel_id: str,
    repo: StorylineRepository = Depends(get_storyline_repo),
):
    items = repo.list_storylines(novel_id)
    return success_response([storyline_to_response(s) for s in items])


@router.post("/novels/{novel_id}/storylines")
def create_storyline(
    novel_id: str,
    req: StorylineCreateRequest,
    repo: StorylineRepository = Depends(get_storyline_repo),
):
    storyline = Storyline(
        novel_id=novel_id,
        name=req.name,
        description=req.description,
        color=req.color,
        order=req.order,
    )
    created = repo.create_storyline(storyline)
    return success_response(storyline_to_response(created))


@router.get("/storylines/{storyline_id}")
def get_storyline(
    storyline_id: str,
    repo: StorylineRepository = Depends(get_storyline_repo),
):
    item = repo.get_storyline(storyline_id)
    if not item:
        raise HTTPException(status_code=404, detail="Storyline not found")
    return success_response(storyline_to_response(item))


@router.put("/storylines/{storyline_id}")
def update_storyline(
    storyline_id: str,
    req: StorylineUpdateRequest,
    repo: StorylineRepository = Depends(get_storyline_repo),
):
    data = {k: v for k, v in req.model_dump().items() if v is not None}
    updated = repo.update_storyline(storyline_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Storyline not found")
    return success_response(storyline_to_response(updated))


@router.delete("/storylines/{storyline_id}")
def delete_storyline(
    storyline_id: str,
    repo: StorylineRepository = Depends(get_storyline_repo),
):
    result = repo.delete_storyline(storyline_id)
    return success_response({"deleted": result})


@router.get("/storylines/{storyline_id}/nodes")
def list_nodes(
    storyline_id: str,
    repo: StorylineRepository = Depends(get_storyline_repo),
):
    nodes = repo.list_nodes(storyline_id)
    return success_response([node_to_response(n) for n in nodes])


@router.get("/novels/{novel_id}/storyline-nodes")
def list_nodes_by_novel(
    novel_id: str,
    repo: StorylineRepository = Depends(get_storyline_repo),
):
    nodes = repo.list_nodes_by_novel(novel_id)
    return success_response([node_to_response(n) for n in nodes])


@router.post("/storylines/{storyline_id}/nodes")
def create_node(
    storyline_id: str,
    req: NodeCreateRequest,
    repo: StorylineRepository = Depends(get_storyline_repo),
):
    storyline = repo.get_storyline(storyline_id)
    if not storyline:
        raise HTTPException(status_code=404, detail="Storyline not found")

    node = StorylineNode(
        novel_id=storyline.novel_id,
        storyline_id=storyline_id,
        title=req.title,
        description=req.description,
        node_type=req.node_type,
        status=req.status,
        chapter_index=req.chapter_index,
        chapter_id=req.chapter_id,
        x=req.x,
        y=req.y,
        width=req.width,
        height=req.height,
        parent_ids=req.parent_ids,
        tags=req.tags,
    )
    created = repo.create_node(node)

    for pid in req.parent_ids:
        repo.connect_nodes(pid, created.id)

    return success_response(node_to_response(created))


@router.get("/storyline-nodes/{node_id}")
def get_node(
    node_id: str,
    repo: StorylineRepository = Depends(get_storyline_repo),
):
    node = repo.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Node not found")
    return success_response(node_to_response(node))


@router.put("/storyline-nodes/{node_id}")
def update_node(
    node_id: str,
    req: NodeUpdateRequest,
    repo: StorylineRepository = Depends(get_storyline_repo),
):
    data = {k: v for k, v in req.model_dump().items() if v is not None}
    updated = repo.update_node(node_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Node not found")
    return success_response(node_to_response(updated))


@router.delete("/storyline-nodes/{node_id}")
def delete_node(
    node_id: str,
    repo: StorylineRepository = Depends(get_storyline_repo),
):
    result = repo.delete_node(node_id)
    return success_response({"deleted": result})


@router.post("/storyline-nodes/connect")
def connect_nodes(
    req: ConnectRequest,
    repo: StorylineRepository = Depends(get_storyline_repo),
):
    result = repo.connect_nodes(req.source_id, req.target_id)
    return success_response({"connected": result})


@router.post("/storyline-nodes/disconnect")
def disconnect_nodes(
    req: ConnectRequest,
    repo: StorylineRepository = Depends(get_storyline_repo),
):
    result = repo.disconnect_nodes(req.source_id, req.target_id)
    return success_response({"disconnected": result})
