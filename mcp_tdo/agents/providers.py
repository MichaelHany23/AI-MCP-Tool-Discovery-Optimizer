"""Adapters that turn different LLM APIs into the same simple interface.

The runner should not need to know about Ollama's response format. Keeping that
translation here also lets us test the runner without contacting a real model.
"""

import json
from typing import Any, Protocol

import httpx

from mcp_tdo.agents.models import AgentToolCall, ProviderResponse


class ChatProvider(Protocol):
    """The one method an LLM adapter needs to provide."""

    model: str

    async def complete(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]], seed: int
    ) -> ProviderResponse: ...


class OllamaProvider:
    """Talk to an Ollama model running on this computer."""

    def __init__(
        self,
        model: str,
        base_url: str = "http://127.0.0.1:11434",
        timeout_seconds: float = 120.0,
        cost_per_1k_tokens: float = 0.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        if cost_per_1k_tokens < 0:
            raise ValueError("cost_per_1k_tokens cannot be negative")
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.cost_per_1k_tokens = cost_per_1k_tokens

    async def complete(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]], seed: int
    ) -> ProviderResponse:
        """Send one request and turn Ollama's answer into our shared format."""
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "stream": False,
            "options": {"seed": seed, "temperature": 0},
        }
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            response.raise_for_status()
            body = response.json()
        message = body.get("message", {})
        calls = []
        for call in message.get("tool_calls", []):
            arguments = call.get("function", {}).get("arguments", {})
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            calls.append(
                AgentToolCall(
                    name=call.get("function", {}).get("name", ""),
                    arguments=arguments,
                )
            )
        return ProviderResponse(
            text=message.get("content", ""),
            tool_calls=calls,
            prompt_tokens=body.get("prompt_eval_count", 0),
            completion_tokens=body.get("eval_count", 0),
            raw=body,
        )


def tool_schemas(tools: list[Any]) -> list[dict[str, Any]]:
    """Convert MCP's tool descriptions into the format chat APIs expect."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.input_schema,
            },
        }
        for tool in tools
    ]
