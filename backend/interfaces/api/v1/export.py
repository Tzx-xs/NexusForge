import urllib.parse

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel

from application.services.export_service import ExportFormat, ExportOptions, ExportScope, ExportService
from interfaces.dependencies import get_export_service
from interfaces.utils.response import success_response

router = APIRouter(prefix="/api/v1", tags=["export"])


class ExportRequest(BaseModel):
    model_config = {"extra": "forbid"}

    format: str = "txt"
    scope: str = "full"
    include_title_page: bool = True
    include_chapter_numbers: bool = True
    include_toc: bool = True
    start_chapter: int | None = None
    end_chapter: int | None = None
    title: str | None = None
    author: str | None = None


@router.post("/novels/{novel_id}/export")
async def export_novel_post(
    novel_id: str,
    request: ExportRequest,
    service: ExportService = Depends(get_export_service),
):
    try:
        fmt = ExportFormat(request.format)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {request.format}") from None

    try:
        scope = ExportScope(request.scope)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported scope: {request.scope}") from None

    options = ExportOptions(
        format=fmt,
        scope=scope,
        include_title_page=request.include_title_page,
        include_chapter_numbers=request.include_chapter_numbers,
        include_toc=request.include_toc,
        start_chapter=request.start_chapter,
        end_chapter=request.end_chapter,
        title=request.title,
        author=request.author,
    )

    content = service.export_novel(novel_id, options)
    filename = service.get_export_filename(novel_id, options)
    encoded_filename = urllib.parse.quote(filename)

    content_types = {
        ExportFormat.TXT: "text/plain; charset=utf-8",
        ExportFormat.MARKDOWN: "text/markdown; charset=utf-8",
        ExportFormat.HTML: "text/html; charset=utf-8",
        ExportFormat.EPUB: "application/epub+zip",
        ExportFormat.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    response = Response(
        content=content,
        media_type=content_types.get(fmt, "application/octet-stream"),
    )
    response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{encoded_filename}"
    return response


@router.get("/novels/{novel_id}/export")
async def export_novel_get(
    novel_id: str,
    format: str = Query("txt"),
    scope: str = Query("full"),
    include_title_page: bool = Query(True),
    include_chapter_numbers: bool = Query(True),
    include_toc: bool = Query(True),
    start_chapter: int | None = Query(None),
    end_chapter: int | None = Query(None),
    title: str | None = Query(None),
    author: str | None = Query(None),
    service: ExportService = Depends(get_export_service),
):
    try:
        fmt = ExportFormat(format)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}") from None

    try:
        scp = ExportScope(scope)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unsupported scope: {scope}") from None

    options = ExportOptions(
        format=fmt,
        scope=scp,
        include_title_page=include_title_page,
        include_chapter_numbers=include_chapter_numbers,
        include_toc=include_toc,
        start_chapter=start_chapter,
        end_chapter=end_chapter,
        title=title,
        author=author,
    )

    content = service.export_novel(novel_id, options)
    filename = service.get_export_filename(novel_id, options)
    encoded_filename = urllib.parse.quote(filename)

    content_types = {
        ExportFormat.TXT: "text/plain; charset=utf-8",
        ExportFormat.MARKDOWN: "text/markdown; charset=utf-8",
        ExportFormat.HTML: "text/html; charset=utf-8",
        ExportFormat.EPUB: "application/epub+zip",
        ExportFormat.DOCX: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    response = Response(
        content=content,
        media_type=content_types.get(fmt, "application/octet-stream"),
    )
    response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{encoded_filename}"
    return response


@router.get("/novels/{novel_id}/export/formats")
def list_export_formats():
    formats = [
        {"format": "txt", "label": "TXT 文本", "description": "纯文本格式，兼容性最好"},
        {"format": "md", "label": "Markdown", "description": "Markdown 格式，支持标题层级"},
        {"format": "html", "label": "HTML", "description": "网页格式，带排版样式"},
        {"format": "epub", "label": "EPUB 电子书", "description": "电子书格式，适合移动端阅读"},
        {"format": "docx", "label": "DOCX 文档", "description": "Word 文档格式，方便二次编辑"},
    ]
    return success_response(formats)


@router.get("/novels/{novel_id}/export/scopes")
def list_export_scopes():
    scopes = [
        {"scope": "full", "label": "全本导出"},
        {"scope": "chapter_range", "label": "章节范围"},
        {"scope": "single_chapter", "label": "单章导出"},
        {"scope": "outline_only", "label": "仅大纲"},
    ]
    return success_response(scopes)
