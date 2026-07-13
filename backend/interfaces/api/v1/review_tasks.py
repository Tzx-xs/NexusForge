from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from application.services.review_task_service import ReviewTaskService
from interfaces.dependencies import get_review_task_service

router = APIRouter(prefix="/api/v1", tags=["review_tasks"])


class ReviewTaskCreateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    title: str = Field(..., min_length=1)
    novel_id: str | None = None


class ReviewTaskUpdateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    status: str | None = None
    result: str | None = None


class ReviewTaskListResponse(BaseModel):
    items: list[dict]
    total: int
    page: int
    page_size: int


def success_response(data):
    return {"code": 0, "message": "success", "data": data}


@router.get("/reviews")
def list_review_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: ReviewTaskService = Depends(get_review_task_service),
):
    result = service.list_tasks(page=page, page_size=page_size)
    return success_response(result)


@router.post("/reviews")
def create_review_task(
    req: ReviewTaskCreateRequest,
    service: ReviewTaskService = Depends(get_review_task_service),
):
    task = service.create_task(title=req.title, novel_id=req.novel_id)
    return success_response(task)


@router.get("/reviews/{task_id}")
def get_review_task(
    task_id: str,
    service: ReviewTaskService = Depends(get_review_task_service),
):
    task = service.get_task(task_id)
    return success_response(task)


@router.put("/reviews/{task_id}")
def update_review_task(
    task_id: str,
    req: ReviewTaskUpdateRequest,
    service: ReviewTaskService = Depends(get_review_task_service),
):
    task = service.update_task(task_id, status=req.status, result=req.result)
    return success_response(task)


@router.delete("/reviews/{task_id}")
def delete_review_task(
    task_id: str,
    service: ReviewTaskService = Depends(get_review_task_service),
):
    deleted = service.delete_task(task_id)
    return success_response({"deleted": deleted})
