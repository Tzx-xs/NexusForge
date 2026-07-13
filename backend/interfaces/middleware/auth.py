"""API 认证中间件 — 基于 X-API-Key 的简单认证。

对于桌面应用场景（Tauri 壳），使用启动时自动生成的本地 API Key。
开发模式下（未设置 API_KEY）所有请求被允许通过。
"""
import os
import secrets

from fastapi import Request
from fastapi.responses import JSONResponse

# 不需要认证的路径前缀
EXCLUDED_PATHS: tuple[str, ...] = (
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
)

# 需要认证的路径前缀
PROTECTED_PREFIX: str = "/api/v1"

# M-04 修复：启动时一次性读取 API_KEY，避免每次请求都调用 os.getenv。
# 旧实现高并发下系统调用开销可观，且运行中被篡改环境变量难以审计。
# 安全实践：密钥应在进程启动时加载到内存，运行期不变。
_API_KEY_CACHED: str | None = None
_API_KEY_LOADED: bool = False


def _get_api_key() -> str:
    """惰性加载并缓存 API_KEY，仅首次调用时读取环境变量。"""
    global _API_KEY_CACHED, _API_KEY_LOADED
    if not _API_KEY_LOADED:
        _API_KEY_CACHED = os.getenv("API_KEY", "")
        _API_KEY_LOADED = True
    return _API_KEY_CACHED or ""


def reload_api_key() -> None:
    """强制重新加载 API_KEY（仅供测试或显式轮换密钥使用）。"""
    global _API_KEY_CACHED, _API_KEY_LOADED
    _API_KEY_CACHED = None
    _API_KEY_LOADED = False


async def auth_middleware(request: Request, call_next):
    """FastAPI 中间件：检查 X-API-Key 请求头。

    - 开发模式（API_KEY 未设置）：允许所有请求，跳过认证
    - 生产模式（API_KEY 已设置）：
      - 排除路径（/health, /docs, /redoc, /openapi.json）直接放行
      - 受保护路径（/api/v1/*）必须携带正确的 X-API-Key
      - 不在排除列表也不在受保护范围内的路径直接放行
    """
    api_key = _get_api_key()

    # 开发模式：未设置 API_KEY 时允许所有请求通过
    if not api_key:
        return await call_next(request)

    path = request.url.path

    # 排除路径直接放行
    for excluded in EXCLUDED_PATHS:
        if path == excluded or path.startswith(excluded):
            return await call_next(request)

    # 受保护路径需要认证
    if path.startswith(PROTECTED_PREFIX):
        request_key = request.headers.get("X-API-Key", "")
        if not secrets.compare_digest(request_key, api_key):
            return JSONResponse(
                status_code=401,
                content={"error_code": "E6001", "message": "未授权访问"},
            )

    # 其他路径直接放行
    return await call_next(request)
