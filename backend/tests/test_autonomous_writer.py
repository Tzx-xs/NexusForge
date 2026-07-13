import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from application.engine.autonomous_writer import (
    AutonomousWritingEngine,
    AutoWriteConfig,
    AutoWriteMode,
    AutoWriteState,
)


class MockChapterService:
    def __init__(self):
        self.call_count = 0

    async def generate_chapter(self, novel_id: str):
        self.call_count += 1
        return type(
            "MockChapter",
            (),
            {
                "id": f"ch_{self.call_count}",
                "content": "测试章节内容",
                "word_count": 500,
            },
        )()


@pytest.mark.asyncio
async def test_create_session():
    engine = AutonomousWritingEngine(chapter_service=MockChapterService())
    session = engine.create_session("test_novel")

    assert session is not None
    assert session.session_id != ""
    assert session.novel_id == "test_novel"
    assert session.state == AutoWriteState.IDLE
    assert session.total_chapters_completed == 0


@pytest.mark.asyncio
async def test_session_config():
    engine = AutonomousWritingEngine(chapter_service=MockChapterService())
    config = AutoWriteConfig(
        mode=AutoWriteMode.BATCH,
        target_chapters=3,
        min_quality_score=70.0,
    )
    session = engine.create_session("test_novel", config)

    assert session.config.target_chapters == 3
    assert session.config.mode == AutoWriteMode.BATCH


def test_list_sessions():
    engine = AutonomousWritingEngine(chapter_service=MockChapterService())
    engine.create_session("novel_1")
    engine.create_session("novel_1")
    engine.create_session("novel_2")

    all_sessions = engine.list_sessions()
    assert len(all_sessions) == 3

    novel1_sessions = engine.list_sessions("novel_1")
    assert len(novel1_sessions) == 2


@pytest.mark.asyncio
async def test_get_status():
    engine = AutonomousWritingEngine(chapter_service=MockChapterService())
    session = engine.create_session("test_novel")

    status = engine.get_status(session.session_id)
    assert status is not None
    assert status.session_id == session.session_id

    assert engine.get_status("nonexistent") is None


@pytest.mark.asyncio
async def test_cancel_nonexistent_session():
    engine = AutonomousWritingEngine(chapter_service=MockChapterService())
    result = await engine.cancel("nonexistent")
    assert result is False
