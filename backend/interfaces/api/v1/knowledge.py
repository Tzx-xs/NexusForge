import logging

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from infrastructure.persistence.knowledge_repo import KnowledgeRepository
from interfaces.dependencies import get_knowledge_repo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["knowledge"])


class SearchRequest(BaseModel):
    model_config = {"extra": "forbid"}

    query: str
    top_k: int = 5


def success_response(data):
    return {"code": 0, "message": "success", "data": data}


@router.get("/novels/{novel_id}/knowledge/triples")
def list_triples(
    novel_id: str,
    subject: str | None = Query(None),
    predicate: str | None = Query(None),
    repo: KnowledgeRepository = Depends(get_knowledge_repo),
):
    triples = repo.get_triples(novel_id, subject=subject, predicate=predicate)
    return success_response([t.__dict__ for t in triples])


@router.get("/novels/{novel_id}/knowledge/summaries")
def list_summaries(
    novel_id: str,
    limit: int = Query(10, ge=1, le=100),
    repo: KnowledgeRepository = Depends(get_knowledge_repo),
):
    summaries = repo.get_summaries(novel_id, limit=limit)
    return success_response([s.__dict__ for s in summaries])


@router.post("/novels/{novel_id}/knowledge/search")
def search_knowledge(
    novel_id: str,
    req: SearchRequest,
    repo: KnowledgeRepository = Depends(get_knowledge_repo),
):
    try:
        results = repo.search(novel_id, req.query, limit=req.top_k)
        return success_response(results)
    except Exception:
        logger.exception("知识搜索失败")
        return {"code": 1, "message": "搜索失败，请稍后重试", "data": []}
