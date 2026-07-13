import asyncio
import json
import re
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any, cast

from config.defaults import (
    DEFAULT_LLM_RATE_LIMIT_RETRIES,
    DEFAULT_LLM_SERVER_ERROR_RETRIES,
    DEFAULT_LLM_TIMEOUT_RETRIES,
)
from config.logging import get_logger
from domain.shared.exceptions import (
    LLMException,
    LLMRateLimitException,
    LLMTimeoutException,
)

from .base_provider import BaseProvider

logger = get_logger(__name__)

try:
    from json_repair import repair_json

    HAS_JSON_REPAIR = True
except ImportError:
    HAS_JSON_REPAIR = False


# ---------------------------------------------------------------------------
# Function Calling 数据类
# ---------------------------------------------------------------------------

@dataclass
class ToolCall:
    """LLM 返回的单个工具调用。"""
    id: str = ""
    type: str = "function"       # "function" 或 "tool_use"
    function_name: str = ""       # 工具名称
    arguments: dict[str, Any] = field(default_factory=dict)  # 已解析的参数字典


@dataclass
class ToolCallResult:
    """LLM 返回的完整决策结果（含工具调用）。"""
    content: str | None = None                          # 文本回复（可能为 None）
    tool_calls: list[ToolCall] = field(default_factory=list)   # 工具调用列表
    finish_reason: str = "stop"                         # "stop" | "tool_calls" | "length"


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _is_server_error(exc: LLMException) -> bool:
    """检测 LLMException 是否由 HTTP 5xx 错误引起。

    通过匹配错误消息中的 HTTP 状态码模式（如 500, 502, 503, 504）
    替代此前脆弱的 `"5" in str(e)` 子串匹配，避免误判用户消息中的 "5" 数字。
    """
    msg = str(exc)
    return bool(re.search(r"\b5(?:0[0-9]|1[0-9]|2[0-9])\b", msg))


# ---------------------------------------------------------------------------
# 主客户端类
# ---------------------------------------------------------------------------

class LLMClient:
    """LLM 客户端：封装 Provider 调用、重试逻辑、工具调用解析。

    通过组合方式持有 Provider 实例，并从 Provider 派生默认参数，
    确保 chat_with_tools 等方法能访问 model/temperature/max_tokens。
    """

    def __init__(self, provider: BaseProvider) -> None:
        self.provider = provider
        # 从 Provider 派生默认值，避免 chat_with_tools 引用未定义属性（P0 Bug 修复）
        self.model: str | None = getattr(provider, "model", None) or None
        self.temperature: float = getattr(provider, "temperature", 0.7)
        self.max_tokens: int = getattr(provider, "max_tokens", 4096)

    async def chat(
        self,
        prompt: str | list[dict[str, str]],
        system_prompt: str = "",
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stream: bool = False,
        response_format: str = "text",
        tools: list[dict] | None = None,
    ) -> str | AsyncGenerator[str, None]:
        messages = self._to_messages(prompt, system_prompt)
        if stream:
            return self._chat_with_retry_stream(messages, model, temperature, max_tokens)
        return await self._chat_with_retry(messages, model, temperature, max_tokens, response_format, tools=tools)

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: str = "text",
    ) -> str:
        """generate 是 chat 的别名，供 aftermath 管线等历史调用方使用。

        行为与 chat(prompt, ...) 完全一致：非流式调用 provider 返回完整文本。
        """
        result = await self.chat(
            prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
        )
        return cast("str", result)

    async def chat_json(
        self,
        prompt: str | list[dict[str, str]],
        system_prompt: str = "你是一个严格的JSON输出助手，所有回复必须是合法的JSON格式。",
        **kwargs,
    ) -> dict:
        if isinstance(prompt, str):
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ]
        else:
            messages = prompt

        try:
            response = await self._chat_with_retry(messages, response_format="json", **kwargs)
        except Exception:
            try:
                response = await self._chat_with_retry(messages, response_format="text", **kwargs)
            except Exception as e:
                raise LLMException(f"JSON 生成失败: {str(e)}") from e

        result = self._parse_json_with_fallback(response)
        if result is None:
            retry_prompt = f"请重新生成，确保输出严格合法的JSON格式。原始请求：\n{messages[-1]['content']}\n\n上次错误输出：\n{response}"
            try:
                retry_response = await self._chat_with_retry(
                    [{"role": "user", "content": retry_prompt}],
                    response_format="json",
                    **kwargs,
                )
                result = self._parse_json_with_fallback(retry_response)
            except Exception as e:
                logger.warning("JSON 重试解析失败: %s", e)

        if result is None:
            raise LLMException("JSON 解析失败，已用尽所有兜底策略")

        return result

    async def chat_with_tools(
        self,
        messages: list[dict[str, str]],
        tools: list[dict] | None = None,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> ToolCallResult | None:
        """使用原生 Function Calling 调用 LLM，返回结构化结果。

        Args:
            messages: 消息列表
            tools: 工具定义列表（OpenAI 兼容格式），为 None 时等同于普通 chat
            model: 模型名称
            temperature: 温度参数
            max_tokens: 最大输出 token 数

        Returns:
            ToolCallResult 实例，调用失败返回 None。
        """
        try:
            response = await self.provider.chat(
                messages=messages,
                model=model or self.model,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                tools=tools,
            )

            return self._parse_tool_call_response(response)
        except Exception as e:
            logger.warning("chat_with_tools failed: %s", e)
            return None

    def _parse_tool_call_response(self, response: str | dict) -> ToolCallResult:
        """将 Provider 的响应（str 或 dict）解析为 ToolCallResult。"""
        if isinstance(response, dict):
            # Provider 返回了包含 tool_calls 的结构化响应
            content = response.get("content")
            raw_tool_calls = response.get("tool_calls", [])
            finish_reason = response.get("finish_reason", "tool_calls" if raw_tool_calls else "stop")

            tool_calls = []
            for tc in raw_tool_calls:
                fn = tc.get("function", {})
                args_str = fn.get("arguments", "{}")
                if isinstance(args_str, str):
                    try:
                        args = json.loads(args_str)
                    except json.JSONDecodeError:
                        args = {"_raw": args_str}
                else:
                    args = args_str

                tool_calls.append(ToolCall(
                    id=tc.get("id", ""),
                    type=tc.get("type", "function"),
                    function_name=fn.get("name", ""),
                    arguments=args,
                ))

            return ToolCallResult(
                content=content,
                tool_calls=tool_calls,
                finish_reason=finish_reason,
            )

        # 纯文本回复，无 tool_calls
        return ToolCallResult(content=cast(str, response), tool_calls=[])

    async def count_tokens(self, text: str) -> int:
        return await self.provider.count_tokens(text)

    async def chat_stream(
        self,
        prompt: str | list[dict[str, str]],
        system_prompt: str = "",
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncGenerator[str, None]:
        async for chunk in self._chat_with_retry_stream(
            self._to_messages(prompt, system_prompt),
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        ):
            yield chunk

    def _to_messages(self, prompt: str | list[dict[str, str]], system_prompt: str = "") -> list[dict[str, str]]:
        if isinstance(prompt, str):
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            return messages
        return prompt

    def _parse_json_with_fallback(self, text: str) -> dict | None:
        try:
            return cast(dict, json.loads(text))
        except json.JSONDecodeError:
            pass

        if HAS_JSON_REPAIR:
            try:
                repaired = repair_json(text)
                return cast(dict, json.loads(repaired))
            except Exception as e:
                logger.warning("json_repair 解析失败: %s", e)

        json_match = re.search(r"\{[\s\S]*\}", text)
        if json_match:
            try:
                return cast(dict, json.loads(json_match.group()))
            except json.JSONDecodeError:
                pass

        return None

    async def _retry_loop(
        self,
        operation_name: str,
        operation,
        timeout_retries: int = DEFAULT_LLM_TIMEOUT_RETRIES,
        server_error_retries: int = DEFAULT_LLM_SERVER_ERROR_RETRIES,
        rate_limit_retries: int = DEFAULT_LLM_RATE_LIMIT_RETRIES,
    ) -> AsyncGenerator:
        for attempt in range(max(timeout_retries, server_error_retries, rate_limit_retries) + 1):
            try:
                async for result in operation():
                    yield result
                return
            except LLMTimeoutException:
                if attempt < timeout_retries:
                    wait = 2**attempt
                    logger.warning("%s 超时，第 %s 次重试，等待 %ss", operation_name, attempt + 1, wait)
                    await asyncio.sleep(wait)
                    continue
                raise
            except LLMRateLimitException:
                if attempt < rate_limit_retries:
                    wait = 2 ** (attempt + 1)
                    logger.warning("%s 限流，第 %s 次重试，等待 %ss", operation_name, attempt + 1, wait)
                    await asyncio.sleep(wait)
                    continue
                raise
            except LLMException as e:
                if _is_server_error(e) and attempt < server_error_retries:
                    wait = 2**attempt
                    logger.warning("%s 5xx 错误，第 %s 次重试，等待 %ss", operation_name, attempt + 1, wait)
                    await asyncio.sleep(wait)
                    continue
                raise
        raise LLMException(f"{operation_name} 调用失败，已达最大重试次数")

    async def _chat_with_retry(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: str = "text",
        tools: list[dict] | None = None,
    ) -> str:
        async def operation():
            result = await self.provider.chat(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                response_format=response_format,
                tools=tools,
            )
            # _chat_with_retry 始终返回 str（向后兼容）
            # 如果传了 tools，provider 可能返回 dict，这里需要提取纯文本
            if isinstance(result, dict):
                yield result.get("content") or ""
            else:
                yield result

        async for result in self._retry_loop("LLM", operation):
            return str(result)

        raise LLMException("LLM 调用失败，已达最大重试次数")

    async def _chat_with_retry_stream(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncGenerator[str, None]:
        async def operation():
            async for chunk in self.provider.chat_stream(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                yield chunk

        async for chunk in self._retry_loop("LLM 流式", operation):
            yield chunk

    async def close(self) -> None:
        if hasattr(self.provider, "close"):
            await self.provider.close()
