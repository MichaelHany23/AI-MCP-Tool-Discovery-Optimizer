"""Small trace records used later by the scorer and experiment tracker."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class ToolCallTrace(BaseModel):
    """A human-readable record of one tool call and its result."""

    server: str
    tool: str
    arguments: dict[str, Any]
    result: Any = None
    error: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
