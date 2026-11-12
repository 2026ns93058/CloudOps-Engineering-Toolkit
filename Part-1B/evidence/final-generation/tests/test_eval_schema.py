"""Tests for output schema evaluation."""

from k8s_review.eval_schema import evaluate_output_schema


def valid_response():
    return {
        "review_summary": "One issue identified.",
        "findings": [
            {
                "finding_id": "F001",
                "issue_id": "K8S-CFG-001",
                "severity": "Medium",
                "category": "Configuration",
                "resource_kind": "Deployment",
                "resource_name": "sample-app",
                "title": "Mutable image tag",
                "explanation": "The image uses the latest tag.",
                "evidence": {
                    "field_path": "spec.template.spec.containers",
                    "observed_value": "nginx:latest",
                    "observation": "The image uses a mutable tag.",
                },
                "remediation": "Pin the image to a specific version.",
            }
        ],
    }


def test_valid_response_passes_schema_evaluation():
    result = evaluate_output_schema(valid_response())

    assert result["schema_pass"] is True
    assert result["schema_errors"] == []


def test_missing_top_level_field_fails_schema_evaluation():
    response = {"findings": []}

    result = evaluate_output_schema(response)

    assert result["schema_pass"] is False
    assert any("review_summary" in error for error in result["schema_errors"])


def test_invalid_finding_field_type_fails_schema_evaluation():
    response = valid_response()
    response["findings"][0]["severity"] = 123

    result = evaluate_output_schema(response)

    assert result["schema_pass"] is False
    assert any("severity" in error for error in result["schema_errors"])


def test_missing_evidence_field_fails_schema_evaluation():
    response = valid_response()
    del response["findings"][0]["evidence"]["field_path"]

    result = evaluate_output_schema(response)

    assert result["schema_pass"] is False
    assert any("field_path" in error for error in result["schema_errors"])
