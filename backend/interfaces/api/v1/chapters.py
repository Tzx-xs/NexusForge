import asyncio
import json
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from application.services.chapter_service import ChapterService
from domain.chapter import Chapter
from domain.shared.exceptions import ChapterNotFoundException
from interfaces.dependencies import get_chapter_service
from interfaces.middleware.rate_limit import generation_rate_limit_dependency
from interfaces.utils.response import success_response
from interfaces.utils.sse_utils import sanitize_error

router = APIRouter(prefix="/api/v1", tags=["chapters"])

_active_generations: set[str] = set()
_active_lock = asyncio.Lock()


class ChapterCreateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    title: str = ""
    number: int | None = None


class ChapterUpdateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    title: str | None = None
    outline: str | None = None
    content: str | None = None
    status: str | None = None
    tension_score: float | None = None


class GenerateContentRequest(BaseModel):
    """AI 控制台生成参数请求体。

    对应 frontend/src/components/workspace/AiConsole.vue handleGenerate 发送的 JSON。
    字段全部可选，未提供时使用默认值。
    """

    model_config = {"extra": "ignore"}

    mode: str = "continue"
    target_length: str = "medium"
    style_strength: int | float = 70
    creativity: int | float = 50
    quality_guards: list[str] | None = None
    context: str = ""


@router.get("/novels/{novel_id}/chapters")
def list_chapters(novel_id: str, service: ChapterService = Depends(get_chapter_service)):
    chapters = service.list_chapters(novel_id)
    return success_response([chapter_to_response(c) for c in chapters])


@router.post("/novels/{novel_id}/chapters")
def create_chapter(novel_id: str, req: ChapterCreateRequest, service: ChapterService = Depends(get_chapter_service)):
    chapter = service.create_chapter(
        novel_id=novel_id,
        title=req.title,
        number=req.number,
    )
    return success_response(chapter_to_response(chapter))


@router.get("/chapters/{chapter_id}")
def get_chapter(chapter_id: str, service: ChapterService = Depends(get_chapter_service)):
    chapter = service.get_chapter(chapter_id)
    return success_response(chapter_to_response(chapter))


@router.put("/chapters/{chapter_id}")
def update_chapter(chapter_id: str, req: ChapterUpdateRequest, service: ChapterService = Depends(get_chapter_service)):
    update_data = req.model_dump(exclude_none=True)
    chapter = service.update_chapter(chapter_id, **update_data)
    return success_response(chapter_to_response(chapter))


@router.delete("/chapters/{chapter_id}")
def delete_chapter(chapter_id: str, service: ChapterService = Depends(get_chapter_service)):
    result = service.delete_chapter(chapter_id)
    return success_response({"deleted": result})


@router.post("/chapters/{chapter_id}/generate-outline")
async def generate_outline(chapter_id: str, service: ChapterService = Depends(get_chapter_service)):
    chapter = await service.generate_outline(chapter_id)
    return success_response(chapter_to_response(chapter))


@router.post("/chapters/{chapter_id}/generate-content")
async def generate_content(
    chapter_id: str,
    req: GenerateContentRequest | None = None,
    service: ChapterService = Depends(get_chapter_service),
    _rate_limit: None = Depends(generation_rate_limit_dependency),
):
    async with _active_lock:
        if chapter_id in _active_generations:
            raise HTTPException(status_code=429, detail="该章节正在生成中，请稍候再试")
        _active_generations.add(chapter_id)

    # 允许空请求体：未提供 req 时使用默认生成参数
    options = req.model_dump() if req is not None else {}

    async def event_generator() -> AsyncGenerator[str, None]:
        full_content = ""
        try:
            async for event_type, data in service.generate_content_stream(chapter_id, options=options):
                if event_type == "token":
                    full_content += data
                    payload = json.dumps({"delta": data}, ensure_ascii=False)
                    yield f"event: token\ndata: {payload}\n\n"
                elif event_type == "progress":
                    try:
                        percent = int(data)
                    except (ValueError, TypeError):
                        percent = 0
                    step = "content"
                    if percent <= 30:
                        step = "outline"
                    elif percent >= 90:
                        step = "review"
                    payload = json.dumps({"step": step, "percent": percent}, ensure_ascii=False)
                    yield f"event: progress\ndata: {payload}\n\n"
                elif event_type == "complete":
                    word_count = len(full_content)
                    payload = json.dumps({"chapter_id": chapter_id, "word_count": word_count}, ensure_ascii=False)
                    yield f"event: complete\ndata: {payload}\n\n"
                elif event_type == "error":
                    payload = json.dumps({"code": "E2001", "message": data}, ensure_ascii=False)
                    yield f"event: error\ndata: {payload}\n\n"
        except Exception as e:
            payload = json.dumps({"code": "E5000", "message": sanitize_error(e)}, ensure_ascii=False)
            yield f"event: error\ndata: {payload}\n\n"
        finally:
            async with _active_lock:
                _active_generations.discard(chapter_id)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chapters/{chapter_id}/ai-suggest")
async def ai_suggest(chapter_id: str, service: ChapterService = Depends(get_chapter_service)):
    """Sprint 5.1: AI 写作建议 SSE 端点。

    基于当前章节内容生成写作建议,流式返回 token/complete/error 事件。
    """
    # 预校验(在 SSE 流启动前,确保正确 HTTP 状态码)
    try:
        chapter = service.get_chapter(chapter_id)
    except ChapterNotFoundException:
        raise HTTPException(status_code=404, detail="章节不存在")

    if not chapter.content or not chapter.content.strip():
        raise HTTPException(status_code=400, detail="章节内容为空,无法生成建议")

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            async for event_type, data in service.generate_ai_suggest_stream(chapter_id):
                if event_type == "token":
                    payload = json.dumps({"delta": data}, ensure_ascii=False)
                    yield f"event: token\ndata: {payload}\n\n"
                elif event_type == "complete":
                    payload = json.dumps(data, ensure_ascii=False)
                    yield f"event: complete\ndata: {payload}\n\n"
                elif event_type == "error":
                    payload = json.dumps({"code": "E5000", "message": str(data)}, ensure_ascii=False)
                    yield f"event: error\ndata: {payload}\n\n"
        except Exception as e:
            payload = json.dumps({"code": "E5000", "message": sanitize_error(e)}, ensure_ascii=False)
            yield f"event: error\ndata: {payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


def chapter_to_response(chapter: Chapter) -> dict:
    return {
        "id": chapter.id,
        "novel_id": chapter.novel_id,
        "number": chapter.number,
        "title": chapter.title,
        "outline": chapter.outline,
        "content": chapter.content,
        "status": chapter.status,
        "word_count": chapter.word_count,
        "tension_score": chapter.tension_score,
        "created_at": chapter.created_at,
        "updated_at": chapter.updated_at,
    }
