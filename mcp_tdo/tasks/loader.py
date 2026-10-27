"""Load and validate the on-disk task dataset."""

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from mcp_tdo.tasks.models import Task, TaskDataset


def load_tasks(path: Path) -> TaskDataset:
    """Load a JSON task file and return typed tasks with useful errors."""
    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise FileNotFoundError(f"Task file not found: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"Task file is not valid JSON: {path}") from error

    if not isinstance(raw, list):
        raise ValueError("Task file must contain a JSON list")
    try:
        dataset = TaskDataset(tasks=[Task.model_validate(item) for item in raw])
    except ValidationError as error:
        raise ValueError(f"Task validation failed: {error}") from error
    dataset.validate_unique_ids()
    return dataset


def validate_tasks(path: Path, minimum_tasks: int = 1) -> dict[str, int]:
    """Validate a dataset and return counts by split for CLI/reporting use."""
    dataset = load_tasks(path)
    if len(dataset.tasks) < minimum_tasks:
        raise ValueError(f"Expected at least {minimum_tasks} tasks, found {len(dataset.tasks)}")
    counts = {split: 0 for split in ("train", "dev", "test")}
    for task in dataset.tasks:
        counts[task.split] += 1
    return counts
