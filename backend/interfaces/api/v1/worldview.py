from typing import Literal

from fastapi import APIRouter, Depends, Query

from application.services.worldview_service import WorldviewService
from interfaces.dependencies import get_worldview_service

router = APIRouter(prefix="/api/v1", tags=["worldview"])

GraphType = Literal["characters", "geography", "rules", "plot"]


def success_response(data):
    return {"code": 0, "message": "success", "data": data}


@router.get("/worldview/{graph_type}")
def get_worldview_graph(
    graph_type: GraphType,
    novel_id: str | None = Query(None, description="小说 ID"),
    service: WorldviewService = Depends(get_worldview_service),
):
    data = service.get_graph(novel_id or "", graph_type)
    return success_response(data)
