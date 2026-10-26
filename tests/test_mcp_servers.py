"""Tests that prove the Phase 1 MCP fixtures behave predictably and safely."""

import asyncio
import sys

import anyio
import pytest
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.server.fastmcp import FastMCP
from mcp_tdo.mcp_client import InMemoryMCPClient
from mcp_tdo.mcp_servers import SERVER_FACTORIES, create_server


def test_all_phase_one_servers_are_registered() -> None:
    """Make sure the application can discover every planned fixture server."""
    assert set(SERVER_FACTORIES) == {
        "calendar",
        "crm",
        "filesystem",
        "issue_tracker",
        "sql_analytics",
    }


def test_unknown_server_has_actionable_error() -> None:
    """A misspelled server name should explain the problem instead of failing mysteriously."""
    with pytest.raises(ValueError, match="Unknown server"):
        create_server("missing")


def test_client_rejects_invalid_timeout() -> None:
    """A zero-second timeout is a configuration mistake and must be rejected early."""
    with pytest.raises(ValueError, match="greater than zero"):
        InMemoryMCPClient(create_server("crm"), "crm", timeout_seconds=0)


@pytest.mark.parametrize("server_name", sorted(SERVER_FACTORIES))
def test_each_server_exposes_tools_and_is_deterministic(server_name: str) -> None:
    """Every fixture must expose tools and return the same answer on repeated runs."""
    async def scenario() -> None:
        # These are safe, known-good examples for every tool in every fixture.
        # Keeping them here makes the test exercise the complete Phase 1 surface.
        tool_arguments = {
            "calendar": {
                "search_events": {"query": "Project"},
                "list_events": {"date": "2026-11-02"},
                "create_event": {"title": "Review", "date": "2026-11-04", "time": "09:00"},
            },
            "crm": {
                "find_contact": {"query": "Dana"},
                "search_accounts": {"query": "Acme"},
            },
            "filesystem": {
                "search_files": {"query": "plan"},
                "read_file": {"path": "/notes/plan.txt"},
            },
            "issue_tracker": {
                "search_issues": {"query": "tool"},
                "find_issues": {"status": "open"},
            },
            "sql_analytics": {
                "query_sales": {"month": "2026-09"},
                "sum_revenue": {"month": "2026-09"},
            },
        }
        # Two separately created servers should look identical to an MCP client.
        first_client = InMemoryMCPClient(create_server(server_name), server_name)
        second_client = InMemoryMCPClient(create_server(server_name), server_name)

        first_tools = await first_client.list_tools()
        second_tools = await second_client.list_tools()

        assert first_tools == second_tools
        assert first_tools
        assert all(tool.name and tool.description for tool in first_tools)

        # Calling the same tool with the same input twice should produce the same
        # result. This protects benchmark comparisons from changing server data.
        for tool_name, arguments in tool_arguments[server_name].items():
            first_result = await first_client.call_tool(tool_name, arguments)
            second_result = await second_client.call_tool(tool_name, arguments)
            assert first_result == second_result

    asyncio.run(scenario())


def test_client_lists_tools_and_records_successful_call() -> None:
    """The client should see tool metadata and save a successful call trace."""
    async def scenario() -> None:
        client = InMemoryMCPClient(create_server("crm"), "crm")

        tools = await client.list_tools()
        assert {tool.name for tool in tools} == {"find_contact", "search_accounts"}

        result = await client.call_tool("find_contact", {"query": "Dana"})
        assert "Dana Lee" in str(result)
        assert len(client.traces) == 1
        assert client.traces[0].error is None

    asyncio.run(scenario())


def test_client_records_failed_call_before_re_raising() -> None:
    """Failures must remain visible in traces while still reaching the caller."""
    async def scenario() -> None:
        client = InMemoryMCPClient(create_server("filesystem"), "filesystem")

        # The virtual filesystem intentionally has no such path. The client
        # should report the MCP failure, not silently return an empty result.
        with pytest.raises(RuntimeError, match="returned an error"):
            await client.call_tool("read_file", {"path": "/missing.txt"})

        assert len(client.traces) == 1
        assert client.traces[0].error is not None

    asyncio.run(scenario())


def test_client_times_out_slow_tool_and_records_reason() -> None:
    """A slow tool must stop at the safety boundary and leave an explainable trace."""
    async def scenario() -> None:
        server = FastMCP("slow-test")

        @server.tool()
        async def slow_tool() -> str:
            await anyio.sleep(0.2)
            return "finished"

        client = InMemoryMCPClient(server, "slow-test", timeout_seconds=0.01)
        with pytest.raises(TimeoutError):
            await client.call_tool("slow_tool", {})

        assert client.traces[0].error == "Tool call exceeded 0.01s timeout"

    asyncio.run(scenario())


def test_stdio_server_supports_real_external_mcp_connection() -> None:
    """The CLI-launched server must work through MCP stdio, not only in memory."""
    async def scenario() -> None:
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "mcp_tdo.mcp_servers.run", "crm"],
        )
        async with (
            stdio_client(parameters) as (read_stream, write_stream),
            ClientSession(read_stream, write_stream) as session,
        ):
            await session.initialize()
            tools = await session.list_tools()
            result = await session.call_tool("find_contact", {"query": "Dana"})

        assert {tool.name for tool in tools.tools} == {"find_contact", "search_accounts"}
        assert result.isError is False
        assert "Dana Lee" in str(result.content)

    asyncio.run(scenario())
