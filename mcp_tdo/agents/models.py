"""The small data objects shared by providers and the agent loop."""

from typing import Any

from pydantic import BaseModel, Field


class AgentToolCall(BaseModel):
    """A tool call returned by a model."""

    name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ProviderResponse(BaseModel):
    """The useful parts of one response from an LLM provider."""

    text: str = ""
    tool_calls: list[AgentToolCall] = Field(default_factory=list)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    raw: dict[str, Any] = Field(default_factory=dict)


class AgentRunResult(BaseModel):
    """Everything we want to keep after one task has finished."""

    model: str
    prompt: str
    final_text: str = ""
    tool_calls: list[AgentToolCall] = Field(default_factory=list)
    tool_results: list[Any] = Field(default_factory=list)
    steps: int = 0
    stopped_reason: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float
    estimated_cost: float = 0.0
    cache_hit: bool = False
