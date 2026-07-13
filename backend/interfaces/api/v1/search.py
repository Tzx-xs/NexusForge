"""Sprint 3.2：全局搜索 API 路由。

跨 5 表（characters/foreshadows/memory_facts/world_settings/chapters）LIKE 查询，
供 WorkspaceShell 的 Search 按钮调用。
"""
from fastapi import APIRouter, Depends, Query

from application.services.search_service import SearchService
from interfaces.dependencies import get_search_service
from interfaces.utils.response import success_response

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.get("")
def search(
    q: str = Query("", description="搜索关键词"),
    novel_id: str = Query(..., description="小说 ID"),
    service: SearchService = Depends(get_search_service),
):
    """全局搜索：跨 5 类实体返回匹配结果。

    - 空查询：返回 5 类空数组
    - 无命中：返回 5 类空数组（非 404）
    """
    results = service.search(novel_id=novel_id, query=q)
    return success_response(results)
