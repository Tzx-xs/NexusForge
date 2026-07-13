import asyncio
import logging
import os
from collections.abc import AsyncGenerator

from ..base_provider import BaseProvider

logger = logging.getLogger(__name__)


class LocalProvider(BaseProvider):
    name = "local"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._mock_text = (
            "在这片被深渊覆盖的世界里，人类的文明只能在漂浮的岛屿上延续。"
            "林渊站在云屿的边缘，望着无尽的渊海，心中充满了对未知的渴望。"
            "他知道，在这片深邃的海洋之下，隐藏着改变命运的秘密。"
        )
        if os.getenv("APP_ENV", "development") == "production":
            logger.warning(
                "LocalProvider 在生产环境中使用！所有 LLM 请求将返回 mock 数据。"
                "请检查 LLM_PROVIDER 配置是否正确（应为 openai/anthropic/ollama）。"
            )

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: str = "text",
        tools: list[dict] | None = None,
    ) -> str | dict:
        await asyncio.sleep(0.5)
        if response_format == "json":
            return '{"total_score": 75.5, "grade": "B", "red_line_violations": [], "dimension_scores": {"情节": 80, "人物": 70, "文笔": 75}, "review_details": "整体质量良好，情节有张力，人物塑造稍显单薄。"}'
        return self._mock_text

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncGenerator[str, None]:
        text = self._mock_text
        chunk_size = max(1, len(text) // 30)
        for i in range(0, len(text), chunk_size):
            chunk = text[i : i + chunk_size]
            yield chunk
            await asyncio.sleep(0.03)

    async def count_tokens(self, text: str) -> int:
        # P4.1 优化：复用基类 tiktoken 实现，避免 mock 场景下精度严重偏低
        return await super().count_tokens(text)
