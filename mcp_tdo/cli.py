"""Command-line entry point for MCP-TDO."""

import asyncio
from pathlib import Path

import typer

app = typer.Typer(
    name="mcp-tdo",
    help="Benchmark and optimize AI-agent MCP tool discovery.",
    no_args_is_help=True,
)
CACHE_DIR_OPTION = typer.Option(None, help="Optional response-cache directory.")


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


@app.command("run")
def run_agent(
    prompt: str = typer.Argument(..., help="Natural-language task for the agent."),
    model: str = typer.Option("qwen3:8b", help="Local Ollama model name."),
    server: str = typer.Option("crm", help="Fixture MCP server name."),
    max_steps: int = typer.Option(5, min=1, help="Maximum model/tool iterations."),
    cache_dir: Path | None = CACHE_DIR_OPTION,
) -> None:
    """Run one task with a local Ollama model and an MCP fixture server."""
    from mcp_tdo.agents import AgentRunner
    from mcp_tdo.agents.providers import OllamaProvider
    from mcp_tdo.mcp_client import InMemoryMCPClient
    from mcp_tdo.mcp_servers import SERVER_FACTORIES

    if server not in SERVER_FACTORIES:
        supported = ", ".join(sorted(SERVER_FACTORIES))
        raise typer.BadParameter(f"Choose one of: {supported}", param_hint="server")

    runner = AgentRunner(
        OllamaProvider(model),
        InMemoryMCPClient(SERVER_FACTORIES[server](), server),
        max_steps=max_steps,
        cache_dir=cache_dir,
    )
    result = asyncio.run(runner.run(prompt))
    typer.echo(result.model_dump_json(indent=2))
