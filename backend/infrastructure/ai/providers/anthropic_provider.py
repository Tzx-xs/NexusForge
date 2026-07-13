import json
from collections.abc import AsyncGenerator
from typing import Any, cast

import httpx

from domain.shared.exceptions import (
    LLMConnectionException,
    LLMException,
    LLMRateLimitException,
    LLMTimeoutException,
)

from ..base_provider import BaseProvider


class AnthropicProvider(BaseProvider):
    name = "anthropic"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._client = httpx.AsyncClient(timeout=self.timeout)

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: str = "text",
        tools: list[dict] | None = None,
    ) -> str | dict:
        system_prompt = ""
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                user_messages.append(msg)

        payload = {
            "model": model or self.model,
            "messages": user_messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
        }
        if system_prompt:
            payload["system"] = system_prompt

        # 转换 tools 格式：OpenAI 兼容格式 → Anthropic 原生格式
        if tools:
            anthropic_tools = []
            for tool in tools:
                fn = tool.get("function", tool)  # 兼容两种传入格式
                anthropic_tools.append({
                    "name": fn.get("name", ""),
                    "description": fn.get("description", ""),
                    "input_schema": fn.get("parameters", fn.get("input_schema", {})),
                })
            payload["tools"] = anthropic_tools

        return await self._request(payload, tools is not None)

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncGenerator[str, None]:
        system_prompt = ""
        user_messages = []
        for msg in messages:
            if msg["role"] == "system":
                system_prompt = msg["content"]
            else:
                user_messages.append(msg)

        payload = {
            "model": model or self.model,
            "messages": user_messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
            "stream": True,
        }
        if system_prompt:
            payload["system"] = system_prompt

        async for chunk in self._stream_request(payload):
            yield chunk

    async def _request(
        self, payload: dict, has_tools: bool = False
    ) -> str | dict:
        url = f"{self.base_url}/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        try:
            response = await self._client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException:
            raise LLMTimeoutException() from None
        except httpx.ConnectError:
            raise LLMConnectionException() from None
        except httpx.HTTPError as e:
            raise LLMException(f"HTTP 请求错误: {str(e)}") from e

        if response.status_code == 429:
            raise LLMRateLimitException()
        if response.status_code >= 500:
            raise LLMException(f"LLM API 5xx 错误: {response.status_code}")
        if response.status_code >= 400:
            raise LLMException(f"LLM API 错误: {response.status_code} - {response.text}")

        try:
            response_data = response.json()
        except json.JSONDecodeError as e:
            raise LLMException(f"响应解析失败: {str(e)}") from e

        # 无 tools 时，直接返回首个 text block
        if not has_tools:
            try:
                return cast(str, response_data["content"][0]["text"])
            except (KeyError, IndexError) as e:
                raise LLMException(f"响应解析失败: {str(e)}") from e

        # 有 tools 时，从 content 数组中提取 text 和 tool_use blocks
        tool_calls: list[dict[str, Any]] = []
        content_text: str | None = None
        for block in response_data.get("content", []):
            if block["type"] == "text":
                content_text = block["text"]
            elif block["type"] == "tool_use":
                tool_calls.append({
                    "id": block["id"],
                    "type": "function",
                    "function": {
                        "name": block["name"],
                        "arguments": json.dumps(block.get("input", {}), ensure_ascii=False),
                    },
                })

        if tool_calls:
            return {
                "content": content_text,
                "tool_calls": tool_calls,
                "finish_reason": "tool_calls",
            }

        # 虽然传了 tools 但 LLM 选择了直接回复文本
        return cast(str, content_text if content_text is not None else "")

    async def _stream_request(self, payload: dict) -> AsyncGenerator[str, None]:
        url = f"{self.base_url}/v1/messages"
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Accept": "text/event-stream",
        }
        try:
            async with self._client.stream("POST", url, json=payload, headers=headers) as response:
                if response.status_code == 429:
                    raise LLMRateLimitException()
                if response.status_code >= 500:
                    raise LLMException(f"LLM API 5xx 错误: {response.status_code}")
                if response.status_code >= 400:
                    body = await response.aread()
                    raise LLMException(f"LLM API 错误: {response.status_code} - {body.decode('utf-8')}")

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:]
                        try:
                            data = json.loads(data_str)
                            if data.get("type") == "content_block_delta":
                                delta = data.get("delta", {})
                                content = delta.get("text", "")
                                if content:
                                    yield content
                        except (json.JSONDecodeError, KeyError):
                            continue
        except httpx.TimeoutException:
            raise LLMTimeoutException() from None
        except httpx.ConnectError:
            raise LLMConnectionException() from None
        except httpx.HTTPError as e:
            raise LLMException(f"HTTP 流式请求错误: {str(e)}") from e

    async def close(self) -> None:
        await self._client.aclose()

    async def count_tokens(self, text: str) -> int:
        """使用 cl100k_base 编码（Claude 系列近似兼容），精确计数 Token。"""
        if not text:
            return 0
        try:
            import tiktoken

            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except Exception:
            return await super().count_tokens(text)
