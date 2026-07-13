from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from application.audit.audit_service import QualityAuditService
from interfaces.dependencies import get_quality_audit_service

router = APIRouter(prefix="/api/v1", tags=["quality"])


def success_response(data):
    return {"code": 0, "message": "success", "data": data}


class AuditRequest(BaseModel):
    model_config = {"extra": "forbid"}

    content: str
    context: dict[str, Any] | None = None
    enabled_guards: list[str] | None = None


@router.post("/quality/audit")
async def run_audit(
    request: AuditRequest,
    service: QualityAuditService = Depends(get_quality_audit_service),
):
    report = await service.run_audit(
        content=request.content,
        context=request.context or {},
        enabled_guards=request.enabled_guards,
    )
    return success_response(report.to_dict())


@router.get("/quality/guards")
def list_guards(
    service: QualityAuditService = Depends(get_quality_audit_service),
):
    guards = service.list_guards()
    return success_response(guards)


@router.post("/quality/chapters/{chapter_id}/audit")
async def audit_chapter(
    chapter_id: str,
    request: AuditRequest | None = None,
    service: QualityAuditService = Depends(get_quality_audit_service),
):
    from interfaces.dependencies import get_chapter_service

    chapter_service = get_chapter_service()
    chapter = chapter_service.get_chapter(chapter_id)
    if not chapter:
        raise HTTPException(status_code=404, detail="Chapter not found")

    content = chapter.content or ""
    context = (request and request.context) or {}

    report = await service.run_audit(
        content=content,
        context=context,
        enabled_guards=request.enabled_guards if request else None,
    )
    return success_response(report.to_dict())
