"""The loop that gives an LLM tools, runs its calls, and records the result."""

import json
import time
from pathlib import Path
from typing import Any

from mcp_tdo.agents.cache import ResponseCache
from mcp_tdo.agents.models import AgentRunResult, AgentToolCall, ProviderResponse
from mcp_tdo.agents.providers import ChatProvider, tool_schemas
from mcp_tdo.mcp_client import InMemoryMCPClient


class AgentRunner:
    """Run one task without allowing the model to loop forever."""

    def __init__(
        self,
        provider: ChatProvider,
        client: InMemoryMCPClient,
        *,
        max_steps: int = 5,
        max_retries: int = 1,
        seed: int = 0,
        cache_dir: Path | None = None,
    ) -> None:
        if max_steps <= 0:
            raise ValueError("max_steps must be greater than zero")
        if max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        self.provider = provider
        self.client = client
        self.max_steps = max_steps
        self.max_retries = max_retries
        self.seed = seed
        self.cache = ResponseCache(cache_dir) if cache_dir is not None else None

    async def run(self, prompt: str) -> AgentRunResult:
        """Keep the conversation moving until the model answers or hits a limit."""
        started = time.perf_counter()
        tools = tool_schemas(await self.client.list_tools())
        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": "Choose tools only when needed. Use the provided schemas exactly.",
            },
            {"role": "user", "content": prompt},
        ]
        calls: list[AgentToolCall] = []
        results: list[Any] = []
        prompt_tokens = 0
        completion_tokens = 0
        final_text = ""
        stopped_reason = "max_steps"
        cache_hit = False

        for step in range(self.max_steps):
            response, was_cached = await self._complete_with_retry(messages, tools)
            cache_hit = cache_hit or was_cached
            prompt_tokens += response.prompt_tokens
            completion_tokens += response.completion_tokens
            final_text = response.text
            if not response.tool_calls:
                stopped_reason = "completed"
                steps = step + 1
                break

            messages.append(
                {
                    "role": "assistant",
                    "content": response.text,
                    "tool_calls": [
                        {"function": {"name": call.name, "arguments": call.arguments}}
                        for call in response.tool_calls
                    ],
                }
            )
            for call in response.tool_calls:
                calls.append(call)
                result = await self.client.call_tool(call.name, call.arguments)
                results.append(result)
                messages.append(
                    {"role": "tool", "name": call.name, "content": json_result(result)}
                )
        else:
            steps = self.max_steps

        latency_ms = (time.perf_counter() - started) * 1000
        total_tokens = prompt_tokens + completion_tokens
        cost_per_1k = getattr(self.provider, "cost_per_1k_tokens", 0.0)
        return AgentRunResult(
            model=self.provider.model,
            prompt=prompt,
            final_text=final_text,
            tool_calls=calls,
            tool_results=results,
            steps=steps,
            stopped_reason=stopped_reason,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            latency_ms=latency_ms,
            estimated_cost=total_tokens / 1000 * cost_per_1k,
            cache_hit=cache_hit,
        )

    async def _complete_with_retry(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]
    ) -> tuple[ProviderResponse, bool]:
        """Retry model requests, but never repeat a tool call behind the scenes."""
        key = (
            self.cache.key(self.provider.model, messages, tools, self.seed)
            if self.cache
            else None
        )
        if key and self.cache:
            cached = self.cache.get(key)
            if cached:
                return cached, True
        last_error: Exception | None = None
        for _attempt in range(self.max_retries + 1):
            try:
                response = await self.provider.complete(messages, tools, self.seed)
                if key and self.cache:
                    self.cache.put(key, response)
                return response, False
            except Exception as error:
                last_error = error
        raise RuntimeError(f"LLM provider failed after retries: {last_error}") from last_error


def json_result(result: Any) -> str:
    """Put a tool result into the text message sent back to the model."""
    return json.dumps(result, sort_keys=True, default=str)
