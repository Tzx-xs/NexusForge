"""故事线 DAG 后端测试

验证：
1. 数据模型：DagNode / DagEdge / Storyline 扩展
2. DagService CRUD：创建/查询/删除节点与边
3. 拓扑排序：无环 DAG 可排序
4. 环检测：有环 DAG 抛 CycleDetected
5. 仓储对接 008 表
"""
import pytest

from application.engine.dag.models import DagNode, DagEdge, NodeType, EdgeType
from application.engine.dag.service import DagService, CycleDetectedError


# ─── 数据模型测试 ───────────────────────────────────────────────────
class TestDagModels:
    def test_dag_node_creation(self):
        node = DagNode(
            id="n1",
            novel_id="novel_001",
            node_type=NodeType.CHAPTER,
            title="第一章 觉醒",
            chapter_number=1,
        )
        assert node.id == "n1"
        assert node.node_type == NodeType.CHAPTER
        assert node.status == "pending"

    def test_dag_edge_creation(self):
        edge = DagEdge(
            id="e1",
            novel_id="novel_001",
            source_node_id="n1",
            target_node_id="n2",
            edge_type=EdgeType.CAUSAL,
        )
        assert edge.edge_type == EdgeType.CAUSAL
        assert edge.weight == 1.0

    def test_node_types(self):
        assert NodeType.CHAPTER.value == "chapter"
        assert NodeType.SUBPLOT.value == "subplot"
        assert NodeType.TURNING_POINT.value == "turning_point"
        assert NodeType.CONVERGENCE.value == "convergence"

    def test_edge_types(self):
        assert EdgeType.CAUSAL.value == "causal"
        assert EdgeType.TEMPORAL.value == "temporal"
        assert EdgeType.CONVERGENCE.value == "convergence"


# ─── DagService 测试（用内存仓储桩）──────────────────────────────
class TestDagServiceCrud:
    @pytest.fixture
    def service(self):
        from application.engine.dag.service import InMemoryDagRepo
        return DagService(InMemoryDagRepo())

    @pytest.mark.asyncio
    async def test_create_node(self, service):
        node = await service.create_node(
            novel_id="n1",
            node_type=NodeType.CHAPTER,
            title="第一章",
            chapter_number=1,
        )
        assert node.id is not None
        assert node.title == "第一章"

    @pytest.mark.asyncio
    async def test_get_node(self, service):
        created = await service.create_node(
            novel_id="n1", node_type=NodeType.CHAPTER, title="第一章",
        )
        fetched = await service.get_node(created.id)
        assert fetched is not None
        assert fetched.title == "第一章"

    @pytest.mark.asyncio
    async def test_list_nodes_by_novel(self, service):
        await service.create_node(novel_id="n1", node_type=NodeType.CHAPTER, title="ch1")
        await service.create_node(novel_id="n1", node_type=NodeType.CHAPTER, title="ch2")
        await service.create_node(novel_id="n2", node_type=NodeType.CHAPTER, title="other")

        nodes = await service.list_nodes("n1")
        assert len(nodes) == 2

    @pytest.mark.asyncio
    async def test_delete_node_cascades_edges(self, service):
        n1 = await service.create_node(novel_id="n1", node_type=NodeType.CHAPTER, title="1")
        n2 = await service.create_node(novel_id="n1", node_type=NodeType.CHAPTER, title="2")
        await service.create_edge(novel_id="n1", source_node_id=n1.id, target_node_id=n2.id)

        await service.delete_node(n1.id)

        edges = await service.list_edges("n1")
        assert len(edges) == 0  # 边被级联删除

    @pytest.mark.asyncio
    async def test_create_edge(self, service):
        n1 = await service.create_node(novel_id="n1", node_type=NodeType.CHAPTER, title="1")
        n2 = await service.create_node(novel_id="n1", node_type=NodeType.CHAPTER, title="2")
        edge = await service.create_edge(
            novel_id="n1", source_node_id=n1.id, target_node_id=n2.id,
        )
        assert edge.id is not None
        assert edge.source_node_id == n1.id


# ─── 拓扑排序与环检测 ─────────────────────────────────────────────
class TestTopologicalSort:
    @pytest.fixture
    def service(self):
        from application.engine.dag.service import InMemoryDagRepo
        return DagService(InMemoryDagRepo())

    @pytest.mark.asyncio
    async def test_linear_dag_sort(self, service):
        """线性 DAG: n1 → n2 → n3"""
        n1 = await service.create_node(novel_id="n1", node_type=NodeType.CHAPTER, title="1")
        n2 = await service.create_node(novel_id="n1", node_type=NodeType.CHAPTER, title="2")
        n3 = await service.create_node(novel_id="n1", node_type=NodeType.CHAPTER, title="3")
        await service.create_edge(novel_id="n1", source_node_id=n1.id, target_node_id=n2.id)
        await service.create_edge(novel_id="n1", source_node_id=n2.id, target_node_id=n3.id)

        order = await service.topological_sort("n1")

        assert len(order) == 3
        # n1 必须在 n2 前，n2 必须在 n3 前
        assert order.index(n1.id) < order.index(n2.id)
        assert order.index(n2.id) < order.index(n3.id)

    @pytest.mark.asyncio
    async def test_parallel_dag_sort(self, service):
        """并行 DAG: n1 → n2, n1 → n3, n2 → n4, n3 → n4"""
        n1 = await service.create_node(novel_id="n1", node_type=NodeType.CHAPTER, title="1")
        n2 = await service.create_node(novel_id="n1", node_type=NodeType.CHAPTER, title="2")
        n3 = await service.create_node(novel_id="n1", node_type=NodeType.CHAPTER, title="3")
        n4 = await service.create_node(novel_id="n1", node_type=NodeType.CHAPTER, title="4")
        await service.create_edge(novel_id="n1", source_node_id=n1.id, target_node_id=n2.id)
        await service.create_edge(novel_id="n1", source_node_id=n1.id, target_node_id=n3.id)
        await service.create_edge(novel_id="n1", source_node_id=n2.id, target_node_id=n4.id)
        await service.create_edge(novel_id="n1", source_node_id=n3.id, target_node_id=n4.id)

        order = await service.topological_sort("n1")

        assert len(order) == 4
        assert order.index(n1.id) < order.index(n2.id)
        assert order.index(n1.id) < order.index(n3.id)
        assert order.index(n2.id) < order.index(n4.id)
        assert order.index(n3.id) < order.index(n4.id)

    @pytest.mark.asyncio
    async def test_cycle_detection(self, service):
        """环检测: n1 → n2 → n3 → n1"""
        n1 = await service.create_node(novel_id="n1", node_type=NodeType.CHAPTER, title="1")
        n2 = await service.create_node(novel_id="n1", node_type=NodeType.CHAPTER, title="2")
        n3 = await service.create_node(novel_id="n1", node_type=NodeType.CHAPTER, title="3")
        await service.create_edge(novel_id="n1", source_node_id=n1.id, target_node_id=n2.id)
        await service.create_edge(novel_id="n1", source_node_id=n2.id, target_node_id=n3.id)
        await service.create_edge(novel_id="n1", source_node_id=n3.id, target_node_id=n1.id)

        with pytest.raises(CycleDetectedError):
            await service.topological_sort("n1")

    @pytest.mark.asyncio
    async def test_empty_dag_sort(self, service):
        """空 DAG 返回空列表"""
        order = await service.topological_sort("n_empty")
        assert order == []

    @pytest.mark.asyncio
    async def test_self_loop_detected(self, service):
        """自环检测：create_edge 阶段即拒绝"""
        n1 = await service.create_node(novel_id="n1", node_type=NodeType.CHAPTER, title="1")
        with pytest.raises(CycleDetectedError):
            await service.create_edge(novel_id="n1", source_node_id=n1.id, target_node_id=n1.id)


# ─── DAG 可视化数据 ────────────────────────────────────────────────
class TestDagVisualization:
    @pytest.fixture
    def service(self):
        from application.engine.dag.service import InMemoryDagRepo
        return DagService(InMemoryDagRepo())

    @pytest.mark.asyncio
    async def test_get_dag_for_visualization(self, service):
        """获取可视化 DAG 数据（节点+边）"""
        n1 = await service.create_node(novel_id="n1", node_type=NodeType.CHAPTER, title="1", chapter_number=1)
        n2 = await service.create_node(novel_id="n1", node_type=NodeType.SUBPLOT, title="支线A")
        await service.create_edge(novel_id="n1", source_node_id=n1.id, target_node_id=n2.id)

        dag_data = await service.get_dag_for_visualization("n1")

        assert "nodes" in dag_data
        assert "edges" in dag_data
        assert len(dag_data["nodes"]) == 2
        assert len(dag_data["edges"]) == 1
        # 节点含可视化字段
        node = dag_data["nodes"][0]
        assert "id" in node
        assert "title" in node
        assert "node_type" in node
        assert "status" in node

    @pytest.mark.asyncio
    async def test_get_dag_empty_novel(self, service):
        dag_data = await service.get_dag_for_visualization("empty_novel")
        assert dag_data["nodes"] == []
        assert dag_data["edges"] == []
