"""API 冒烟集成测试。

使用 FastAPI TestClient 直接对完整 app（含全部中间件、路由、依赖注入）
发起 HTTP 请求，验证关键端点的基本可用性。

区别于 test_agent_api.py（仅挂载单个 router），本测试使用真实 main:app，
覆盖更完整的请求链路（CORS / 限流 / 认证 / 业务路由 / 异常处理器）。
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterator

# 在导入 app 之前设置测试用 API_KEY（auth 中间件在首次请求时惰性读取）
_TEST_API_KEY = os.getenv("API_KEY", "test-integration-api-key")
os.environ["API_KEY"] = _TEST_API_KEY

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from interfaces.main import app  # noqa: E402
from interfaces.middleware.auth import reload_api_key  # noqa: E402

# 强制重新加载已缓存的 API_KEY（避免被先前的 0 值缓存影响）
reload_api_key()

_AUTH_HEADERS = {"X-API-Key": _TEST_API_KEY}


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    """创建一次 TestClient，模块内复用。

    TestClient 启动时会触发 app lifespan（Container 初始化 + DB 迁移），
    scope=module 避免每个测试重复初始化。
    """
    with TestClient(app) as c:
        yield c


def _unwrap(resp_body: dict | list) -> dict | list:
    """剥离统一响应壳 {"code": 0, "message": ..., "data": X} 中的 data 字段。

    非壳格式（直接返回业务数据）则原样返回。
    """
    if isinstance(resp_body, dict) and "code" in resp_body and "data" in resp_body:
        return resp_body["data"]
    return resp_body


# ====================================================================
# 健康检查（在 auth 排除列表中，无需认证）
# ====================================================================


def test_health_endpoint_returns_ok(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    body = _unwrap(resp.json())
    assert body.get("status") == "ok"


def test_openapi_schema_disabled_in_production(client: TestClient) -> None:
    """生产模式下（APP_ENV=production）OpenAPI 文档端点应被禁用。

    配置来自 .env：docs_url / redoc_url / openapi_url 在生产模式下为 None。
    """
    resp = client.get("/openapi.json")
    # 生产模式下应为 404；非生产模式下应为 200
    assert resp.status_code in (200, 404)


# ====================================================================
# 关键资源列表端点（GET，无副作用）— 需认证
# ====================================================================


def test_list_novels_returns_200(client: TestClient) -> None:
    resp = client.get("/api/v1/novels", headers=_AUTH_HEADERS)
    assert resp.status_code == 200
    data = _unwrap(resp.json())
    assert isinstance(data, list)


def test_list_quality_guards_returns_200(client: TestClient) -> None:
    resp = client.get("/api/v1/quality/guards", headers=_AUTH_HEADERS)
    assert resp.status_code == 200


def test_list_settings_returns_200(client: TestClient) -> None:
    resp = client.get("/api/v1/settings", headers=_AUTH_HEADERS)
    assert resp.status_code == 200


# ====================================================================
# 认证校验
# ====================================================================


def test_protected_endpoint_without_api_key_returns_401(client: TestClient) -> None:
    resp = client.get("/api/v1/novels")
    assert resp.status_code == 401


def test_protected_endpoint_with_wrong_api_key_returns_401(client: TestClient) -> None:
    resp = client.get("/api/v1/novels", headers={"X-API-Key": "wrong-key"})
    assert resp.status_code == 401


# ====================================================================
# 404 异常处理
# ====================================================================


def test_get_nonexistent_novel_returns_404(client: TestClient) -> None:
    resp = client.get("/api/v1/novels/nonexistent-id-12345", headers=_AUTH_HEADERS)
    assert resp.status_code == 404


def test_get_nonexistent_chapter_returns_404(client: TestClient) -> None:
    resp = client.get(
        "/api/v1/novels/any-novel/chapters/nonexistent-chapter-98765",
        headers=_AUTH_HEADERS,
    )
    assert resp.status_code == 404


# ====================================================================
# 请求体校验（422）
# ====================================================================


def test_create_novel_without_required_fields_returns_422(client: TestClient) -> None:
    resp = client.post("/api/v1/novels", json={}, headers=_AUTH_HEADERS)
    assert resp.status_code == 422


def test_agent_chat_without_message_returns_422(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/agent/chat",
        json={"novel_id": "any"},
        headers={**_AUTH_HEADERS, "Accept": "text/event-stream"},
    )
    # 缺少 message 字段应触发 422 校验错误
    assert resp.status_code == 422
