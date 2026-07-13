from config.defaults import DEFAULT_LLM_TIMEOUT, DEFAULT_TOP_P
from config.settings import Settings
from domain.shared.exceptions import DomainException

from .base_provider import BaseProvider
from .llm_client import LLMClient
from .providers.anthropic_provider import AnthropicProvider
from .providers.local_provider import LocalProvider
from .providers.ollama_provider import OllamaProvider
from .providers.openai_provider import OpenAIProvider

PROVIDER_MAP = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "ollama": OllamaProvider,
    # 保留 local 作为开发/零配置兜底，但前端不再暴露
    "local": LocalProvider,
}


def create_provider(settings: Settings) -> BaseProvider:
    provider_name = settings.llm_provider.lower()
    provider_cls = PROVIDER_MAP.get(provider_name)

    if provider_cls is None:
        raise DomainException(
            code="E3001",
            message=f"Provider '{provider_name}' 暂未实现，请使用 'openai'、'anthropic' 或 'ollama'",
        )

    return provider_cls(  # type: ignore[abstract]
        api_key=settings.api_key,
        base_url=settings.api_base_url,
        model=settings.default_model,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
        top_p=settings.top_p,
        timeout=settings.llm_timeout,
    )


def create_llm_client(settings: Settings) -> LLMClient:
    provider = create_provider(settings)
    return LLMClient(provider)


def is_llm_configured(provider: BaseProvider) -> bool:
    """检查 Provider 是否已配置可用凭据/地址。

    - local: 开发兜底，视为已配置
    - ollama: 需要 base_url 与 model
    - openai / anthropic: 需要 api_key、base_url 与 model
    """
    name = getattr(provider, "name", "")
    api_key = (getattr(provider, "api_key", "") or "").strip()
    base_url = (getattr(provider, "base_url", "") or "").strip()
    model = (getattr(provider, "model", "") or "").strip()

    if name == "local":
        return True
    if name == "ollama":
        return bool(base_url and model)
    if name in ("openai", "anthropic"):
        return bool(api_key and base_url and model)
    # 未知 provider，保守认为未配置
    return bool(api_key or base_url)


def create_llm_client_from_dict(config: dict) -> LLMClient:
    """从数据库设置字典构建 LLM 客户端（供运行时重载使用）。

    config 键：ai_provider / api_key / api_base_url / default_model /
    temperature / max_tokens
    """
    provider_name = str(config.get("ai_provider", "ollama")).lower()
    provider_cls = PROVIDER_MAP.get(provider_name)
    if provider_cls is None:
        raise DomainException(
            code="E3001",
            message=f"Provider '{provider_name}' 暂未实现，请使用 'openai'、'anthropic' 或 'ollama'",
        )

    def _to_float(val, default: float) -> float:
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    def _to_int(val, default: int) -> int:
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    return LLMClient(
        provider_cls(  # type: ignore[abstract]
            api_key=config.get("api_key", ""),
            base_url=config.get("api_base_url", ""),
            model=config.get("default_model", ""),
            temperature=_to_float(config.get("temperature"), 0.7),
            max_tokens=_to_int(config.get("max_tokens"), 4096),
            top_p=DEFAULT_TOP_P,
            timeout=DEFAULT_LLM_TIMEOUT,
        )
    )
