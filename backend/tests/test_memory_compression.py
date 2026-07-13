import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.memory_compressor import (
    MemoryCompressor,
    estimate_tokens,
)

# ====================================================================
# estimate_tokens 单元测试
# ====================================================================


def test_estimate_tokens_empty_string():
    assert estimate_tokens("") == 0


def test_estimate_tokens_english():
    # 10 个字符 → 5 个 Token
    assert estimate_tokens("abcdefghij") == 5


def test_estimate_tokens_chinese():
    # 12 个中文字符 → 6 个 Token（按 1 Token ≈ 2 字符估算）
    assert estimate_tokens("你好世界你好世界你好世界") == 6


# ====================================================================
# MemoryCompressor 单元测试
# ====================================================================


@pytest.fixture
def llm_client():
    client = MagicMock()
    client.chat = AsyncMock(return_value="用户讨论了角色设定，决定添加新角色。")
    return client


def _make_compressor(llm_client):
    return MemoryCompressor(llm_client)


# ---- needs_compression ----

def test_no_compression_when_under_threshold(llm_client):
    """短消息（总 Token < 4000），needs_compression 返回 False"""
    compressor = _make_compressor(llm_client)
    short_msgs = [{"role": "user", "content": "hi"}]
    assert not compressor.needs_compression(short_msgs)


def test_compression_needed_when_over_threshold(llm_client):
    """长消息（总 Token ≥ 4000），needs_compression 返回 True"""
    compressor = _make_compressor(llm_client)
    long_msgs = [
        {"role": "user", "content": "x" * 4000},
        {"role": "assistant", "content": "y" * 4000},
    ]
    assert compressor.needs_compression(long_msgs)


# ---- compress ----

@pytest.mark.asyncio
async def test_compress_no_compression_when_under_threshold(llm_client):
    """短消息 compress 返回原消息列表"""
    compressor = _make_compressor(llm_client)
    short_msgs = [{"role": "user", "content": "hi"}]
    result = await compressor.compress(short_msgs)
    assert result == short_msgs


@pytest.mark.asyncio
async def test_compress_returns_compressed_when_over_threshold(llm_client):
    """长消息 compress 返回压缩后消息（摘要作为 system 消息 + 后 50% 原始消息）"""
    compressor = _make_compressor(llm_client)
    long_msgs = [
        {"role": "user", "content": "x" * 4000},
        {"role": "assistant", "content": "y" * 4000},
    ]
    assert compressor.needs_compression(long_msgs)

    result = await compressor.compress(long_msgs)

    # 压缩后消息更少（原始 2 条 → 摘要 + 后半 1 条 = 2 条，但摘要更短）
    assert len(result) < len(long_msgs) + 1  # 不增加消息数
    # 第一条是 system 摘要
    assert result[0]["role"] == "system"
    assert "[对话摘要]" in result[0]["content"]
    # 后半部分原始消息保留
    assert result[1]["content"] == "y" * 4000


@pytest.mark.asyncio
async def test_compress_preserves_key_info_in_prompt(llm_client):
    """验证压缩摘要调用 LLM 时 prompt 包含「保留关键信息」等关键词"""
    compressor = _make_compressor(llm_client)
    long_msgs = [
        {"role": "user", "content": "x" * 4000},
        {"role": "assistant", "content": "y" * 4000},
    ]

    await compressor.compress(long_msgs)

    # 验证 LLM chat 被调用
    llm_client.chat.assert_awaited_once()
    call_args = llm_client.chat.call_args.args[0]
    # 调用参数是 messages 列表
    prompt_text = call_args[0]["content"]
    assert "摘要压缩" in prompt_text
    assert "保留" in prompt_text
    assert "关键" in prompt_text


@pytest.mark.asyncio
async def test_compress_partition_is_correct(llm_client):
    """验证奇数消息列表时 split 正确（前半 floor(n/2)，后半 ceil(n/2)）"""
    compressor = _make_compressor(llm_client)
    msgs = [
        {"role": "user", "content": "x" * 2000},
        {"role": "assistant", "content": "x" * 2000},
        {"role": "user", "content": "x" * 2000},
        {"role": "assistant", "content": "x" * 2000},
        {"role": "user", "content": "x" * 2000},
    ]
    # 5 条消息，split_idx = 2，前半 2 条，后半 3 条
    result = await compressor.compress(msgs)
    # 压缩后：system 摘要 + 后半 3 条 = 4 条
    assert len(result) == 4
    assert result[0]["role"] == "system"


@pytest.mark.asyncio
async def test_compress_llm_failure_fallback(llm_client):
    """LLM 调用失败时降级为简单截断摘要"""
    llm_client.chat = AsyncMock(side_effect=RuntimeError("llm unavailable"))
    compressor = _make_compressor(llm_client)
    long_msgs = [
        {"role": "user", "content": "x" * 4000},
        {"role": "assistant", "content": "y" * 4000},
    ]

    result = await compressor.compress(long_msgs)

    assert result[0]["role"] == "system"
    assert "压缩失败" in result[0]["content"]
    assert "前 1 条消息" in result[0]["content"]
