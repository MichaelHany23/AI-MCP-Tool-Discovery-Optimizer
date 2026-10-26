"""Command-line entry point for MCP-TDO."""

import typer

app = typer.Typer(
    name="mcp-tdo",
    help="Benchmark and optimize AI-agent MCP tool discovery.",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """Run MCP-TDO commands."""


@app.command()
def version() -> None:
    """Show the current MCP-TDO version."""
    from mcp_tdo import __version__

    typer.echo(__version__)
