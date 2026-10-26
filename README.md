# MCP Tool Discovery Optimizer

MCP-TDO benchmarks whether AI agents choose the right MCP tool, arguments, and
call order, then tests whether clearer tool metadata improves those decisions.

> This project is in Phase 0. No benchmark results have been produced yet.

## Phase 0 setup

Requirements:

- Python 3.11+
- An MCP-compatible model provider for later benchmark runs

Create a virtual environment and install the project:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Copy `.env.example` to `.env` when provider credentials are needed. The `.env`
file is ignored by Git and must never be committed.

Run the initial checks:

```powershell
ruff check .
mypy mcp_tdo
pytest
```

## Project status

The implementation follows the phases in
[MCP_TOOL_DISCOVERY_OPTIMIZER_PLAN.md](./MCP_TOOL_DISCOVERY_OPTIMIZER_PLAN.md).
The metric definitions and evaluation safeguards are documented in
[docs/methodology.md](./docs/methodology.md).

## License

This project is released under the MIT License. See [LICENSE](./LICENSE).

