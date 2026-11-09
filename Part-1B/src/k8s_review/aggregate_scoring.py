"""Calculate aggregate semantic evaluation scores."""

from typing import Any


def calculate_aggregate_score(
    case_scores: list[float],
) -> dict[str, Any]:
    """Calculate the arithmetic mean of AI-eligible case scores."""
    if not case_scores:
        raise ValueError("At least one AI-eligible case score is required.")

    for score in case_scores:
        if not isinstance(score, (int, float)) or isinstance(score, bool):
            raise ValueError("Case scores must be numeric.")

        if not 0.0 <= score <= 1.0:
            raise ValueError("Case scores must be between 0 and 1.")

    aggregate_score = sum(case_scores) / len(case_scores)

    return {
        "aggregate_semantic_score": aggregate_score,
        "evaluated_case_count": len(case_scores),
    }
