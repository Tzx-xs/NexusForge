"""DAG API 端点"""
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from application.engine.dag.models import EdgeType, NodeType
from application.engine.dag.service import CycleDetectedError, DagService, InMemoryDagRepo

router = APIRouter(prefix="/api/v1/dag", tags=["dag"])

# 开发期默认用内存仓储，后续接入 DB 仓储时替换
_service = DagService(InMemoryDagRepo())


def _success(data: Any) -> dict:
    return {"code": 0, "message": "success", "data": data}


def _error(message: str, code: int = -1) -> dict:
    return {"code": code, "message": message, "data": None}


class NodeCreateRequest(BaseModel):
    novel_id: str
    node_type: str = "chapter"
    title: str = ""
    description: str = ""
    chapter_number: int | None = None
    storyline_id: str | None = None
    outline: str = ""


class EdgeCreateRequest(BaseModel):
    novel_id: str
    source_node_id: str
    target_node_id: str
    edge_type: str = "causal"
    weight: float = 1.0


@router.get("/{novel_id}")
async def get_dag(novel_id: str):
    """获取可视化 DAG 数据"""
    data = await _service.get_dag_for_visualization(novel_id)
    return _success(data)


@router.post("/nodes")
async def create_node(req: NodeCreateRequest):
    """创建节点"""
    try:
        node = await _service.create_node(
            novel_id=req.novel_id,
            node_type=NodeType(req.node_type),
            title=req.title,
            description=req.description,
            chapter_number=req.chapter_number,
            storyline_id=req.storyline_id,
            outline=req.outline,
        )
        return _success(node.to_dict())
    except ValueError as e:
        return _error(f"无效节点类型: {e}")


@router.delete("/nodes/{node_id}")
async def delete_node(node_id: str):
    await _service.delete_node(node_id)
    return _success({"deleted": node_id})


@router.post("/edges")
async def create_edge(req: EdgeCreateRequest):
    """创建边"""
    try:
        edge = await _service.create_edge(
            novel_id=req.novel_id,
            source_node_id=req.source_node_id,
            target_node_id=req.target_node_id,
            edge_type=EdgeType(req.edge_type),
            weight=req.weight,
        )
        return _success(edge.to_dict())
    except CycleDetectedError as e:
        return _error(f"环检测失败: {e}")
    except ValueError as e:
        return _error(f"无效边类型: {e}")


@router.get("/{novel_id}/topological-sort")
async def topological_sort(novel_id: str):
    """拓扑排序"""
    try:
        order = await _service.topological_sort(novel_id)
        return _success(order)
    except CycleDetectedError as e:
        return _error(f"DAG 存在环: {e}")
