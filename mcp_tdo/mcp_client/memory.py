"""An MCP client that connects to local servers without network or cloud costs."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import anyio
from mcp.client.session import ClientSession
from mcp.shared.memory import create_connected_server_and_client_session
from pydantic import BaseModel

from mcp_tdo.mcp_client.traces import ToolCallTrace


class ToolSummary(BaseModel):
    """The metadata an agent would see when deciding which tool to use."""

    name: str
    description: str | None
    input_schema: dict[str, Any]


class InMemoryMCPClient:
    """Connect to a FastMCP server in-process using the real MCP protocol."""

    def __init__(self, server: Any, server_name: str, timeout_seconds: float = 10.0) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        self._server = server
        self.server_name = server_name
        self.timeout_seconds = timeout_seconds
        self.traces: list[ToolCallTrace] = []

    @asynccontextmanager
    async def session(self) -> AsyncIterator[ClientSession]:
        """Open a short-lived session and close it reliably after the operation."""
        async with create_connected_server_and_client_session(self._server) as session:
            yield session

    async def list_tools(self) -> list[ToolSummary]:
        """List the exact tool metadata that an agent receives."""
        with anyio.fail_after(self.timeout_seconds):
            async with self.session() as session:
                result = await session.list_tools()
        return [
            ToolSummary(
                name=tool.name,
                description=tool.description,
                input_schema=tool.inputSchema,
            )
            for tool in result.tools
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Call a tool and save the result so later scoring can inspect it."""
        trace = ToolCallTrace(server=self.server_name, tool=name, arguments=arguments)
        try:
            with anyio.fail_after(self.timeout_seconds):
                async with self.session() as session:
                    result = await session.call_tool(name, arguments)
            trace.result = [content.model_dump(mode="json") for content in result.content]
            if result.isError:
                trace.error = f"MCP tool {name!r} returned an error"
                self.traces.append(trace)
                raise RuntimeError(trace.error)
            self.traces.append(trace)
            return trace.result
        except Exception as error:
            if isinstance(error, TimeoutError):
                trace.error = f"Tool call exceeded {self.timeout_seconds:g}s timeout"
            else:
                trace.error = str(error)
            if not self.traces or self.traces[-1] is not trace:
                self.traces.append(trace)
            raise
