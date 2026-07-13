import json

from fastapi import APIRouter, Depends

from application.services.review_service import ReviewService
from domain.review import ReviewResult
from interfaces.dependencies import get_review_service

router = APIRouter(prefix="/api/v1", tags=["review"])


def success_response(data):
    return {"code": 0, "message": "success", "data": data}


def _parse_review_details(raw: str):
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
    except (ValueError, TypeError):
        return []
    if isinstance(parsed, list):
        return parsed
    return []


@router.post("/chapters/{chapter_id}/review")
async def review_chapter(chapter_id: str, service: ReviewService = Depends(get_review_service)):
    review = await service.review_chapter(chapter_id)
    return success_response(review_to_response(review))


@router.get("/chapters/{chapter_id}/review")
def get_review(chapter_id: str, service: ReviewService = Depends(get_review_service)):
    review = service.get_review(chapter_id)
    return success_response(review_to_response(review) if review else None)


def review_to_response(review: ReviewResult) -> dict:
    return {
        "id": review.id,
        "chapter_id": review.chapter_id,
        "total_score": review.total_score,
        "grade": review.grade,
        "red_line_violations": review.red_line_violations,
        "dimension_scores": review.dimension_scores,
        "review_details": _parse_review_details(review.review_details),
        "created_at": review.created_at,
    }
