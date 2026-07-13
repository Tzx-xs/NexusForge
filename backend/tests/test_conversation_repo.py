import contextlib
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from domain.agent import Conversation, Message
from infrastructure.persistence.conversation_repo import ConversationRepository
from infrastructure.persistence.database import Database

# ====================================================================
# Fixtures
# ====================================================================


@pytest.fixture
def database():
    """使用临时文件 SQLite 数据库（每次 get_connection 都新建连接，
    :memory: 无法跨连接保留状态，因此用临时文件）"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = Database(path)
    db.init_db()
    yield db
    if os.path.exists(path):
        with contextlib.suppress(OSError):
            os.remove(path)


@pytest.fixture
def repo(database):
    return ConversationRepository(database)


# ====================================================================
# create_conversation
# ====================================================================


def test_create_conversation_returns_conversation_object(repo):
    conv = repo.create_conversation(novel_id="n1", title="测试会话")

    assert isinstance(conv, Conversation)
    assert conv.id
    assert len(conv.id) > 0
    assert conv.novel_id == "n1"
    assert conv.title == "测试会话"
    assert conv.created_at is not None
    assert conv.updated_at is not None


def test_create_conversation_default_values(repo):
    conv = repo.create_conversation()

    assert conv.novel_id is None
    assert conv.title == ""


def test_create_multiple_conversations_have_unique_ids(repo):
    c1 = repo.create_conversation(title="第一个")
    c2 = repo.create_conversation(title="第二个")

    assert c1.id != c2.id


# ====================================================================
# get_conversation
# ====================================================================


def test_get_conversation_returns_stored_conversation(repo):
    created = repo.create_conversation(novel_id="n1", title="查询测试")
    fetched = repo.get_conversation(created.id)

    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.novel_id == "n1"
    assert fetched.title == "查询测试"


def test_get_conversation_returns_none_for_missing(repo):
    assert repo.get_conversation("non_existent_id") is None


# ====================================================================
# list_conversations
# ====================================================================


def test_list_conversations_returns_all(repo):
    repo.create_conversation(novel_id="n1", title="a")
    repo.create_conversation(novel_id="n2", title="b")
    repo.create_conversation(novel_id="n1", title="c")

    convs = repo.list_conversations()
    assert len(convs) == 3


def test_list_conversations_filter_by_novel_id(repo):
    repo.create_conversation(novel_id="n1", title="a")
    repo.create_conversation(novel_id="n2", title="b")
    repo.create_conversation(novel_id="n1", title="c")

    filtered = repo.list_conversations(novel_id="n1")
    assert len(filtered) == 2
    for c in filtered:
        assert c.novel_id == "n1"


def test_list_conversations_respects_limit(repo):
    for i in range(5):
        repo.create_conversation(title=f"c{i}")

    convs = repo.list_conversations(limit=3)
    assert len(convs) == 3


def test_list_conversations_empty(repo):
    assert repo.list_conversations() == []


# ====================================================================
# add_message & list_messages
# ====================================================================


def test_add_message_returns_message_object(repo):
    conv = repo.create_conversation(novel_id="n1", title="t")
    msg = repo.add_message(
        conversation_id=conv.id,
        role="user",
        content="你好",
    )

    assert isinstance(msg, Message)
    assert msg.id
    assert msg.conversation_id == conv.id
    assert msg.role == "user"
    assert msg.content == "你好"
    assert msg.created_at is not None


def test_add_message_with_tool_metadata(repo):
    conv = repo.create_conversation(novel_id="n1", title="t")
    msg = repo.add_message(
        conversation_id=conv.id,
        role="assistant",
        content="已调用工具",
        tool_calls='{"tool": "stub", "args": {}}',
        tool_name="stub",
    )

    assert msg.tool_calls == '{"tool": "stub", "args": {}}'
    assert msg.tool_name == "stub"


def test_list_messages_returns_in_order(repo):
    conv = repo.create_conversation(novel_id="n1", title="t")
    repo.add_message(conversation_id=conv.id, role="user", content="第一条")
    repo.add_message(conversation_id=conv.id, role="assistant", content="第二条")
    repo.add_message(conversation_id=conv.id, role="user", content="第三条")

    msgs = repo.list_messages(conv.id)
    assert len(msgs) == 3
    assert msgs[0].content == "第一条"
    assert msgs[1].content == "第二条"
    assert msgs[2].content == "第三条"


def test_list_messages_empty_for_new_conversation(repo):
    conv = repo.create_conversation(title="空")
    msgs = repo.list_messages(conv.id)
    assert msgs == []


def test_list_messages_only_returns_messages_for_specified_conversation(repo):
    c1 = repo.create_conversation(title="c1")
    c2 = repo.create_conversation(title="c2")
    repo.add_message(conversation_id=c1.id, role="user", content="c1-msg")
    repo.add_message(conversation_id=c2.id, role="user", content="c2-msg")

    msgs_c1 = repo.list_messages(c1.id)
    msgs_c2 = repo.list_messages(c2.id)

    assert len(msgs_c1) == 1
    assert msgs_c1[0].content == "c1-msg"
    assert len(msgs_c2) == 1
    assert msgs_c2[0].content == "c2-msg"


def test_add_message_updates_conversation_timestamp(repo):
    conv = repo.create_conversation(novel_id="n1", title="t")
    original_updated = conv.updated_at

    # 确保时间戳能区分
    import time

    time.sleep(0.01)
    repo.add_message(conversation_id=conv.id, role="user", content="hi")

    updated_conv = repo.get_conversation(conv.id)
    assert updated_conv.updated_at >= original_updated


# ====================================================================
# delete_conversation
# ====================================================================


def test_delete_conversation_returns_true(repo):
    conv = repo.create_conversation(novel_id="n1", title="待删除")
    result = repo.delete_conversation(conv.id)
    assert result is True
    assert repo.get_conversation(conv.id) is None


def test_delete_conversation_returns_false_for_missing(repo):
    result = repo.delete_conversation("non_existent")
    assert result is False


def test_delete_conversation_cascades_messages(repo):
    conv = repo.create_conversation(novel_id="n1", title="t")
    repo.add_message(conversation_id=conv.id, role="user", content="hi")
    repo.add_message(conversation_id=conv.id, role="assistant", content="hello")

    assert len(repo.list_messages(conv.id)) == 2
    repo.delete_conversation(conv.id)
    assert repo.list_messages(conv.id) == []


# ====================================================================
# 端到端：完整会话流
# ====================================================================


def test_full_conversation_lifecycle(repo):
    # 1. 创建会话
    conv = repo.create_conversation(novel_id="novel_x", title="完整流程")
    assert conv.id

    # 2. 添加多条消息
    repo.add_message(conversation_id=conv.id, role="user", content="生成第一章")
    repo.add_message(
        conversation_id=conv.id,
        role="assistant",
        content="已生成第一章",
        tool_name="generate_chapter",
        tool_calls='{"tool": "generate_chapter", "args": {"novel_id": "novel_x"}}',
    )
    repo.add_message(conversation_id=conv.id, role="user", content="审查一下")

    # 3. 查询消息
    msgs = repo.list_messages(conv.id)
    assert len(msgs) == 3
    assert msgs[1].tool_name == "generate_chapter"
    assert msgs[1].tool_calls is not None

    # 4. 删除会话
    assert repo.delete_conversation(conv.id) is True
    assert repo.get_conversation(conv.id) is None
    assert repo.list_messages(conv.id) == []


# ====================================================================
# Database 基础设施
# ====================================================================


def test_database_normalize_path_strips_sqlite_prefix():
    db = Database("sqlite:///some/path.db")
    assert db.db_path == "some/path.db"


def test_database_normalize_path_keeps_plain_path():
    db = Database("/plain/path.db")
    assert db.db_path == "/plain/path.db"
