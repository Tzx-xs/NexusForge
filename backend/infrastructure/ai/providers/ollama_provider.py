import json
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from domain.shared.exceptions import (
    LLMConnectionException,
    LLMException,
    LLMRateLimitException,
    LLMTimeoutException,
)

from ..base_provider import BaseProvider


class OllamaProvider(BaseProvider):
    """Ollama 原生 /api/chat 协议 Provider。

    用户填写 base_url（如 http://localhost:11434）和 model（如 qwen2.5:14b）即可使用本地模型。
    """

    name = "ollama"

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._client = httpx.AsyncClient(timeout=self.timeout)

    def _url(self, path: str) -> str:
        base = self.base_url.rstrip("/")
        return f"{base}{path}"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: str = "text",
        tools: list[dict] | None = None,
    ) -> str | dict:
        payload = self._build_payload(
            messages, model, temperature, max_tokens, response_format,
            tools=tools,
        )
        url = self._url("/api/chat")

        try:
            response = await self._client.post(url, json=payload, headers=self._headers())
        except httpx.TimeoutException:
            raise LLMTimeoutException() from None
        except httpx.ConnectError:
            raise LLMConnectionException() from None
        except httpx.HTTPError as e:
            raise LLMException(f"Ollama HTTP 请求错误: {str(e)}") from e

        if response.status_code == 429:
            raise LLMRateLimitException()
        # 400 错误可能来自模型不支持 tools，返回空 tool_calls 表示降级
        if response.status_code == 400 and tools:
            return {"content": "", "tool_calls": [], "finish_reason": "stop"}
        if response.status_code >= 400:
            raise LLMException(f"Ollama API 错误: {response.status_code} - {response.text}")

        try:
            data = response.json()
        except json.JSONDecodeError as e:
            raise LLMException(f"Ollama 响应解析失败: {str(e)}") from e

        if not tools:
            return str(data["message"]["content"])

        # 有 tools 时，检查 message 中是否包含 tool_calls
        msg = data.get("message", {})
        raw_tool_calls = msg.get("tool_calls")
        if raw_tool_calls:
            # Ollama tool_calls 格式： [{"function": {"name": "...", "arguments": {...}}}, ...]
            # 转换为 OpenAI 兼容格式
            converted_tool_calls = []
            for tc in raw_tool_calls:
                fn = tc.get("function", {})
                args = fn.get("arguments", {})
                converted_tool_calls.append({
                    "id": tc.get("id", f"ollama_{id(tc)}"),
                    "type": "function",
                    "function": {
                        "name": fn.get("name", ""),
                        "arguments": json.dumps(args, ensure_ascii=False) if isinstance(args, dict) else str(args),
                    },
                })
            return {
                "content": msg.get("content", ""),
                "tool_calls": converted_tool_calls,
                "finish_reason": "tool_calls",
            }

        return str(msg.get("content", ""))

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncGenerator[str, None]:
        payload = self._build_payload(messages, model, temperature, max_tokens, stream=True)
        url = self._url("/api/chat")

        try:
            async with self._client.stream("POST", url, json=payload, headers=self._headers()) as response:
                if response.status_code == 429:
                    raise LLMRateLimitException()
                if response.status_code >= 400:
                    body = await response.aread()
                    raise LLMException(f"Ollama API 错误: {response.status_code} - {body.decode('utf-8')}")

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if data.get("done"):
                        break
                    content = data.get("message", {}).get("content", "")
                    if content:
                        yield content
        except httpx.TimeoutException:
            raise LLMTimeoutException() from None
        except httpx.ConnectError:
            raise LLMConnectionException() from None
        except httpx.HTTPError as e:
            raise LLMException(f"Ollama HTTP 流式请求错误: {str(e)}") from e

    def _build_payload(
        self,
        messages: list[dict[str, str]],
        model: str | None,
        temperature: float | None,
        max_tokens: int | None,
        response_format: str = "text",
        stream: bool = False,
        tools: list[dict] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature if temperature is not None else self.temperature,
            },
        }
        if max_tokens is not None:
            payload["options"]["num_predict"] = max_tokens
        elif self.max_tokens:
            payload["options"]["num_predict"] = self.max_tokens

        if response_format == "json":
            payload["format"] = "json"

        if tools:
            # Ollama 使用与 OpenAI 兼容的 tools 格式
            payload["tools"] = tools

        return payload

    async def close(self) -> None:
        await self._client.aclose()
