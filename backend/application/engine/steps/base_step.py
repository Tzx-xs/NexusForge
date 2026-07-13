import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BaseStep(ABC):
    """GenerationPipeline（SSE 流式管线）的步骤基类。

    职责边界：
        GenerationPipeline 负责用户交互场景下的流式章节生成（已存在 chapter_id），
        入口为 ``generate_content_stream`` / ``generate_ai_suggest``。
        与之并存的 ``StoryPipeline``（``engine.pipeline.base``）负责 Agent 自动
        调用场景下的十步批处理管线（含 find_next_chapter / finalize），
        入口为 ``generate_chapter``。两者不可互相替代，本类仅服务前者。

    返回契约：
        execute(chapter_id, context) -> (success, result_data, error_message)
    """

    name: str = "base"
    description: str = "Base step"

    def __init__(self, llm_client=None, prompt_manager=None, context_builder=None, chapter_repo=None, review_repo=None):
        self.llm_client = llm_client
        self.prompt_manager = prompt_manager
        self.context_builder = context_builder
        self.chapter_repo = chapter_repo
        self.review_repo = review_repo

    @abstractmethod
    async def execute(self, chapter_id: str, context: dict[str, Any]) -> tuple[bool, dict[str, Any], str]:
        """
        执行步骤

        Returns:
            (success, result_data, error_message)
        """
        pass

    def can_skip(self, chapter_id: str) -> bool:
        return False
