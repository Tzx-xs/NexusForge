import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from application.audit.audit_service import QualityAuditService
from application.memory.memory_engine import MemoryEngine
from application.services.export_service import ExportFormat, ExportOptions, ExportService
from application.voice.voice_service import VoiceService
from engine.pipeline.context import PipelineContext, PipelineStatus, StepResult


class MockMemoryRepo:
    def __init__(self):
        self.facts = []
        self.beats = []
        self.clues = []

    def bulk_upsert_facts(self, facts):
        self.facts.extend(facts)

    def bulk_upsert_beats(self, beats):
        self.beats.extend(beats)

    def bulk_upsert_clues(self, clues):
        for clue in clues:
            existing = next((c for c in self.clues if c.id == clue.id), None)
            if existing:
                idx = self.clues.index(existing)
                self.clues[idx] = clue
            else:
                self.clues.append(clue)

    def get_fact_locks(self, novel_id, fact_type=None, immutable_only=False):
        result = [f for f in self.facts if f.novel_id == novel_id]
        if fact_type:
            result = [f for f in result if f.fact_type == fact_type]
        if immutable_only:
            result = [f for f in result if f.is_immutable]
        return result

    def get_beat_locks(self, novel_id, up_to_chapter=None):
        result = [b for b in self.beats if b.novel_id == novel_id]
        if up_to_chapter:
            result = [b for b in result if b.chapter_index <= up_to_chapter]
        return result

    def get_clue_locks(self, novel_id, statuses=None):
        result = [c for c in self.clues if c.novel_id == novel_id]
        if statuses:
            result = [c for c in result if c.status in statuses]
        return result


class MockNovelRepo:
    def get_by_id(self, novel_id):
        return type(
            "MockNovel",
            (),
            {
                "id": novel_id,
                "title": "星渊传说",
                "premise": "一个关于少年守护世界的故事",
                "author": "测试作者",
            },
        )()


class MockChapterRepo:
    def list_by_novel(self, novel_id):
        return [
            type(
                "MockChapter",
                (),
                {
                    "id": "ch_1",
                    "number": 1,
                    "title": "第一章 命运的开端",
                    "content": "云泽站在星渊崖边，望着下方无尽的深渊。今天是他十六岁的生日。\n他不知道的是，从今天起，他的人生将彻底改变。",
                    "word_count": 2000,
                    "status": "completed",
                },
            )(),
            type(
                "MockChapter",
                (),
                {
                    "id": "ch_2",
                    "number": 2,
                    "title": "第二章 初入宗门",
                    "content": "第二天，云泽踏上了前往青云宗的路。师叔在路口等他。\n青云宗是这片大陆上最著名的修仙宗门。",
                    "word_count": 2500,
                    "status": "completed",
                },
            )(),
            type(
                "MockChapter",
                (),
                {
                    "id": "ch_3",
                    "number": 3,
                    "title": "第三章 试炼",
                    "content": "云泽参加了入门试炼。他遇到了苏晚。\n两人一起通过了试炼，成为了外门弟子。",
                    "word_count": 3000,
                    "status": "completed",
                },
            )(),
        ]


@pytest.fixture
def sample_text():
    return """云泽站在星渊崖边，望着下方无尽的深渊。今天是他十六岁的生日。
他不知道的是，从今天起，他的人生将彻底改变。
师叔走了过来，拍了拍他的肩膀。"小泽，准备好了吗？"
云泽点了点头，眼中闪过一丝坚定。"""


@pytest.fixture
def memory_engine():
    return MemoryEngine(memory_repo=MockMemoryRepo())


@pytest.fixture
def export_service():
    return ExportService(
        novel_repo=MockNovelRepo(),
        chapter_repo=MockChapterRepo(),
    )


@pytest.fixture
def quality_service():
    return QualityAuditService.with_default_guards()


@pytest.fixture
def voice_service():
    return VoiceService()


@pytest.mark.asyncio
async def test_memory_quality_integration(memory_engine, quality_service, sample_text):
    novel_id = "test_novel_1"

    memory_engine.lock_fact(
        novel_id=novel_id,
        fact_type="character",
        key="protagonist",
        value="云泽",
        locked_at_chapter=1,
    )
    memory_engine.lock_fact(
        novel_id=novel_id,
        fact_type="character",
        key="mentor",
        value="师叔",
        locked_at_chapter=1,
    )

    memory_prompt = memory_engine.generate_memory_prompt(novel_id, up_to_chapter=2)
    assert isinstance(memory_prompt, str)
    assert len(memory_prompt) > 0

    report = await quality_service.run_audit(
        sample_text,
        context={
            "character_names": ["云泽", "师叔"],
            "memory_prompt": memory_prompt,
        },
    )

    assert report is not None
    assert 0 <= report.overall_score <= 100
    assert len(report.guard_results) == 8


def test_memory_voice_export_workflow(memory_engine, voice_service, export_service, sample_text):
    novel_id = "test_novel_2"

    memory_engine.lock_fact(
        novel_id=novel_id,
        fact_type="character",
        key="protagonist",
        value="云泽",
        locked_at_chapter=1,
    )
    memory_engine.lock_beat(
        novel_id=novel_id,
        chapter_id="ch_1",
        chapter_index=1,
        beat_type="inciting_incident",
        description="云泽发现自己的命运",
        significance="major",
        characters=["云泽"],
    )
    memory_engine.lock_clue(
        novel_id=novel_id,
        clue_type="foreshadow",
        title="玉佩来历",
        description="云泽的玉佩来历不明",
        planted_chapter=1,
        related_characters=["云泽"],
        urgency="high",
    )

    iron_lock = memory_engine.build_t0_iron_lock(novel_id, up_to_chapter=2)
    assert "facts" in iron_lock
    assert "beats" in iron_lock
    assert "clues" in iron_lock

    fp = voice_service.extract_fingerprint([sample_text], name="test_fingerprint")
    assert fp is not None
    assert fp.fingerprint_id != ""

    drift_result = voice_service.detect_drift(fp.fingerprint_id, sample_text)
    assert drift_result is not None
    assert drift_result.drifted is False

    style_guide = voice_service.generate_style_guide(fp.fingerprint_id)
    assert style_guide is not None
    assert len(style_guide) > 0

    txt_result = export_service.export_novel(novel_id, ExportOptions(format=ExportFormat.TXT))
    assert len(txt_result) > 0

    md_result = export_service.export_novel(novel_id, ExportOptions(format=ExportFormat.MARKDOWN))
    assert len(md_result) > 0

    html_result = export_service.export_novel(novel_id, ExportOptions(format=ExportFormat.HTML))
    assert len(html_result) > 0


def test_pipeline_context_data_flow():
    ctx = PipelineContext(novel_id="novel_e2e", chapter_id="ch_1")
    ctx.chapter_index = 1

    assert ctx.status == PipelineStatus.PENDING

    ctx.set("context", {"characters": ["云泽"], "locations": ["星渊崖"]})
    ctx.set("chapter_plan", {"title": "第一章 命运的开端", "beats": []})

    assert ctx.get("context")["characters"] == ["云泽"]
    assert ctx.get("nonexistent", "default") == "default"

    result1 = StepResult(step_name="build_context", status="success", output={"context": "..."})
    result2 = StepResult(step_name="generate", status="success", output={"content": "..."})

    ctx.add_step_result(result1)
    ctx.add_step_result(result2)

    assert len(ctx.step_results) == 2
    assert ctx.step_results[0].step_name == "build_context"
    assert ctx.step_results[1].status == "success"


@pytest.mark.asyncio
async def test_quality_voice_cross_validation(quality_service, voice_service, sample_text):
    quality_report = await quality_service.run_audit(sample_text)
    assert quality_report is not None

    fp = voice_service.extract_fingerprint([sample_text], name="validation")
    assert fp is not None

    assert quality_report.overall_score >= 0
    assert fp.lexical_richness > 0


@pytest.mark.asyncio
async def test_full_chapter_processing_pipeline(memory_engine, quality_service, voice_service, sample_text):
    novel_id = "full_pipeline_test"
    chapter_number = 1

    memory_engine.lock_fact(
        novel_id=novel_id,
        fact_type="character",
        key="protagonist",
        value="云泽",
        locked_at_chapter=chapter_number,
    )

    memory_prompt = memory_engine.generate_memory_prompt(novel_id, up_to_chapter=chapter_number)
    assert len(memory_prompt) > 0

    quality_report = await quality_service.run_audit(
        sample_text,
        context={"character_names": ["云泽"], "memory_prompt": memory_prompt},
    )
    assert quality_report is not None
    assert 0 <= quality_report.overall_score <= 100

    fp = voice_service.extract_fingerprint([sample_text], name=f"ch_{chapter_number}")
    assert fp is not None
    assert fp.source_sample_count == 1

    drift_result = voice_service.detect_drift(fp.fingerprint_id, sample_text)
    assert drift_result is not None
    assert 0 <= drift_result.overall_similarity <= 1

    memory_engine.lock_beat(
        novel_id=novel_id,
        chapter_id=f"ch_{chapter_number}",
        chapter_index=chapter_number,
        beat_type="chapter_end",
        description=f"第{chapter_number}章完成",
        significance="minor",
        characters=["云泽"],
    )

    beats = memory_engine.get_beat_locks(novel_id)
    assert len(beats) >= 1


def test_export_all_formats(export_service):
    novel_id = "export_test"

    formats = [
        ExportFormat.TXT,
        ExportFormat.MARKDOWN,
        ExportFormat.HTML,
        ExportFormat.DOCX,
        ExportFormat.EPUB,
    ]

    for fmt in formats:
        result = export_service.export_novel(
            novel_id,
            ExportOptions(format=fmt, include_title_page=True),
        )
        assert result is not None
        assert len(result) > 0
        assert isinstance(result, bytes)


def test_memory_consistency_check(memory_engine, sample_text):
    novel_id = "consistency_test"

    memory_engine.lock_fact(
        novel_id=novel_id,
        fact_type="character",
        key="protagonist_name",
        value="云泽",
        locked_at_chapter=1,
    )

    is_consistent, issues = memory_engine.check_consistency(novel_id, sample_text)
    assert isinstance(is_consistent, bool)
    assert isinstance(issues, list)


def test_clue_lifecycle(memory_engine):
    novel_id = "clue_lifecycle_test"

    clue = memory_engine.lock_clue(
        novel_id=novel_id,
        clue_type="foreshadow",
        title="测试伏笔",
        description="这是一个测试伏笔",
        planted_chapter=1,
        urgency="normal",
    )
    assert clue.status == "planted"

    clues = memory_engine.get_pending_clues(novel_id)
    assert len(clues) >= 1

    memory_engine.update_clue_status(
        novel_id=novel_id,
        clue_id=clue.id,
        new_status="developing",
    )

    developing_clues = memory_engine.get_clue_locks(novel_id, statuses=["developing"])
    assert len(developing_clues) >= 1

    memory_engine.update_clue_status(
        novel_id=novel_id,
        clue_id=clue.id,
        new_status="resolved",
        revealed_chapter=5,
    )

    all_clues = memory_engine.get_clue_locks(novel_id)
    resolved = [c for c in all_clues if c.status == "resolved"]
    assert len(resolved) >= 1


def test_voice_style_guide_generation(voice_service, sample_text):
    fp = voice_service.extract_fingerprint([sample_text], name="style_test")
    assert fp is not None

    guide = voice_service.generate_style_guide(fp.fingerprint_id)
    assert guide is not None
    assert isinstance(guide, str)
    assert len(guide) > 50

    fps = voice_service.list_fingerprints()
    assert len(fps) >= 1

    retrieved = voice_service.get_fingerprint(fp.fingerprint_id)
    assert retrieved is not None
    assert retrieved.name == "style_test"
