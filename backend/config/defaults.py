import os

DEFAULT_APP_ENV: str = "production"
# M-01 修复：桌面应用默认绑定 127.0.0.1，避免暴露到局域网。
# 需要外部访问时显式设置 APP_HOST=0.0.0.0。
# 安全实践：本地服务默认仅监听回环地址，对外暴露必须是显式行为。
DEFAULT_APP_HOST: str = "127.0.0.1"
DEFAULT_APP_PORT: int = 8000
DEFAULT_DEBUG: bool = False

DEFAULT_DATABASE_URL: str = "sqlite:///./data/xingyuanbi.db"
DB_PATH: str = "data/xingyuanbi.db"

DEFAULT_LLM_PROVIDER: str = "ollama"
DEFAULT_BASE_URL: str = ""
DEFAULT_MODEL: str = ""
DEFAULT_TEMPERATURE: float = 0.7
DEFAULT_MAX_TOKENS: int = 4096
DEFAULT_TOP_P: float = 0.9
DEFAULT_LLM_TIMEOUT: int = 120
DEFAULT_LLM_TIMEOUT_RETRIES: int = 2
DEFAULT_LLM_SERVER_ERROR_RETRIES: int = 2
DEFAULT_LLM_RATE_LIMIT_RETRIES: int = 3
DEFAULT_MAX_TOOL_CALLS: int = 5

DEFAULT_GENERATION_MAX_RETRIES: int = 2
DEFAULT_GENERATION_STREAMING: bool = True
DEFAULT_OUTLINE_TARGET_WORDS: int = 500
DEFAULT_CONTENT_TARGET_WORDS: int = 2000

DEFAULT_LOG_LEVEL: str = "info"
DEFAULT_LOG_FILE: str = "./logs/app.log"

DEFAULT_CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:1420", "tauri://localhost"]

DEFAULT_NOVEL_GENRES: list[str] = ["玄幻", "都市", "科幻", "武侠", "仙侠", "历史", "悬疑", "言情"]
CHAPTER_STATUS: list[str] = ["draft", "planned", "generated", "reviewed"]
GRADES: list[str] = ["S", "A", "B", "C", "D"]
SETTING_TYPES: list[str] = ["geography", "faction", "rule", "history", "other"]
CHARACTER_ROLES: list[str] = ["主角", "配角", "反派", "龙套"]

# ChromaDB 生产模式配置
CHROMA_HOST: str = os.getenv("CHROMA_HOST", "")
CHROMA_PORT: int = int(os.getenv("CHROMA_PORT", "0"))

# SQLite 配置
SQLITE_BUSY_TIMEOUT: int = 30000
