import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from application.services.settings_service import SettingsService
from infrastructure.crypto import mask_api_key
from infrastructure.validators import validate_api_base_url
from interfaces.container import Container
from interfaces.dependencies import get_settings_service
from interfaces.utils.response import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


class SettingsUpdateRequest(BaseModel):
    model_config = {"extra": "ignore"}

    ai_provider: str | None = None
    default_model: str | None = None
    api_base_url: str | None = None
    api_key: str | None = None
    temperature: str | None = None
    max_tokens: str | None = None
    target_words: str | None = None
    auto_review: str | None = None
    review_threshold: str | None = None
    max_retries: str | None = None
    language: str | None = None
    theme: str | None = None


@router.get("")
def get_settings(service: SettingsService = Depends(get_settings_service)):
    settings = service.get_all()
    # 脱敏 api_key，防止 API 响应泄露原始密钥
    if "api_key" in settings and settings["api_key"]:
        settings["api_key"] = mask_api_key(settings["api_key"])
    return success_response(settings)


@router.put("")
def update_settings(req: SettingsUpdateRequest, service: SettingsService = Depends(get_settings_service)):
    update_data = req.model_dump(exclude_none=True)
    # SSRF 防护：校验 api_base_url
    if "api_base_url" in update_data and update_data["api_base_url"]:
        if not validate_api_base_url(update_data["api_base_url"]):
            raise HTTPException(
                status_code=400,
                detail={"error_code": "E3001", "message": "api_base_url 不合法：禁止使用内网地址，请使用 HTTPS 公网地址"},
            )
    service.batch_update(update_data)
    # AI 配置变更后即时重载 LLM 客户端，使 UI 设置真正生效
    reload_ok = Container.get_instance().reload_llm_from_db()
    if not reload_ok:
        return {"code": 1, "message": "AI 配置已保存但重载 LLM 客户端失败，请检查配置后重试或重启服务", "data": service.get_all()}
    return success_response(service.get_all())


@router.post("/reset")
def reset_settings(service: SettingsService = Depends(get_settings_service)):
    service.reset_to_defaults()
    reload_ok = Container.get_instance().reload_llm_from_db()
    if not reload_ok:
        return {"code": 1, "message": "设置已重置但重载 LLM 客户端失败，请重新配置 AI 参数", "data": service.get_all()}
    return success_response(service.get_all())


@router.post("/test-connection")
async def test_connection():
    """测试当前 LLM 配置是否可用（审查报告 5.2）"""
    container = Container.get_instance()
    client = container.llm_client
    if client is None:
        return {"code": 1, "message": "LLM 客户端未初始化，请先配置 AI 参数", "data": {"ok": False}}
    try:
        response = await client.chat('请回复"连接成功"四个字。', temperature=0.0, max_tokens=20)
        return success_response({"ok": True, "response": response})
    except Exception:
        logger.exception("LLM 连接测试失败")
        return {"code": 1, "message": "操作失败，请稍后重试", "data": {"ok": False}}
