from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from application.services.novel_service import NovelService
from domain.novel import Novel, VALID_STAGES, STAGE_PREPARING
from interfaces.dependencies import get_novel_service

router = APIRouter(prefix="/api/v1/novels", tags=["novels"])


class NovelCreateRequest(BaseModel):
    """对齐 PlotPilot 前端 createNovel 入参。

    允许额外字段（world_preset/story_structure 等）— 旧字段 model_config forbid 会拒绝。
    NexusForge 后端按需存档，未知字段忽略。
    """
    model_config = {"extra": "ignore"}

    title: str = Field(..., min_length=1)
    premise: str = ""
    genre: str = ""
    target_chapters: int = 0
    cover_url: str = ""
    style_tags: list[str] | None = None
    perspective: str | None = None
    # NexusForge Phase 3.5：PlotPilot 建档字段
    novel_id: str | None = None
    author: str = ""
    stage: str = STAGE_PREPARING
    auto_approve_mode: bool = False
    target_words_per_chapter: int | None = None
    generation_prefs: dict | None = None
    world_preset: str = ""
    story_structure: str = ""
    pacing_control: str = ""
    writing_style: str = ""
    special_requirements: str = ""
    length_tier: str | None = None  # 前端 V1 体量档，后端解析为 target_chapters


class NovelUpdateRequest(BaseModel):
    model_config = {"extra": "ignore"}

    title: str | None = None
    premise: str | None = None
    genre: str | None = None
    target_chapters: int | None = None
    cover_url: str | None = None
    style_tags: list[str] | None = None
    perspective: str | None = None
    author: str | None = None
    stage: str | None = None
    auto_approve_mode: bool | None = None
    target_words_per_chapter: int | None = None
    generation_prefs: dict | None = None
    world_preset: str | None = None
    story_structure: str | None = None
    pacing_control: str | None = None
    writing_style: str | None = None
    special_requirements: str | None = None


class NovelStageUpdateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    stage: str


class NovelAutoApproveModeRequest(BaseModel):
    model_config = {"extra": "forbid"}

    auto_approve_mode: bool


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
    # NexusForge Phase 3.5：PlotPilot 字段
    author: str = ""
    stage: str = STAGE_PREPARING
    auto_approve_mode: bool = False
    target_words_per_chapter: int = 2500
    generation_prefs: dict = {}
    world_preset: str = ""
    story_structure: str = ""
    pacing_control: str = ""
    writing_style: str = ""
    special_requirements: str = ""
    # 前端 NovelDTO 期望的派生字段（聚合自关联表）
    chapters: list[dict] = []
    total_word_count: int = 0
    has_bible: bool = False
    has_outline: bool = False
    autopilot_status: str = "stopped"


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


# 体量档 → 章节数映射（PlotPilot 前端 length_tier）
_LENGTH_TIER_TO_CHAPTERS: dict[str, int] = {
    "short": 30,
    "standard": 100,
    "epic": 300,
}


def _resolve_target_chapters(req: NovelCreateRequest) -> int:
    """优先 target_chapters；其次 length_tier；最后默认 0。"""
    if req.target_chapters and req.target_chapters > 0:
        return req.target_chapters
    if req.length_tier and req.length_tier in _LENGTH_TIER_TO_CHAPTERS:
        return _LENGTH_TIER_TO_CHAPTERS[req.length_tier]
    return 0


def _chapter_to_dict(ch) -> dict:
    return {
        "id": ch.id,
        "number": ch.number,
        "title": ch.title,
        "content": ch.content,
        "word_count": ch.word_count,
    }


def novel_to_response(novel: Novel, chapters: list | None = None) -> dict:
    """将 Novel 领域对象转为响应字典。

    chapters: 已查询的章节列表，None 时不填充 chapters/total_word_count（list 场景避免 N+1）。
    """
    has_bible = bool(novel.world_preset or novel.story_structure)
    has_outline = bool(novel.story_structure or novel.pacing_control)
    data = {
        "id": novel.id,
        "title": novel.title,
        "premise": novel.premise,
        "genre": novel.genre,
        "target_chapters": novel.target_chapters,
        "current_chapter": novel.current_chapter,
        "cover_url": novel.cover_url,
        "style_tags": novel.style_tags,
        "perspective": novel.perspective,
        "created_at": novel.created_at.isoformat() if hasattr(novel.created_at, "isoformat") else str(novel.created_at),
        "updated_at": novel.updated_at.isoformat() if hasattr(novel.updated_at, "isoformat") else str(novel.updated_at),
        "author": novel.author,
        "stage": novel.stage,
        "auto_approve_mode": novel.auto_approve_mode,
        "target_words_per_chapter": novel.target_words_per_chapter,
        "generation_prefs": novel.generation_prefs,
        "world_preset": novel.world_preset,
        "story_structure": novel.story_structure,
        "pacing_control": novel.pacing_control,
        "writing_style": novel.writing_style,
        "special_requirements": novel.special_requirements,
        "has_bible": has_bible,
        "has_outline": has_outline,
        "autopilot_status": "stopped",
    }
    if chapters is not None:
        data["chapters"] = [_chapter_to_dict(c) for c in chapters]
        data["total_word_count"] = sum(c.word_count for c in chapters)
    else:
        data["chapters"] = []
        data["total_word_count"] = 0
    return data


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
    # PlotPilot 前端 listNovels 期望扁平数组（非分页信封），后端按扁平数组返回
    return success_response([novel_to_response(n) for n in novels])


@router.post("")
def create_novel(req: NovelCreateRequest, service: NovelService = Depends(get_novel_service)):
    target_chapters = _resolve_target_chapters(req)
    target_words = req.target_words_per_chapter if req.target_words_per_chapter else 2500
    novel = service.create_novel(
        title=req.title,
        premise=req.premise,
        genre=req.genre,
        target_chapters=target_chapters,
        cover_url=req.cover_url,
        style_tags=req.style_tags,
        perspective=req.perspective or "",
        novel_id=req.novel_id,
        author=req.author,
        stage=req.stage,
        auto_approve_mode=req.auto_approve_mode,
        target_words_per_chapter=target_words,
        generation_prefs=req.generation_prefs,
        world_preset=req.world_preset,
        story_structure=req.story_structure,
        pacing_control=req.pacing_control,
        writing_style=req.writing_style,
        special_requirements=req.special_requirements,
    )
    return success_response(novel_to_response(novel, chapters=[]))


@router.get("/{novel_id}")
def get_novel(novel_id: str, service: NovelService = Depends(get_novel_service)):
    novel = service.get_novel(novel_id)
    chapters = service.chapter_repo.list_by_novel(novel_id)
    return success_response(novel_to_response(novel, chapters=chapters))


@router.put("/{novel_id}")
def update_novel(novel_id: str, req: NovelUpdateRequest, service: NovelService = Depends(get_novel_service)):
    update_data = req.model_dump(exclude_none=True)
    novel = service.update_novel(novel_id, **update_data)
    chapters = service.chapter_repo.list_by_novel(novel_id)
    return success_response(novel_to_response(novel, chapters=chapters))


@router.delete("/{novel_id}")
def delete_novel(novel_id: str, service: NovelService = Depends(get_novel_service)):
    result = service.delete_novel(novel_id)
    return success_response({"deleted": result})


@router.put("/{novel_id}/stage")
def update_novel_stage(
    novel_id: str,
    req: NovelStageUpdateRequest,
    service: NovelService = Depends(get_novel_service),
):
    """更新小说阶段（对齐 PlotPilot 前端 PUT /novels/{id}/stage）。"""
    if req.stage not in VALID_STAGES:
        raise HTTPException(status_code=400, detail=f"无效阶段: {req.stage}")
    novel = service.update_stage(novel_id, req.stage)
    chapters = service.chapter_repo.list_by_novel(novel_id)
    return success_response(novel_to_response(novel, chapters=chapters))


@router.patch("/{novel_id}/auto-approve-mode")
def update_auto_approve_mode(
    novel_id: str,
    req: NovelAutoApproveModeRequest,
    service: NovelService = Depends(get_novel_service),
):
    """更新自动审核模式（对齐 PlotPilot 前端 PATCH /novels/{id}/auto-approve-mode）。"""
    novel = service.update_auto_approve_mode(novel_id, req.auto_approve_mode)
    chapters = service.chapter_repo.list_by_novel(novel_id)
    return success_response(novel_to_response(novel, chapters=chapters))


@router.get("/{novel_id}/statistics")
def get_novel_statistics(novel_id: str, service: NovelService = Depends(get_novel_service)):
    """PlotPilot 风格统计（对齐前端 getNovelStatistics 调用）。"""
    stats = service.get_novel_statistics(novel_id)
    return success_response(stats)


@router.get("/{novel_id}/stats")
def get_novel_stats(novel_id: str, service: NovelService = Depends(get_novel_service)):
    """StellarScribe 旧版统计端点（保留向后兼容）。"""
    stats = service.get_novel_stats(novel_id)
    return success_response(stats)
