"""速率限制中间件 — 基于 IP 的内存级令牌桶算法。

- RateLimiter: 令牌桶实现，纯内存，零外部依赖
- create_rate_limit_middleware: 通用 API 限流（默认 30 req/min）
- create_generation_rate_limit_middleware: 生成端点限流（默认 5 req/min）
- generation_rate_limit_dependency: 生成端点的 FastAPI Depends 限流依赖
"""
import logging
import os
import threading
import time
from collections import defaultdict

from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# M-05 修复：仅当来源 IP 在信任代理列表时才解析 X-Forwarded-For。
# 旧实现直接信任 XFF 头，攻击者可伪造不同 IP 绕过限流。
# 安全实践：XFF 必须基于可信反向代理链路，不可信端应使用 request.client.host。
_TRUSTED_PROXIES: set[str] = {
    ip.strip() for ip in os.getenv("TRUSTED_PROXIES", "127.0.0.1,::1").split(",") if ip.strip()
}


class RateLimiter:
    """基于 IP 的令牌桶限流器。

    每个 IP 拥有独立的令牌桶：
    - 桶容量 = max_tokens（burst 能力）
    - 每秒补充 rate / 60 个令牌
    - 每次请求消耗 1 个令牌
    """

    def __init__(self, requests_per_minute: int = 30, burst_multiplier: float = 1.5):
        self.rate = requests_per_minute / 60.0  # tokens per second
        self.max_tokens = int(requests_per_minute * burst_multiplier)
        self._buckets: dict[str, float] = defaultdict(lambda: self.max_tokens)
        self._last_refill: dict[str, float] = defaultdict(time.time)

    def _refill(self, ip: str) -> None:
        now = time.time()
        elapsed = now - self._last_refill[ip]
        if elapsed > 0:
            self._buckets[ip] = min(
                self.max_tokens,
                self._buckets[ip] + elapsed * self.rate,
            )
        self._last_refill[ip] = now

    def allow(self, ip: str) -> bool:
        """检查是否允许请求，消耗 1 个令牌。"""
        self._refill(ip)
        if self._buckets[ip] >= 1.0:
            self._buckets[ip] -= 1.0
            return True
        return False

    def cleanup_expired(self, max_idle_seconds: int = 1800) -> None:
        """清理长时间未活动的 IP 记录，防止内存泄漏。"""
        now = time.time()
        expired = [ip for ip, t in self._last_refill.items() if now - t > max_idle_seconds]
        for ip in expired:
            self._buckets.pop(ip, None)
            self._last_refill.pop(ip, None)


# L-04 修复：移除每个 RateLimiter 实例启动独立守护线程的旧实现。
# 旧实现 3 个全局实例会启动 3 个线程，资源浪费且无统一生命周期管理。
# 安全实践：后台任务应在应用 lifespan 中集中启动，便于审计与关闭。
_CLEANUP_THREAD_STARTED: bool = False
_CLEANUP_LOCK = threading.Lock()
_ALL_LIMITERS: list = []


def _ensure_cleanup_thread() -> None:
    """启动单一清理线程，遍历所有注册的限流器清理过期 IP。"""
    global _CLEANUP_THREAD_STARTED
    import threading

    with _CLEANUP_LOCK:
        if _CLEANUP_THREAD_STARTED:
            return
        _CLEANUP_THREAD_STARTED = True

        def _cleanup():
            while True:
                time.sleep(300)  # 5 分钟
                for limiter in list(_ALL_LIMITERS):
                    try:
                        limiter.cleanup_expired()
                    except Exception as e:
                        logger.warning("limiter cleanup 失败: %s", e)

        t = threading.Thread(target=_cleanup, daemon=True)
        t.start()


def _register_limiter(limiter: RateLimiter) -> RateLimiter:
    """注册限流器到全局清理任务，并确保清理线程已启动。"""
    _ALL_LIMITERS.append(limiter)
    _ensure_cleanup_thread()
    return limiter


# 全局限流器实例（懒初始化）
_default_limiter: RateLimiter | None = None
_generation_limiter: RateLimiter | None = None


def _get_default_limiter() -> RateLimiter:
    global _default_limiter
    if _default_limiter is None:
        _default_limiter = _register_limiter(RateLimiter(requests_per_minute=30))
    return _default_limiter


def _get_generation_limiter() -> RateLimiter:
    global _generation_limiter
    if _generation_limiter is None:
        _generation_limiter = _register_limiter(RateLimiter(requests_per_minute=5))
    return _generation_limiter


def _get_client_ip(request: Request) -> str:
    """获取客户端 IP，仅在可信代理来源时解析 X-Forwarded-For。

    安全实践：直接信任 XFF 头可被伪造绕过限流。
    仅当 request.client.host 在 TRUSTED_PROXIES 时才采用 XFF 的最左一段。
    """
    # 取真实 TCP 连接对端 IP
    peer_ip = "127.0.0.1"
    client = getattr(request, "client", None)
    if client is not None:
        peer_ip = client.host if hasattr(client, "host") else str(client)

    # 仅信任来自反向代理的 XFF
    if peer_ip in _TRUSTED_PROXIES:
        forwarded = request.headers.get("X-Forwarded-For", "")
        if forwarded:
            # 取最左侧的客户端 IP（最接近真实用户）
            return forwarded.split(",")[0].strip() or peer_ip
    return peer_ip


def create_rate_limit_middleware(requests_per_minute: int = 30):
    """创建通用 API 限流中间件工厂函数。

    使用方式：
        app.middleware("http")(create_rate_limit_middleware(30))
    """
    limiter = RateLimiter(requests_per_minute=requests_per_minute)

    async def middleware(request: Request, call_next):
        ip = _get_client_ip(request)
        if not limiter.allow(ip):
            return JSONResponse(
                status_code=429,
                content={"error_code": "E6002", "message": "请求过于频繁，请稍后再试"},
            )
        return await call_next(request)

    return middleware


def create_generation_rate_limit_middleware(requests_per_minute: int = 5):
    """创建生成端点（SSE）专用限流中间件工厂函数。

    使用方式：
        app.middleware("http")(create_generation_rate_limit_middleware(5))
    """
    limiter = RateLimiter(requests_per_minute=requests_per_minute)

    async def middleware(request: Request, call_next):
        ip = _get_client_ip(request)
        if not limiter.allow(ip):
            return JSONResponse(
                status_code=429,
                content={"error_code": "E6002", "message": "请求过于频繁，请稍后再试"},
            )
        return await call_next(request)

    return middleware


# ---- FastAPI Depends 风格的限流依赖 ----
# 用于在特定路由上直接注入，比全局中间件更精确

_generation_dep_limiter: RateLimiter | None = None


def _get_generation_dep_limiter() -> RateLimiter:
    global _generation_dep_limiter
    if _generation_dep_limiter is None:
        _generation_dep_limiter = _register_limiter(RateLimiter(requests_per_minute=5))
    return _generation_dep_limiter


async def generation_rate_limit_dependency(request: Request):
    """FastAPI Depends：生成端点限流（5 req/min）。

    使用方式：
        @router.post("/some-endpoint")
        async def handler(_: None = Depends(generation_rate_limit_dependency)):
            ...
    """
    from fastapi import HTTPException

    ip = _get_client_ip(request)
    limiter = _get_generation_dep_limiter()
    if not limiter.allow(ip):
        raise HTTPException(
            status_code=429,
            detail={"error_code": "E6002", "message": "请求过于频繁，请稍后再试"},
        )
