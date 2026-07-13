import os
from typing import ClassVar, Optional

from .defaults import (
    CHROMA_HOST,
    CHROMA_PORT,
    DEFAULT_APP_ENV,
    DEFAULT_APP_HOST,
    DEFAULT_APP_PORT,
    DEFAULT_BASE_URL,
    DEFAULT_CONTENT_TARGET_WORDS,
    DEFAULT_CORS_ORIGINS,
    DEFAULT_DATABASE_URL,
    DEFAULT_DEBUG,
    DEFAULT_GENERATION_MAX_RETRIES,
    DEFAULT_GENERATION_STREAMING,
    DEFAULT_LLM_PROVIDER,
    DEFAULT_LLM_TIMEOUT,
    DEFAULT_LOG_FILE,
    DEFAULT_LOG_LEVEL,
    DEFAULT_MAX_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_OUTLINE_TARGET_WORDS,
    DEFAULT_TEMPERATURE,
    DEFAULT_TOP_P,
    SQLITE_BUSY_TIMEOUT,
)

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass


def _get_env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def _get_env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except (ValueError, TypeError):
        return default


def _get_env_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)))
    except (ValueError, TypeError):
        return default


def _get_env_bool(key: str, default: bool) -> bool:
    val = os.getenv(key, str(default)).lower()
    return val in ("true", "1", "yes", "on")


def _resolve_prod_data_dir() -> str | None:
    """解析 Tauri 桌面端注入的生产数据目录。

    优先级：NEXUSFORGE_PROD_DATA_DIR > PLOTPILOT_PROD_DATA_DIR > AITEXT_PROD_DATA_DIR
    目录不存在时自动创建。
    """
    for env_key in ("NEXUSFORGE_PROD_DATA_DIR", "PLOTPILOT_PROD_DATA_DIR", "AITEXT_PROD_DATA_DIR"):
        val = os.getenv(env_key, "").strip()
        if val:
            try:
                os.makedirs(val, exist_ok=True)
                return val
            except OSError:
                continue
    return None


class Settings:
    app_env: str
    app_host: str
    app_port: int
    debug: bool

    database_url: str

    llm_provider: str
    api_key: str
    api_base_url: str
    default_model: str
    temperature: float
    max_tokens: int
    top_p: float
    llm_timeout: int

    generation_max_retries: int
    generation_streaming: bool
    outline_target_words: int
    content_target_words: int

    log_level: str
    log_file: str
    chroma_host: str
    chroma_port: int
    sqlite_busy_timeout: int

    cors_origins: list[str]

    _instance: ClassVar[Optional["Settings"]] = None

    def __init__(self) -> None:
        self.app_env = _get_env("APP_ENV", DEFAULT_APP_ENV)
        self.app_host = _get_env("APP_HOST", DEFAULT_APP_HOST)
        self.app_port = _get_env_int("APP_PORT", DEFAULT_APP_PORT)
        self.debug = _get_env_bool("DEBUG", DEFAULT_DEBUG)

        prod_data_dir = _resolve_prod_data_dir()

        db_url = _get_env("DATABASE_URL", DEFAULT_DATABASE_URL)
        if prod_data_dir and db_url.startswith("sqlite:///./"):
            db_path = db_url[len("sqlite:///./"):]
            self.database_url = f"sqlite:///{os.path.join(prod_data_dir, db_path)}"
            os.makedirs(os.path.dirname(os.path.join(prod_data_dir, db_path)), exist_ok=True)
        else:
            self.database_url = db_url

        self.llm_provider = _get_env("LLM_PROVIDER", DEFAULT_LLM_PROVIDER)
        self.api_key = _get_env("LLM_API_KEY", "")
        self.api_base_url = _get_env("LLM_BASE_URL", DEFAULT_BASE_URL)
        self.default_model = _get_env("LLM_MODEL", DEFAULT_MODEL)
        self.temperature = _get_env_float("LLM_TEMPERATURE", DEFAULT_TEMPERATURE)
        self.max_tokens = _get_env_int("LLM_MAX_TOKENS", DEFAULT_MAX_TOKENS)
        self.top_p = _get_env_float("LLM_TOP_P", DEFAULT_TOP_P)
        self.llm_timeout = _get_env_int("LLM_TIMEOUT", DEFAULT_LLM_TIMEOUT)

        self.generation_max_retries = _get_env_int("GENERATION_MAX_RETRIES", DEFAULT_GENERATION_MAX_RETRIES)
        self.generation_streaming = _get_env_bool("GENERATION_STREAMING", DEFAULT_GENERATION_STREAMING)
        self.outline_target_words = _get_env_int("OUTLINE_TARGET_WORDS", DEFAULT_OUTLINE_TARGET_WORDS)
        self.content_target_words = _get_env_int("CONTENT_TARGET_WORDS", DEFAULT_CONTENT_TARGET_WORDS)

        self.chroma_host = _get_env("CHROMA_HOST", CHROMA_HOST)
        self.chroma_port = _get_env_int("CHROMA_PORT", CHROMA_PORT)
        self.sqlite_busy_timeout = _get_env_int("SQLITE_BUSY_TIMEOUT", SQLITE_BUSY_TIMEOUT)

        self.log_level = _get_env("LOG_LEVEL", DEFAULT_LOG_LEVEL)
        log_file = _get_env("LOG_FILE", DEFAULT_LOG_FILE)
        if prod_data_dir and log_file.startswith("./"):
            self.log_file = os.path.join(prod_data_dir, log_file[2:])
            os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        else:
            self.log_file = log_file

        cors_raw = _get_env("CORS_ORIGINS", "")
        if cors_raw:
            self.cors_origins = [o.strip() for o in cors_raw.split(",") if o.strip()]
        elif self.app_env == "production":
            # 生产环境未显式配置 CORS_ORIGINS 时，默认仅允许 Tauri 桌面客户端源
            self.cors_origins = ["tauri://localhost"]
        else:
            self.cors_origins = list(DEFAULT_CORS_ORIGINS)

    @property
    def db_path(self) -> str:
        url = self.database_url
        if url.startswith("sqlite:///"):
            return url[10:]
        return url

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @classmethod
    def get_instance(cls) -> "Settings":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


def validate_config() -> list[str]:
    """启动时配置校验，返回告警列表（空列表表示全部通过）

    优先级规则：
    - DATABASE_URL 必须存在，否则抛 ConfigException
    - LLM_API_KEY / LLM_BASE_URL 缺失时仅告警（开发模式可零配置运行）
    """
    from domain.shared.exceptions import ConfigException

    warnings = []

    if not _get_env("DATABASE_URL", DEFAULT_DATABASE_URL):
        raise ConfigException("缺少必要配置: DATABASE_URL")

    if not _get_env("LLM_API_KEY", ""):
        warnings.append("LLM_API_KEY 未配置，LLM 生成功能不可用")
    if not _get_env("LLM_BASE_URL", DEFAULT_BASE_URL):
        warnings.append("LLM_BASE_URL 未配置，LLM 生成功能不可用")

    return warnings
