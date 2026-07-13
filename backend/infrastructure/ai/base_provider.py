from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

# 当 tools 参数非空时 chat() 可能返回 dict
# 返回 dict 结构：{"content": str | None, "tool_calls": list[dict]}
# 其中 tool_calls 元素格式（OpenAI 兼容）：
#   {"id": str, "type": "function", "function": {"name": str, "arguments": str}}


class BaseProvider(ABC):
    name: str = "base"

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "",
        model: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        top_p: float = 0.9,
        timeout: int = 120,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.top_p = top_p
        self.timeout = timeout

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: str = "text",
        tools: list[dict] | None = None,
    ) -> str | dict:
        """执行 LLM 对话。

        Args:
            messages: 消息列表 [{"role": "...", "content": "..."}, ...]
            model: 模型名称，为 None 时使用默认值
            temperature: 温度参数，为 None 时使用默认值
            max_tokens: 最大输出 token 数，为 None 时使用默认值
            response_format: 响应格式，"text" 或 "json"
            tools: 工具定义列表（OpenAI 兼容格式），为 None 时表示不使用 Function Calling

        Returns:
            当 tools=None 时返回 str（纯文本回复）。
            当 tools 非空且 API 返回了 tool_calls 时返回 dict：
                {"content": str | None, "tool_calls": list[dict]}
            其中 tool_calls 元素格式为 OpenAI 兼容格式：
                {"id": str, "type": "function", "function": {"name": str, "arguments": str}}
        """
        pass

    @abstractmethod
    def chat_stream(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncGenerator[str, None]:
        raise NotImplementedError

    async def count_tokens(self, text: str) -> int:
        """统计文本 Token 数。

        优先使用 tiktoken 库进行精确计数（cl100k_base 编码，与 GPT-4/GPT-4o 兼容）。
        当 tiktoken 不可用或编码出错时，降级回基于中英文比例的估算：
        - 中文 1 字 ≈ 1 token
        - 英文/数字 4 字符 ≈ 1 token
        """
        if not text:
            return 0
        try:
            import tiktoken

            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except ImportError:
            import logging

            logging.getLogger(__name__).warning(
                "tiktoken 未安装，使用中英文比例粗估 Token 计数"
            )
            return self._estimate_tokens(text)
        except Exception:
            import logging

            logging.getLogger(__name__).warning(
                "tiktoken 编码失败，降级使用中英文比例粗估", exc_info=True
            )
            return self._estimate_tokens(text)

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """基于中英文比例的 Token 估算（tiktoken 不可用时的降级方案）。

        - 中文字符（含全角标点）按 1 字 ≈ 1 token 估算
        - ASCII 字符按 4 字符 ≈ 1 token 估算（与 GPT 分词器对英文的平均比例一致）
        """
        if not text:
            return 0
        cjk_count = sum(1 for c in text if ord(c) > 0x2E80)
        ascii_count = len(text) - cjk_count
        return max(1, cjk_count + ascii_count // 4)
