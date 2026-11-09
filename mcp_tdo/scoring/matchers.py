"""Small argument matchers used by task labels."""

import re
from datetime import datetime
from typing import Any


def matches(expected: Any, actual: Any) -> bool:
    """Compare one expected value with one actual value using a task matcher."""
    if isinstance(expected, dict):
        if "contains" in expected:
            return str(expected["contains"]).lower() in str(actual).lower()
        if "regex" in expected:
            return re.search(str(expected["regex"]), str(actual)) is not None
        if "numeric_tolerance" in expected:
            tolerance = float(expected["numeric_tolerance"])
            return abs(float(actual) - float(expected.get("value", 0))) <= tolerance
        if "datetime_approx" in expected:
            return _datetime_close(str(expected["datetime_approx"]), str(actual))
        if "set_equal" in expected:
            return bool(set(expected["set_equal"]) == set(actual))
    if isinstance(expected, list):
        return bool(expected == actual)
    return bool(expected == actual)


def arguments_match(expected: dict[str, Any], actual: dict[str, Any]) -> bool:
    """Require every labeled argument to match and reject missing arguments."""
    return all(key in actual and matches(value, actual[key]) for key, value in expected.items())


def _datetime_close(expected: str, actual: str) -> bool:
    """Handle ISO timestamps; unresolved natural language is compared literally."""
    try:
        expected_date = datetime.fromisoformat(expected.replace("Z", "+00:00"))
        actual_date = datetime.fromisoformat(actual.replace("Z", "+00:00"))
    except ValueError:
        return expected.lower() in actual.lower()
    return abs((expected_date - actual_date).total_seconds()) <= 300
