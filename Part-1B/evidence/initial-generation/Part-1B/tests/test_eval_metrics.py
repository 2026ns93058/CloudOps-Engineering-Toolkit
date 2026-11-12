"""Tests for evaluation metric calculations."""

from k8s_review.eval_metrics import calculate_issue_metrics


def test_all_findings_matched():
    result = calculate_issue_metrics(3, 3, 3)

    assert result["true_positives"] == 3
    assert result["false_positives"] == 0
    assert result["false_negatives"] == 0
    assert result["precision"] == 1.0
    assert result["recall"] == 1.0


def test_false_positive_is_counted():
    result = calculate_issue_metrics(2, 3, 2)

    assert result["false_positives"] == 1
    assert result["false_negatives"] == 0
    assert result["precision"] == 2 / 3
    assert result["recall"] == 1.0


def test_false_negative_is_counted():
    result = calculate_issue_metrics(3, 2, 2)

    assert result["false_positives"] == 0
    assert result["false_negatives"] == 1
    assert result["precision"] == 1.0
    assert result["recall"] == 2 / 3


def test_empty_expected_and_generated_findings():
    result = calculate_issue_metrics(0, 0, 0)

    assert result["precision"] == 1.0
    assert result["recall"] == 1.0


def test_no_generated_findings_with_expected_issues():
    result = calculate_issue_metrics(2, 0, 0)

    assert result["false_negatives"] == 2
    assert result["precision"] == 0.0
    assert result["recall"] == 0.0
