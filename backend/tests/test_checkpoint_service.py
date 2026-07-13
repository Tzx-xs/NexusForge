"""检查点服务测试

验证：
1. Checkpoint 模型
2. CheckpointService 创建/获取/恢复/清理
3. 单 novel 单 active 检查点约束
"""
import pytest

from application.checkpoint.models import Checkpoint, CheckpointStatus
from application.checkpoint.service import CheckpointService


class TestCheckpointModels:
    def test_checkpoint_defaults(self):
        cp = Checkpoint(
            id="cp1",
            novel_id="n1",
            chapter_number=5,
            pipeline_run_id="run_001",
            step_name="generate",
        )
        assert cp.step_status == "success"
        assert cp.status == CheckpointStatus.ACTIVE
        assert cp.context_snapshot == {}

    def test_checkpoint_statuses(self):
        assert CheckpointStatus.ACTIVE.value == "active"
        assert CheckpointStatus.ARCHIVED.value == "archived"


class TestCheckpointService:
    @pytest.fixture
    def service(self):
        from application.checkpoint.service import InMemoryCheckpointRepo
        return CheckpointService(InMemoryCheckpointRepo())

    @pytest.mark.asyncio
    async def test_create_checkpoint(self, service):
        cp = await service.create_checkpoint(
            novel_id="n1",
            chapter_number=5,
            pipeline_run_id="run_001",
            step_name="generate",
            context_snapshot={"last_output": "..."},
        )
        assert cp.id is not None
        assert cp.status == CheckpointStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_get_active_checkpoint(self, service):
        """获取活跃检查点（每 novel 仅一个 active）"""
        await service.create_checkpoint(
            novel_id="n1", chapter_number=5, pipeline_run_id="r1", step_name="s1",
        )
        cp = await service.get_active_checkpoint("n1")
        assert cp is not None
        assert cp.step_name == "s1"

    @pytest.mark.asyncio
    async def test_new_checkpoint_archives_previous(self, service):
        """新建检查点时归档前一个 active"""
        cp1 = await service.create_checkpoint(
            novel_id="n1", chapter_number=5, pipeline_run_id="r1", step_name="s1",
        )
        cp2 = await service.create_checkpoint(
            novel_id="n1", chapter_number=6, pipeline_run_id="r2", step_name="s2",
        )

        active = await service.get_active_checkpoint("n1")
        assert active.id == cp2.id
        # cp1 被归档
        all_cps = await service.list_all("n1")
        assert len(all_cps) == 2
        archived = next(c for c in all_cps if c.id == cp1.id)
        assert archived.status == CheckpointStatus.ARCHIVED

    @pytest.mark.asyncio
    async def test_clear_active(self, service):
        """清除活跃检查点（章节完成后）"""
        await service.create_checkpoint(
            novel_id="n1", chapter_number=5, pipeline_run_id="r1", step_name="s1",
        )
        await service.clear_active("n1")

        cp = await service.get_active_checkpoint("n1")
        assert cp is None

    @pytest.mark.asyncio
    async def test_resume_from_checkpoint(self, service):
        """从检查点恢复：返回快照数据"""
        await service.create_checkpoint(
            novel_id="n1",
            chapter_number=5,
            pipeline_run_id="r1",
            step_name="generate",
            context_snapshot={"chapter_content": "部分内容..."},
            audit_snapshot={"validated": False},
        )

        snapshot = await service.resume_from("n1")
        assert snapshot is not None
        assert snapshot["context_snapshot"]["chapter_content"] == "部分内容..."
        assert snapshot["step_name"] == "generate"

    @pytest.mark.asyncio
    async def test_resume_no_checkpoint_returns_none(self, service):
        """无检查点时返回 None"""
        snapshot = await service.resume_from("n_empty")
        assert snapshot is None
