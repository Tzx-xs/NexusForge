"""application/governance — 叙事治理子系统

借鉴 PlotPilot application/governance，简化为：
- models: ChapterBudget / NarrativeDebt / GateResult
- service: GovernanceService（预算分配 + 债务登记 + 写前校验）

写前校验（Gate）是核心：在章节生成前检查是否超预算，
防止 AI 跑飞开新主线或过早揭秘。
"""
from .models import (
    ChapterBudget,
    DebtKind,
    DebtStatus,
    GateResult,
    NarrativeDebt,
    RevealLevel,
)
from .service import GovernanceService, GovernanceViolation, InMemoryGovernanceRepo

__all__ = [
    "ChapterBudget",
    "NarrativeDebt",
    "DebtKind",
    "DebtStatus",
    "RevealLevel",
    "GateResult",
    "GovernanceService",
    "GovernanceViolation",
    "InMemoryGovernanceRepo",
]
