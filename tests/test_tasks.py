"""Tests for Phase 2 task validation and labeling statistics."""

import json
from pathlib import Path

import pytest
from mcp_tdo.tasks.agreement import cohens_kappa
from mcp_tdo.tasks.loader import load_tasks, validate_tasks
from mcp_tdo.tasks.models import Task, TaskDataset
from mcp_tdo.tasks.splits import content_hash

ROOT = Path(__file__).parents[1]
TASK_PATH = ROOT / "data" / "tasks" / "tasks.json"
SPLIT_PATH = ROOT / "data" / "splits.json"


def test_frozen_dataset_has_expected_size_and_splits() -> None:
    """The committed dataset must keep the promised 50/20/30 split."""
    counts = validate_tasks(TASK_PATH, minimum_tasks=300)

    assert counts == {"train": 150, "dev": 60, "test": 90}


def test_split_manifest_matches_task_file() -> None:
    """The manifest hash prevents silently changing tasks after a run."""
    manifest = json.loads(SPLIT_PATH.read_text(encoding="utf-8"))
    dataset = load_tasks(TASK_PATH)

    assert manifest["task_count"] == len(dataset.tasks)
    assert manifest["content_sha256"] == content_hash(TASK_PATH)
    assert manifest["review_sample_size"] == 45
    assert 0.0 <= manifest["cohens_kappa"] <= 1.0


def test_duplicate_ids_are_rejected() -> None:
    """Duplicate IDs would make model traces impossible to join to labels."""
    task = Task.model_validate(json.loads(TASK_PATH.read_text(encoding="utf-8"))[0])

    with pytest.raises(ValueError, match="Duplicate task IDs"):
        TaskDataset(tasks=[task, task]).validate_unique_ids()


def test_kappa_requires_matching_non_empty_labels() -> None:
    """Agreement is undefined when annotators reviewed different item counts."""
    with pytest.raises(ValueError, match="equal, non-zero"):
        cohens_kappa(["easy"], [])
