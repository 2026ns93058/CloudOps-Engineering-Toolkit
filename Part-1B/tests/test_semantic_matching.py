"""Tests for semantic issue matching."""

from k8s_review.semantic_matching import match_findings


def finding(
    issue_id="K8S-CFG-001",
    resource_name="sample-app",
    category="Configuration",
    severity="Medium",
):
    return {
        "issue_id": issue_id,
        "resource_kind": "Deployment",
        "resource_name": resource_name,
        "category": category,
        "severity": severity,
    }


def test_correct_finding_is_matched():
    result = match_findings(
        [finding()],
        [finding()],
    )

    assert result["matched_count"] == 1
    assert result["unmatched_expected"] == []
    assert result["unmatched_generated"] == []


def test_wrong_issue_id_is_not_matched():
    result = match_findings(
        [finding()],
        [finding(issue_id="K8S-SEC-001")],
    )

    assert result["matched_count"] == 0
    assert result["unmatched_expected"] == [0]
    assert result["unmatched_generated"] == [0]


def test_wrong_resource_identity_is_not_matched():
    result = match_findings(
        [finding()],
        [finding(resource_name="different-app")],
    )

    assert result["matched_count"] == 0


def test_severity_difference_does_not_prevent_issue_match():
    result = match_findings(
        [finding(severity="High")],
        [finding(severity="Low")],
    )

    assert result["matched_count"] == 1


def test_matching_is_one_to_one():
    result = match_findings(
        [finding()],
        [finding(), finding()],
    )

    assert result["matched_count"] == 1
    assert result["unmatched_generated"] == [1]


def test_duplicate_findings_are_detected():
    result = match_findings(
        [finding()],
        [finding(), finding(), finding()],
    )

    assert result["matched_count"] == 1
    assert result["duplicate_count"] == 2
    assert result["duplicate_indices"] == [1, 2]


def test_duplicate_findings_receive_no_additional_credit():
    result = match_findings(
        [finding()],
        [finding(), finding()],
    )

    assert len(result["matched"]) == 1
    assert result["unmatched_generated"] == [1]
