"""A tiny calendar server with deliberately similar search tools."""

from mcp.server.fastmcp import FastMCP


def create_calendar_server() -> FastMCP:
    """Return a calendar backed by fixed events so every run is repeatable."""
    server = FastMCP("calendar")
    events = [
        {"id": "evt-1", "title": "Project kickoff", "date": "2026-11-02", "time": "10:00"},
        {"id": "evt-2", "title": "Dentist", "date": "2026-11-03", "time": "15:00"},
    ]

    @server.tool(description="Find calendar things by text.")
    def search_events(query: str) -> list[dict[str, str]]:
        """Search event titles."""
        query_lower = query.lower()
        return [event for event in events if query_lower in event["title"].lower()]

    @server.tool(description="Get events for a date.")
    def list_events(date: str) -> list[dict[str, str]]:
        """List events on an ISO date."""
        return [event for event in events if event["date"] == date]

    @server.tool(description="Add a calendar thing.")
    def create_event(title: str, date: str, time: str) -> dict[str, str]:
        """Return the event that would be created without changing shared state."""
        return {"id": "evt-new", "title": title, "date": date, "time": time}

    return server

