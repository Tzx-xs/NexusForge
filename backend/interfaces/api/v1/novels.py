from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from application.services.novel_service import NovelService
from domain.novel import Novel
from interfaces.dependencies import get_novel_service

router = APIRouter(prefix="/api/v1/novels", tags=["novels"])


class NovelCreateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    title: str = Field(..., min_length=1)
    premise: str = ""
    genre: str = ""
    target_chapters: int = 0
    cover_url: str = ""
    style_tags: list[str] | None = None
    perspective: str | None = None


class NovelUpdateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    title: str | None = None
    premise: str | None = None
    genre: str | None = None
    target_chapters: int | None = None
    cover_url: str | None = None
    style_tags: list[str] | None = None
    perspective: str | None = None


class NovelResponse(BaseModel):
    id: str
    title: str
    premise: str
    genre: str
    target_chapters: int
    current_chapter: int
    cover_url: str
    style_tags: list[str]
    perspective: str
    created_at: str
    updated_at: str


class NovelListResponse(BaseModel):
    items: list[NovelResponse]
    total: int
    page: int
    page_size: int


class NovelStatsResponse(BaseModel):
    novel_id: str
    title: str
    chapter_count: int
    completed_chapters: int
    total_words: int
    target_chapters: int
    completion_rate: float
    today_words: int
    streak_days: int
    total_chapters: int


def success_response(data):
    return {"code": 0, "message": "success", "data": data}


@router.get("")
def list_novels(
    page: int | None = Query(None, ge=1),
    page_size: int | None = Query(None, ge=1),
    service: NovelService = Depends(get_novel_service),
):
    if page is not None and page_size is not None:
        novels, total = service.list_novels(page=page, page_size=page_size)
        return success_response(
            {
                "items": [novel_to_response(n) for n in novels],
                "total": total,
                "page": page,
                "page_size": page_size,
            }
        )
    novels, _ = service.list_novels()
    return success_response([novel_to_response(n) for n in novels])


@router.post("")
def create_novel(req: NovelCreateRequest, service: NovelService = Depends(get_novel_service)):
    novel = service.create_novel(
        title=req.title,
        premise=req.premise,
        genre=req.genre,
        target_chapters=req.target_chapters,
        cover_url=req.cover_url,
        style_tags=req.style_tags,
        perspective=req.perspective,
    )
    return success_response(novel_to_response(novel))


@router.get("/{novel_id}")
def get_novel(novel_id: str, service: NovelService = Depends(get_novel_service)):
    novel = service.get_novel(novel_id)
    return success_response(novel_to_response(novel))


@router.put("/{novel_id}")
def update_novel(novel_id: str, req: NovelUpdateRequest, service: NovelService = Depends(get_novel_service)):
    update_data = req.model_dump(exclude_none=True)
    novel = service.update_novel(novel_id, **update_data)
    return success_response(novel_to_response(novel))


@router.delete("/{novel_id}")
def delete_novel(novel_id: str, service: NovelService = Depends(get_novel_service)):
    result = service.delete_novel(novel_id)
    return success_response({"deleted": result})


@router.get("/{novel_id}/stats")
def get_novel_stats(novel_id: str, service: NovelService = Depends(get_novel_service)):
    stats = service.get_novel_stats(novel_id)
    return success_response(stats)


def novel_to_response(novel: Novel) -> dict:
    return {
        "id": novel.id,
        "title": novel.title,
        "premise": novel.premise,
        "genre": novel.genre,
        "target_chapters": novel.target_chapters,
        "current_chapter": novel.current_chapter,
        "cover_url": novel.cover_url,
        "style_tags": novel.style_tags,
        "perspective": novel.perspective,
        "created_at": novel.created_at,
        "updated_at": novel.updated_at,
    }
