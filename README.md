# MCP Tool Discovery Optimizer

MCP-TDO benchmarks whether AI agents choose the right MCP tool, arguments, and
call order, then tests whether clearer tool metadata improves those decisions.

> Phase 1 is complete. No benchmark results have been produced yet.

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

### Phase 1 so far

The project now includes five small, local MCP servers:

- **Calendar** for events
- **CRM** for contacts and accounts
- **Filesystem** using safe in-memory files
- **Issue tracker** for searching and filtering issues
- **SQL analytics** using fixed sales rows

They are deliberately deterministic, which means the same task produces the
same server result every time. Their descriptions also include a few realistic
ambiguities, such as two tools that both sound like search tools. Those
ambiguities are the problems the optimizer will later try to fix.

The in-process MCP client uses the real MCP protocol to list tool metadata and
call tools without a network service or paid API. Every call is saved as a
trace, including failures, so later scoring can explain what happened.

For integration testing, a fixture can also run over the standard MCP stdio
transport:

```powershell
mcp-tdo serve crm
```

The client uses a configurable timeout, rejects invalid timeout settings, and
turns MCP error responses into explicit failures. The filesystem fixture is
fully in memory, so benchmark runs cannot read or modify the real computer.
The test suite also verifies a slow tool timeout and a complete external stdio
connection through the standalone server command.

### Phase 2: tasks and labeling

Phase 2 now includes 300 validated tasks in
[data/tasks/tasks.json](./data/tasks/tasks.json), distributed across all five
servers:

- 150 train tasks
- 60 development tasks
- 90 sealed test tasks

The split is frozen in [data/splits.json](./data/splits.json), which records the
seed, task-file SHA-256 hash, split counts, and Cohen's kappa for a 15% review
sample. Run the validator with:

```powershell
mcp-tdo validate-tasks data/tasks/tasks.json
```

### Phase 3: agent runner

Phase 3 lets a local Ollama model work with an MCP server. The runner first
shows the model the available tools, carries out the calls the model requests,
and sends each result back so the model can decide what to do next. It stops
when the model has an answer or reaches the safety limit.

Run one local task without a paid API:

```powershell
mcp-tdo run "Find Dana at Acme." --model qwen3:8b --server crm --cache-dir .cache\agents
```

The result includes the model name, selected tools, tool results, stop reason,
number of steps, latency, token counts, estimated cost, and whether a cached
provider response was reused. The Ollama adapter uses temperature zero and a
fixed seed to make local development runs easier to repeat. The cache key
includes the model, messages, tool schemas, and seed, so changing a tool
description cannot accidentally reuse an unrelated response.

### Phase 4: scoring and baseline

Phase 4 compares an agent run with the gold calls in the task file. It reports
tool selection, macro F1, argument validity, argument correctness, call order,
task success, hallucinated tools, average calls, and a confusion matrix.

The offline baseline can be reproduced with:

```powershell
python scripts\run_phase4_baseline.py
```

It writes JSON and Markdown reports under
[data/reports/](./data/reports/). This first result is a control run, not a
claim about Qwen or another LLM: it deliberately picks a confusable tool on
one quarter of eligible tasks so the scoring pipeline can be inspected before
live model experiments begin.

## License

This project is released under the MIT License. See [LICENSE](./LICENSE).
