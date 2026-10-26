"""A deterministic issue tracker with near-duplicate search tools."""

from mcp.server.fastmcp import FastMCP


def create_issue_tracker_server() -> FastMCP:
    """Return a small issue tracker whose state is fixed for reproducible runs."""
    server = FastMCP("issue_tracker")
    issues = [
        {"id": "ISSUE-1", "title": "Improve tool descriptions", "status": "open"},
        {"id": "ISSUE-2", "title": "Document local setup", "status": "closed"},
    ]

    @server.tool(description="Search issues.")
    def search_issues(query: str) -> list[dict[str, str]]:
        """Search issue titles and IDs."""
        query_lower = query.lower()
        return [
            issue
            for issue in issues
            if query_lower in issue["title"].lower() or query_lower in issue["id"].lower()
        ]

    @server.tool(description="Find issues.")
    def find_issues(status: str) -> list[dict[str, str]]:
        """Find issues by exact status."""
        return [issue for issue in issues if issue["status"] == status]

    return server

