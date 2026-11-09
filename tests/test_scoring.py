"""Tests for Phase 4 metrics and argument matching."""

from mcp_tdo.agents.models import AgentRunResult, AgentToolCall
from mcp_tdo.scoring.matchers import arguments_match, matches
from mcp_tdo.scoring.metrics import sequence_similarity


def test_argument_matchers_cover_common_labeling_cases() -> None:
    assert matches({"contains": "Acme"}, "Dana at Acme")
    assert matches({"regex": r"ISSUE-\d+"}, "ISSUE-12")
    assert matches({"numeric_tolerance": 2, "value": 10}, 11)
    assert matches({"set_equal": ["a", "b"]}, ["b", "a"])
    assert arguments_match({"query": "Dana"}, {"query": "Dana"})


def test_sequence_similarity_rewards_exact_order() -> None:
    assert sequence_similarity(["a", "b"], ["a", "b"]) == 1.0
    assert sequence_similarity(["a", "b"], ["b", "a"]) < 1.0


def test_agent_result_model_can_hold_scoring_input() -> None:
    result = AgentRunResult(
        model="test",
        prompt="Find Dana",
        tool_calls=[AgentToolCall(name="find_contact", arguments={"query": "Dana"})],
        stopped_reason="completed",
        latency_ms=1.0,
    )
    assert result.tool_calls[0].name == "find_contact"
