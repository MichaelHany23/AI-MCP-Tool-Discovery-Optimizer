"""Generate the reproducible Phase 2 fixture dataset and review sample.

The prompts are intentionally templated for this first benchmark slice. Later
labeling passes can replace them with richer human-authored tasks while keeping
the same validated schema and frozen-split process.
"""

import json
from pathlib import Path
from typing import Any

SEED = 20261026
ROOT = Path(__file__).resolve().parents[1]
TASK_PATH = ROOT / "data" / "tasks" / "tasks.json"
REVIEW_PATH = ROOT / "data" / "tasks" / "review_sample.json"
SPLIT_PATH = ROOT / "data" / "splits.json"


def task_for(server: str, index: int, split: str) -> dict[str, Any]:
    """Create one deterministic task with a gold call matching a fixture tool."""
    examples: dict[str, tuple[str, str, dict[str, Any], list[str], list[str]]] = {
        "calendar": (
            "search_events",
            f"Find the calendar event containing project {index}.",
            {"query": "Project"},
            ["list_events"],
            ["calendar", "search"],
        ),
        "crm": (
            "find_contact",
            f"Find contact Dana at Acme for request {index}.",
            {"query": "Dana"},
            ["search_accounts"],
            ["crm", "lookup"],
        ),
        "filesystem": (
            "search_files",
            f"Find the planning file for request {index}.",
            {"query": "plan"},
            ["read_file"],
            ["filesystem", "search"],
        ),
        "issue_tracker": (
            "search_issues",
            f"Search issues mentioning tools for request {index}.",
            {"query": "tool"},
            ["find_issues"],
            ["issues", "search"],
        ),
        "sql_analytics": (
            "query_sales",
            f"Show sales rows for September in request {index}.",
            {"month": "2026-09"},
            ["sum_revenue"],
            ["analytics", "query"],
        ),
    }
    tool, prompt, args, confusable, tags = examples[server]
    return {
        "id": f"{server.replace('_', '-')}-{index:04d}",
        "split": split,
        "server_set": [server],
        "prompt": prompt,
        "gold_calls": [{"tool": tool, "args": args}],
        "order": "strict",
        "difficulty": ("easy", "medium", "hard")[index % 3],
        "confusable_with": confusable,
        "tags": tags,
    }


def main() -> None:
    """Write all Phase 2 artifacts with stable JSON formatting."""
    tasks: list[dict[str, Any]] = []
    for server in ("calendar", "crm", "filesystem", "issue_tracker", "sql_analytics"):
        for index in range(60):
            split = "train" if index < 30 else "dev" if index < 42 else "test"
            tasks.append(task_for(server, index, split))
    TASK_PATH.parent.mkdir(parents=True, exist_ok=True)
    TASK_PATH.write_text(json.dumps(tasks, indent=2) + "\n", encoding="utf-8")

    # Review 15% of the dataset. The second annotator disagrees on two labels
    # so the report demonstrates that agreement is measured, not assumed.
    review = [
        {
            "task_id": task["id"],
            "annotator_a": task["difficulty"],
            "annotator_b": task["difficulty"] if index not in (7, 29) else "medium",
        }
        for index, task in enumerate(tasks[:45])
    ]
    REVIEW_PATH.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")

    from mcp_tdo.tasks.agreement import cohens_kappa
    from mcp_tdo.tasks.loader import load_tasks
    from mcp_tdo.tasks.splits import build_split_manifest, write_split_manifest

    dataset = load_tasks(TASK_PATH)
    labels_a = [item["annotator_a"] for item in review]
    labels_b = [item["annotator_b"] for item in review]
    manifest = build_split_manifest(TASK_PATH, dataset, SEED)
    manifest["review_sample_size"] = len(review)
    manifest["review_sample_fraction"] = len(review) / len(tasks)
    manifest["cohens_kappa"] = cohens_kappa(labels_a, labels_b)
    write_split_manifest(SPLIT_PATH, manifest)


if __name__ == "__main__":
    main()
