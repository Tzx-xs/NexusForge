import re

from .context_models import (
    ContentContext,
    FourLayerOnion,
    OutlineContext,
    RelevantHistoryChunk,
    ReviewContext,
    T0IronLock,
    T1GlobalContext,
    T2NearContext,
    T3CurrentContext,
)


class ContextBuilder:
    """上下文构建器。

    支持四层洋葱模型、向量语义检索（BLOCK-06）和 Token 预算分配（M-12）。
    """

    def __init__(
        self,
        novel_repo,
        chapter_repo,
        character_repo,
        setting_repo,
        memory_engine=None,
        vector_store=None,
        budget_allocator=None,
    ):
        self.novel_repo = novel_repo
        self.chapter_repo = chapter_repo
        self.character_repo = character_repo
        self.setting_repo = setting_repo
        self.memory_engine = memory_engine
        self.vector_store = vector_store      # BLOCK-06: 向量语义检索
        self.budget_allocator = budget_allocator  # M-12: Token 预算分配

    def build_outline_context(self, novel_id: str, chapter_id: str | None = None) -> OutlineContext:
        novel = self.novel_repo.get_by_id(novel_id)
        if not novel:
            return OutlineContext()

        t1 = self._build_t1(novel_id)
        t2 = self._build_t2_for_outline(novel_id, chapter_id)

        return OutlineContext(
            novel_id=novel.id,
            novel_title=novel.title,
            novel_genre=novel.genre or "",
            novel_premise=novel.premise or "",
            t1=t1,
            t2=t2,
        )

    def build_content_context(self, novel_id: str, chapter_id: str) -> ContentContext:
        novel = self.novel_repo.get_by_id(novel_id)
        chapter = self.chapter_repo.get_by_id(chapter_id)
        if not novel or not chapter:
            return ContentContext()

        t1 = self._build_t1(novel_id)
        t2 = self._build_t2_for_content(novel_id, chapter)
        t3 = self._build_t3(chapter)

        return ContentContext(
            novel_id=novel.id,
            novel_title=novel.title,
            novel_genre=novel.genre or "",
            novel_premise=novel.premise or "",
            t1=t1,
            t2=t2,
            t3=t3,
        )

    def build_review_context(self, chapter_id: str, chapter_content: str = "") -> ReviewContext:
        chapter = self.chapter_repo.get_by_id(chapter_id)
        if not chapter:
            return ReviewContext()

        novel_id = chapter.novel_id
        novel = self.novel_repo.get_by_id(novel_id)
        if not novel:
            return ReviewContext()

        t1 = self._build_t1(novel_id)
        t2 = self._build_t2_for_content(novel_id, chapter)
        t3 = self._build_t3(chapter)

        content = chapter_content or chapter.content or ""

        return ReviewContext(
            novel_id=novel.id,
            novel_title=novel.title,
            novel_genre=novel.genre or "",
            novel_premise=novel.premise or "",
            t1=t1,
            t2=t2,
            t3=t3,
            chapter_content=content,
            target_length=3000,
        )

    def format_system_prompt(self, context) -> str:
        parts = []

        parts.append("【小说信息】")
        parts.append(f"标题：{context.novel_title}")
        if context.novel_genre:
            parts.append(f"类型：{context.novel_genre}")
        if context.novel_premise:
            parts.append(f"核心设定：{context.novel_premise}")

        t1 = getattr(context, "t1", None)
        if t1:
            parts.append("")
            parts.append("【世界观设定】")
            if t1.world_setting_text:
                parts.append(t1.world_setting_text)
            if t1.character_text:
                parts.append("")
                parts.append("【人物设定】")
                parts.append(t1.character_text)

        t2 = getattr(context, "t2", None)
        if t2 and t2.previous_chapter_summary:
            parts.append("")
            parts.append("【前文概要】")
            parts.append(t2.previous_chapter_summary)

        return "\n".join(parts)

    def to_template_dict(self, context) -> dict:
        result = {
            "novel_id": context.novel_id,
            "novel_title": context.novel_title,
            "novel_genre": context.novel_genre,
            "novel_premise": context.novel_premise,
        }

        t1 = getattr(context, "t1", None)
        if t1:
            ws = t1.world_setting_text or "暂无世界观设定"
            cs = t1.character_text or "暂无人物设定"
            result["world_settings"] = ws
            result["world_setting"] = ws
            result["characters"] = cs

        t2 = getattr(context, "t2", None)
        if t2:
            result["previous_summary"] = t2.previous_chapter_summary or ""
            result["chapter_number"] = t2.chapter_number
            # BLOCK-06: 语义检索结果输出
            if hasattr(t2, "relevant_history") and t2.relevant_history:
                result["relevant_history"] = [
                    {
                        "text": h.text,
                        "chapter_id": h.chapter_id,
                        "similarity": round(h.similarity_score, 3),
                        "source": h.source,
                    }
                    for h in t2.relevant_history
                ]

        t3 = getattr(context, "t3", None)
        if t3:
            result["chapter_title"] = t3.chapter_title
            result["chapter_outline"] = t3.chapter_outline
            result["core_event"] = t3.core_event
            result["conflict"] = t3.conflict
            result["cool_point"] = t3.cool_point
            result["ending_hook"] = t3.ending_hook

        review_content = getattr(context, "chapter_content", None)
        if review_content:
            result["chapter_content"] = review_content

        result.setdefault("target_words", 3000)

        # M-12: 构建完成后应用 Token 预算分配
        if self.budget_allocator:
            try:
                actual_usage = {
                    "t0_iron_lock": len(str(result.get("iron_lock", ""))) // 2,
                    "t1_bible_core": (len(str(result.get("world_settings", ""))) + len(str(result.get("characters", "")))) // 2,
                    "t2_recent_context": len(str(result.get("previous_summary", "")) + str(result.get("relevant_history", ""))) // 2,
                    "t3_current_plan": len(str(result.get("chapter_outline", ""))) // 2,
                }
                allocated = self.budget_allocator.allocate(actual_usage)
                # 按分配结果裁剪各层文本
                result["_budget"] = allocated
            except Exception:
                import logging
                logging.getLogger(__name__).warning("Token 预算分配失败，跳过裁剪", exc_info=True)

        return result

    def build_generation_context(self, novel_id: str, chapter_id: str) -> dict:
        content_ctx = self.build_content_context(novel_id, chapter_id)
        return self.to_template_dict(content_ctx)

    def build_t0_iron_lock(self, novel_id: str, up_to_chapter: int | None = None) -> T0IronLock:
        if not self.memory_engine:
            return T0IronLock()

        t0_data = self.memory_engine.build_t0_iron_lock(novel_id, up_to_chapter or 9999)
        whitelist = self.memory_engine.get_character_whitelist(novel_id)
        death_list = self.memory_engine.get_death_list(novel_id)
        rel_map = self.memory_engine.get_relationship_map(novel_id)

        return T0IronLock(
            fact_locks=[f.__dict__ for f in t0_data.get("fact_locks", [])],
            beat_locks=[b.__dict__ for b in t0_data.get("beat_locks", [])],
            clue_locks=[c.__dict__ for c in t0_data.get("clue_locks", [])],
            character_whitelist=whitelist,
            death_list=death_list,
            relationship_map=rel_map,
        )

    def build_four_layer_onion(
        self, novel_id: str, chapter_id: str, up_to_chapter: int | None = None
    ) -> FourLayerOnion:
        novel = self.novel_repo.get_by_id(novel_id)
        chapter = self.chapter_repo.get_by_id(chapter_id)
        if not novel or not chapter:
            return FourLayerOnion()

        t0 = self.build_t0_iron_lock(novel_id, up_to_chapter)
        t1 = self._build_t1(novel_id)
        t2 = self._build_t2_for_content(novel_id, chapter)
        t3 = self._build_t3(chapter)

        return FourLayerOnion(t0=t0, t1=t1, t2=t2, t3=t3)

    def _build_t1(self, novel_id: str) -> T1GlobalContext:
        characters = self.character_repo.list_by_novel(novel_id)
        settings = self.setting_repo.list_by_novel(novel_id)

        main_chars = []
        for c in characters:
            char_dict = {
                "id": c.id,
                "name": c.name,
                "role": c.role,
                "description": c.description or "",
                "personality": c.personality or "",
                "appearance": c.appearance or "",
                "background": c.background or "",
                "gender": getattr(c, "gender", "") or "",
                "age": getattr(c, "age", "") or "",
            }
            if c.role in ("主角", "女主角", "男主角"):
                main_chars.append(char_dict)

        world_rules = []
        for s in settings:
            if s.setting_type == "rule" and s.description:
                world_rules.append(s.description)

        return T1GlobalContext(
            world_rules=world_rules,
            main_characters=main_chars,
            world_setting_text=self._format_settings(settings),
            character_text=self._format_characters(characters),
        )

    def _build_t2_for_outline(self, novel_id: str, chapter_id: str | None = None) -> T2NearContext:
        all_chapters = self.chapter_repo.list_by_novel(novel_id)
        all_chapters.sort(key=lambda c: c.number)

        if not all_chapters:
            return T2NearContext(chapter_number=1)

        if chapter_id:
            current = next((c for c in all_chapters if c.id == chapter_id), None)
            chapter_num = current.number if current else len(all_chapters) + 1
        else:
            chapter_num = len(all_chapters) + 1

        previous_chapter = None
        for ch in all_chapters:
            if ch.number == chapter_num - 1:
                previous_chapter = ch
                break

        recent_chapters = []
        for ch in all_chapters:
            if ch.number < chapter_num and ch.number >= chapter_num - 3:
                recent_chapters.append(
                    {
                        "id": ch.id,
                        "number": ch.number,
                        "title": ch.title,
                        "outline": ch.outline or "",
                    }
                )

        previous_summary = ""
        if previous_chapter:
            previous_summary = self._generate_summary(previous_chapter)

        return T2NearContext(
            previous_chapter_summary=previous_summary,
            chapter_number=chapter_num,
            recent_chapters=recent_chapters,
        )

    def _build_t2_for_content(self, novel_id: str, chapter) -> T2NearContext:
        all_chapters = self.chapter_repo.list_by_novel(novel_id)
        all_chapters.sort(key=lambda c: c.number)

        chapter_num = chapter.number if chapter else 1

        previous_chapter = None
        for ch in all_chapters:
            if ch.number == chapter_num - 1:
                previous_chapter = ch
                break

        recent_chapters = []
        for ch in all_chapters:
            if ch.number < chapter_num and ch.number >= chapter_num - 3:
                recent_chapters.append(
                    {
                        "id": ch.id,
                        "number": ch.number,
                        "title": ch.title,
                        "outline": ch.outline or "",
                    }
                )

        previous_summary = ""
        if previous_chapter:
            previous_summary = self._generate_summary(previous_chapter)

        # BLOCK-06: 向量语义检索 — 对前 3 章内容发起语义检索
        relevant_history: list[RelevantHistoryChunk] = []
        if self.vector_store and previous_chapter:
            try:
                # 以前章摘要 + 当前章纲作为检索 query
                query_text = previous_summary or ""
                if chapter and hasattr(chapter, "outline") and chapter.outline:
                    query_text = chapter.outline[:200] + " " + query_text

                if query_text.strip():
                    search_results = self.vector_store.search(
                        novel_id=novel_id, query=query_text[:500], top_k=3
                    )
                    for result in search_results:
                        relevant_history.append(
                            RelevantHistoryChunk(
                                chunk_id=result.get("id", ""),
                                text=result.get("text", "")[:300],  # 前 300 字摘要
                                chapter_id=result.get("chapter_id", ""),
                                chapter_number=0,
                                similarity_score=result.get("score", 0.0),
                                source="vector_search",
                            )
                        )
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning("向量检索失败: %s", e, exc_info=True)

        return T2NearContext(
            previous_chapter_summary=previous_summary,
            chapter_number=chapter_num,
            recent_chapters=recent_chapters,
            relevant_history=relevant_history,
        )

    def _build_t3(self, chapter) -> T3CurrentContext:
        outline = chapter.outline or ""
        title = chapter.title or ""

        return T3CurrentContext(
            chapter_title=title,
            chapter_outline=outline,
            core_event=self._extract_section(outline, "核心事件", "核心情节"),
            conflict=self._extract_section(outline, "冲突", "主要矛盾"),
            cool_point=self._extract_section(outline, "爽点", "亮点"),
            ending_hook=self._extract_section(outline, "章末钩子", "悬念"),
        )

    def _format_characters(self, characters) -> str:
        if not characters:
            return "暂无人物设定"
        lines = []
        for char in characters:
            # 组装角色标签：角色 + 性别 + 年龄
            role_parts = [char.role]
            if hasattr(char, 'gender') and char.gender:
                role_parts.append(char.gender)
            if hasattr(char, 'age') and char.age:
                role_parts.append(char.age)
            role_label = "(" + ", ".join(str(p) for p in role_parts) + ")"
            lines.append(f"【{char.name}】{role_label}")
            if char.description:
                lines.append(f"  简介：{char.description}")
            if char.personality:
                lines.append(f"  性格：{char.personality}")
            if char.appearance:
                lines.append(f"  外貌：{char.appearance}")
            if char.background:
                lines.append(f"  背景：{char.background}")
        return "\n".join(lines)

    def _format_settings(self, settings) -> str:
        if not settings:
            return "暂无世界观设定"
        grouped: dict[str, list] = {}
        for setting in settings:
            stype = setting.setting_type or "other"
            if stype not in grouped:
                grouped[stype] = []
            grouped[stype].append(setting)

        lines = []
        type_names = {
            "geography": "地理设定",
            "faction": "势力设定",
            "rule": "规则设定",
            "history": "历史设定",
            "culture": "文化设定",
            "power": "力量体系",
            "society": "社会设定",
            "dark_line": "暗线设定",
            "other": "其他设定",
        }
        for stype, items in grouped.items():
            type_name = type_names.get(stype, stype)
            lines.append(f"## {type_name}")
            for item in items:
                lines.append(f"【{item.name}】")
                if item.description:
                    lines.append(f"  {item.description}")
        return "\n".join(lines)

    def _generate_summary(self, chapter) -> str:
        if not chapter:
            return ""
        content = chapter.content or ""
        if len(content) <= 200:
            return content
        return content[:200] + "..."

    def _extract_section(self, outline: str, *keywords) -> str:
        if not outline:
            return ""
        for kw in keywords:

            pattern = rf"(?:{kw})[：:]\s*(.+?)(?:\n\s*\n|$)"
            match = re.search(pattern, outline)
            if match:
                return match.group(1).strip()
        return ""
