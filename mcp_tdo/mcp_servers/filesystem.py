"""A safe, in-memory filesystem server for deterministic benchmark tasks."""

from mcp.server.fastmcp import FastMCP


def create_filesystem_server() -> FastMCP:
    """Return a filesystem-like server that never touches the real disk."""
    server = FastMCP("filesystem")
    files = {
        "/notes/plan.txt": "MCP-TDO Phase 1 plan",
        "/notes/ideas.txt": "Compare tool descriptions",
    }

    @server.tool(description="Find files.")
    def search_files(query: str) -> list[str]:
        """Find virtual paths containing the query."""
        return [path for path in files if query.lower() in path.lower()]

    @server.tool(description="Read a file.")
    def read_file(path: str) -> str:
        """Read one virtual file and fail clearly when it does not exist."""
        try:
            return files[path]
        except KeyError as error:
            raise ValueError(f"Virtual file not found: {path}") from error

    return server

