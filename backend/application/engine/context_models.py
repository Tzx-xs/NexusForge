from dataclasses import dataclass, field


@dataclass
class BaseContext:
    novel_id: str = ""
    novel_title: str = ""
    novel_genre: str = ""
    novel_premise: str = ""


@dataclass
class RelevantHistoryChunk:
    """BLOCK-06: 语义检索返回的相关历史片段"""
    chunk_id: str = ""
    text: str = ""
    chapter_id: str = ""
    chapter_number: int = 0
    similarity_score: float = 0.0
    source: str = "vector_search"  # "vector_search" | "db_query"


@dataclass
class T1GlobalContext:
    world_rules: list[str] = field(default_factory=list)
    main_characters: list[dict] = field(default_factory=list)
    world_setting_text: str = ""
    character_text: str = ""


@dataclass
class T2NearContext:
    previous_chapter_summary: str = ""
    chapter_number: int = 0
    recent_chapters: list[dict] = field(default_factory=list)
    relevant_history: list[RelevantHistoryChunk] = field(default_factory=list)  # BLOCK-06: 向量检索结果


@dataclass
class T3CurrentContext:
    chapter_title: str = ""
    chapter_outline: str = ""
    core_event: str = ""
    conflict: str = ""
    cool_point: str = ""
    ending_hook: str = ""


@dataclass
class OutlineContext(BaseContext):
    t1: T1GlobalContext = field(default_factory=T1GlobalContext)
    t2: T2NearContext = field(default_factory=T2NearContext)


@dataclass
class ContentContext(BaseContext):
    t1: T1GlobalContext = field(default_factory=T1GlobalContext)
    t2: T2NearContext = field(default_factory=T2NearContext)
    t3: T3CurrentContext = field(default_factory=T3CurrentContext)


@dataclass
class ReviewContext(BaseContext):
    t1: T1GlobalContext = field(default_factory=T1GlobalContext)
    t2: T2NearContext = field(default_factory=T2NearContext)
    t3: T3CurrentContext = field(default_factory=T3CurrentContext)
    chapter_content: str = ""
    target_length: int = 3000


@dataclass
class T0IronLock:
    fact_locks: list[dict] = field(default_factory=list)
    beat_locks: list[dict] = field(default_factory=list)
    clue_locks: list[dict] = field(default_factory=list)
    character_whitelist: list[str] = field(default_factory=list)
    death_list: list[str] = field(default_factory=list)
    relationship_map: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class FourLayerOnion:
    t0: T0IronLock = field(default_factory=T0IronLock)
    t1: T1GlobalContext = field(default_factory=T1GlobalContext)
    t2: T2NearContext = field(default_factory=T2NearContext)
    t3: T3CurrentContext = field(default_factory=T3CurrentContext)

    def total_tokens_estimate(self, provider=None) -> int:
        """估算四层上下文总 Token 数。

        优先使用 provider.count_tokens()（BLOCK-07 精确计数），
        否则降级为 len(text)//2 粗估。
        """
        import json

        text = json.dumps(
            {
                "t0": self.t0.__dict__,
                "t1": self.t1.__dict__,
                "t2": self.t2.__dict__,
                "t3": self.t3.__dict__,
            },
            ensure_ascii=False,
        )
        if provider:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        future = pool.submit(lambda: provider.count_tokens.__wrapped__(text) if hasattr(provider.count_tokens, '__wrapped__') else len(text) // 2)
                        return future.result(timeout=5)
                else:
                    return len(text) // 2
            except Exception:
                return len(text) // 2
        return len(text) // 2


@dataclass
class ContextBudget:
    total_budget: int = 8000
    t0_budget: int = 800
    t1_budget: int = 1500
    t2_budget: int = 2500
    t3_budget: int = 1200
    used: int = 0
