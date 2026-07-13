"""Legacy /api/stats 端点 — 对齐 PlotPilot 前端 statsApi（旧版 /api 路径）。

PlotPilot 前端 src/api/stats.ts 用 legacyStatsHttp（baseURL=/api）调用：
- GET /api/stats/global              → GlobalStats
- GET /api/stats/book/{slug}/chapter/{chapterId}  → ChapterStats
- GET /api/stats/book/{slug}/progress?days=30      → WritingProgress[]

NexusForge 后端原无此端点。本路由提供轻量实现，复用 NovelService 聚合数据。
响应格式：PlotPilot legacyStatsHttp interceptor 期望 {success:true, data:...}，
故本端点返回 PlotPilot 风格而非 NexusForge {code,message,data} 信封。
"""
from fastapi import APIRouter, Depends, Query

from application.services.novel_service import NovelService
from interfaces.dependencies import get_novel_service

router = APIRouter(prefix="/api/stats", tags=["stats-legacy"])


def _plotpilot_success(data) -> dict:
    """PlotPilot legacyStatsHttp 期望的响应格式。"""
    return {"success": True, "data": data, "message": "ok"}


@router.get("/global")
def get_global_stats(service: NovelService = Depends(get_novel_service)):
    """全局统计：总数 + 按阶段分布。"""
    novels, _ = service.list_novels()
    total_books = len(novels)
    total_chapters = 0
    total_words = 0
    total_characters = 0
    books_by_stage: dict[str, int] = {}
    for novel in novels:
        chapters = service.chapter_repo.list_by_novel(novel.id)
        total_chapters += len(chapters)
        total_words += sum(c.word_count for c in chapters)
        # characters 表
        characters = service.character_repo.list_by_novel(novel.id)
        total_characters += len(characters)
        stage = novel.stage or "preparing"
        books_by_stage[stage] = books_by_stage.get(stage, 0) + 1
    return _plotpilot_success({
        "total_books": total_books,
        "total_chapters": total_chapters,
        "total_words": total_words,
        "total_characters": total_characters,
        "books_by_stage": books_by_stage,
    })


@router.get("/book/{slug}/chapter/{chapter_id}")
def get_chapter_stats(
    slug: str,
    chapter_id: int,
    service: NovelService = Depends(get_novel_service),
):
    """章节统计（占位返回基础字段）。"""
    chapters = service.chapter_repo.list_by_novel(slug)
    chapter = next((c for c in chapters if c.number == chapter_id), None)
    if not chapter:
        return _plotpilot_success(None)
    return _plotpilot_success({
        "chapter_id": chapter.id,
        "novel_id": slug,
        "chapter_number": chapter.number,
        "title": chapter.title,
        "word_count": chapter.word_count,
        "tension_score": chapter.tension_score,
        "status": chapter.status,
    })


@router.get("/book/{slug}/progress")
def get_writing_progress(
    slug: str,
    days: int = Query(default=30, ge=1, le=365),
    service: NovelService = Depends(get_novel_service),
):
    """写作进度（占位返回空数组，PlotPilot 用此画趋势图，无数据时图表为空）。"""
    return _plotpilot_success([])
