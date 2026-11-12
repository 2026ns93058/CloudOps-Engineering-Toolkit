"""Tests for AI-generated finding validation."""

import pytest

from k8s_review.finding_validation import validate_findings


@pytest.fixture
def manifest():
    return [
        {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": {"name": "sample-app"},
            "spec": {
                "template": {
                    "spec": {
                        "containers": [
                            {"name": "app", "image": "nginx:latest"}
                        ]
                    }
                }
            },
        }
    ]


@pytest.fixture
def finding():
    return {
        "finding_id": "F001",
        "issue_id": "K8S-SEC-001",
        "severity": "High",
        "category": "Security",
        "resource_kind": "Deployment",
        "resource_name": "sample-app",
        "title": "Unpinned container image",
        "explanation": "The image uses the latest tag.",
        "evidence": {
            "field_path": "spec.template.spec.containers",
            "observed_value": (
                "[{'name': 'app', 'image': 'nginx:latest'}]"
            ),
            "observation": "The container image uses the latest tag.",
        },
        "remediation": "Use a specific image version.",
    }



def test_valid_finding_passes(finding, manifest):
    assert validate_findings([finding], manifest) == []


def test_invalid_severity_is_rejected(finding, manifest):
    finding["severity"] = "Urgent"

    errors = validate_findings([finding], manifest)

    assert any("invalid severity" in error for error in errors)


def test_invalid_category_is_rejected(finding, manifest):
    finding["category"] = "Performance"

    errors = validate_findings([finding], manifest)

    assert any("invalid category" in error for error in errors)


def test_unknown_resource_is_rejected(finding, manifest):
    finding["resource_name"] = "unknown-app"

    errors = validate_findings([finding], manifest)

    assert any("unknown resource" in error for error in errors)


def test_mismatched_evidence_value_is_rejected(finding, manifest):
    finding["evidence"]["observed_value"] = "redis:latest"

    errors = validate_findings([finding], manifest)

    assert any("does not match" in error for error in errors)


def test_missing_field_can_be_valid_evidence(finding, manifest):
    finding["evidence"] = {
        "field_path": "spec.template.spec.securityContext",
        "observed_value": None,
        "observation": "No pod security context is configured.",
    }

    assert validate_findings([finding], manifest) == []


def test_non_list_findings_are_rejected(manifest):
    errors = validate_findings({}, manifest)

    assert any("must be a list" in error for error in errors)


def test_empty_evidence_field_path_is_rejected(finding, manifest):
    finding["evidence"]["field_path"] = ""

    errors = validate_findings([finding], manifest)

    assert any("field path" in error for error in errors)


def test_empty_evidence_observation_is_rejected(finding, manifest):
    finding["evidence"]["observation"] = "  "

    errors = validate_findings([finding], manifest)

    assert any("observation" in error for error in errors)


def test_non_object_finding_is_rejected(manifest):
    errors = validate_findings(["invalid"], manifest)

    assert any("must be an object" in error for error in errors)


def test_list_index_field_path_is_resolved(finding, manifest):
    finding["evidence"] = {
        "field_path": "spec.template.spec.containers[0].image",
        "observed_value": "nginx:latest",
        "observation": "The container uses the latest image tag.",
    }
    assert validate_findings([finding], manifest) == []


def test_out_of_range_list_index_is_rejected(finding, manifest):
    finding["evidence"] = {
        "field_path": "spec.template.spec.containers[1].image",
        "observed_value": "nginx:latest",
        "observation": "The container uses the latest image tag.",
    }
    errors = validate_findings([finding], manifest)
    assert any("does not exist" in error for error in errors)


def test_boolean_evidence_value_must_match_manifest(finding, manifest):
    manifest[0]["spec"]["template"]["spec"]["containers"][0]["securityContext"] = {
        "privileged": True
    }
    finding["evidence"] = {
        "field_path": "spec.template.spec.containers[0].securityContext.privileged",
        "observed_value": "true",
        "observation": "The container is configured as privileged.",
    }
    assert validate_findings([finding], manifest) == []
