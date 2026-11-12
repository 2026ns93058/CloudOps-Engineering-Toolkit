"""Tests for AI review response schema validation."""

from k8s_review.schema_validation import validate_review_response


def valid_finding():
    """Return a finding that follows the documented data model."""
    return {
        "finding_id": "F001",
        "issue_id": "K8S-SEC-001",
        "severity": "High",
        "category": "Security",
        "resource_kind": "Deployment",
        "resource_name": "sample-app",
        "title": "Container runs as root",
        "explanation": "The manifest does not disable root execution.",
        "evidence": {
            "field_path": "spec.template.spec.containers[0].securityContext",
            "observed_value": None,
            "observation": "No security context is configured.",
        },
        "remediation": "Configure runAsNonRoot: true.",
    }


def test_valid_review_response_passes_schema_validation():
    """A response with all required fields should pass."""
    response = {
        "review_summary": "One security issue identified.",
        "findings": [valid_finding()],
    }

    assert validate_review_response(response) == []


def test_empty_findings_list_is_valid():
    """A review with no findings should be valid."""
    response = {
        "review_summary": "No findings identified.",
        "findings": [],
    }

    assert validate_review_response(response) == []


def test_missing_review_summary_is_rejected():
    """The review summary is required."""
    response = {"findings": []}

    errors = validate_review_response(response)

    assert any("review_summary" in error for error in errors)


def test_findings_must_be_a_list():
    """Findings must be represented as a list."""
    response = {
        "review_summary": "Review complete.",
        "findings": {},
    }

    errors = validate_review_response(response)

    assert any("must be a list" in error for error in errors)


def test_missing_finding_field_is_rejected():
    """Every finding must contain all required fields."""
    finding = valid_finding()
    del finding["remediation"]

    response = {
        "review_summary": "Review complete.",
        "findings": [finding],
    }

    errors = validate_review_response(response)

    assert any("remediation" in error for error in errors)


def test_invalid_finding_field_type_is_rejected():
    """Finding fields must have the documented data types."""
    finding = valid_finding()
    finding["finding_id"] = 123

    response = {
        "review_summary": "Review complete.",
        "findings": [finding],
    }

    errors = validate_review_response(response)

    assert any("finding_id" in error for error in errors)


def test_incomplete_evidence_object_is_rejected():
    """Evidence must contain all three required fields."""
    finding = valid_finding()
    del finding["evidence"]["observation"]

    response = {
        "review_summary": "Review complete.",
        "findings": [finding],
    }

    errors = validate_review_response(response)

    assert any("observation" in error for error in errors)


def test_non_object_response_is_rejected():
    """The review response must be a JSON object."""
    errors = validate_review_response(["invalid"])

    assert any("JSON object" in error for error in errors)


def test_non_object_finding_is_rejected():
    """Each finding must be a JSON object."""
    response = {
        "review_summary": "Review complete.",
        "findings": ["invalid"],
    }

    errors = validate_review_response(response)

    assert any("must be a JSON object" in error for error in errors)
