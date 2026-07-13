import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agents.tools.base import Tool, ToolResult
from agents.tools.export_novel import ExportNovelTool
from agents.tools.generate_chapter import GenerateChapterTool
from agents.tools.manage_foreshadows import ManageForeshadowsTool
from agents.tools.query_bible import QueryBibleTool
from agents.tools.query_characters import QueryCharactersTool
from agents.tools.registry import ToolRegistry
from agents.tools.review_chapter import ReviewChapterTool

# ====================================================================
# Mock 工厂函数
# ====================================================================


def _make_chapter(cid="ch_1", number=1, title="第一章 命运的开端", word_count=3500, status="completed"):
    return type(
        "MockChapter",
        (),
        {
            "id": cid,
            "number": number,
            "title": title,
            "content": "云泽站在星渊崖边。",
            "word_count": word_count,
            "status": status,
        },
    )()


def _make_review(rid="rev_1", chapter_id="ch_1", score=85.0, grade="A", violations=None, dimensions=None):
    return type(
        "MockReview",
        (),
        {
            "id": rid,
            "chapter_id": chapter_id,
            "total_score": score,
            "grade": grade,
            "red_line_violations": violations if violations is not None else [],
            "dimension_scores": dimensions if dimensions is not None else {"rhythm": 85},
            "review_details": "",
        },
    )()


def _make_character(c_id="c1", name="林渊", role="主角"):
    return type(
        "MockCharacter",
        (),
        {
            "id": c_id,
            "name": name,
            "role": role,
            "description": "少年",
            "personality": "冷静",
            "appearance": "黑发",
            "background": "渔村",
        },
    )()


def _make_setting(s_id="s1", name="云屿", setting_type="world"):
    return type(
        "MockSetting",
        (),
        {
            "id": s_id,
            "name": name,
            "setting_type": setting_type,
            "description": "漂浮岛屿",
            "parent_id": None,
        },
    )()


def _make_foreshadow(f_id="f1", title="星渊反应", status="planted", priority="P1"):
    return type(
        "MockForeshadow",
        (),
        {
            "id": f_id,
            "title": title,
            "description": "渊墟伏笔",
            "priority": priority,
            "status": status,
            "planted_chapter_id": "ch_1",
            "planted_chapter_index": 1,
            "resolved_chapter_id": None,
            "resolved_chapter_index": None,
            "urgency": "normal",
            "tags": [],
            "notes": "",
        },
    )()


# ====================================================================
# 通用 schema 校验工具
# ====================================================================


def _assert_openai_schema(schema: dict, expected_name: str):
    """校验 OpenAI Function Calling schema 格式"""
    assert isinstance(schema, dict)
    assert schema["type"] == "function"
    fn = schema["function"]
    assert fn["name"] == expected_name
    assert fn["description"]
    assert isinstance(fn["description"], str)
    params = fn["parameters"]
    assert params["type"] == "object"
    assert isinstance(params["properties"], dict)
    assert len(params["properties"]) > 0


# ====================================================================
# GenerateChapterTool
# ====================================================================


@pytest.fixture
def chapter_service():
    svc = MagicMock()
    svc.generate_chapter = AsyncMock(return_value=_make_chapter())
    return svc


@pytest.fixture
def generate_chapter_tool(chapter_service):
    return GenerateChapterTool(chapter_service)


def test_generate_chapter_attributes(generate_chapter_tool):
    assert generate_chapter_tool.name == "generate_chapter"
    assert generate_chapter_tool.description
    assert generate_chapter_tool.parameters


def test_generate_chapter_schema(generate_chapter_tool):
    _assert_openai_schema(generate_chapter_tool.to_openai_schema(), "generate_chapter")


@pytest.mark.asyncio
async def test_generate_chapter_execute_success(generate_chapter_tool, chapter_service):
    result = await generate_chapter_tool.execute(novel_id="n1")
    assert result.success is True
    assert result.data["chapter_id"] == "ch_1"
    assert result.data["chapter_number"] == 1
    assert result.data["word_count"] == 3500
    assert result.data["title"] == "第一章 命运的开端"
    assert result.data["status"] == "completed"
    chapter_service.generate_chapter.assert_awaited_once_with("n1", chapter_number=None, outline=None)


@pytest.mark.asyncio
async def test_generate_chapter_execute_returns_none(chapter_service, generate_chapter_tool):
    chapter_service.generate_chapter = AsyncMock(return_value=None)
    result = await generate_chapter_tool.execute(novel_id="n1")
    assert result.success is False
    assert "None" in result.error


@pytest.mark.asyncio
async def test_generate_chapter_execute_service_raises(chapter_service, generate_chapter_tool):
    chapter_service.generate_chapter = AsyncMock(side_effect=RuntimeError("pipeline boom"))
    result = await generate_chapter_tool.execute(novel_id="n1")
    assert result.success is False
    assert "pipeline boom" in result.error


# ====================================================================
# ReviewChapterTool
# ====================================================================


@pytest.fixture
def review_service():
    svc = MagicMock()
    svc.review_chapter = AsyncMock(return_value=_make_review())
    return svc


@pytest.fixture
def review_chapter_tool(review_service):
    return ReviewChapterTool(review_service)


def test_review_chapter_attributes(review_chapter_tool):
    assert review_chapter_tool.name == "review_chapter"
    assert review_chapter_tool.description
    assert review_chapter_tool.parameters


def test_review_chapter_schema(review_chapter_tool):
    _assert_openai_schema(review_chapter_tool.to_openai_schema(), "review_chapter")


@pytest.mark.asyncio
async def test_review_chapter_execute_success(review_chapter_tool, review_service):
    result = await review_chapter_tool.execute(chapter_id="ch_1")
    assert result.success is True
    assert result.data["review_id"] == "rev_1"
    assert result.data["chapter_id"] == "ch_1"
    assert result.data["overall_score"] == 85.0
    assert result.data["grade"] == "A"
    assert result.data["passed"] is True
    assert result.data["total_issues"] == 0
    review_service.review_chapter.assert_awaited_once_with("ch_1")


@pytest.mark.asyncio
async def test_review_chapter_execute_with_violations(review_service, review_chapter_tool):
    review_service.review_chapter = AsyncMock(
        return_value=_make_review(
            score=55.0,
            grade="C",
            violations=[{"rule": "no_gou", "message": "出现苟字"}],
        )
    )
    result = await review_chapter_tool.execute(chapter_id="ch_1")
    assert result.success is True
    assert result.data["passed"] is False
    assert result.data["total_issues"] == 1


@pytest.mark.asyncio
async def test_review_chapter_execute_returns_none(review_service, review_chapter_tool):
    review_service.review_chapter = AsyncMock(return_value=None)
    result = await review_chapter_tool.execute(chapter_id="ch_1")
    assert result.success is False
    assert "None" in result.error


@pytest.mark.asyncio
async def test_review_chapter_execute_service_raises(review_service, review_chapter_tool):
    review_service.review_chapter = AsyncMock(side_effect=ValueError("chapter missing"))
    result = await review_chapter_tool.execute(chapter_id="ch_1")
    assert result.success is False
    assert "chapter missing" in result.error


# ====================================================================
# QueryBibleTool
# ====================================================================


@pytest.fixture
def bible_service():
    svc = MagicMock()
    svc.list_settings = MagicMock(
        return_value=[_make_setting("s1", "云屿", "world"), _make_setting("s2", "青云宗", "faction")]
    )
    svc.list_characters = MagicMock(return_value=[_make_character()])
    return svc


@pytest.fixture
def query_bible_tool(bible_service):
    return QueryBibleTool(bible_service)


def test_query_bible_attributes(query_bible_tool):
    assert query_bible_tool.name == "query_bible"
    assert query_bible_tool.description
    assert query_bible_tool.parameters


def test_query_bible_schema(query_bible_tool):
    _assert_openai_schema(query_bible_tool.to_openai_schema(), "query_bible")


@pytest.mark.asyncio
async def test_query_bible_execute_success(query_bible_tool, bible_service):
    result = await query_bible_tool.execute(novel_id="n1")
    assert result.success is True
    assert result.data["novel_id"] == "n1"
    assert result.data["total"] == 2
    assert len(result.data["settings"]) == 2
    bible_service.list_settings.assert_called_once_with("n1", setting_type=None)


@pytest.mark.asyncio
async def test_query_bible_execute_with_type_filter(query_bible_tool, bible_service):
    bible_service.list_settings = MagicMock(return_value=[_make_setting("s1", "云屿", "world")])
    result = await query_bible_tool.execute(novel_id="n1", setting_type="world")
    assert result.success is True
    assert result.data["total"] == 1
    assert result.data["settings"][0]["setting_type"] == "world"
    bible_service.list_settings.assert_called_once_with("n1", setting_type="world")


@pytest.mark.asyncio
async def test_query_bible_execute_service_raises(bible_service, query_bible_tool):
    bible_service.list_settings = MagicMock(side_effect=RuntimeError("db error"))
    result = await query_bible_tool.execute(novel_id="n1")
    assert result.success is False
    assert "db error" in result.error


# ====================================================================
# QueryCharactersTool
# ====================================================================


@pytest.fixture
def query_characters_tool(bible_service):
    return QueryCharactersTool(bible_service)


def test_query_characters_attributes(query_characters_tool):
    assert query_characters_tool.name == "query_characters"
    assert query_characters_tool.description
    assert query_characters_tool.parameters


def test_query_characters_schema(query_characters_tool):
    _assert_openai_schema(query_characters_tool.to_openai_schema(), "query_characters")


@pytest.mark.asyncio
async def test_query_characters_list_success(query_characters_tool, bible_service):
    bible_service.list_characters = MagicMock(
        return_value=[_make_character("c1", "林渊"), _make_character("c2", "苏清寒", "女主")]
    )
    result = await query_characters_tool.execute(novel_id="n1")
    assert result.success is True
    assert result.data["total"] == 2
    assert len(result.data["characters"]) == 2
    bible_service.list_characters.assert_called_once_with("n1")


@pytest.mark.asyncio
async def test_query_characters_detail_success(query_characters_tool, bible_service):
    bible_service.list_characters = MagicMock(
        return_value=[_make_character("c1", "林渊"), _make_character("c2", "苏清寒")]
    )
    result = await query_characters_tool.execute(novel_id="n1", character_id="c2")
    assert result.success is True
    assert result.data["character"]["id"] == "c2"
    assert result.data["character"]["name"] == "苏清寒"


@pytest.mark.asyncio
async def test_query_characters_detail_not_found(query_characters_tool, bible_service):
    bible_service.list_characters = MagicMock(return_value=[_make_character("c1", "林渊")])
    result = await query_characters_tool.execute(novel_id="n1", character_id="missing")
    assert result.success is False
    assert "未找到人物" in result.error


@pytest.mark.asyncio
async def test_query_characters_service_raises(bible_service, query_characters_tool):
    bible_service.list_characters = MagicMock(side_effect=RuntimeError("conn lost"))
    result = await query_characters_tool.execute(novel_id="n1")
    assert result.success is False
    assert "conn lost" in result.error


# ====================================================================
# ManageForeshadowsTool
# ====================================================================


@pytest.fixture
def foreshadow_repo():
    repo = MagicMock()
    repo.list_foreshadows = MagicMock(return_value=[_make_foreshadow()])
    repo.update_foreshadow = MagicMock(return_value=_make_foreshadow(status="resolved"))
    return repo


@pytest.fixture
def manage_foreshadows_tool(foreshadow_repo):
    return ManageForeshadowsTool(foreshadow_repo)


def test_manage_foreshadows_attributes(manage_foreshadows_tool):
    assert manage_foreshadows_tool.name == "manage_foreshadows"
    assert manage_foreshadows_tool.description
    assert manage_foreshadows_tool.parameters


def test_manage_foreshadows_schema(manage_foreshadows_tool):
    _assert_openai_schema(manage_foreshadows_tool.to_openai_schema(), "manage_foreshadows")


@pytest.mark.asyncio
async def test_manage_foreshadows_list_success(manage_foreshadows_tool, foreshadow_repo):
    result = await manage_foreshadows_tool.execute(novel_id="n1", action="list")
    assert result.success is True
    assert result.data["total"] == 1
    assert len(result.data["foreshadows"]) == 1
    foreshadow_repo.list_foreshadows.assert_called_once_with("n1", status=None, priority=None)


@pytest.mark.asyncio
async def test_manage_foreshadows_list_with_filters(manage_foreshadows_tool, foreshadow_repo):
    foreshadow_repo.list_foreshadows = MagicMock(return_value=[_make_foreshadow(status="planted", priority="P1")])
    result = await manage_foreshadows_tool.execute(novel_id="n1", action="list", status="planted", priority="P1")
    assert result.success is True
    assert result.data["total"] == 1
    foreshadow_repo.list_foreshadows.assert_called_once_with("n1", status="planted", priority="P1")


@pytest.mark.asyncio
async def test_manage_foreshadows_update_success(manage_foreshadows_tool, foreshadow_repo):
    result = await manage_foreshadows_tool.execute(
        novel_id="n1", action="update", foreshadow_id="f1", status="resolved"
    )
    assert result.success is True
    assert result.data["foreshadow_id"] == "f1"
    assert result.data["status"] == "resolved"
    foreshadow_repo.update_foreshadow.assert_called_once_with("f1", {"status": "resolved"})


@pytest.mark.asyncio
async def test_manage_foreshadows_update_no_id(manage_foreshadows_tool):
    result = await manage_foreshadows_tool.execute(novel_id="n1", action="update", status="resolved")
    assert result.success is False
    assert "foreshadow_id" in result.error


@pytest.mark.asyncio
async def test_manage_foreshadows_update_not_found(foreshadow_repo, manage_foreshadows_tool):
    foreshadow_repo.update_foreshadow = MagicMock(return_value=None)
    result = await manage_foreshadows_tool.execute(
        novel_id="n1", action="update", foreshadow_id="missing", status="resolved"
    )
    assert result.success is False
    assert "未找到伏笔" in result.error


@pytest.mark.asyncio
async def test_manage_foreshadows_invalid_action(manage_foreshadows_tool):
    result = await manage_foreshadows_tool.execute(novel_id="n1", action="delete")
    assert result.success is False
    assert "不支持的操作类型" in result.error


@pytest.mark.asyncio
async def test_manage_foreshadows_service_raises(foreshadow_repo, manage_foreshadows_tool):
    foreshadow_repo.list_foreshadows = MagicMock(side_effect=RuntimeError("sql error"))
    result = await manage_foreshadows_tool.execute(novel_id="n1", action="list")
    assert result.success is False
    assert "sql error" in result.error


# ====================================================================
# ExportNovelTool
# ====================================================================


@pytest.fixture
def export_service():
    svc = MagicMock()
    svc.export_novel = MagicMock(return_value=b"export content bytes")
    svc.get_export_filename = MagicMock(return_value="星渊传说.txt")
    return svc


@pytest.fixture
def export_novel_tool(export_service):
    return ExportNovelTool(export_service)


def test_export_novel_attributes(export_novel_tool):
    assert export_novel_tool.name == "export_novel"
    assert export_novel_tool.description
    assert export_novel_tool.parameters


def test_export_novel_schema(export_novel_tool):
    _assert_openai_schema(export_novel_tool.to_openai_schema(), "export_novel")


@pytest.mark.asyncio
async def test_export_novel_execute_success(export_novel_tool, export_service):
    result = await export_novel_tool.execute(novel_id="n1", format="txt")
    assert result.success is True
    assert result.data["novel_id"] == "n1"
    assert result.data["format"] == "txt"
    assert result.data["filename"] == "星渊传说.txt"
    assert result.data["byte_size"] == len(b"export content bytes")
    export_service.export_novel.assert_called_once()
    export_service.get_export_filename.assert_called_once()


@pytest.mark.asyncio
async def test_export_novel_invalid_format_falls_back_to_txt(export_novel_tool, export_service):
    result = await export_novel_tool.execute(novel_id="n1", format="weird_format")
    assert result.success is True
    assert result.data["format"] == "txt"


@pytest.mark.asyncio
async def test_export_novel_service_raises(export_service, export_novel_tool):
    export_service.export_novel = MagicMock(side_effect=ValueError("novel not found"))
    result = await export_novel_tool.execute(novel_id="missing")
    assert result.success is False
    assert "novel not found" in result.error


# ====================================================================
# ToolRegistry
# ====================================================================


def _build_default_registry():
    return ToolRegistry.create_default(
        chapter_service=MagicMock(),
        review_service=MagicMock(),
        bible_service=MagicMock(),
        export_service=MagicMock(),
        foreshadow_repo=MagicMock(),
    )


def test_registry_create_default_has_eight_tools():
    registry = _build_default_registry()
    names = registry.list_names()
    # 默认注册表包含 6 个基础工具 + 2 个新增工具（edit_paragraph, delete_character）= 8 个
    # 另有 2 个条件工具（polish_content, analyze_plot）需要 llm_client + novel_service
    assert len(names) == 8
    for name in (
        "generate_chapter",
        "review_chapter",
        "query_bible",
        "query_characters",
        "manage_foreshadows",
        "export_novel",
        "edit_paragraph",
        "delete_character",
    ):
        assert name in names


def test_registry_to_openai_schemas():
    registry = _build_default_registry()
    schemas = registry.to_openai_schemas()
    assert isinstance(schemas, list)
    assert len(schemas) == 8
    for schema in schemas:
        assert schema["type"] == "function"
        assert "name" in schema["function"]
        assert schema["function"]["name"]


def test_registry_register_and_get():
    registry = ToolRegistry()
    tool = MagicMock(spec=Tool)
    tool.name = "custom_tool"
    tool.to_openai_schema = MagicMock(return_value={"type": "function", "function": {"name": "custom_tool"}})
    registry.register(tool)
    assert registry.get("custom_tool") is tool
    assert registry.get("nonexistent") is None


def test_registry_register_empty_name_raises():
    registry = ToolRegistry()
    tool = MagicMock(spec=Tool)
    tool.name = ""
    with pytest.raises(ValueError, match="name"):
        registry.register(tool)


def test_tool_result_dataclass_defaults():
    success_result = ToolResult(success=True)
    assert success_result.success is True
    assert success_result.data == {}
    assert success_result.error == ""

    fail_result = ToolResult(success=False, error="boom")
    assert fail_result.success is False
    assert fail_result.error == "boom"


def test_tool_is_abstract():
    """Tool 是 ABC，不能直接实例化"""
    with pytest.raises(TypeError):
        Tool()  # type: ignore[abstract]


def test_tool_to_openai_schema_format_for_all_tools():
    """所有 6 个 tool 的 schema 都符合 OpenAI Function Calling 格式"""
    registry = _build_default_registry()
    for schema in registry.to_openai_schemas():
        _assert_openai_schema(schema, schema["function"]["name"])
