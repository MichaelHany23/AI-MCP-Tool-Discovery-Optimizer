"""Small, deterministic MCP servers used by the benchmark.

The servers intentionally start with imperfect metadata. That gives the later
optimizer something real to improve instead of beginning with a perfect toy.
"""

from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from mcp_tdo.mcp_servers.calendar import create_calendar_server
from mcp_tdo.mcp_servers.crm import create_crm_server
from mcp_tdo.mcp_servers.filesystem import create_filesystem_server
from mcp_tdo.mcp_servers.issue_tracker import create_issue_tracker_server
from mcp_tdo.mcp_servers.sql_analytics import create_sql_analytics_server

SERVER_FACTORIES: dict[str, Callable[[], FastMCP]] = {
    "calendar": create_calendar_server,
    "crm": create_crm_server,
    "filesystem": create_filesystem_server,
    "issue_tracker": create_issue_tracker_server,
    "sql_analytics": create_sql_analytics_server,
}


def create_server(name: str) -> FastMCP:
    """Create one named deterministic server, with a helpful error for typos."""
    try:
        factory = SERVER_FACTORIES[name]
    except KeyError as error:
        supported = ", ".join(sorted(SERVER_FACTORIES))
        raise ValueError(f"Unknown server {name!r}; choose from: {supported}") from error
    return factory()
