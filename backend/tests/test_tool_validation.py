"""Tool 参数校验单元测试 — C11 核心模块补充测试.

覆盖: 合法参数、缺少必填字段、类型错误、minimum/minLength 约束、
无 schema/非 object schema 跳过、空参数、额外属性、真实工具校验。
"""

import os
import sys
from typing import Any
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.tools.base import Tool, ToolResult
from agents.tools.generate_chapter import GenerateChapterTool
from agents.tools.review_chapter import ReviewChapterTool

# ====================================================================
# 测试用桩件
# ====================================================================


class _NoSchemaTool(Tool):
    """无 parameters schema 的工具."""

    name = "no_schema_tool"
    description = "tool without schema"

    @property
    def parameters(self) -> dict[str, Any]:
        return {}

    async def execute(self, **kwargs: Any) -> ToolResult:
        return ToolResult(success=True, data=kwargs)


class _NonObjectSchemaTool(Tool):
    """非 object 类型的 schema 工具."""

    name = "non_object_tool"
    description = "tool with array schema"

    @property
    def parameters(self) -> dict[str, Any]:
        return {"type": "array", "items": {"type": "string"}}

    async def execute(self, **kwargs: Any) -> ToolResult:
        return ToolResult(success=True)


class _SampleTool(Tool):
    """标准参数 schema 的测试工具."""

    name = "sample_tool"
    description = "sample tool for validation"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "novel_id": {"type": "string"},
                "chapter_number": {"type": "integer", "minimum": 1},
                "word_count": {"type": "integer", "minimum": 100},
                "title": {"type": "string", "minLength": 1},
            },
            "required": ["novel_id", "chapter_number"],
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        return ToolResult(success=True, data=kwargs)


class _NoRequiredTool(Tool):
    """无必填字段的工具."""

    name = "no_required_tool"
    description = "tool with no required fields"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "option_a": {"type": "string"},
                "option_b": {"type": "integer"},
            },
        }

    async def execute(self, **kwargs: Any) -> ToolResult:
        return ToolResult(success=True)


# ====================================================================
# Fixtures
# ====================================================================


@pytest.fixture
def sample_tool():
    return _SampleTool()


@pytest.fixture
def no_schema_tool():
    return _NoSchemaTool()


@pytest.fixture
def non_object_tool():
    return _NonObjectSchemaTool()


@pytest.fixture
def no_required_tool():
    return _NoRequiredTool()


# ====================================================================
# 合法参数校验
# ====================================================================


def test_validate_valid_args(sample_tool):
    """合法参数通过校验."""
    is_valid, error = sample_tool.validate_args({
        "novel_id": "novel_1",
        "chapter_number": 3,
    })
    assert is_valid is True
    assert error is None


def test_validate_valid_args_with_optional_fields(sample_tool):
    """包含可选字段的合法参数通过校验."""
    is_valid, error = sample_tool.validate_args({
        "novel_id": "novel_1",
        "chapter_number": 5,
        "word_count": 2000,
        "title": "深渊觉醒",
    })
    assert is_valid is True
    assert error is None


# ====================================================================
# 缺少必填字段
# ====================================================================


def test_validate_missing_required(sample_tool):
    """缺少必填字段返回错误."""
    is_valid, error = sample_tool.validate_args({
        "novel_id": "novel_1",
        # 缺少 chapter_number
    })
    assert is_valid is False
    assert error is not None
    assert "chapter_number" in error.lower() or "required" in error.lower()


def test_validate_missing_all_required(sample_tool):
    """缺少所有必填字段."""
    is_valid, error = sample_tool.validate_args({})
    assert is_valid is False
    assert error is not None


# ====================================================================
# 类型错误
# ====================================================================


def test_validate_wrong_type(sample_tool):
    """类型错误返回错误."""
    is_valid, error = sample_tool.validate_args({
        "novel_id": "novel_1",
        "chapter_number": "not_a_number",  # 应为 integer
    })
    assert is_valid is False
    assert error is not None
    assert "integer" in error.lower() or "number" in error.lower() or "type" in error.lower()


def test_validate_wrong_type_string_for_int(sample_tool):
    """字符串代替整数."""
    is_valid, error = sample_tool.validate_args({
        "novel_id": 123,  # 应为 string
        "chapter_number": 1,
    })
    assert is_valid is False
    assert error is not None


# ====================================================================
# minimum 约束
# ====================================================================


def test_validate_minimum_violation(sample_tool):
    """minimum 约束违反时返回错误."""
    is_valid, error = sample_tool.validate_args({
        "novel_id": "novel_1",
        "chapter_number": 0,  # minimum=1
    })
    assert is_valid is False
    assert error is not None
    assert "1" in error.lower() or "minimum" in error.lower()


def test_validate_minimum_boundary(sample_tool):
    """minimum 边界值（恰好等于 minimum）应通过."""
    is_valid, error = sample_tool.validate_args({
        "novel_id": "novel_1",
        "chapter_number": 1,
    })
    assert is_valid is True


# ====================================================================
# 无 schema / 非 object schema
# ====================================================================


def test_validate_no_schema(no_schema_tool):
    """无 schema 的工具跳过校验，任何参数都通过."""
    is_valid, error = no_schema_tool.validate_args({"anything": "goes"})
    assert is_valid is True
    assert error is None


def test_validate_non_object_schema(non_object_tool):
    """非 object schema 跳过校验."""
    is_valid, error = non_object_tool.validate_args({"anything": "goes"})
    assert is_valid is True
    assert error is None


# ====================================================================
# 空参数
# ====================================================================


def test_validate_empty_args_with_required(sample_tool):
    """空参数但有必填字段时应返回错误."""
    is_valid, error = sample_tool.validate_args({})
    assert is_valid is False
    assert error is not None


def test_validate_empty_args_no_required(no_required_tool):
    """无必填字段时，空参数应通过校验."""
    is_valid, error = no_required_tool.validate_args({})
    assert is_valid is True
    assert error is None


# ====================================================================
# 额外属性
# ====================================================================


def test_validate_extra_properties(sample_tool):
    """额外属性（默认允许）应通过校验."""
    # JSON Schema 默认允许额外属性
    is_valid, error = sample_tool.validate_args({
        "novel_id": "novel_1",
        "chapter_number": 1,
        "extra_field": "should_be_ok",
    })
    assert is_valid is True
    assert error is None


# ====================================================================
# 字符串 minLength 约束
# ====================================================================


def test_validate_string_min_length(sample_tool):
    """字符串 minLength 约束违反时返回错误."""
    is_valid, error = sample_tool.validate_args({
        "novel_id": "novel_1",
        "chapter_number": 1,
        "title": "",  # minLength=1
    })
    assert is_valid is False
    assert error is not None


def test_validate_string_min_length_boundary(sample_tool):
    """字符串 minLength 边界值（恰好等于 minLength）应通过."""
    is_valid, error = sample_tool.validate_args({
        "novel_id": "novel_1",
        "chapter_number": 1,
        "title": "x",  # minLength=1
    })
    assert is_valid is True


# ====================================================================
# 真实工具校验
# ====================================================================


class _FakeChapterService:
    """用于 GenerateChapterTool 的假 service."""

    async def generate_chapter(self, novel_id, chapter_number=None, outline=None):
        return MagicMock(id="ch_1", number=1, word_count=2000, title="第一章", status="generated")


class _FakeReviewService:
    """用于 ReviewChapterTool 的假 service."""

    async def review_chapter(self, chapter_id):
        return MagicMock(
            id="rev_1",
            chapter_id=chapter_id,
            total_score=85,
            grade="A",
            dimension_scores={},
            red_line_violations=[],
        )


def test_validate_on_generate_chapter():
    """对 generate_chapter 工具做真实校验：合法参数通过."""
    tool = GenerateChapterTool(_FakeChapterService())
    is_valid, error = tool.validate_args({"novel_id": "novel_1"})
    assert is_valid is True
    assert error is None


def test_validate_on_generate_chapter_missing_required():
    """对 generate_chapter 工具做真实校验：缺少 novel_id 返回错误."""
    tool = GenerateChapterTool(_FakeChapterService())
    is_valid, error = tool.validate_args({})
    assert is_valid is False
    assert error is not None
    assert "novel_id" in error.lower()


def test_validate_on_generate_chapter_wrong_type():
    """对 generate_chapter 工具做真实校验：chapter_number 类型错误."""
    tool = GenerateChapterTool(_FakeChapterService())
    is_valid, error = tool.validate_args({
        "novel_id": "novel_1",
        "chapter_number": "one",  # 应为 integer
    })
    assert is_valid is False
    assert error is not None


def test_validate_on_review_chapter():
    """对 review_chapter 工具做真实校验：合法参数通过."""
    tool = ReviewChapterTool(_FakeReviewService())
    is_valid, error = tool.validate_args({"chapter_id": "ch_1"})
    assert is_valid is True
    assert error is None


def test_validate_on_review_chapter_missing_required():
    """对 review_chapter 工具做真实校验：缺少 chapter_id 返回错误."""
    tool = ReviewChapterTool(_FakeReviewService())
    is_valid, error = tool.validate_args({})
    assert is_valid is False
    assert error is not None
    assert "chapter_id" in error.lower()
