"""Tests for semantic acceptance threshold decisions."""

import pytest

from k8s_review.acceptance import evaluate_semantic_threshold


def test_score_above_threshold_passes():
    result = evaluate_semantic_threshold(0.90)

    assert result["semantic_threshold_pass"] is True
    assert result["acceptance_threshold"] == 0.80


def test_score_exactly_at_threshold_passes():
    result = evaluate_semantic_threshold(0.80)

    assert result["semantic_threshold_pass"] is True


def test_score_below_threshold_fails():
    result = evaluate_semantic_threshold(0.79)

    assert result["semantic_threshold_pass"] is False


def test_zero_score_fails():
    result = evaluate_semantic_threshold(0.0)

    assert result["semantic_threshold_pass"] is False


def test_perfect_score_passes():
    result = evaluate_semantic_threshold(1.0)

    assert result["semantic_threshold_pass"] is True


def test_invalid_score_is_rejected():
    with pytest.raises(ValueError, match="between 0 and 1"):
        evaluate_semantic_threshold(1.2)


def test_boolean_score_is_rejected():
    with pytest.raises(ValueError, match="numeric"):
        evaluate_semantic_threshold(True)


def test_invalid_threshold_is_rejected():
    with pytest.raises(ValueError, match="between 0 and 1"):
        evaluate_semantic_threshold(0.90, threshold=1.5)


def test_all_quality_gates_pass():
    from k8s_review.acceptance import evaluate_quality_gates

    result = evaluate_quality_gates(0.90, 1.0, 1.0)

    assert result["overall_status"] == "PASS"
    assert result["schema_requirement_pass"] is True
    assert result["safety_requirement_pass"] is True


def test_schema_failure_causes_overall_failure():
    from k8s_review.acceptance import evaluate_quality_gates

    result = evaluate_quality_gates(0.95, 0.99, 1.0)

    assert result["overall_status"] == "FAIL"
    assert result["schema_requirement_pass"] is False


def test_safety_failure_causes_overall_failure():
    from k8s_review.acceptance import evaluate_quality_gates

    result = evaluate_quality_gates(0.95, 1.0, 0.99)

    assert result["overall_status"] == "FAIL"
    assert result["safety_requirement_pass"] is False


def test_semantic_failure_causes_overall_failure():
    from k8s_review.acceptance import evaluate_quality_gates

    result = evaluate_quality_gates(0.79, 1.0, 1.0)

    assert result["overall_status"] == "FAIL"


def test_multiple_quality_gate_failures():
    from k8s_review.acceptance import evaluate_quality_gates

    result = evaluate_quality_gates(0.60, 0.95, 0.90)

    assert result["overall_status"] == "FAIL"
    assert result["semantic_threshold_pass"] is False
    assert result["schema_requirement_pass"] is False
    assert result["safety_requirement_pass"] is False


def test_invalid_schema_rate_is_rejected():
    from k8s_review.acceptance import evaluate_quality_gates

    with pytest.raises(ValueError, match="Schema pass rate"):
        evaluate_quality_gates(0.90, 1.5, 1.0)
