"""Sprint 5.1: AI 写作建议 SSE 端点测试。

为新增的 POST /api/v1/chapters/{chapter_id}/ai-suggest 端点补测试:
- 章节存在时返回 200 + SSE 流(token/complete 事件)
- 章节不存在返回 404
- 章节内容为空返回 400
- LLM 异常 yield error 事件
- 多 token 事件正确拼接
- 验证章节内容被读取(传入 LLM)

策略:创建独立 FastAPI app(只挂载 chapters router),用 dependency_overrides
覆盖 get_chapter_service,完全避开 Container lifespan。
"""

import json
import os
import sys
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from domain.chapter import Chapter  # noqa: E402
from domain.shared.exceptions import ChapterNotFoundException  # noqa: E402
from interfaces.api.v1.chapters import router as chapters_router  # noqa: E402
from interfaces.dependencies import get_chapter_service  # noqa: E402

# ====================================================================
# 测试桩件
# ====================================================================


def _make_chapter(chapter_id: str = "c1", content: str = "章节正文内容") -> Chapter:
    """构造测试用 Chapter 实体。"""
    return Chapter(
        id=chapter_id,
        novel_id="n1",
        number=1,
        title="第1章",
        content=content,
        status="completed",
        word_count=len(content),
    )


def _build_app(service: Any) -> FastAPI:
    """构造独立测试 app,只挂载 chapters router,避开 Container lifespan。"""
    app = FastAPI()
    app.include_router(chapters_router)
    app.dependency_overrides[get_chapter_service] = lambda: service
    return app


def parse_sse_events(text: str) -> list[dict]:
    """解析 SSE 文本流为事件列表。"""
    events = []
    for block in text.strip().split("\n\n"):
        if not block.strip():
            continue
        event: dict = {}
        for line in block.split("\n"):
            if line.startswith("event: "):
                event["event"] = line[7:]
            elif line.startswith("data: "):
                event["data"] = line[6:]
        if event:
            events.append(event)
    return events


# ====================================================================
# Fixtures
# ====================================================================


@pytest.fixture
def service_with_chapter():
    """mock service:章节存在,content 非空,流式返回 token。"""
    s = MagicMock()
    s.get_chapter = MagicMock(return_value=_make_chapter())

    async def _stream(chapter_id):
        yield "token", "建议1"
        yield "token", "建议2"
        yield "complete", {"chapter_id": "c1"}

    s.generate_ai_suggest_stream = MagicMock(side_effect=_stream)
    return s


@pytest.fixture
def service_no_chapter():
    """mock service:章节不存在。"""
    s = MagicMock()
    s.get_chapter = MagicMock(side_effect=ChapterNotFoundException())
    return s


@pytest.fixture
def service_empty_content():
    """mock service:章节内容为空。"""
    s = MagicMock()
    s.get_chapter = MagicMock(return_value=_make_chapter(content=""))
    return s


@pytest.fixture
def service_with_error_stream():
    """mock service:LLM 异常时 yield error 事件。"""
    s = MagicMock()
    s.get_chapter = MagicMock(return_value=_make_chapter())

    async def _stream_with_error(chapter_id):
        yield "token", "部分内容"
        yield "error", "LLM 调用失败"

    s.generate_ai_suggest_stream = MagicMock(side_effect=_stream_with_error)
    return s


@pytest.fixture
def client_with_chapter(service_with_chapter):
    app = _build_app(service_with_chapter)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client_no_chapter(service_no_chapter):
    app = _build_app(service_no_chapter)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client_empty_content(service_empty_content):
    app = _build_app(service_empty_content)
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client_with_error_stream(service_with_error_stream):
    app = _build_app(service_with_error_stream)
    with TestClient(app) as c:
        yield c


# ====================================================================
# 测试用例
# ====================================================================


def test_ai_suggest_returns_text_event_stream(client_with_chapter):
    """1. 章节存在时返回 200 + SSE 流,包含 token/complete 事件。"""
    response = client_with_chapter.post("/api/v1/chapters/c1/ai-suggest")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    events = parse_sse_events(response.text)
    event_types = [e["event"] for e in events]
    assert "token" in event_types
    assert "complete" in event_types


def test_ai_suggest_returns_404_when_chapter_not_found(client_no_chapter):
    """2. 章节不存在抛 404。"""
    response = client_no_chapter.post("/api/v1/chapters/notexist/ai-suggest")
    assert response.status_code == 404


def test_ai_suggest_passes_chapter_content_to_llm(service_with_chapter, client_with_chapter):
    """3. 验证 service.get_chapter 被调用(确保章节内容被读取后传入 LLM)。"""
    client_with_chapter.post("/api/v1/chapters/c1/ai-suggest")
    service_with_chapter.get_chapter.assert_called_with("c1")


def test_ai_suggest_empty_content_returns_400(client_empty_content):
    """4. 章节内容为空时返回 400。"""
    response = client_empty_content.post("/api/v1/chapters/c1/ai-suggest")
    assert response.status_code == 400


def test_ai_suggest_llm_failure_yields_error_event(client_with_error_stream):
    """5. LLM 异常时 yield error 事件。"""
    response = client_with_error_stream.post("/api/v1/chapters/c1/ai-suggest")
    assert response.status_code == 200  # SSE 已启动,返回 200
    events = parse_sse_events(response.text)
    event_types = [e["event"] for e in events]
    assert "error" in event_types


def test_ai_suggest_streaming_tokens_concatenated(client_with_chapter):
    """6. 多 token 事件正确拼接。"""
    response = client_with_chapter.post("/api/v1/chapters/c1/ai-suggest")
    events = parse_sse_events(response.text)
    token_events = [e for e in events if e["event"] == "token"]
    assert len(token_events) == 2
    # 验证 data 中有 delta 字段
    deltas = []
    for te in token_events:
        data = json.loads(te["data"])
        assert "delta" in data
        deltas.append(data["delta"])
    assert "".join(deltas) == "建议1建议2"
