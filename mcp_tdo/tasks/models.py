"""Typed definitions for benchmark tasks.

Keeping the task format typed makes labeling errors visible before an expensive
model run starts.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Split = Literal["train", "dev", "test"]
OrderConstraint = Literal["strict", "partial", "any"]
Difficulty = Literal["easy", "medium", "hard"]


class GoldCall(BaseModel):
    """One tool call the agent is expected to make."""

    model_config = ConfigDict(extra="forbid")

    tool: str = Field(min_length=1)
    args: dict[str, Any] = Field(default_factory=dict)
    args_match: dict[str, Any] = Field(default_factory=dict)


class Task(BaseModel):
    """A single prompt, its gold workflow, and metadata for analysis."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]+$")
    split: Split
    server_set: list[str] = Field(min_length=1)
    prompt: str = Field(min_length=1)
    gold_calls: list[GoldCall] = Field(min_length=1)
    order: OrderConstraint
    difficulty: Difficulty
    confusable_with: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class TaskDataset(BaseModel):
    """A validated collection of unique benchmark tasks."""

    tasks: list[Task] = Field(min_length=1)

    def validate_unique_ids(self) -> None:
        """Reject duplicate IDs because they make traces impossible to join."""
        ids = [task.id for task in self.tasks]
        duplicates = sorted({task_id for task_id in ids if ids.count(task_id) > 1})
        if duplicates:
            raise ValueError(f"Duplicate task IDs: {', '.join(duplicates)}")

