"""Run an honest, offline baseline against the frozen task set.

This is not pretending to be an LLM result. It is a deterministic control run
that intentionally gets one quarter of tool choices wrong, which lets us verify
the scoring and report pipeline before spending time on model experiments.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

from mcp_tdo.agents.models import AgentRunResult, AgentToolCall
from mcp_tdo.mcp_client import InMemoryMCPClient
from mcp_tdo.mcp_servers import create_server
from mcp_tdo.scoring import EvaluationSummary, score_task
from mcp_tdo.tasks.loader import load_tasks

ROOT = Path(__file__).resolve().parents[1]
TASK_PATH = ROOT / "data" / "tasks" / "tasks.json"
REPORT_DIR = ROOT / "data" / "reports"


async def available_tools() -> dict[str, set[str]]:
    """Read the real MCP metadata so the baseline uses genuine tool names."""
    names: dict[str, set[str]] = {}
    for server in ("calendar", "crm", "filesystem", "issue_tracker", "sql_analytics"):
        client = InMemoryMCPClient(create_server(server), server)
        names[server] = {tool.name for tool in await client.list_tools()}
    return names


def build_result(task: Any, model_tools: set[str]) -> AgentRunResult:
    """Create one deterministic control result for a labeled task."""
    gold_call = task.gold_calls[0]
    index = int(task.id.rsplit("-", 1)[1])
    chosen_tool = gold_call.tool
    if index % 4 == 0 and task.confusable_with and task.confusable_with[0] in model_tools:
        chosen_tool = task.confusable_with[0]
    return AgentRunResult(
        model="offline-control-v0",
        prompt=task.prompt,
        final_text="Control run completed.",
        tool_calls=[AgentToolCall(name=chosen_tool, arguments=gold_call.args)],
        tool_results=[],
        steps=1,
        stopped_reason="completed",
        latency_ms=0.0,
    )


def markdown_report(reports: dict[str, dict[str, Any]]) -> str:
    """Make the baseline results easy to read without opening JSON."""
    lines = [
        "# Phase 4 offline baseline",
        "",
        "This is a deterministic control run, not an LLM result. It intentionally",
        "selects a confusable tool for one out of every four eligible tasks so the",
        "scoring and confusion-matrix pipeline can be checked end to end.",
        "",
        "| Split | Selection | Arguments | Order | Task success |",
        "|---|---:|---:|---:|---:|",
    ]
    for split, report in reports.items():
        metrics = report["metrics"]
        lines.append(
            f"| {split} | {metrics['tool_selection_accuracy']:.1%} | "
            f"{metrics['argument_correctness']:.1%} | {metrics['call_order_score']:.1%} | "
            f"{metrics['task_success_rate']:.1%} |"
        )
    lines.extend(["", "## Top confusions", ""])
    for split, report in reports.items():
        lines.append(f"### {split}")
        for pair in report["top_confusions"][:5]:
            lines.append(
                f"- Expected `{pair['gold']}`, selected `{pair['selected']}`: "
                f"{pair['count']} task(s)"
            )
    return "\n".join(lines) + "\n"


async def main() -> None:
    """Score all 300 tasks and write JSON plus a readable Markdown report."""
    dataset = load_tasks(TASK_PATH)
    tools_by_server = await available_tools()
    reports: dict[str, dict[str, Any]] = {}
    for split in ("train", "dev", "test"):
        scores = []
        for task in [item for item in dataset.tasks if item.split == split]:
            result = build_result(task, tools_by_server[task.server_set[0]])
            scores.append(score_task(task, result, tools_by_server[task.server_set[0]]))
        reports[split] = EvaluationSummary(scores).as_dict()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (REPORT_DIR / "phase4_baseline.json").write_text(
        json.dumps(reports, indent=2) + "\n", encoding="utf-8"
    )
    (REPORT_DIR / "phase4_baseline.md").write_text(markdown_report(reports), encoding="utf-8")
    print(markdown_report(reports))


if __name__ == "__main__":
    asyncio.run(main())
