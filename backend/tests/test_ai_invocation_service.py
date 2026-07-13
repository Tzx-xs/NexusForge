"""AI Invocation 调用记录测试

验证：
1. InvocationRecord 模型
2. InvocationService 记录/查询/统计
3. 可观测性：按 stage/novel/session 查询
"""
import pytest

from application.ai_invocation.models import InvocationRecord, InvocationStatus
from application.ai_invocation.service import InvocationService


class TestInvocationModels:
    def test_record_defaults(self):
        r = InvocationRecord(
            id="inv1",
            stage="generate",
            operation="chapter_content",
            prompt_key="chapter-content",
        )
        assert r.status == InvocationStatus.SUCCESS
        assert r.tokens_input == 0
        assert r.tokens_output == 0

    def test_statuses(self):
        assert InvocationStatus.SUCCESS.value == "success"
        assert InvocationStatus.FAILED.value == "failed"
        assert InvocationStatus.TIMEOUT.value == "timeout"


class TestInvocationService:
    @pytest.fixture
    def service(self):
        from application.ai_invocation.service import InMemoryInvocationRepo
        return InvocationService(InMemoryInvocationRepo())

    @pytest.mark.asyncio
    async def test_record_invocation(self, service):
        r = await service.record(
            stage="generate",
            operation="chapter_content",
            prompt_key="chapter-content",
            model="gpt-4",
            provider="openai",
            tokens_input=1500,
            tokens_output=800,
            duration_ms=4200,
        )
        assert r.id is not None
        assert r.tokens_input == 1500

    @pytest.mark.asyncio
    async def test_record_with_novel_and_chapter(self, service):
        r = await service.record(
            novel_id="n1",
            chapter_number=5,
            stage="aftermath",
            operation="extract_summary",
            prompt_key="aftermath/unified_extraction",
        )
        assert r.novel_id == "n1"
        assert r.chapter_number == 5

    @pytest.mark.asyncio
    async def test_list_by_novel(self, service):
        await service.record(novel_id="n1", stage="s1", operation="o1", prompt_key="k1")
        await service.record(novel_id="n1", stage="s2", operation="o2", prompt_key="k2")
        await service.record(novel_id="n2", stage="s1", operation="o1", prompt_key="k1")

        records = await service.list_by_novel("n1")
        assert len(records) == 2

    @pytest.mark.asyncio
    async def test_list_by_session(self, service):
        await service.record(session_id="sess1", stage="s1", operation="o1", prompt_key="k1")
        await service.record(session_id="sess1", stage="s2", operation="o2", prompt_key="k2")
        await service.record(session_id="sess2", stage="s1", operation="o1", prompt_key="k1")

        records = await service.list_by_session("sess1")
        assert len(records) == 2

    @pytest.mark.asyncio
    async def test_stats_by_novel(self, service):
        """统计：调用次数、token 总量、平均耗时"""
        await service.record(
            novel_id="n1", stage="s1", operation="o1", prompt_key="k1",
            tokens_input=1000, tokens_output=500, duration_ms=2000,
        )
        await service.record(
            novel_id="n1", stage="s2", operation="o2", prompt_key="k2",
            tokens_input=2000, tokens_output=1000, duration_ms=4000,
        )
        await service.record(
            novel_id="n2", stage="s1", operation="o1", prompt_key="k1",
            tokens_input=500, tokens_output=200, duration_ms=1000,
        )

        stats = await service.stats_by_novel("n1")
        assert stats["count"] == 2
        assert stats["total_tokens_input"] == 3000
        assert stats["total_tokens_output"] == 1500
        assert stats["avg_duration_ms"] == 3000.0

    @pytest.mark.asyncio
    async def test_record_failure(self, service):
        """记录失败调用"""
        r = await service.record(
            stage="generate",
            operation="chapter_content",
            prompt_key="k1",
            status=InvocationStatus.FAILED,
            error="LLM 超时",
        )
        assert r.status == InvocationStatus.FAILED
        assert r.error == "LLM 超时"
