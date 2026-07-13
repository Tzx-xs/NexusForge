from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field

from application.services.bible_service import BibleService
from domain.character import Character
from domain.world_setting import WorldSetting
from interfaces.dependencies import get_bible_service

router = APIRouter(prefix="/api/v1", tags=["bible"])


class CharacterCreateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    name: str = Field(..., min_length=1)
    role: str = "配角"
    description: str = ""
    personality: str = ""
    appearance: str = ""
    background: str = ""
    gender: str = ""
    age: str = ""


class CharacterUpdateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    name: str | None = None
    role: str | None = None
    description: str | None = None
    personality: str | None = None
    appearance: str | None = None
    background: str | None = None
    gender: str | None = None
    age: str | None = None


class SettingCreateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    name: str = Field(..., min_length=1)
    setting_type: str = "other"
    description: str = ""
    parent_id: str | None = None


class SettingUpdateRequest(BaseModel):
    model_config = {"extra": "forbid"}

    name: str | None = None
    setting_type: str | None = None
    description: str | None = None
    parent_id: str | None = None


def success_response(data):
    return {"code": 0, "message": "success", "data": data}


@router.get("/novels/{novel_id}/characters")
def list_characters(novel_id: str, service: BibleService = Depends(get_bible_service)):
    characters = service.list_characters(novel_id)
    return success_response([character_to_response(c) for c in characters])


@router.post("/novels/{novel_id}/characters")
def create_character(novel_id: str, req: CharacterCreateRequest, service: BibleService = Depends(get_bible_service)):
    character = service.create_character(
        novel_id=novel_id,
        name=req.name,
        role=req.role,
        description=req.description,
        personality=req.personality,
        appearance=req.appearance,
        background=req.background,
        gender=req.gender,
        age=req.age,
    )
    return success_response(character_to_response(character))


@router.put("/characters/{character_id}")
def update_character(
    character_id: str, req: CharacterUpdateRequest, service: BibleService = Depends(get_bible_service)
):
    update_data = req.model_dump(exclude_none=True)
    character = service.update_character(character_id, **update_data)
    return success_response(character_to_response(character))


@router.delete("/characters/{character_id}")
def delete_character(character_id: str, service: BibleService = Depends(get_bible_service)):
    result = service.delete_character(character_id)
    return success_response({"deleted": result})


@router.get("/novels/{novel_id}/settings")
def list_settings(
    novel_id: str,
    setting_type: str | None = Query(None),
    service: BibleService = Depends(get_bible_service),
):
    settings = service.list_settings(novel_id, setting_type=setting_type)
    return success_response([setting_to_response(s) for s in settings])


@router.post("/novels/{novel_id}/settings")
def create_setting(novel_id: str, req: SettingCreateRequest, service: BibleService = Depends(get_bible_service)):
    setting = service.create_setting(
        novel_id=novel_id,
        name=req.name,
        setting_type=req.setting_type,
        description=req.description,
        parent_id=req.parent_id,
    )
    return success_response(setting_to_response(setting))


@router.put("/settings/{setting_id}")
def update_setting(setting_id: str, req: SettingUpdateRequest, service: BibleService = Depends(get_bible_service)):
    update_data = req.model_dump(exclude_none=True)
    setting = service.update_setting(setting_id, **update_data)
    return success_response(setting_to_response(setting))


@router.delete("/settings/{setting_id}")
def delete_setting(setting_id: str, service: BibleService = Depends(get_bible_service)):
    result = service.delete_setting(setting_id)
    return success_response({"deleted": result})


def character_to_response(character: Character) -> dict:
    return {
        "id": character.id,
        "novel_id": character.novel_id,
        "name": character.name,
        "role": character.role,
        "description": character.description,
        "personality": character.personality,
        "appearance": character.appearance,
        "background": character.background,
        "gender": character.gender,
        "age": character.age,
        "created_at": character.created_at,
        "updated_at": character.updated_at,
    }


def setting_to_response(setting: WorldSetting) -> dict:
    return {
        "id": setting.id,
        "novel_id": setting.novel_id,
        "name": setting.name,
        "setting_type": setting.setting_type,
        "description": setting.description,
        "parent_id": setting.parent_id,
        "created_at": setting.created_at,
        "updated_at": setting.updated_at,
    }
