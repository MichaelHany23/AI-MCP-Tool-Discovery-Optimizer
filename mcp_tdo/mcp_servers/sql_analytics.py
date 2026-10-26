"""A read-only analytics server backed by fixed rows."""

from typing import TypedDict

from mcp.server.fastmcp import FastMCP


class SalesRow(TypedDict):
    """One predictable row returned by the analytics fixture."""

    month: str
    region: str
    revenue: int


def create_sql_analytics_server() -> FastMCP:
    """Return analytics tools without requiring a database service."""
    server = FastMCP("sql_analytics")
    sales: list[SalesRow] = [
        {"month": "2026-09", "region": "North", "revenue": 1200},
        {"month": "2026-09", "region": "South", "revenue": 900},
        {"month": "2026-10", "region": "North", "revenue": 1500},
    ]

    @server.tool(description="Get data.")
    def query_sales(month: str) -> list[SalesRow]:
        """Return sales rows for an exact YYYY-MM month."""
        return [row for row in sales if row["month"] == month]

    @server.tool(description="Get a number.")
    def sum_revenue(month: str) -> int:
        """Return total revenue for an exact YYYY-MM month."""
        return sum(row["revenue"] for row in sales if row["month"] == month)

    return server
