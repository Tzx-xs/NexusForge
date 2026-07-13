"""Sprint 1.1 RED：ChapterStatus 枚举的失败测试。

验证状态字段一致性的核心约束：
- 三个合法状态值：draft / planned / completed
- 删除 "generated" 死状态（被立刻覆盖为 completed，永不持久化）
- 提供 is_valid / transition 辅助方法
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from domain.chapter_status import ChapterStatus, InvalidStatusTransitionError


def test_chapter_status_values():
    """三个核心状态值必须与现有数据库存量数据兼容。"""
    assert ChapterStatus.DRAFT.value == "draft"
    assert ChapterStatus.PLANNED.value == "planned"
    assert ChapterStatus.COMPLETED.value == "completed"


def test_chapter_status_no_generated():
    """删除 "generated" 死状态：它被立刻覆盖为 completed，永不持久化。"""
    values = {s.value for s in ChapterStatus}
    assert "generated" not in values, '"generated" 死状态应被删除'


def test_chapter_status_is_valid():
    """is_valid 应识别合法/非法状态。"""
    assert ChapterStatus.is_valid("draft") is True
    assert ChapterStatus.is_valid("planned") is True
    assert ChapterStatus.is_valid("completed") is True
    assert ChapterStatus.is_valid("generated") is False
    assert ChapterStatus.is_valid("invalid") is False
    assert ChapterStatus.is_valid("") is False
    assert ChapterStatus.is_valid(None) is False


def test_chapter_status_from_string():
    """from_string 应返回对应枚举，未知值抛 ValueError。"""
    assert ChapterStatus.from_string("draft") is ChapterStatus.DRAFT
    assert ChapterStatus.from_string("planned") is ChapterStatus.PLANNED
    assert ChapterStatus.from_string("completed") is ChapterStatus.COMPLETED
    with pytest.raises(ValueError):
        ChapterStatus.from_string("generated")
    with pytest.raises(ValueError):
        ChapterStatus.from_string("unknown")


def test_chapter_status_transition_legal():
    """合法流转：draft -> planned -> completed。"""
    ChapterStatus.transition("draft", "planned")
    ChapterStatus.transition("planned", "completed")
    ChapterStatus.transition("draft", "completed")  # 允许跳过 planned


def test_chapter_status_transition_illegal():
    """非法流转应抛 InvalidStatusTransitionError。"""
    with pytest.raises(InvalidStatusTransitionError):
        ChapterStatus.transition("completed", "draft")  # 完成后不能回退
    with pytest.raises(InvalidStatusTransitionError):
        ChapterStatus.transition("completed", "planned")
    with pytest.raises(InvalidStatusTransitionError):
        ChapterStatus.transition("planned", "draft")  # 不能回退
    with pytest.raises(InvalidStatusTransitionError):
        ChapterStatus.transition("draft", "generated")  # 死状态非法


def test_chapter_status_transition_unknown():
    """未知状态参与流转应抛错。"""
    with pytest.raises(InvalidStatusTransitionError):
        ChapterStatus.transition("draft", "unknown")
    with pytest.raises(InvalidStatusTransitionError):
        ChapterStatus.transition("unknown", "draft")


def test_chapter_status_to_string():
    """枚举可被直接当作字符串使用（兼容 SQLite TEXT 字段）。"""
    assert ChapterStatus.DRAFT == "draft" or ChapterStatus.DRAFT.value == "draft"
    # 与现有 schema 兼容：直接赋值给 Chapter.status 字段
    sample_status = ChapterStatus.PLANNED.value
    assert sample_status == "planned"
