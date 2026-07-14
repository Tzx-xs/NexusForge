import os
import sys
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from config.logging import get_logger, setup_logging
from config.settings import Settings, validate_config
from domain.shared.error_codes import ErrorCodeRegistry
from domain.shared.exceptions import DomainException
from interfaces.api.v1.agent import router as agent_router
from interfaces.api.v1.ai_invocation import router as ai_invocation_router
from interfaces.api.v1.autonomous import router as autonomous_router
from interfaces.api.v1.autopilot import router as autopilot_router
from interfaces.api.v1.bible import router as bible_router
from interfaces.api.v1.chapters import router as chapters_router
from interfaces.api.v1.checkpoint import router as checkpoint_router
from interfaces.api.v1.dag import router as dag_router
from interfaces.api.v1.export import router as export_router
from interfaces.api.v1.foreshadows import router as foreshadows_router
from interfaces.api.v1.governance import router as governance_router
from interfaces.api.v1.knowledge import router as knowledge_router
from interfaces.api.v1.memory import router as memory_router
from interfaces.api.v1.novels import router as novels_router
from interfaces.api.v1.quality import router as quality_router
from interfaces.api.v1.review import router as review_router
from interfaces.api.v1.review_tasks import router as review_tasks_router
from interfaces.api.v1.search import router as search_router
from interfaces.api.v1.settings import router as settings_router
from interfaces.api.v1.snapshots import router as snapshots_router
from interfaces.api.v1.stats_legacy import router as stats_legacy_router
from interfaces.api.v1.storylines import router as storylines_router
from interfaces.api.v1.voice import router as voice_router
from interfaces.api.v1.worldview import router as worldview_router
from interfaces.container import Container
from interfaces.middleware.auth import auth_middleware

setup_logging()
logger = get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting XingYuanBi application...")

    warnings = validate_config()
    for w in warnings:
        logger.warning("Config warning: %s", w)

    container = Container.get_instance()
    container.db.init_db()
    logger.info("Database initialized")
    container.setting_repo.init_default_settings()
    logger.info("Default settings loaded")
    logger.info("Application startup complete")
    yield
    logger.info("Application shutting down")


settings = Settings.get_instance()

app = FastAPI(
    title="星渊笔 API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
    max_age=86400,
)

# API 认证中间件 — 保护 /api/v1/* 端点
app.middleware("http")(auth_middleware)


# 请求追踪中间件 — 生成/读取 X-Request-ID，注入日志上下文
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


# H-03 修复：移除 script-src 'unsafe-inline'，Vite 构建后的 Vue 3 生产包不需要内联脚本。
# connect-src 收紧为白名单：'self' + 主流 LLM Provider 端点 + 本地 Ollama/开发服务。
# 安全实践：CSP 是 XSS 的最后一道防线，script-src 必须严格限制为 'self'。
CSP_POLICY = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: blob:; "
    "font-src 'self' data:; "
    "connect-src 'self' https://api.openai.com https://api.anthropic.com "
    "http://localhost:11434 http://127.0.0.1:11434 "
    "ws://localhost:* ws://127.0.0.1:*; "
    "frame-ancestors 'self'; "
    "base-uri 'self'; "
    "form-action 'self'"
)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    if settings.is_production:
        response.headers["Content-Security-Policy"] = CSP_POLICY
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    else:
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if request.url.path.endswith(".html") or request.url.path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


# M-22: ERROR_STATUS_MAP 从 ErrorCodeRegistry 集中查询，消除重复定义
ERROR_STATUS_MAP = ErrorCodeRegistry.to_http_status_map()


@app.exception_handler(DomainException)
async def domain_exception_handler(request: Request, exc: DomainException):
    logger.warning("Domain exception: [%s] %s", exc.code, exc.message)
    status_code = ERROR_STATUS_MAP.get(exc.code, 500)
    return JSONResponse(
        status_code=status_code,
        content={
            "code": exc.code,
            "message": exc.message,
            "data": None,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    # 安全：日志中记录完整异常但不暴露给客户端，防止泄露内部实现细节
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    # 仅在开发环境且明确开启 debug 时返回详细错误信息
    if settings.debug and not settings.is_production:
        message = str(exc)
    else:
        message = "服务器内部错误，请稍后重试"
    return JSONResponse(
        status_code=500,
        content={
            "code": "E5000",
            "message": message,
            "data": None,
        },
    )


@app.get("/health")
def health_check():
    return {"code": 0, "message": "success", "data": {"status": "ok"}}


app.include_router(novels_router)
app.include_router(chapters_router)
app.include_router(bible_router)
app.include_router(review_router)
app.include_router(review_tasks_router)
app.include_router(settings_router)
app.include_router(memory_router)
app.include_router(knowledge_router)
app.include_router(foreshadows_router)
app.include_router(quality_router)
app.include_router(voice_router)
app.include_router(autonomous_router)
app.include_router(autopilot_router)
app.include_router(agent_router)
app.include_router(storylines_router)
app.include_router(worldview_router)
app.include_router(snapshots_router)
app.include_router(export_router)
app.include_router(search_router)
app.include_router(stats_legacy_router)
# NexusForge 新增端点
app.include_router(dag_router)
app.include_router(governance_router)
app.include_router(checkpoint_router)
app.include_router(ai_invocation_router)

# 前端静态文件目录解析
# - PyInstaller 冻结模式：exe 同级的 frontend/dist
# - 开发模式：优先 frontend/dist，回退根目录 dist/
if getattr(sys, "frozen", False):
    _frontend_dist = os.path.join(os.path.dirname(sys.executable), "frontend", "dist")
else:
    _root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    _frontend_dist = os.path.join(_root, "frontend", "dist")
    if not os.path.isdir(_frontend_dist):
        _frontend_dist = os.path.join(_root, "dist")
if os.path.isdir(_frontend_dist):
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="frontend")
    logger.info("Static files mounted from %s", _frontend_dist)
