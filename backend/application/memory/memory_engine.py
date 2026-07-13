from __future__ import annotations

from domain.memory.beat_lock import BeatLock
from domain.memory.clue_lock import ClueLock
from domain.memory.fact_lock import FactLock
from infrastructure.persistence.chapter_repo import ChapterRepository
from infrastructure.persistence.character_repo import CharacterRepository
from infrastructure.persistence.knowledge_repo import KnowledgeRepository
from infrastructure.persistence.memory_repo import MemoryRepository


class MemoryEngine:
    def __init__(
        self,
        memory_repo: MemoryRepository,
        knowledge_repo: KnowledgeRepository | None = None,
        character_repo: CharacterRepository | None = None,
        chapter_repo: ChapterRepository | None = None,
    ):
        self.memory_repo = memory_repo
        self.knowledge_repo = knowledge_repo
        self.character_repo = character_repo
        self.chapter_repo = chapter_repo

    def build_t0_iron_lock(self, novel_id: str, up_to_chapter: int) -> dict:
        fact_locks = self.memory_repo.get_fact_locks(novel_id, immutable_only=True)
        beat_locks = self.memory_repo.get_beat_locks(novel_id, up_to_chapter=up_to_chapter)
        clue_locks = self.memory_repo.get_clue_locks(novel_id, statuses=["planted", "developing"])

        iron_facts: dict[str, list[dict]] = {}
        for fact in fact_locks:
            if fact.fact_type not in iron_facts:
                iron_facts[fact.fact_type] = []
            iron_facts[fact.fact_type].append(
                {"key": fact.key, "value": fact.value, "locked_at_chapter": fact.locked_at_chapter}
            )

        return {
            "facts": iron_facts,
            "beats": [
                {
                    "chapter_index": beat.chapter_index,
                    "beat_type": beat.beat_type,
                    "description": beat.description,
                    "significance": beat.significance,
                    "characters": beat.characters,
                }
                for beat in beat_locks
            ],
            "clues": [
                {
                    "title": clue.title,
                    "description": clue.description,
                    "status": clue.status,
                    "planted_chapter": clue.planted_chapter,
                    "urgency": clue.urgency,
                }
                for clue in clue_locks
            ],
        }

    def lock_fact(
        self, novel_id: str, fact_type: str, key: str, value: str, locked_at_chapter: int, is_immutable: bool = True
    ) -> FactLock:
        fact = FactLock(
            novel_id=novel_id,
            fact_type=fact_type,
            key=key,
            value=value,
            locked_at_chapter=locked_at_chapter,
            is_immutable=is_immutable,
            source="memory_engine",
        )
        self.memory_repo.bulk_upsert_facts([fact])
        return fact

    def lock_beat(
        self,
        novel_id: str,
        chapter_id: str,
        chapter_index: int,
        beat_type: str,
        description: str,
        significance: str = "major",
        characters: list = None,
    ) -> BeatLock:
        beat = BeatLock(
            novel_id=novel_id,
            chapter_id=chapter_id,
            chapter_index=chapter_index,
            beat_type=beat_type,
            description=description,
            significance=significance,
            characters=characters or [],
        )
        self.memory_repo.bulk_upsert_beats([beat])
        return beat

    def lock_clue(
        self,
        novel_id: str,
        clue_type: str,
        title: str,
        description: str,
        planted_chapter: int,
        related_characters: list = None,
        urgency: str = "normal",
    ) -> ClueLock:
        clue = ClueLock(
            novel_id=novel_id,
            clue_type=clue_type,
            title=title,
            description=description,
            status="planted",
            planted_chapter=planted_chapter,
            related_characters=related_characters or [],
            urgency=urgency,
        )
        self.memory_repo.bulk_upsert_clues([clue])
        return clue

    def update_clue_status(self, novel_id: str, clue_id: str, new_status: str, revealed_chapter: int = None) -> None:
        clues = self.memory_repo.get_clue_locks(novel_id)
        clue = next((c for c in clues if c.id == clue_id), None)
        if clue:
            clue.status = new_status
            if revealed_chapter:
                clue.revealed_chapter = revealed_chapter
            self.memory_repo.bulk_upsert_clues([clue])

    def get_fact_locks(self, novel_id: str, fact_type: str = None) -> list[FactLock]:
        return self.memory_repo.get_fact_locks(novel_id, fact_type=fact_type)

    def get_beat_locks(self, novel_id: str, up_to_chapter: int = None) -> list[BeatLock]:
        return self.memory_repo.get_beat_locks(novel_id, up_to_chapter=up_to_chapter)

    def get_clue_locks(self, novel_id: str, statuses: list[str] = None) -> list[ClueLock]:
        return self.memory_repo.get_clue_locks(novel_id, statuses=statuses)

    def get_character_whitelist(self, novel_id: str) -> list[str]:
        fact_locks = self.memory_repo.get_fact_locks(novel_id, fact_type="character_status")
        whitelist = []
        for fact in fact_locks:
            if fact.value == "alive" or fact.value == "active":
                whitelist.append(fact.key)
        return whitelist

    def get_death_list(self, novel_id: str) -> list[str]:
        fact_locks = self.memory_repo.get_fact_locks(novel_id, fact_type="character_status")
        death_list = []
        for fact in fact_locks:
            if fact.value == "dead":
                death_list.append(fact.key)
        return death_list

    def get_relationship_map(self, novel_id: str) -> dict[str, list[str]]:
        if not self.knowledge_repo:
            return {}
        triples = self.knowledge_repo.get_triples(novel_id, predicate="related_to")
        relationship_map: dict[str, list[str]] = {}
        for triple in triples:
            if triple.subject not in relationship_map:
                relationship_map[triple.subject] = []
            relationship_map[triple.subject].append(triple.object)
        return relationship_map

    def check_consistency(self, novel_id: str, new_content: str) -> tuple[bool, list[str]]:
        violations = []

        death_list = self.get_death_list(novel_id)
        for dead_char in death_list:
            if dead_char in new_content:
                violations.append(f"已死亡角色 '{dead_char}' 在新内容中出现")

        immutable_facts = self.get_fact_locks(novel_id)
        for fact in immutable_facts:
            if fact.value not in new_content:
                violations.append(f"锁定事实 '{fact.key}: {fact.value}' 未在新内容中体现")

        return len(violations) == 0, violations

    def generate_memory_prompt(self, novel_id: str, up_to_chapter: int) -> str:
        iron_lock = self.build_t0_iron_lock(novel_id, up_to_chapter)

        prompt = "【记忆锁定 - 以下内容不可违背】\n\n"

        if iron_lock["facts"]:
            prompt += "一、核心事实\n"
            for fact_type, facts in iron_lock["facts"].items():
                prompt += f"\n  {fact_type}:\n"
                for fact in facts:
                    prompt += f"    - {fact['key']}: {fact['value']}\n"

        if iron_lock["beats"]:
            prompt += "\n二、已完成节拍\n"
            for beat in iron_lock["beats"]:
                prompt += f"  第{beat['chapter_index']}章 [{beat['beat_type']}]: {beat['description']}\n"

        if iron_lock["clues"]:
            prompt += "\n三、待收伏笔\n"
            for clue in iron_lock["clues"]:
                prompt += f"  [{clue['urgency']}] {clue['title']}: {clue['description']} (第{clue['planted_chapter']}章埋下)\n"

        return prompt

    def get_pending_clues(self, novel_id: str) -> list[ClueLock]:
        return self.memory_repo.get_clue_locks(novel_id, statuses=["planted", "developing"])
