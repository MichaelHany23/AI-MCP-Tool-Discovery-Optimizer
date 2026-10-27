"""Agreement statistics for a reviewed sample of task labels."""

from collections.abc import Sequence


def cohens_kappa(first: Sequence[str], second: Sequence[str]) -> float:
    """Calculate Cohen's kappa for two annotators labeling the same items."""
    if len(first) != len(second) or not first:
        raise ValueError("Annotator label lists must have equal, non-zero length")
    categories = set(first) | set(second)
    observed = sum(left == right for left, right in zip(first, second, strict=True)) / len(first)
    expected = sum(
        (first.count(category) / len(first)) * (second.count(category) / len(second))
        for category in categories
    )
    if expected == 1:
        return 1.0
    return (observed - expected) / (1 - expected)
