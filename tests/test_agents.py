"""Offline tests for the agent loop and its local response cache."""

import asyncio
from pathlib import Path
from typing import Any

from mcp_tdo.agents import AgentRunner, AgentToolCall, ProviderResponse
from mcp_tdo.mcp_client import InMemoryMCPClient
from mcp_tdo.mcp_servers import create_server


class FakeProvider:
    """A tiny predictable model substitute for tests."""

    model = "fake-model"
    cost_per_1k_tokens = 0.25

    def __init__(self) -> None:
        self.calls = 0

    async def complete(
        self, messages: list[dict[str, Any]], tools: list[dict[str, Any]], seed: int
    ) -> ProviderResponse:
        self.calls += 1
        if self.calls == 1:
            return ProviderResponse(
                tool_calls=[AgentToolCall(name="find_contact", arguments={"query": "Dana"})],
                prompt_tokens=10,
                completion_tokens=4,
            )
        return ProviderResponse(text="Dana was found.", prompt_tokens=8, completion_tokens=3)


def test_agent_runner_calls_tool_and_stops() -> None:
    """The runner should call the requested MCP tool and then finish normally."""
    async def scenario() -> None:
        provider = FakeProvider()
        runner = AgentRunner(provider, InMemoryMCPClient(create_server("crm"), "crm"))

        result = await runner.run("Find Dana.")

        assert result.stopped_reason == "completed"
        assert result.steps == 2
        assert result.tool_calls[0].name == "find_contact"
        assert "Dana Lee" in str(result.tool_results)
        assert result.estimated_cost > 0

    asyncio.run(scenario())


def test_agent_runner_reuses_response_cache(tmp_path: Path) -> None:
    """An identical second run should use the saved response instead of the model."""
    async def scenario() -> None:
        first_provider = FakeProvider()
        first = AgentRunner(
            first_provider,
            InMemoryMCPClient(create_server("crm"), "crm"),
            cache_dir=tmp_path,
        )
        await first.run("Find Dana.")

        second_provider = FakeProvider()
        second = AgentRunner(
            second_provider,
            InMemoryMCPClient(create_server("crm"), "crm"),
            cache_dir=tmp_path,
        )
        result = await second.run("Find Dana.")

        assert result.cache_hit is True
        assert second_provider.calls == 0

    asyncio.run(scenario())
