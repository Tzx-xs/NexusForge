import json
import os

from .context import PipelineContext


class PipelineRecoveryManager:
    """管线恢复管理器 - 支持断点续跑"""

    def __init__(self, storage_path: str = "./data/checkpoints"):
        self.storage_path = storage_path

    def _get_checkpoint_path(self, pipeline_name: str, novel_id: str) -> str:
        """获取检查点文件路径。"""
        os.makedirs(self.storage_path, exist_ok=True)
        return os.path.join(self.storage_path, f"{pipeline_name}_{novel_id}.json")

    def save_checkpoint(self, ctx: PipelineContext, pipeline_name: str = "generation") -> None:
        """将 PipelineContext 持久化为 JSON 检查点文件。"""
        filepath = self._get_checkpoint_path(pipeline_name, ctx.novel_id)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(ctx.to_dict(), f, ensure_ascii=False, indent=2)

    def load_checkpoint(self, pipeline_id: str, pipeline_name: str = "generation") -> PipelineContext | None:
        """从 JSON 检查点文件恢复 PipelineContext。

        Args:
            pipeline_id: 格式为 "{pipeline_name}_{novel_id}" 或仅 novel_id
            pipeline_name: 当 pipeline_id 仅为 novel_id 时使用的管线名称
        """
        # 兼容两种格式：直接传 composite id 或 novel_id
        if "_" in pipeline_id and pipeline_id.startswith(pipeline_name + "_"):
            filepath = os.path.join(self.storage_path, f"{pipeline_id}.json")
        else:
            filepath = self._get_checkpoint_path(pipeline_name, pipeline_id)

        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
            return PipelineContext.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError):
            return None

    def can_resume(self, pipeline_id: str, pipeline_name: str = "generation") -> bool:
        """检查是否存在可恢复的检查点文件。"""
        if "_" in pipeline_id and pipeline_id.startswith(pipeline_name + "_"):
            filepath = os.path.join(self.storage_path, f"{pipeline_id}.json")
        else:
            filepath = self._get_checkpoint_path(pipeline_name, pipeline_id)
        return os.path.isfile(filepath)
