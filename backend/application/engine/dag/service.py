"""故事线 DAG 服务

借鉴 PlotPilot application/engine/dag/engine.py，简化为：
- CRUD（节点/边）
- 拓扑排序（Kahn 算法）
- 环检测
- 可视化数据导出

不依赖 LangGraph，执行仍走 BaseStoryPipeline。
"""
from __future__ import annotations

import logging
import uuid
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from typing import Any

from .models import DagEdge, DagNode, EdgeType, NodeStatus, NodeType

logger = logging.getLogger(__name__)


class CycleDetectedError(Exception):
    """DAG 存在环"""


class DagRepo(ABC):
    """DAG 仓储接口"""

    @abstractmethod
    async def insert_node(self, node: DagNode) -> None: ...

    @abstractmethod
    async def get_node(self, node_id: str) -> DagNode | None: ...

    @abstractmethod
    async def list_nodes_by_novel(self, novel_id: str) -> list[DagNode]: ...

    @abstractmethod
    async def delete_node(self, node_id: str) -> None: ...

    @abstractmethod
    async def insert_edge(self, edge: DagEdge) -> None: ...

    @abstractmethod
    async def list_edges_by_novel(self, novel_id: str) -> list[DagEdge]: ...

    @abstractmethod
    async def delete_edges_of_node(self, node_id: str) -> None: ...


class InMemoryDagRepo(DagRepo):
    """内存仓储（测试用 + 开发期默认实现）"""

    def __init__(self):
        self._nodes: dict[str, DagNode] = {}
        self._edges: dict[str, DagEdge] = {}

    async def insert_node(self, node: DagNode) -> None:
        self._nodes[node.id] = node

    async def get_node(self, node_id: str) -> DagNode | None:
        return self._nodes.get(node_id)

    async def list_nodes_by_novel(self, novel_id: str) -> list[DagNode]:
        return [n for n in self._nodes.values() if n.novel_id == novel_id]

    async def delete_node(self, node_id: str) -> None:
        self._nodes.pop(node_id, None)
        # 级联删除关联边
        to_remove = [
            eid for eid, e in self._edges.items()
            if e.source_node_id == node_id or e.target_node_id == node_id
        ]
        for eid in to_remove:
            self._edges.pop(eid, None)

    async def insert_edge(self, edge: DagEdge) -> None:
        self._edges[edge.id] = edge

    async def list_edges_by_novel(self, novel_id: str) -> list[DagEdge]:
        return [e for e in self._edges.values() if e.novel_id == novel_id]

    async def delete_edges_of_node(self, node_id: str) -> None:
        to_remove = [
            eid for eid, e in self._edges.items()
            if e.source_node_id == node_id or e.target_node_id == node_id
        ]
        for eid in to_remove:
            self._edges.pop(eid, None)


class DagService:
    """DAG 应用服务"""

    def __init__(self, repo: DagRepo):
        self.repo = repo

    # ─── 节点 CRUD ───
    async def create_node(
        self,
        novel_id: str,
        node_type: NodeType,
        title: str = "",
        description: str = "",
        chapter_number: int | None = None,
        storyline_id: str | None = None,
        outline: str = "",
    ) -> DagNode:
        node = DagNode(
            id=str(uuid.uuid4()),
            novel_id=novel_id,
            node_type=node_type,
            title=title,
            description=description,
            chapter_number=chapter_number,
            storyline_id=storyline_id,
            outline=outline,
        )
        await self.repo.insert_node(node)
        logger.info("DAG node created: %s (%s)", node.id, node.title)
        return node

    async def get_node(self, node_id: str) -> DagNode | None:
        return await self.repo.get_node(node_id)

    async def list_nodes(self, novel_id: str) -> list[DagNode]:
        return await self.repo.list_nodes_by_novel(novel_id)

    async def delete_node(self, node_id: str) -> None:
        await self.repo.delete_node(node_id)
        logger.info("DAG node deleted: %s", node_id)

    # ─── 边 CRUD ───
    async def create_edge(
        self,
        novel_id: str,
        source_node_id: str,
        target_node_id: str,
        edge_type: EdgeType = EdgeType.CAUSAL,
        weight: float = 1.0,
    ) -> DagEdge:
        # 自环检测
        if source_node_id == target_node_id:
            raise CycleDetectedError(f"自环不允许: {source_node_id}")

        edge = DagEdge(
            id=str(uuid.uuid4()),
            novel_id=novel_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            edge_type=edge_type,
            weight=weight,
        )
        await self.repo.insert_edge(edge)
        return edge

    async def list_edges(self, novel_id: str) -> list[DagEdge]:
        return await self.repo.list_edges_by_novel(novel_id)

    # ─── 拓扑排序（Kahn 算法）───
    async def topological_sort(self, novel_id: str) -> list[str]:
        """返回拓扑排序的节点 ID 列表，有环抛 CycleDetectedError"""
        nodes = await self.repo.list_nodes_by_novel(novel_id)
        edges = await self.repo.list_edges_by_novel(novel_id)

        if not nodes:
            return []

        # 构建邻接表与入度表
        node_ids = {n.id for n in nodes}
        adj: dict[str, list[str]] = defaultdict(list)
        in_degree: dict[str, int] = {nid: 0 for nid in node_ids}

        for edge in edges:
            if edge.source_node_id in node_ids and edge.target_node_id in node_ids:
                adj[edge.source_node_id].append(edge.target_node_id)
                in_degree[edge.target_node_id] += 1

        # Kahn 算法
        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        order: list[str] = []

        while queue:
            nid = queue.popleft()
            order.append(nid)
            for neighbor in adj[nid]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(node_ids):
            # 存在环
            remaining = [nid for nid in node_ids if nid not in order]
            raise CycleDetectedError(f"DAG 存在环，涉及节点: {remaining}")

        return order

    # ─── 可视化数据 ───
    async def get_dag_for_visualization(self, novel_id: str) -> dict[str, Any]:
        """导出前端可视化所需的节点+边数据"""
        nodes = await self.repo.list_nodes_by_novel(novel_id)
        edges = await self.repo.list_edges_by_novel(novel_id)

        return {
            "nodes": [n.to_dict() for n in nodes],
            "edges": [e.to_dict() for e in edges],
        }
