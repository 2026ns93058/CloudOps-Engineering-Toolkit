"""Calculate weighted semantic scores for individual evaluation cases."""

from typing import Any


WEIGHTS = {
    "issue_identification": 0.50,
    "severity_correctness": 0.20,
    "evidence_grounding": 0.20,
    "remediation_quality": 0.10,
}


def calculate_case_score(
    expected_count: int,
    generated_count: int,
    matched_count: int,
    severity_correct_count: int,
    evidence_grounded_count: int,
    remediation_quality_count: int,
) -> dict[str, Any]:
    """Calculate F1 and weighted semantic quality components."""

    if min(
        expected_count,
        generated_count,
        matched_count,
        severity_correct_count,
        evidence_grounded_count,
        remediation_quality_count,
    ) < 0:
        raise ValueError("Evaluation counts cannot be negative.")

    if matched_count > min(expected_count, generated_count):
        raise ValueError("Matched count exceeds expected or generated findings.")

    if any(
        count > matched_count
        for count in (
            severity_correct_count,
            evidence_grounded_count,
            remediation_quality_count,
        )
    ):
        raise ValueError("Quality counts cannot exceed matched findings.")

    true_positives = matched_count
    false_positives = generated_count - matched_count
    false_negatives = expected_count - matched_count

    if expected_count == 0 and generated_count == 0:
        precision = recall = f1 = 1.0
    else:
        precision = (
            true_positives / generated_count if generated_count else 0.0
        )
        recall = (
            true_positives / expected_count if expected_count else 0.0
        )
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        )

    if expected_count == 0:
        severity_score = 1.0 if generated_count == 0 else 0.0
        evidence_score = severity_score
        remediation_score = severity_score
    else:
        severity_score = severity_correct_count / expected_count
        evidence_score = evidence_grounded_count / expected_count
        remediation_score = remediation_quality_count / expected_count

    semantic_score = (
        f1 * WEIGHTS["issue_identification"]
        + severity_score * WEIGHTS["severity_correctness"]
        + evidence_score * WEIGHTS["evidence_grounding"]
        + remediation_score * WEIGHTS["remediation_quality"]
    )

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "severity_score": severity_score,
        "evidence_score": evidence_score,
        "remediation_score": remediation_score,
        "semantic_score": semantic_score,
        "false_positive_count": false_positives,
        "false_negative_count": false_negatives,
    }
