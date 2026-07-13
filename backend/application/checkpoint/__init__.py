"""application/checkpoint — 引擎检查点子系统

借鉴 PlotPilot application/checkpoint，简化为：
- models: Checkpoint / CheckpointStatus
- service: CheckpointService（创建/获取/恢复/清理）

每 novel 仅一个 active 检查点，新建时归档前一个。
用于 EngineDaemon 崩溃恢复。
"""
from .models import Checkpoint, CheckpointStatus
from .service import CheckpointService, InMemoryCheckpointRepo

__all__ = [
    "Checkpoint",
    "CheckpointStatus",
    "CheckpointService",
    "InMemoryCheckpointRepo",
]
