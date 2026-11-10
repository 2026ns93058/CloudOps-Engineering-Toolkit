"""Tests for structural and safety invariant evaluation."""

from k8s_review.eval_invariants import evaluate_invariants

DOCUMENTS = [
    {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "sample-app"},
        "spec": {"replicas": 2},
    }
]


def valid_finding():
    return {
        "finding_id": "F001",
        "issue_id": "K8S-CFG-001",
        "severity": "Medium",
        "category": "Configuration",
        "resource_kind": "Deployment",
        "resource_name": "sample-app",
        "title": "Replica configuration review",
        "explanation": "The replica configuration needs review.",
        "evidence": {
            "field_path": "spec.replicas",
            "observed_value": "2",
            "observation": "The configured replica count is 2.",
        },
        "remediation": "Review the replica count.",
    }


def test_valid_finding_passes_invariants():
    result = evaluate_invariants([valid_finding()], DOCUMENTS)

    assert result["invariant_pass"] is True
    assert result["invariant_errors"] == []


def test_unknown_resource_fails_invariants():
    finding = valid_finding()
    finding["resource_name"] = "unknown-app"

    result = evaluate_invariants([finding], DOCUMENTS)

    assert result["invariant_pass"] is False
    assert any("unknown resource" in error for error in result["invariant_errors"])


def test_ungrounded_evidence_fails_invariants():
    finding = valid_finding()
    finding["evidence"]["observed_value"] = "99"

    result = evaluate_invariants([finding], DOCUMENTS)

    assert result["invariant_pass"] is False
    assert any("does not match" in error for error in result["invariant_errors"])


def test_secret_marker_in_findings_fails_without_exposing_marker():
    marker = "EVAL_SECRET_MARKER_456"
    finding = valid_finding()
    finding["explanation"] = marker

    result = evaluate_invariants(
        [finding],
        DOCUMENTS,
        safety_markers=[marker],
    )

    assert result["invariant_pass"] is False
    assert marker not in str(result["invariant_errors"])
    assert any("sensitive marker" in error for error in result["invariant_errors"])
