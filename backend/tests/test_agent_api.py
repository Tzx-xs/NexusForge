"""Sprint 4.1: 补全 SSE 端点测试。

为 backend/interfaces/api/v1/agent.py 的 4 个路由补测试:
- POST /api/v1/agent/chat (SSE 流式)
- GET /api/v1/agent/conversations (列表)
- GET /api/v1/agent/conversations/{id} (详情+消息)
- DELETE /api/v1/agent/conversations/{id} (删除)

策略:创建独立 FastAPI app(只挂载 agent router),用 dependency_overrides
覆盖 get_writing_agent 与 get_conversation_repo,完全避开 Container lifespan。
"""

import os
import sys
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from domain.agent import Conversation, Message  # noqa: E402
from interfaces.api.v1.agent import router as agent_router  # noqa: E402
from interfaces.dependencies import get_conversation_repo, get_writing_agent  # noqa: E402

# ====================================================================
# 测试桩件
# ====================================================================


def _make_conv(conv_id: str = "conv_1", novel_id: str | None = "n1", title: str = "测试会话") -> Conversation:
    return Conversation(id=conv_id, novel_id=novel_id, title=title, created_at=1000.0, updated_at=1000.0)


def _make_msg(msg_id: str = "msg_1", role: str = "user", content: str = "你好") -> Message:
    return Message(
        id=msg_id,
        conversation_id="conv_1",
        role=role,
        content=content,
        created_at=1000.0,
    )


def _build_app(repo: Any, agent: Any) -> FastAPI:
    """构造独立测试 app,只挂载 agent router,避开 Container lifespan。"""
    app = FastAPI()
    app.include_router(agent_router)
    app.dependency_overrides[get_conversation_repo] = lambda: repo
    app.dependency_overrides[get_writing_agent] = lambda: agent
    return app


# ====================================================================
# Fixtures
# ====================================================================


@pytest.fixture
def repo():
    """默认 mock repo:空列表,会话不存在,删除成功。"""
    r = MagicMock()
    r.list_conversations = MagicMock(return_value=[])
    r.get_conversation = MagicMock(return_value=None)
    r.list_messages = MagicMock(return_value=[])
    r.delete_conversation = MagicMock(return_value=True)
    return r


@pytest.fixture
def agent():
    """默认 mock agent:chat 返回空流。"""
    a = MagicMock()

    async def _empty_chat(*args, **kwargs):
        return
        yield  # noqa: E701 - 让函数成为 async generator

    a.chat = MagicMock(side_effect=_empty_chat)
    return a


@pytest.fixture
def client(repo, agent):
    app = _build_app(repo, agent)
    with TestClient(app) as c:
        yield c


# ====================================================================
# GET /api/v1/agent/conversations - 列表
# ====================================================================


def test_list_conversations_returns_200_with_empty_list(client, repo):
    repo.list_conversations = MagicMock(return_value=[])

    resp = client.get("/api/v1/agent/conversations?novel_id=n1")

    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"] == []
    repo.list_conversations.assert_called_once()


def test_list_conversations_returns_200_with_conversations(client, repo):
    conv = _make_conv("c1", "n1", "测试")
    repo.list_conversations = MagicMock(return_value=[conv])

    resp = client.get("/api/v1/agent/conversations?novel_id=n1")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["data"]) == 1
    assert body["data"][0]["id"] == "c1"
    assert body["data"][0]["title"] == "测试"


# ====================================================================
# POST /api/v1/agent/chat - SSE 流式
# ====================================================================


def test_agent_chat_without_message_returns_422(client):
    resp = client.post("/api/v1/agent/chat", json={})

    assert resp.status_code == 422


def test_agent_chat_returns_text_event_stream_with_5_event_types(client, agent):
    async def _mock_chat(*args, **kwargs):
        yield "tool_call", {"tool": "stub", "args": {}}
        yield "tool_result", {"tool": "stub", "success": True, "data": {}}
        yield "token", {"delta": "你好"}
        yield "complete", {"conversation_id": "c1", "message_id": "m1"}

    agent.chat = MagicMock(side_effect=_mock_chat)

    resp = client.post("/api/v1/agent/chat", json={"message": "hi", "novel_id": "n1"})

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")

    text = resp.text
    assert "event: tool_call" in text
    assert "event: tool_result" in text
    assert "event: token" in text
    assert "event: complete" in text
    # 验证 token 事件的 payload 包含 delta
    assert '"delta"' in text and "你好" in text
    # 验证 complete 事件的 payload 包含 conversation_id
    assert '"conversation_id"' in text and "c1" in text


def test_agent_chat_exception_yields_error_event(client, agent):
    async def _mock_chat(*args, **kwargs):
        raise RuntimeError("test error")
        yield  # noqa: E701 - 让函数成为 async generator

    agent.chat = MagicMock(side_effect=_mock_chat)

    resp = client.post("/api/v1/agent/chat", json={"message": "hi"})

    # 注意:StreamingResponse 已开始流式输出,异常被 agent_chat 端点内部 try/except 捕获
    assert resp.status_code == 200
    assert "event: error" in resp.text
    # T01: sanitize_error() 在生产模式下脱敏为 "服务器内部错误"
    assert "服务器内部错误" in resp.text


# ====================================================================
# GET /api/v1/agent/conversations/{id} - 详情+消息
# ====================================================================


def test_get_conversation_returns_200_with_conversation_and_messages(client, repo):
    conv = _make_conv("c1", "n1", "测试")
    msg = _make_msg("m1", "user", "你好")
    repo.get_conversation = MagicMock(return_value=conv)
    repo.list_messages = MagicMock(return_value=[msg])

    resp = client.get("/api/v1/agent/conversations/c1")

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["conversation"]["id"] == "c1"
    assert len(body["data"]["messages"]) == 1
    assert body["data"]["messages"][0]["content"] == "你好"
    repo.get_conversation.assert_called_once_with("c1")
    repo.list_messages.assert_called_once_with("c1")


def test_get_conversation_returns_404_when_not_found(client, repo):
    repo.get_conversation = MagicMock(return_value=None)

    resp = client.get("/api/v1/agent/conversations/missing")

    assert resp.status_code == 404


# ====================================================================
# DELETE /api/v1/agent/conversations/{id} - 删除
# ====================================================================


def test_delete_conversation_returns_200_with_deleted_true(client, repo):
    repo.delete_conversation = MagicMock(return_value=True)

    resp = client.delete("/api/v1/agent/conversations/c1")

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["deleted"] is True
    repo.delete_conversation.assert_called_once_with("c1")


def test_delete_conversation_returns_404_when_not_found(client, repo):
    repo.delete_conversation = MagicMock(return_value=False)

    resp = client.delete("/api/v1/agent/conversations/missing")

    assert resp.status_code == 404
