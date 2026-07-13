"""检查点服务

借鉴 PlotPilot application/checkpoint/services/unified_checkpoint_service.py。
每 novel 仅一个 active 检查点，新建时归档前一个。
"""
from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from typing import Any

from .models import Checkpoint, CheckpointStatus

logger = logging.getLogger(__name__)


class CheckpointRepo(ABC):
    """检查点仓储接口"""

    @abstractmethod
    async def insert(self, cp: Checkpoint) -> None: ...

    @abstractmethod
    async def update(self, cp: Checkpoint) -> None: ...

    @abstractmethod
    async def get_active(self, novel_id: str) -> Checkpoint | None: ...

    @abstractmethod
    async def list_all(self, novel_id: str) -> list[Checkpoint]: ...

    @abstractmethod
    async def archive_active(self, novel_id: str) -> None: ...


class InMemoryCheckpointRepo(CheckpointRepo):
    """内存仓储（测试用 + 开发期默认）"""

    def __init__(self):
        self._checkpoints: dict[str, Checkpoint] = {}

    async def insert(self, cp: Checkpoint) -> None:
        self._checkpoints[cp.id] = cp

    async def update(self, cp: Checkpoint) -> None:
        self._checkpoints[cp.id] = cp

    async def get_active(self, novel_id: str) -> Checkpoint | None:
        for cp in self._checkpoints.values():
            if cp.novel_id == novel_id and cp.status == CheckpointStatus.ACTIVE:
                return cp
        return None

    async def list_all(self, novel_id: str) -> list[Checkpoint]:
        return [cp for cp in self._checkpoints.values() if cp.novel_id == novel_id]

    async def archive_active(self, novel_id: str) -> None:
        for cp in self._checkpoints.values():
            if cp.novel_id == novel_id and cp.status == CheckpointStatus.ACTIVE:
                cp.status = CheckpointStatus.ARCHIVED


class CheckpointService:
    """检查点应用服务"""

    def __init__(self, repo: CheckpointRepo):
        self.repo = repo

    async def create_checkpoint(
        self,
        novel_id: str,
        chapter_number: int | None = None,
        pipeline_run_id: str | None = None,
        step_name: str = "",
        step_status: str = "success",
        context_snapshot: dict[str, Any] | None = None,
        audit_snapshot: dict[str, Any] | None = None,
    ) -> Checkpoint:
        """创建检查点（归档前一个 active）"""
        await self.repo.archive_active(novel_id)

        cp = Checkpoint(
            id=str(uuid.uuid4()),
            novel_id=novel_id,
            chapter_number=chapter_number,
            pipeline_run_id=pipeline_run_id,
            step_name=step_name,
            step_status=step_status,
            context_snapshot=context_snapshot or {},
            audit_snapshot=audit_snapshot or {},
        )
        await self.repo.insert(cp)
        logger.info("检查点创建: novel=%s chapter=%s step=%s", novel_id, chapter_number, step_name)
        return cp

    async def get_active_checkpoint(self, novel_id: str) -> Checkpoint | None:
        return await self.repo.get_active(novel_id)

    async def clear_active(self, novel_id: str) -> None:
        """清除活跃检查点（章节完成后调用）"""
        await self.repo.archive_active(novel_id)

    async def list_all(self, novel_id: str) -> list[Checkpoint]:
        return await self.repo.list_all(novel_id)

    async def resume_from(self, novel_id: str) -> dict[str, Any] | None:
        """从检查点恢复：返回快照数据

        无活跃检查点返回 None。
        """
        cp = await self.repo.get_active(novel_id)
        if cp is None:
            return None
        return {
            "checkpoint_id": cp.id,
            "chapter_number": cp.chapter_number,
            "pipeline_run_id": cp.pipeline_run_id,
            "step_name": cp.step_name,
            "step_status": cp.step_status,
            "context_snapshot": cp.context_snapshot,
            "audit_snapshot": cp.audit_snapshot,
        }
