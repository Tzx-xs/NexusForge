from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from application.voice.voice_service import VoiceService
from interfaces.dependencies import get_voice_service

router = APIRouter(prefix="/api/v1", tags=["voice"])


def success_response(data):
    return {"code": 0, "message": "success", "data": data}


class ExtractRequest(BaseModel):
    model_config = {"extra": "forbid"}

    texts: list[str]
    name: str = "default"
    novel_id: str = ""


class DriftRequest(BaseModel):
    model_config = {"extra": "forbid"}

    baseline_id: str
    sample_text: str


class RewriteRequest(BaseModel):
    model_config = {"extra": "forbid"}

    baseline_id: str
    target_text: str
    drift_dimensions: list[str] = []


@router.post("/voice/extract")
def extract_fingerprint(
    request: ExtractRequest,
    service: VoiceService = Depends(get_voice_service),
):
    fp = service.extract_fingerprint(
        texts=request.texts,
        name=request.name,
        novel_id=request.novel_id,
    )
    return success_response(fp.to_dict())


@router.get("/voice/fingerprints")
def list_fingerprints(
    service: VoiceService = Depends(get_voice_service),
):
    fps = service.list_fingerprints()
    return success_response(fps)


@router.get("/voice/fingerprints/{fp_id}")
def get_fingerprint(
    fp_id: str,
    service: VoiceService = Depends(get_voice_service),
):
    fp = service.get_fingerprint(fp_id)
    if not fp:
        raise HTTPException(status_code=404, detail="Fingerprint not found")
    return success_response(fp.to_dict())


@router.post("/voice/detect-drift")
async def detect_drift(
    request: DriftRequest,
    service: VoiceService = Depends(get_voice_service),
):
    result = service.detect_drift(
        baseline_id=request.baseline_id,
        sample_text=request.sample_text,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Baseline fingerprint not found")
    return success_response(result.to_dict())


@router.post("/voice/rewrite-prompt")
def generate_rewrite_prompt(
    request: RewriteRequest,
    service: VoiceService = Depends(get_voice_service),
):
    prompt = service.generate_rewrite_prompt(
        baseline_id=request.baseline_id,
        target_text=request.target_text,
        drift_dimensions=request.drift_dimensions,
    )
    if not prompt:
        raise HTTPException(status_code=404, detail="Baseline fingerprint not found")
    return success_response({"prompt": prompt})


@router.get("/voice/fingerprints/{fp_id}/style-guide")
def get_style_guide(
    fp_id: str,
    service: VoiceService = Depends(get_voice_service),
):
    guide = service.generate_style_guide(fp_id)
    if not guide:
        raise HTTPException(status_code=404, detail="Fingerprint not found")
    return success_response({"style_guide": guide})


@router.post("/voice/fingerprints/merge")
def merge_fingerprints(
    request: ExtractRequest,
    service: VoiceService = Depends(get_voice_service),
):
    fps: list[Any] = []
    for text in request.texts:
        fp = service.extract_fingerprint(
            texts=[text],
            name=f"sample_{len(fps)}",
            novel_id=request.novel_id,
        )
        fps.append(fp)

    merged = service.merge_fingerprints(fps, name=request.name)
    return success_response(merged.to_dict())
