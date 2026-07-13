"""Sprint 3.1 RED：后端全局搜索 SearchService 的失败测试。

SearchService 跨 5 表（characters/foreshadows/memory_facts/world_settings/chapters）
做 LIKE 查询，供 WorkspaceShell 的 Search 按钮调用。
"""
import contextlib
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from infrastructure.persistence.database import Database


@pytest.fixture
def database():
    """临时 SQLite 数据库，预填测试数据。"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = Database(path)
    db.init_db()

    # 插入测试数据
    db.execute(
        "INSERT INTO novels (id, title, premise, genre, target_chapters, current_chapter, created_at, updated_at) "
        "VALUES ('n1', '测试小说', '关于唐凌轩的故事', '玄幻', 10, 2, '2026-01-01', '2026-01-01')"
    )
    db.execute(
        "INSERT INTO characters (id, novel_id, name, role, description, created_at, updated_at) "
        "VALUES ('c1', 'n1', '唐凌轩', '主角', '经脉通畅的少年', '2026-01-01', '2026-01-01')"
    )
    db.execute(
        "INSERT INTO characters (id, novel_id, name, role, description, created_at, updated_at) "
        "VALUES ('c2', 'n1', '苏雨晴', '配角', '医师', '2026-01-01', '2026-01-01')"
    )
    db.execute(
        "INSERT INTO foreshadows (id, novel_id, title, description, priority, status, "
        "planted_chapter_index, urgency, created_at, updated_at) "
        "VALUES ('f1', 'n1', '星渊之谜', '唐凌轩掌心的暗纹', 'P1', 'planted', 1, 'normal', '2026-01-01', '2026-01-01')"
    )
    db.execute(
        "INSERT INTO memory_facts (id, novel_id, fact_type, key, value, locked_at_chapter, is_immutable, source, created_at, updated_at) "
        "VALUES ('mf1', 'n1', 'character', '唐凌轩境界', '通脉期', 1, 1, 'extracted', '2026-01-01', '2026-01-01')"
    )
    db.execute(
        "INSERT INTO world_settings (id, novel_id, name, setting_type, description, created_at, updated_at) "
        "VALUES ('ws1', 'n1', '青鸾学院', 'location', '修真学院', '2026-01-01', '2026-01-01')"
    )
    db.execute(
        "INSERT INTO chapters (id, novel_id, number, title, outline, content, status, word_count, "
        "tension_score, created_at, updated_at) "
        "VALUES ('ch1', 'n1', 1, '初入学院', '唐凌轩入学', '正文内容', 'completed', 3000, 60.0, '2026-01-01', '2026-01-01')"
    )

    yield db
    if os.path.exists(path):
        with contextlib.suppress(OSError):
            os.remove(path)


def test_search_service_searches_characters(database):
    """SearchService 应能在 characters 表搜索。"""
    from application.services.search_service import SearchService

    svc = SearchService(database)
    results = svc.search(novel_id="n1", query="唐凌轩")
    assert len(results["characters"]) >= 1
    assert any(c["name"] == "唐凌轩" for c in results["characters"])


def test_search_service_searches_foreshadows(database):
    """SearchService 应能在 foreshadows 表搜索。"""
    from application.services.search_service import SearchService

    svc = SearchService(database)
    results = svc.search(novel_id="n1", query="星渊")
    assert len(results["foreshadows"]) >= 1
    assert any(f["title"] == "星渊之谜" for f in results["foreshadows"])


def test_search_service_searches_memory_facts(database):
    """SearchService 应能在 memory_facts 表搜索。"""
    from application.services.search_service import SearchService

    svc = SearchService(database)
    results = svc.search(novel_id="n1", query="通脉")
    assert len(results["facts"]) >= 1


def test_search_service_searches_world_settings(database):
    """SearchService 应能在 world_settings 表搜索。"""
    from application.services.search_service import SearchService

    svc = SearchService(database)
    results = svc.search(novel_id="n1", query="学院")
    assert len(results["settings"]) >= 1
    assert any(s["name"] == "青鸾学院" for s in results["settings"])


def test_search_service_searches_chapters(database):
    """SearchService 应能在 chapters 表搜索标题与内容。"""
    from application.services.search_service import SearchService

    svc = SearchService(database)
    results = svc.search(novel_id="n1", query="学院")
    assert len(results["chapters"]) >= 1
    assert any(c["title"] == "初入学院" for c in results["chapters"])


def test_search_service_returns_all_five_categories(database):
    """SearchService 返回结果必须包含全部 5 类 key。"""
    from application.services.search_service import SearchService

    svc = SearchService(database)
    results = svc.search(novel_id="n1", query="唐凌轩")
    expected_keys = {"characters", "foreshadows", "facts", "settings", "chapters"}
    assert set(results.keys()) == expected_keys, (
        f"结果应包含全部 5 类，实际：{set(results.keys())}"
    )


def test_search_service_empty_query_returns_empty_all_categories(database):
    """空查询应返回 5 类空数组（而非 400 或异常）。"""
    from application.services.search_service import SearchService

    svc = SearchService(database)
    results = svc.search(novel_id="n1", query="")
    for key in ["characters", "foreshadows", "facts", "settings", "chapters"]:
        assert results[key] == [], f"空查询时 {key} 应为空数组"


def test_search_service_no_match_returns_empty_not_404(database):
    """无命中应返回空数组而非 404。"""
    from application.services.search_service import SearchService

    svc = SearchService(database)
    results = svc.search(novel_id="n1", query="不存在的关键词XYZ123")
    for key in ["characters", "foreshadows", "facts", "settings", "chapters"]:
        assert results[key] == [], f"无命中时 {key} 应为空数组"


def test_search_service_filters_by_novel_id(database):
    """应按 novel_id 过滤，不返回其他小说的数据。"""
    from application.services.search_service import SearchService

    # 插入另一个小说的角色
    database.execute(
        "INSERT INTO novels (id, title, premise, genre, target_chapters, current_chapter, created_at, updated_at) "
        "VALUES ('n2', '另一部', '', '玄幻', 5, 0, '2026-01-01', '2026-01-01')"
    )
    database.execute(
        "INSERT INTO characters (id, novel_id, name, role, created_at, updated_at) "
        "VALUES ('c3', 'n2', '另一个唐凌轩', '配角', '2026-01-01', '2026-01-01')"
    )

    svc = SearchService(database)
    results = svc.search(novel_id="n1", query="唐凌轩")
    # 不应包含 n2 的数据
    for c in results["characters"]:
        assert c["novel_id"] == "n1", f"不应返回其他小说的角色：{c}"
