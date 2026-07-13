from fastapi import APIRouter, Depends, Query

from application.memory.memory_engine import MemoryEngine
from interfaces.dependencies import get_memory_engine

router = APIRouter(prefix="/api/v1", tags=["memory"])


def success_response(data):
    return {"code": 0, "message": "success", "data": data}


@router.get("/novels/{novel_id}/memory/iron-lock")
def get_iron_lock(
    novel_id: str,
    up_to_chapter: int | None = Query(None),
    engine: MemoryEngine = Depends(get_memory_engine),
):
    t0 = engine.build_t0_iron_lock(novel_id, up_to_chapter or 9999)
    whitelist = engine.get_character_whitelist(novel_id)
    death_list = engine.get_death_list(novel_id)
    rel_map = engine.get_relationship_map(novel_id)
    return success_response(
        {
            "fact_locks": [f.__dict__ for f in t0.get("fact_locks", [])],
            "beat_locks": [b.__dict__ for b in t0.get("beat_locks", [])],
            "clue_locks": [c.__dict__ for c in t0.get("clue_locks", [])],
            "character_whitelist": whitelist,
            "death_list": death_list,
            "relationship_map": rel_map,
        }
    )


@router.get("/novels/{novel_id}/memory/facts")
def list_facts(
    novel_id: str,
    fact_type: str | None = Query(None),
    immutable_only: bool = Query(False),
    engine: MemoryEngine = Depends(get_memory_engine),
):
    facts = engine.memory_repo.get_fact_locks(novel_id, fact_type=fact_type, immutable_only=immutable_only)
    return success_response([f.__dict__ for f in facts])


@router.get("/novels/{novel_id}/memory/beats")
def list_beats(
    novel_id: str,
    up_to_chapter: int | None = Query(None),
    engine: MemoryEngine = Depends(get_memory_engine),
):
    beats = engine.memory_repo.get_beat_locks(novel_id, up_to_chapter=up_to_chapter)
    return success_response([b.__dict__ for b in beats])


@router.get("/novels/{novel_id}/memory/clues")
def list_clues(
    novel_id: str,
    status: str | None = Query(None),
    engine: MemoryEngine = Depends(get_memory_engine),
):
    statuses = [s.strip() for s in status.split(",")] if status else None
    clues = engine.memory_repo.get_clue_locks(novel_id, statuses=statuses)
    return success_response([c.__dict__ for c in clues])
