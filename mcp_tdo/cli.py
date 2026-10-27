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


@app.command()
def serve(
    server: str = typer.Argument(..., help="Fixture server name, for example 'crm'."),
) -> None:
    """Run one fixture server over MCP stdio."""
    from mcp_tdo.mcp_servers import SERVER_FACTORIES

    if server not in SERVER_FACTORIES:
        supported = ", ".join(sorted(SERVER_FACTORIES))
        raise typer.BadParameter(f"Choose one of: {supported}", param_hint="server")
    SERVER_FACTORIES[server]().run("stdio")


@app.command("validate-tasks")
def validate_tasks_command(
    path: str = typer.Argument(..., help="Path to a JSON task file."),
) -> None:
    """Validate task labels and print counts for each frozen split."""
    from pathlib import Path

    from mcp_tdo.tasks.loader import validate_tasks

    try:
        counts = validate_tasks(Path(path), minimum_tasks=1)
    except (FileNotFoundError, ValueError) as error:
        raise typer.BadParameter(str(error), param_hint="path") from error
    typer.echo(f"valid tasks: {sum(counts.values())}")
    for split, count in counts.items():
        typer.echo(f"{split}: {count}")
