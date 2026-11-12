"""Tests for per-case semantic scoring."""

import pytest

from k8s_review.case_scoring import calculate_case_score


def test_perfect_evaluation_scores_one():
    result = calculate_case_score(2, 2, 2, 2, 2, 2)

    assert result["f1"] == 1.0
    assert result["semantic_score"] == pytest.approx(1.0)
    assert result["false_positive_count"] == 0
    assert result["false_negative_count"] == 0


def test_partial_quality_uses_specified_weights():
    result = calculate_case_score(2, 2, 2, 1, 2, 1)

    assert result["f1"] == 1.0
    assert result["severity_score"] == 0.5
    assert result["evidence_score"] == 1.0
    assert result["remediation_score"] == 0.5
    assert result["semantic_score"] == pytest.approx(0.85)


def test_missed_finding_reduces_f1_and_score():
    result = calculate_case_score(2, 1, 1, 1, 1, 1)

    assert result["false_negative_count"] == 1
    assert result["f1"] == pytest.approx(2 / 3)
    assert result["semantic_score"] < 1.0


def test_empty_expected_and_generated_findings_score_one():
    result = calculate_case_score(0, 0, 0, 0, 0, 0)

    assert result["f1"] == 1.0
    assert result["semantic_score"] == pytest.approx(1.0)


def test_invalid_negative_count_is_rejected():
    with pytest.raises(ValueError, match="cannot be negative"):
        calculate_case_score(2, 2, 2, -1, 2, 2)


def test_matched_count_cannot_exceed_expected_count():
    with pytest.raises(ValueError, match="exceeds"):
        calculate_case_score(1, 2, 2, 2, 2, 2)
