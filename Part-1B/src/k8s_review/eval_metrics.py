"""Calculate evaluation metrics for AI-generated findings."""

from typing import Any


def calculate_issue_metrics(
    expected_count: int,
    generated_count: int,
    matched_count: int,
) -> dict[str, Any]:
    """Calculate true positives, false positives, false negatives, precision, and recall."""
    true_positives = matched_count
    false_positives = generated_count - matched_count
    false_negatives = expected_count - matched_count

    if expected_count == 0 and generated_count == 0:
        precision = 1.0
        recall = 1.0
    else:
        precision = (
            true_positives / generated_count if generated_count else 0.0
        )
        recall = (
            true_positives / expected_count if expected_count else 0.0
        )

    return {
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "precision": precision,
        "recall": recall,
    }
