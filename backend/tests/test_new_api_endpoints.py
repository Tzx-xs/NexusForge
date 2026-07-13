"""新 API 端点 smoke 测试

验证 4 个新路由可挂载并响应：
- /api/v1/dag/*
- /api/v1/governance/*
- /api/v1/checkpoint/*
- /api/v1/ai-invocations/*
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from application.ai_invocation.service import InMemoryInvocationRepo, InvocationService
from application.checkpoint.service import InMemoryCheckpointRepo, CheckpointService
from application.engine.dag.service import InMemoryDagRepo, DagService
from application.governance.service import InMemoryGovernanceRepo, GovernanceService
from interfaces.api.v1.ai_invocation import router as ai_invocation_router
from interfaces.api.v1.checkpoint import router as checkpoint_router
from interfaces.api.v1.dag import router as dag_router
from interfaces.api.v1.governance import router as governance_router


@pytest.fixture
def app():
    # 重置所有模块级 service 的 repo（测试隔离）
    from interfaces.api.v1 import dag as dag_mod
    from interfaces.api.v1 import governance as gov_mod
    from interfaces.api.v1 import checkpoint as cp_mod
    from interfaces.api.v1 import ai_invocation as ai_mod
    dag_mod._service = DagService(InMemoryDagRepo())
    gov_mod._service = GovernanceService(InMemoryGovernanceRepo())
    cp_mod._service = CheckpointService(InMemoryCheckpointRepo())
    ai_mod._service = InvocationService(InMemoryInvocationRepo())

    app = FastAPI()
    app.include_router(dag_router)
    app.include_router(governance_router)
    app.include_router(checkpoint_router)
    app.include_router(ai_invocation_router)
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestDagEndpoints:
    def test_get_dag_empty(self, client):
        """获取空 DAG"""
        r = client.get("/api/v1/dag/n1")
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 0
        assert body["data"]["nodes"] == []
        assert body["data"]["edges"] == []

    def test_create_node(self, client):
        """创建节点"""
        r = client.post("/api/v1/dag/nodes", json={
            "novel_id": "n1",
            "node_type": "chapter",
            "title": "第一章",
            "chapter_number": 1,
        })
        assert r.status_code == 200
        body = r.json()
        assert body["code"] == 0
        assert body["data"]["title"] == "第一章"

    def test_create_edge(self, client):
        """创建边"""
        n1 = client.post("/api/v1/dag/nodes", json={
            "novel_id": "n1", "node_type": "chapter", "title": "1",
        }).json()["data"]
        n2 = client.post("/api/v1/dag/nodes", json={
            "novel_id": "n1", "node_type": "chapter", "title": "2",
        }).json()["data"]

        r = client.post("/api/v1/dag/edges", json={
            "novel_id": "n1",
            "source_node_id": n1["id"],
            "target_node_id": n2["id"],
        })
        assert r.status_code == 200

    def test_topological_sort(self, client):
        """拓扑排序"""
        n1 = client.post("/api/v1/dag/nodes", json={
            "novel_id": "n1", "node_type": "chapter", "title": "1",
        }).json()["data"]
        n2 = client.post("/api/v1/dag/nodes", json={
            "novel_id": "n1", "node_type": "chapter", "title": "2",
        }).json()["data"]
        client.post("/api/v1/dag/edges", json={
            "novel_id": "n1", "source_node_id": n1["id"], "target_node_id": n2["id"],
        })

        r = client.get("/api/v1/dag/n1/topological-sort")
        assert r.status_code == 200
        order = r.json()["data"]
        assert len(order) == 2
        assert order.index(n1["id"]) < order.index(n2["id"])


class TestGovernanceEndpoints:
    def test_allocate_budget(self, client):
        r = client.post("/api/v1/governance/budgets", json={
            "novel_id": "n1",
            "chapter_number": 5,
            "max_new_storylines": 1,
            "max_debt_closures": 2,
            "allowed_reveal_level": "partial",
        })
        assert r.status_code == 200
        assert r.json()["data"]["max_new_storylines"] == 1

    def test_get_budget(self, client):
        client.post("/api/v1/governance/budgets", json={
            "novel_id": "n1", "chapter_number": 5,
        })
        r = client.get("/api/v1/governance/budgets/n1/5")
        assert r.status_code == 200
        assert r.json()["data"]["chapter_number"] == 5

    def test_register_debt(self, client):
        r = client.post("/api/v1/governance/debts", json={
            "novel_id": "n1",
            "description": "古卷符号未解",
            "kind": "foreshadow",
            "raised_chapter": 3,
        })
        assert r.status_code == 200

    def test_list_open_debts(self, client):
        client.post("/api/v1/governance/debts", json={
            "novel_id": "n1", "description": "d1",
        })
        r = client.get("/api/v1/governance/debts/n1/open")
        assert r.status_code == 200
        assert len(r.json()["data"]) == 1

    def test_check_gate(self, client):
        client.post("/api/v1/governance/budgets", json={
            "novel_id": "n1", "chapter_number": 5, "max_new_storylines": 0,
        })
        r = client.post("/api/v1/governance/gate/check", json={
            "novel_id": "n1",
            "chapter_number": 5,
            "new_storylines_count": 1,
            "debt_closures_count": 0,
            "reveal_level": "none",
        })
        assert r.status_code == 200
        assert r.json()["data"]["passed"] is False


class TestCheckpointEndpoints:
    def test_create_checkpoint(self, client):
        r = client.post("/api/v1/checkpoint", json={
            "novel_id": "n1",
            "chapter_number": 5,
            "pipeline_run_id": "r1",
            "step_name": "generate",
        })
        assert r.status_code == 200

    def test_get_active_checkpoint(self, client):
        client.post("/api/v1/checkpoint", json={
            "novel_id": "n1", "chapter_number": 5, "step_name": "s1",
        })
        r = client.get("/api/v1/checkpoint/n1/active")
        assert r.status_code == 200
        assert r.json()["data"]["step_name"] == "s1"

    def test_clear_active(self, client):
        client.post("/api/v1/checkpoint", json={
            "novel_id": "n1", "chapter_number": 5, "step_name": "s1",
        })
        r = client.delete("/api/v1/checkpoint/n1/active")
        assert r.status_code == 200

        r = client.get("/api/v1/checkpoint/n1/active")
        assert r.json()["data"] is None


class TestAiInvocationEndpoints:
    def test_record_invocation(self, client):
        r = client.post("/api/v1/ai-invocations", json={
            "stage": "generate",
            "operation": "chapter_content",
            "prompt_key": "chapter-content",
            "model": "gpt-4",
            "tokens_input": 1500,
            "tokens_output": 800,
        })
        assert r.status_code == 200

    def test_list_by_novel(self, client):
        client.post("/api/v1/ai-invocations", json={
            "novel_id": "n1", "stage": "s1", "operation": "o1", "prompt_key": "k1",
        })
        client.post("/api/v1/ai-invocations", json={
            "novel_id": "n1", "stage": "s2", "operation": "o2", "prompt_key": "k2",
        })
        r = client.get("/api/v1/ai-invocations/novel/n1")
        assert r.status_code == 200
        assert len(r.json()["data"]) == 2

    def test_stats_by_novel(self, client):
        client.post("/api/v1/ai-invocations", json={
            "novel_id": "n1", "stage": "s1", "operation": "o1", "prompt_key": "k1",
            "tokens_input": 1000, "tokens_output": 500, "duration_ms": 2000,
        })
        r = client.get("/api/v1/ai-invocations/novel/n1/stats")
        assert r.status_code == 200
        stats = r.json()["data"]
        assert stats["count"] == 1
        assert stats["total_tokens_input"] == 1000
