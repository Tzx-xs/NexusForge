"""AI Invocation 服务

借鉴 PlotPilot application/ai_invocation，简化为：
- record: 记录 LLM 调用
- list_by_novel / list_by_session: 查询
- stats_by_novel: 统计
"""
from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from typing import Any

from .models import InvocationRecord, InvocationStatus

logger = logging.getLogger(__name__)


class InvocationRepo(ABC):
    """Invocation 仓储接口"""

    @abstractmethod
    async def insert(self, record: InvocationRecord) -> None: ...

    @abstractmethod
    async def list_by_novel(self, novel_id: str) -> list[InvocationRecord]: ...

    @abstractmethod
    async def list_by_session(self, session_id: str) -> list[InvocationRecord]: ...


class InMemoryInvocationRepo(InvocationRepo):
    """内存仓储（测试用 + 开发期默认）"""

    def __init__(self):
        self._records: dict[str, InvocationRecord] = {}

    async def insert(self, record: InvocationRecord) -> None:
        self._records[record.id] = record

    async def list_by_novel(self, novel_id: str) -> list[InvocationRecord]:
        return [r for r in self._records.values() if r.novel_id == novel_id]

    async def list_by_session(self, session_id: str) -> list[InvocationRecord]:
        return [r for r in self._records.values() if r.session_id == session_id]


class InvocationService:
    """AI Invocation 应用服务"""

    def __init__(self, repo: InvocationRepo):
        self.repo = repo

    async def record(
        self,
        stage: str,
        operation: str,
        prompt_key: str,
        novel_id: str | None = None,
        chapter_number: int | None = None,
        session_id: str | None = None,
        prompt_text: str = "",
        prompt_variables: dict[str, Any] | None = None,
        model: str = "",
        provider: str = "",
        tokens_input: int = 0,
        tokens_output: int = 0,
        duration_ms: int = 0,
        status: InvocationStatus = InvocationStatus.SUCCESS,
        error: str = "",
    ) -> InvocationRecord:
        record = InvocationRecord(
            id=str(uuid.uuid4()),
            stage=stage,
            operation=operation,
            prompt_key=prompt_key,
            novel_id=novel_id,
            chapter_number=chapter_number,
            session_id=session_id,
            prompt_text=prompt_text,
            prompt_variables=prompt_variables or {},
            model=model,
            provider=provider,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            duration_ms=duration_ms,
            status=status,
            error=error,
        )
        await self.repo.insert(record)
        return record

    async def list_by_novel(self, novel_id: str) -> list[InvocationRecord]:
        return await self.repo.list_by_novel(novel_id)

    async def list_by_session(self, session_id: str) -> list[InvocationRecord]:
        return await self.repo.list_by_session(session_id)

    async def stats_by_novel(self, novel_id: str) -> dict[str, Any]:
        """统计：调用次数、token 总量、平均耗时"""
        records = await self.repo.list_by_novel(novel_id)
        if not records:
            return {"count": 0, "total_tokens_input": 0, "total_tokens_output": 0, "avg_duration_ms": 0.0}

        total_input = sum(r.tokens_input for r in records)
        total_output = sum(r.tokens_output for r in records)
        total_duration = sum(r.duration_ms for r in records)

        return {
            "count": len(records),
            "total_tokens_input": total_input,
            "total_tokens_output": total_output,
            "avg_duration_ms": total_duration / len(records),
        }
