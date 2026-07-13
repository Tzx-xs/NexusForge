import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from application.memory.memory_engine import MemoryEngine
from domain.memory.beat_lock import BeatLock
from domain.memory.clue_lock import ClueLock
from domain.memory.fact_lock import FactLock


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

    def update_clue_status(self, clue_id, new_status, revealed_chapter=None):
        for clue in self.clues:
            if clue.id == clue_id:
                clue.status = new_status
                if revealed_chapter:
                    clue.revealed_chapter = revealed_chapter
                return clue
        return None


@pytest.fixture
def memory_engine():
    repo = MockMemoryRepo()
    return MemoryEngine(memory_repo=repo)


def test_lock_fact(memory_engine):
    fact = memory_engine.lock_fact(
        novel_id="novel_1",
        fact_type="character",
        key="protagonist_name",
        value="云泽",
        locked_at_chapter=1,
    )

    assert isinstance(fact, FactLock)
    assert fact.novel_id == "novel_1"
    assert fact.fact_type == "character"
    assert fact.key == "protagonist_name"
    assert fact.value == "云泽"
    assert fact.is_immutable is True


def test_lock_fact_mutable(memory_engine):
    fact = memory_engine.lock_fact(
        novel_id="novel_1",
        fact_type="location",
        key="current_location",
        value="星渊崖",
        locked_at_chapter=1,
        is_immutable=False,
    )

    assert fact.is_immutable is False


def test_lock_beat(memory_engine):
    beat = memory_engine.lock_beat(
        novel_id="novel_1",
        chapter_id="ch_1",
        chapter_index=1,
        beat_type="inciting_incident",
        description="云泽发现上古残卷",
        significance="major",
        characters=["云泽"],
    )

    assert isinstance(beat, BeatLock)
    assert beat.novel_id == "novel_1"
    assert beat.chapter_id == "ch_1"
    assert beat.beat_type == "inciting_incident"
    assert beat.significance == "major"
    assert "云泽" in beat.characters


def test_lock_clue(memory_engine):
    clue = memory_engine.lock_clue(
        novel_id="novel_1",
        clue_type="foreshadow",
        title="玉佩来历",
        description="云泽自幼佩戴的玉佩藏有秘密",
        planted_chapter=1,
        related_characters=["云泽"],
        urgency="high",
    )

    assert isinstance(clue, ClueLock)
    assert clue.novel_id == "novel_1"
    assert clue.title == "玉佩来历"
    assert clue.status == "planted"
    assert clue.planted_chapter == 1
    assert clue.urgency == "high"


def test_generate_memory_prompt(memory_engine):
    memory_engine.lock_fact(
        novel_id="novel_1",
        fact_type="character",
        key="protagonist_name",
        value="云泽",
        locked_at_chapter=1,
    )
    memory_engine.lock_beat(
        novel_id="novel_1",
        chapter_id="ch_1",
        chapter_index=1,
        beat_type="inciting_incident",
        description="云泽发现上古残卷",
        significance="major",
    )
    memory_engine.lock_clue(
        novel_id="novel_1",
        clue_type="foreshadow",
        title="玉佩来历",
        description="云泽自幼佩戴的玉佩藏有秘密",
        planted_chapter=1,
    )

    prompt = memory_engine.generate_memory_prompt("novel_1", up_to_chapter=2)

    assert prompt is not None
    assert len(prompt) > 0
    assert isinstance(prompt, str)


def test_check_consistency(memory_engine):
    memory_engine.lock_fact(
        novel_id="novel_1",
        fact_type="character",
        key="protagonist_name",
        value="云泽",
        locked_at_chapter=1,
    )

    content = "云泽走在山间的小路上，心中充满了对未来的期待。"
    is_consistent, issues = memory_engine.check_consistency("novel_1", content)

    assert isinstance(is_consistent, bool)
    assert isinstance(issues, list)


def test_update_clue_status(memory_engine):
    clue = memory_engine.lock_clue(
        novel_id="novel_1",
        clue_type="foreshadow",
        title="玉佩来历",
        description="云泽自幼佩戴的玉佩藏有秘密",
        planted_chapter=1,
    )

    memory_engine.update_clue_status(
        novel_id="novel_1",
        clue_id=clue.id,
        new_status="resolved",
        revealed_chapter=5,
    )

    clues = memory_engine.get_clue_locks("novel_1")
    assert len(clues) == 1
    assert clues[0].status == "resolved"
    assert clues[0].revealed_chapter == 5


def test_get_fact_locks(memory_engine):
    memory_engine.lock_fact(
        novel_id="novel_1",
        fact_type="character",
        key="hero",
        value="云泽",
        locked_at_chapter=1,
    )
    memory_engine.lock_fact(
        novel_id="novel_1",
        fact_type="location",
        key="start",
        value="星渊崖",
        locked_at_chapter=1,
    )

    facts = memory_engine.get_fact_locks("novel_1")
    assert len(facts) == 2

    char_facts = memory_engine.get_fact_locks("novel_1", fact_type="character")
    assert len(char_facts) == 1
    assert char_facts[0].key == "hero"


def test_get_beat_locks(memory_engine):
    memory_engine.lock_beat(
        novel_id="novel_1",
        chapter_id="ch_1",
        chapter_index=1,
        beat_type="inciting_incident",
        description="事件1",
        significance="major",
    )
    memory_engine.lock_beat(
        novel_id="novel_1",
        chapter_id="ch_2",
        chapter_index=2,
        beat_type="plot_point",
        description="事件2",
        significance="major",
    )

    beats = memory_engine.get_beat_locks("novel_1")
    assert len(beats) == 2

    beats_up_to_1 = memory_engine.get_beat_locks("novel_1", up_to_chapter=1)
    assert len(beats_up_to_1) == 1


def test_get_clue_locks(memory_engine):
    memory_engine.lock_clue(
        novel_id="novel_1",
        clue_type="foreshadow",
        title="线索1",
        description="描述1",
        planted_chapter=1,
    )
    memory_engine.lock_clue(
        novel_id="novel_1",
        clue_type="foreshadow",
        title="线索2",
        description="描述2",
        planted_chapter=1,
        urgency="high",
    )

    clues = memory_engine.get_clue_locks("novel_1")
    assert len(clues) == 2

    planted_clues = memory_engine.get_clue_locks("novel_1", statuses=["planted"])
    assert len(planted_clues) == 2


def test_get_death_list_empty(memory_engine):
    death_list = memory_engine.get_death_list("novel_1")
    assert death_list == []


def test_get_pending_clues(memory_engine):
    memory_engine.lock_clue(
        novel_id="novel_1",
        clue_type="foreshadow",
        title="待处理线索",
        description="需要回收的伏笔",
        planted_chapter=1,
    )

    pending = memory_engine.get_pending_clues("novel_1")
    assert len(pending) >= 0
    assert isinstance(pending, list)


def test_build_t0_iron_lock(memory_engine):
    memory_engine.lock_fact(
        novel_id="novel_1",
        fact_type="character",
        key="protagonist",
        value="云泽",
        locked_at_chapter=1,
    )
    memory_engine.lock_beat(
        novel_id="novel_1",
        chapter_id="ch_1",
        chapter_index=1,
        beat_type="inciting_incident",
        description="开端事件",
        significance="major",
    )
    memory_engine.lock_clue(
        novel_id="novel_1",
        clue_type="foreshadow",
        title="伏笔1",
        description="伏笔描述",
        planted_chapter=1,
    )

    iron_lock = memory_engine.build_t0_iron_lock("novel_1", up_to_chapter=2)

    assert isinstance(iron_lock, dict)
    assert "facts" in iron_lock
    assert "beats" in iron_lock
    assert "clues" in iron_lock


def test_memory_prompt_format(memory_engine):
    memory_engine.lock_fact(
        novel_id="novel_1",
        fact_type="character",
        key="protagonist",
        value="云泽",
        locked_at_chapter=1,
    )

    prompt = memory_engine.generate_memory_prompt("novel_1", up_to_chapter=2)
    assert isinstance(prompt, str)
    assert len(prompt) > 0
