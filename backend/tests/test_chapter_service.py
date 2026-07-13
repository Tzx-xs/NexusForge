"""Sprint 4.3: 补全 ChapterService 测试。

为 backend/application/services/chapter_service.py 的核心方法补测试,
覆盖状态流转(DRAFT→PLANNED→COMPLETED)、委托关系、字数计算、异常路径。
"""

import os
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from application.services.chapter_service import ChapterService  # noqa: E402
from domain.chapter import Chapter  # noqa: E402
from domain.chapter_status import ChapterStatus  # noqa: E402
from domain.novel import Novel  # noqa: E402
from domain.shared.exceptions import NovelNotFoundException  # noqa: E402

# ====================================================================
# Fixtures
# ====================================================================


@pytest.fixture
def chapter_repo():
    repo = MagicMock()
    repo.create = MagicMock(side_effect=lambda c: c)
    repo.update = MagicMock(side_effect=lambda c: c)
    repo.delete = MagicMock(return_value=True)
    repo.get_by_id = MagicMock(return_value=None)
    repo.list_by_novel = MagicMock(return_value=[])
    return repo


@pytest.fixture
def novel_repo():
    repo = MagicMock()
    novel = Novel(id="n1", title="测试小说", current_chapter=0)
    repo.get_by_id = MagicMock(return_value=novel)
    repo.update = MagicMock()
    return repo


@pytest.fixture
def generation_pipeline():
    return MagicMock()


@pytest.fixture
def story_pipeline():
    return MagicMock()


@pytest.fixture
def service(chapter_repo, novel_repo, generation_pipeline, story_pipeline):
    return ChapterService(
        chapter_repo=chapter_repo,
        novel_repo=novel_repo,
        generation_pipeline=generation_pipeline,
        story_pipeline=story_pipeline,
    )


# ====================================================================
# 1. create_chapter 默认 status == DRAFT
# ====================================================================


def test_create_chapter_default_status_is_draft(service, chapter_repo, novel_repo):
    chapter = service.create_chapter("n1", "第一章")

    assert chapter.status == ChapterStatus.DRAFT.value
    assert chapter.title == "第一章"
    chapter_repo.create.assert_called_once()
    novel_repo.get_by_id.assert_called_once_with("n1")


# ====================================================================
# 2. create_chapter novel 不存在抛 NovelNotFoundException
# ====================================================================


def test_create_chapter_raises_when_novel_not_found(service, novel_repo):
    novel_repo.get_by_id = MagicMock(return_value=None)

    with pytest.raises(NovelNotFoundException):
        service.create_chapter("missing", "title")


# ====================================================================
# 3. create_chapter 自动计算 number
# ====================================================================


def test_create_chapter_auto_calculates_number(service, chapter_repo):
    existing = [Chapter(novel_id="n1", number=i) for i in range(3)]
    chapter_repo.list_by_novel = MagicMock(return_value=existing)

    chapter = service.create_chapter("n1", "第四章")

    assert chapter.number == 4


# ====================================================================
# 4. generate_outline 完成后 status == PLANNED
# ====================================================================


async def test_generate_outline_sets_status_to_planned(service, chapter_repo, generation_pipeline):
    chapter = Chapter(id="c1", novel_id="n1", number=1, title="测试", status=ChapterStatus.DRAFT.value)
    chapter_repo.get_by_id = MagicMock(return_value=chapter)
    generation_pipeline.generate_outline = AsyncMock(return_value="大纲内容")

    result = await service.generate_outline("c1")

    assert result.status == ChapterStatus.PLANNED.value
    assert result.outline == "大纲内容"
    chapter_repo.update.assert_called_once()
    generation_pipeline.generate_outline.assert_awaited_once_with("c1")


# ====================================================================
# 5. generate_content_stream 完成后 status == COMPLETED
# ====================================================================


async def test_generate_content_stream_sets_status_to_completed(service, chapter_repo, generation_pipeline):
    chapter = Chapter(id="c1", novel_id="n1", number=1, title="测试", status=ChapterStatus.PLANNED.value)
    chapter_repo.get_by_id = MagicMock(return_value=chapter)

    async def _mock_stream(chapter_id, options=None):
        yield "token", "你"
        yield "token", "好"

    generation_pipeline.generate_content_stream = MagicMock(side_effect=_mock_stream)

    events = []
    async for event_type, data in service.generate_content_stream("c1"):
        events.append((event_type, data))

    # 验证事件被透传
    assert len(events) == 2
    assert events[0] == ("token", "你")
    assert events[1] == ("token", "好")
    # 验证章节状态更新
    assert chapter.status == ChapterStatus.COMPLETED.value
    assert chapter.content == "你好"
    assert chapter.word_count == 2
    chapter_repo.update.assert_called_once()


# ====================================================================
# 6. generate_chapter 委托给 StoryPipeline
# ====================================================================


async def test_generate_chapter_delegates_to_story_pipeline(service, story_pipeline, chapter_repo):
    from engine.pipeline.context import PipelineContext

    expected_ctx = PipelineContext(novel_id="n1", chapter_id="c2")
    story_pipeline.generate_chapter = AsyncMock(return_value=expected_ctx)
    chapter = Chapter(id="c2", novel_id="n1", number=2, title="第二章")
    chapter_repo.get_by_id = MagicMock(return_value=chapter)

    result = await service.generate_chapter("n1")

    story_pipeline.generate_chapter.assert_awaited_once()
    assert result is chapter


# ====================================================================
# 7. update_chapter 透传 kwargs 给 repository
# ====================================================================


def test_update_chapter_passes_kwargs_to_repository(service, chapter_repo):
    chapter = Chapter(id="c1", novel_id="n1", number=1, title="旧标题", status=ChapterStatus.DRAFT.value)
    chapter_repo.get_by_id = MagicMock(return_value=chapter)

    result = service.update_chapter("c1", title="新标题", content="<p>新内容</p>")

    assert result.title == "新标题"
    assert result.content == "<p>新内容</p>"
    # HTML 标签被去除后字数应为 4("新内容")
    assert result.word_count == 3
    chapter_repo.update.assert_called_once()


# ====================================================================
# 8. delete_chapter 调用 repository.delete
# ====================================================================


def test_delete_chapter_calls_repository_delete(service, chapter_repo):
    result = service.delete_chapter("c1")

    chapter_repo.delete.assert_called_once_with("c1")
    assert result is True
