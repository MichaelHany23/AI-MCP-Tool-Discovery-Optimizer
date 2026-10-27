"""Create a reproducible manifest describing the frozen dataset split."""

import hashlib
import json
from pathlib import Path
from typing import Any

from mcp_tdo.tasks.models import TaskDataset


def content_hash(dataset_path: Path) -> str:
    """Hash the exact task file bytes so later runs can prove what was used."""
    return hashlib.sha256(dataset_path.read_bytes()).hexdigest()


def build_split_manifest(dataset_path: Path, dataset: TaskDataset, seed: int) -> dict[str, Any]:
    """Build the small manifest tracked with a frozen task dataset."""
    counts = {split: 0 for split in ("train", "dev", "test")}
    for task in dataset.tasks:
        counts[task.split] += 1
    return {
        "seed": seed,
        "content_sha256": content_hash(dataset_path),
        "task_count": len(dataset.tasks),
        "split_counts": counts,
        "split_proportions": {split: count / len(dataset.tasks) for split, count in counts.items()},
    }


def write_split_manifest(path: Path, manifest: dict[str, Any]) -> None:
    """Write the manifest in stable formatting for review and reproducibility."""
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
