"""Run one deterministic MCP server over the standard MCP stdio transport."""

import argparse

from mcp_tdo.mcp_servers import SERVER_FACTORIES


def main() -> None:
    """Start a named server for an MCP host such as Claude Desktop."""
    parser = argparse.ArgumentParser(description="Run an MCP-TDO fixture server.")
    parser.add_argument("server", choices=sorted(SERVER_FACTORIES))
    args = parser.parse_args()
    SERVER_FACTORIES[args.server]().run("stdio")


if __name__ == "__main__":
    main()
