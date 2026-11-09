"""Core benchmark metrics, written around one task at a time."""

from collections import defaultdict
from typing import Any

from mcp_tdo.agents.models import AgentRunResult
from mcp_tdo.tasks.models import Task


class TaskScore:
    """The pass/fail details that explain one task's score."""

    def __init__(
        self,
        task_id: str,
        selected_tools: list[str],
        gold_tools: list[str],
        selection_correct: bool,
        argument_valid: bool,
        argument_correct: bool,
        order_score: float,
        success: bool,
    ) -> None:
        self.task_id = task_id
        self.selected_tools = selected_tools
        self.gold_tools = gold_tools
        self.selection_correct = selection_correct
        self.argument_valid = argument_valid
        self.argument_correct = argument_correct
        self.order_score = order_score
        self.success = success

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-friendly version for reports."""
        return self.__dict__.copy()


class EvaluationSummary:
    """Aggregate metrics and the confusion matrix for a group of tasks."""

    def __init__(self, scores: list[TaskScore]) -> None:
        self.scores = scores
        self.confusion_matrix = build_confusion_matrix(scores)
        self.metrics = {
            "task_count": len(scores),
            "tool_selection_accuracy": _mean(score.selection_correct for score in scores),
            "argument_validity_rate": _mean(score.argument_valid for score in scores),
            "argument_correctness": _mean(score.argument_correct for score in scores),
            "call_order_score": _mean(score.order_score for score in scores),
            "task_success_rate": _mean(score.success for score in scores),
            "hallucinated_tool_rate": _mean(
                "HALLUCINATED" in score.selected_tools for score in scores
            ),
            "average_calls_per_task": _mean(len(score.selected_tools) for score in scores),
        }
        self.metrics["tool_selection_f1_macro"] = macro_f1(scores)

    def as_dict(self) -> dict[str, Any]:
        """Return the summary in a format suitable for JSON or Markdown."""
        return {
            "metrics": self.metrics,
            "confusion_matrix": self.confusion_matrix,
            "top_confusions": top_confusions(self.confusion_matrix),
            "tasks": [score.as_dict() for score in self.scores],
        }


def score_task(task: Task, result: AgentRunResult, valid_tools: set[str]) -> TaskScore:
    """Compare one agent result with one labeled task."""
    from mcp_tdo.scoring.matchers import arguments_match

    selected = [call.name for call in result.tool_calls]
    gold = [call.tool for call in task.gold_calls]
    selection_correct = selected == gold
    argument_valid = all(call.name in valid_tools for call in result.tool_calls)
    argument_correct = len(selected) == len(task.gold_calls) and all(
        arguments_match(gold_call.args_match or gold_call.args, call.arguments)
        for call, gold_call in zip(result.tool_calls, task.gold_calls, strict=False)
    )
    order_score = sequence_similarity(gold, selected)
    success = selection_correct and argument_valid and argument_correct and order_score == 1.0
    return TaskScore(
        task.id,
        [tool if tool in valid_tools else "HALLUCINATED" for tool in selected],
        gold,
        selection_correct,
        argument_valid,
        argument_correct,
        order_score,
        success,
    )


def sequence_similarity(expected: list[str], actual: list[str]) -> float:
    """Return a normalized edit similarity between two call sequences."""
    if not expected and not actual:
        return 1.0
    distance = [[0] * (len(actual) + 1) for _ in range(len(expected) + 1)]
    for row in range(len(expected) + 1):
        distance[row][0] = row
    for column in range(len(actual) + 1):
        distance[0][column] = column
    for row in range(1, len(expected) + 1):
        for column in range(1, len(actual) + 1):
            distance[row][column] = min(
                distance[row - 1][column] + 1,
                distance[row][column - 1] + 1,
                distance[row - 1][column - 1] + (expected[row - 1] != actual[column - 1]),
            )
    return max(0.0, 1 - distance[-1][-1] / max(len(expected), len(actual), 1))


def build_confusion_matrix(scores: list[TaskScore]) -> dict[str, dict[str, int]]:
    """Build rows of gold tools against columns of selected tools."""
    matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for score in scores:
        for index, gold in enumerate(score.gold_tools):
            selected = score.selected_tools[index] if index < len(score.selected_tools) else "NONE"
            matrix[gold][selected] += 1
    return {row: dict(columns) for row, columns in sorted(matrix.items())}


def top_confusions(matrix: dict[str, dict[str, int]]) -> list[dict[str, Any]]:
    """List incorrect tool choices in descending order."""
    pairs = [
        {"gold": gold, "selected": selected, "count": count}
        for gold, columns in matrix.items()
        for selected, count in columns.items()
        if gold != selected
    ]
    return sorted(pairs, key=lambda pair: (-pair["count"], pair["gold"], pair["selected"]))


def macro_f1(scores: list[TaskScore]) -> float:
    """Calculate macro F1 over the tools that appear as gold labels."""
    labels = sorted({tool for score in scores for tool in score.gold_tools})
    values = []
    for label in labels:
        true_positive = sum(
            label in score.selected_tools and label in score.gold_tools for score in scores
        )
        false_positive = sum(
            label in score.selected_tools and label not in score.gold_tools for score in scores
        )
        false_negative = sum(
            label not in score.selected_tools and label in score.gold_tools for score in scores
        )
        precision = (
            true_positive / (true_positive + false_positive)
            if true_positive + false_positive
            else 0
        )
        recall = (
            true_positive / (true_positive + false_negative)
            if true_positive + false_negative
            else 0
        )
        values.append(2 * precision * recall / (precision + recall) if precision + recall else 0)
    return sum(values) / len(values) if values else 0.0


def _mean(values: Any) -> float:
    values = list(values)
    return sum(float(value) for value in values) / len(values) if values else 0.0
