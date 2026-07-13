"""Sprint 3.2 GREEN：全局搜索服务。

跨 5 表（characters / foreshadows / memory_facts / world_settings / chapters）
做 LIKE 查询，供 WorkspaceShell 的 Search 按钮调用。

v0.2.0 优化：优先使用 FTS5 虚拟表 MATCH 查询，回退到 LIKE。
v0.2.1 修复：CJK 查询直接走 LIKE。unicode61 tokenizer 把整个 CJK 字符串当作
单一 token，FTS5 精确短语查询无法做中文子串匹配（"学院" 匹配不到 "青鸾学院"），
因此包含中日韩字符的查询绕过 FTS5 走 LIKE，保证中文搜索召回率。
"""
from __future__ import annotations

import logging
import re

from infrastructure.persistence.database import Database

logger = logging.getLogger(__name__)

# FTS5 特殊字符：这些字符在 FTS5 查询语法中有特殊含义，需要转义
_FTS5_SPECIAL_CHARS = re.compile(r'([*"()+\-\~&|!^\[\]])')

# CJK 统一表意字符范围（含扩展A区与常用区间）
_CJK_PATTERN = re.compile(r'[\u3400-\u9fff\uf900-\ufaff]')


def _escape_fts5_query(query: str) -> str:
    """转义 FTS5 特殊字符，并用双引号包裹以支持精确短语匹配。"""
    escaped = _FTS5_SPECIAL_CHARS.sub(r'\\\1', query)
    return f'"{escaped}"'


def _contains_cjk(query: str) -> bool:
    """判断查询是否包含 CJK 字符。

    含 CJK 字符时 FTS5 精确短语查询无法做子串匹配，应走 LIKE 路径。
    """
    return bool(_CJK_PATTERN.search(query))


class SearchService:
    # L-03 修复：表名白名单，防止未来传入用户控制的列名/表名形成 SQL 注入。
    # 当前所有列名/表名为代码内常量，但白名单提供前置防御。
    ALLOWED_SOURCE_TABLES = frozenset(
        {"characters", "foreshadows", "memory_facts", "world_settings", "chapters"}
    )
    ALLOWED_FTS_TABLES = frozenset(
        {
            "characters_fts",
            "foreshadows_fts",
            "memory_facts_fts",
            "world_settings_fts",
            "chapters_fts",
        }
    )

    def __init__(self, database: Database):
        self.database = database

    def _fts5_table_exists(self, fts_name: str) -> bool:
        """检查 FTS5 虚拟表是否存在。"""
        try:
            result = self.database.query_one(
                "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                (fts_name,),
            )
            return result is not None
        except Exception:
            return False

    def search(self, novel_id: str, query: str) -> dict[str, list[dict]]:
        """跨 5 表搜索，返回 {characters, foreshadows, facts, settings, chapters}。

        v0.2.0: 优先使用 FTS5 MATCH 查询，回退到 LIKE。

        Args:
            novel_id: 小说 ID（按此过滤）
            query: 搜索关键词，空字符串时返回全空数组

        Returns:
            5 类结果的字典，每类是匹配行的列表
        """
        # 空查询：返回 5 类空数组（防御）
        if not query or not query.strip():
            return {
                "characters": [],
                "foreshadows": [],
                "facts": [],
                "settings": [],
                "chapters": [],
            }

        # 长度限制：截断到 200 字符
        if len(query) > 200:
            query = query[:200]

        # CJK 查询直接走 LIKE：unicode61 tokenizer 将整个 CJK 字符串视为单一 token，
        # FTS5 精确短语查询无法做中文子串匹配（"学院" 匹配不到 "青鸾学院"），
        # 绕过 FTS5 保证中文搜索召回率。个人本地创作系统 LIKE 性能足够。
        if _contains_cjk(query):
            return self._like_search(novel_id, query)

        # 非 CJK 查询尝试 FTS5 优先路径
        if self._fts5_table_exists("chapters_fts"):
            try:
                return self._fts5_search(novel_id, query)
            except Exception:
                logger.warning("FTS5 search failed, falling back to LIKE", exc_info=True)

        # 回退到 LIKE
        return self._like_search(novel_id, query)

    def _fts5_search(self, novel_id: str, query: str) -> dict[str, list[dict]]:
        """使用 FTS5 虚拟表进行全文搜索。"""
        fts_query = _escape_fts5_query(query)

        characters = self._fts5_query_table(
            "characters_fts", "characters",
            "id, novel_id, name, role, description",
            novel_id, fts_query,
            limit=20,
        )

        foreshadows = self._fts5_query_table(
            "foreshadows_fts", "foreshadows",
            "id, novel_id, title, description, priority, status, planted_chapter_index",
            novel_id, fts_query,
            limit=20,
        )

        facts = self._fts5_query_table(
            "memory_facts_fts", "memory_facts",
            "id, novel_id, fact_type, key, value, locked_at_chapter",
            novel_id, fts_query,
            limit=20,
        )

        settings = self._fts5_query_table(
            "world_settings_fts", "world_settings",
            "id, novel_id, name, setting_type, description",
            novel_id, fts_query,
            limit=20,
        )

        chapters = self._fts5_query_table(
            "chapters_fts", "chapters",
            "id, novel_id, number, title, outline, status, word_count",
            novel_id, fts_query,
            limit=20,
        )

        return {
            "characters": characters,
            "foreshadows": foreshadows,
            "facts": facts,
            "settings": settings,
            "chapters": chapters,
        }

    def _fts5_query_table(
        self,
        fts_table: str,
        source_table: str,
        select_cols: str,
        novel_id: str,
        fts_query: str,
        limit: int = 20,
    ) -> list[dict]:
        """对单个 FTS5 虚拟表执行 MATCH 查询并关联源表。"""
        # L-03 修复：白名单校验表名，防止未来误传用户控制值导致 SQL 注入。
        if source_table not in self.ALLOWED_SOURCE_TABLES:
            raise ValueError(f"非法源表名: {source_table}")
        if fts_table not in self.ALLOWED_FTS_TABLES:
            raise ValueError(f"非法 FTS 表名: {fts_table}")
        sql = (
            f"SELECT {select_cols} FROM {source_table} "
            f"WHERE novel_id = ? AND rowid IN ("
            f"SELECT rowid FROM {fts_table} WHERE {fts_table} MATCH ?"
            f") LIMIT ?"
        )
        return self.database.query(sql, (novel_id, fts_query, limit))

    def _like_search(self, novel_id: str, query: str) -> dict[str, list[dict]]:
        """回退：使用 LIKE 进行模糊搜索。"""
        # 转义 LIKE 通配符，防止用户输入中的 % 和 _ 被当作通配符
        escaped_query = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

        # 使用 LIKE 模糊匹配，参数化避免 SQL 注入
        like = f"%{escaped_query}%"
        params = (novel_id, like)

        characters = self.database.query(
            "SELECT id, novel_id, name, role, description FROM characters "
            "WHERE novel_id = ? AND (name LIKE ? ESCAPE '\\' OR description LIKE ? ESCAPE '\\')",
            (params[0], like, like),
        )

        foreshadows = self.database.query(
            "SELECT id, novel_id, title, description, priority, status, planted_chapter_index "
            "FROM foreshadows WHERE novel_id = ? AND (title LIKE ? ESCAPE '\\' OR description LIKE ? ESCAPE '\\')",
            (params[0], like, like),
        )

        facts = self.database.query(
            "SELECT id, novel_id, fact_type, key, value, locked_at_chapter "
            "FROM memory_facts WHERE novel_id = ? AND (key LIKE ? ESCAPE '\\' OR value LIKE ? ESCAPE '\\')",
            (params[0], like, like),
        )

        settings = self.database.query(
            "SELECT id, novel_id, name, setting_type, description FROM world_settings "
            "WHERE novel_id = ? AND (name LIKE ? ESCAPE '\\' OR description LIKE ? ESCAPE '\\')",
            (params[0], like, like),
        )

        chapters = self.database.query(
            "SELECT id, novel_id, number, title, outline, status, word_count "
            "FROM chapters WHERE novel_id = ? AND (title LIKE ? ESCAPE '\\' OR outline LIKE ? ESCAPE '\\' OR content LIKE ? ESCAPE '\\')",
            (params[0], like, like, like),
        )

        return {
            "characters": characters,
            "foreshadows": foreshadows,
            "facts": facts,
            "settings": settings,
            "chapters": chapters,
        }
