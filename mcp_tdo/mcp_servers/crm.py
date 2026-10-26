"""A deterministic CRM server for contact and account lookup tasks."""

from mcp.server.fastmcp import FastMCP


def create_crm_server() -> FastMCP:
    """Return a CRM with a few records and intentionally vague descriptions."""
    server = FastMCP("crm")
    contacts = [
        {"id": "con-1", "name": "Dana Lee", "company": "Acme", "email": "dana@acme.test"},
        {
            "id": "con-2",
            "name": "Sam Rivera",
            "company": "Northwind",
            "email": "sam@northwind.test",
        },
    ]
    accounts = [
        {"id": "acc-1", "name": "Acme", "industry": "Manufacturing"},
        {"id": "acc-2", "name": "Northwind", "industry": "Retail"},
    ]

    @server.tool(description="Search CRM records.")
    def find_contact(query: str) -> list[dict[str, str]]:
        """Find people by name, company, or email."""
        query_lower = query.lower()
        return [
            contact
            for contact in contacts
            if any(query_lower in value.lower() for value in contact.values())
        ]

    @server.tool(description="Search CRM records.")
    def search_accounts(query: str) -> list[dict[str, str]]:
        """Find companies by name or industry."""
        query_lower = query.lower()
        return [
            account
            for account in accounts
            if any(query_lower in value.lower() for value in account.values())
        ]

    return server
