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


class OpenAIProvider(BaseProvider):
    name = "openai"

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
        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
            "top_p": self.top_p,
            "stream": False,
        }
        if response_format == "json":
            payload["response_format"] = {"type": "json_object"}

        if tools:
            payload["tools"] = tools
            # OpenAI 要求当 tools 存在时不能同时设定 response_format="json_object"
            if response_format == "json":
                payload.pop("response_format", None)

        return await self._request(payload, tools is not None)

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncGenerator[str, None]:
        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature if temperature is not None else self.temperature,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
            "top_p": self.top_p,
            "stream": True,
        }
        async for chunk in self._stream_request(payload):
            yield chunk

    async def _request(
        self, payload: dict, has_tools: bool = False
    ) -> str | dict:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
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
            data = response.json()
        except json.JSONDecodeError as e:
            raise LLMException(f"响应解析失败: {str(e)}") from e

        if not has_tools:
            return cast(str, data["choices"][0]["message"]["content"])

        # 有 tools 时，检查 message 中是否包含 tool_calls
        msg = data["choices"][0].get("message", {})
        tool_calls = msg.get("tool_calls")
        if tool_calls:
            result: dict[str, Any] = {
                "content": msg.get("content"),
                "tool_calls": tool_calls,
                "finish_reason": data["choices"][0].get("finish_reason", "tool_calls"),
            }
            return result
        # 虽然传了 tools 但 LLM 选择了直接回复文本
        return cast(str, msg.get("content", ""))

    async def _stream_request(self, payload: dict) -> AsyncGenerator[str, None]:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
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
                        if data_str == "[DONE]":
                            break
                        try:
                            data = json.loads(data_str)
                            delta = data["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except (json.JSONDecodeError, KeyError, IndexError):
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
        """使用 o200k_base 编码（GPT-4o 专用 tokenizer），精确计数 Token。"""
        if not text:
            return 0
        try:
            import tiktoken

            encoding = tiktoken.get_encoding("o200k_base")
            return len(encoding.encode(text))
        except Exception:
            return await super().count_tokens(text)
