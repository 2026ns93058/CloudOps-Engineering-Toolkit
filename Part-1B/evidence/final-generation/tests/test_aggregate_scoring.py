"""Tests for aggregate evaluation scoring."""

import pytest

from k8s_review.aggregate_scoring import calculate_aggregate_score


def test_aggregate_uses_arithmetic_mean():
    result = calculate_aggregate_score([0.8, 0.9, 1.0])

    assert result["aggregate_semantic_score"] == pytest.approx(0.9)
    assert result["evaluated_case_count"] == 3


def test_model_execution_failure_contributes_zero():
    result = calculate_aggregate_score([1.0, 0.8, 0.0])

    assert result["aggregate_semantic_score"] == pytest.approx(0.6)
    assert result["evaluated_case_count"] == 3


def test_perfect_aggregate_score():
    result = calculate_aggregate_score([1.0, 1.0])

    assert result["aggregate_semantic_score"] == pytest.approx(1.0)


def test_empty_score_list_is_rejected():
    with pytest.raises(ValueError, match="At least one"):
        calculate_aggregate_score([])


def test_out_of_range_score_is_rejected():
    with pytest.raises(ValueError, match="between 0 and 1"):
        calculate_aggregate_score([0.8, 1.2])


def test_boolean_score_is_rejected():
    with pytest.raises(ValueError, match="numeric"):
        calculate_aggregate_score([True, 0.8])
