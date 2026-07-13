"""review_tasks 端点集成测试。"""
from __future__ import annotations

import os
import sys
from collections.abc import Iterator

_TEST_API_KEY = os.getenv("API_KEY", "test-review-task-key")
os.environ["API_KEY"] = _TEST_API_KEY

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from interfaces.main import app  # noqa: E402
from interfaces.middleware.auth import reload_api_key  # noqa: E402

reload_api_key()

_AUTH_HEADERS = {"X-API-Key": _TEST_API_KEY}


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    with TestClient(app) as c:
        yield c


def _unwrap(resp_body: dict) -> dict | list:
    if isinstance(resp_body, dict) and "code" in resp_body and "data" in resp_body:
        return resp_body["data"]
    return resp_body


def test_create_review_task(client: TestClient) -> None:
    resp = client.post(
        "/api/v1/reviews",
        json={"title": "审查第一章", "novel_id": "novel-1"},
        headers=_AUTH_HEADERS,
    )
    assert resp.status_code == 200
    data = _unwrap(resp.json())
    assert data["title"] == "审查第一章"
    assert data["novel_id"] == "novel-1"
    assert data["status"] == "pending"


def test_list_review_tasks(client: TestClient) -> None:
    resp = client.get("/api/v1/reviews", headers=_AUTH_HEADERS)
    assert resp.status_code == 200
    data = _unwrap(resp.json())
    assert isinstance(data["items"], list)
    assert data["total"] >= 1


def test_update_and_delete_review_task(client: TestClient) -> None:
    create_resp = client.post(
        "/api/v1/reviews",
        json={"title": "临时审查任务"},
        headers=_AUTH_HEADERS,
    )
    task_id = _unwrap(create_resp.json())["id"]

    update_resp = client.put(
        f"/api/v1/reviews/{task_id}",
        json={"status": "completed", "result": "通过"},
        headers=_AUTH_HEADERS,
    )
    assert update_resp.status_code == 200
    updated = _unwrap(update_resp.json())
    assert updated["status"] == "completed"
    assert updated["result"] == "通过"

    get_resp = client.get(f"/api/v1/reviews/{task_id}", headers=_AUTH_HEADERS)
    assert get_resp.status_code == 200
    assert _unwrap(get_resp.json())["id"] == task_id

    delete_resp = client.delete(f"/api/v1/reviews/{task_id}", headers=_AUTH_HEADERS)
    assert delete_resp.status_code == 200
    assert _unwrap(delete_resp.json())["deleted"] is True
