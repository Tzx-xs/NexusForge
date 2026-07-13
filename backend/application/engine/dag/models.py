"""故事线 DAG 数据模型

借鉴 PlotPilot application/engine/dag/models.py，简化为 NexusForge 适用版本。
不依赖 LangGraph，仅做数据建模 + 拓扑排序 + 环检测。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class NodeType(StrEnum):
    """DAG 节点类型"""
    CHAPTER = "chapter"              # 章节节点
    SUBPLOT = "subplot"              # 支线节点
    TURNING_POINT = "turning_point"  # 转折点
    CONVERGENCE = "convergence"      # 汇合点（多线收束）


class EdgeType(StrEnum):
    """DAG 边类型"""
    CAUSAL = "causal"          # 因果（A 导致 B）
    TEMPORAL = "temporal"      # 时序（A 先于 B）
    CONVERGENCE = "convergence"  # 汇合（多线收束到一点）


class NodeStatus(StrEnum):
    """节点状态"""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    SKIPPED = "skipped"


@dataclass
class DagNode:
    """DAG 节点"""
    id: str
    novel_id: str
    node_type: NodeType
    title: str = ""
    description: str = ""
    chapter_number: int | None = None
    storyline_id: str | None = None
    outline: str = ""
    status: NodeStatus = NodeStatus.PENDING
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "novel_id": self.novel_id,
            "node_type": self.node_type.value,
            "title": self.title,
            "description": self.description,
            "chapter_number": self.chapter_number,
            "storyline_id": self.storyline_id,
            "outline": self.outline,
            "status": self.status.value,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class DagEdge:
    """DAG 边"""
    id: str
    novel_id: str
    source_node_id: str
    target_node_id: str
    edge_type: EdgeType = EdgeType.CAUSAL
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "novel_id": self.novel_id,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "edge_type": self.edge_type.value,
            "weight": self.weight,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }
