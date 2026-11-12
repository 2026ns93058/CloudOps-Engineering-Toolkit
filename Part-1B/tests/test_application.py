"""Integration tests for the Kubernetes review application."""

import json
from pathlib import Path

import pytest

from k8s_review.application import (
    ReviewApplicationError,
    review_manifest,
)
from k8s_review.ollama_client import OllamaConfig, OllamaResult


def create_manifest(tmp_path):
    """Create a sample manifest containing a Deployment and Secret."""
    manifest = tmp_path / "deployment.yaml"
    manifest.write_text(
        """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: sample-app
spec:
  template:
    spec:
      containers:
        - name: app
          image: nginx:latest
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
          securityContext:
            runAsNonRoot: true
            allowPrivilegeEscalation: false
          readinessProbe:
            httpGet:
              path: /
              port: 80
          livenessProbe:
            httpGet:
              path: /
              port: 80
---
apiVersion: v1
kind: Secret
metadata:
  name: app-secret
type: Opaque
stringData:
  password: KNOWN_SECRET_MARKER_123
""",
        encoding="utf-8",
    )
    return manifest


def controlled_model_response():
    """Return a predictable, valid model result."""
    content = json.dumps({
        "review_summary": "One configuration issue identified.",
        "findings": [
            {
                "finding_id": "F001",
                "issue_id": "K8S-CFG-001",
                "severity": "Medium",
                "category": "Configuration",
                "resource_kind": "Deployment",
                "resource_name": "sample-app",
                "title": "Container image uses latest tag",
                "explanation": "The image tag is not pinned to a specific version.",
                "evidence": {
                    "field_path": "spec.template.spec.containers[0].image",
                    "observed_value": "nginx:latest",
                    "observation": "The container image uses the latest tag.",
                },
                "remediation": "Use a specific, immutable image version.",
            }
        ],
    })
    return OllamaResult(
        content=content,
        model="qwen3:4b",
        temperature=0.2,
        duration_ms=1500,
    )


def test_successful_review_generates_json_report(tmp_path):
    """A controlled model response should produce a complete report."""
    manifest = create_manifest(tmp_path)
    output = tmp_path / "review.json"

    def mock_model(config, prompt, sanitized_yaml):
        return controlled_model_response()

    report = review_manifest(
        manifest,
        output,
        config=OllamaConfig(),
        model_call=mock_model,
    )

    assert output.exists()
    assert report["review_summary"] == "One configuration issue identified."
    assert len(report["resources_reviewed"]) == 2
    assert report["resources_reviewed"][0]["name"] == "sample-app"
    assert report["resources_reviewed"][1]["name"] == "app-secret"
    assert len(report["findings"]) == 1



    assert any(
        finding["issue_id"] == "K8S-CFG-001"
        for finding in report["findings"]
    )
    deterministic = next(
        finding for finding in report["findings"]
        if finding["issue_id"] == "K8S-CFG-001"
    )
    assert deterministic["title"] == "Container image uses the mutable latest tag"
    assert deterministic["evidence"]["field_path"] == (
        "spec.template.spec.containers"
    )
    assert len({
        finding["finding_id"] for finding in report["findings"]
    }) == 1

    assert report["model_metadata"]["provider"] == "Ollama"
    assert report["model_metadata"]["prompt_version"] == "1.0.5"
    assert json.loads(output.read_text(encoding="utf-8")) == report


def test_unrelated_ai_finding_is_preserved_with_static_findings(tmp_path):
    manifest = create_manifest(tmp_path)
    output = tmp_path / "review.json"

    def mock_model(config, prompt, sanitized_yaml):
        response = {
            "review_summary": "Independent configuration issue identified.",
            "findings": [
                {
                    "finding_id": "F001",
                    "issue_id": "K8S-CFG-002",
                    "severity": "Low",
                    "category": "Configuration",
                    "resource_kind": "Deployment",
                    "resource_name": "sample-app",
                    "title": "Service port mapping needs review",
                    "explanation": "The service port mapping needs review.",
                    "evidence": {
                        "field_path": (
                            "spec.template.spec.containers[0].image"
                        ),
                        "observed_value": "nginx:latest",
                        "observation": "The container image is nginx:latest.",
                    },
                    "remediation": "Review the service and container port mapping.",
                }
            ],
        }
        return OllamaResult(
            content=json.dumps(response),
            model="qwen3:4b",
            temperature=0.2,
            duration_ms=1500,
        )

    report = review_manifest(
        manifest,
        output,
        config=OllamaConfig(),
        model_call=mock_model,
    )

    issue_ids = [finding["issue_id"] for finding in report["findings"]]
    assert issue_ids.count("K8S-CFG-001") == 1
    assert issue_ids.count("K8S-CFG-002") == 1


def test_ai_finding_is_suppressed_when_deterministic_check_finds_no_issue(
    tmp_path,
):
    manifest = create_manifest(tmp_path)
    manifest.write_text(
        manifest.read_text(encoding="utf-8").replace(
            "nginx:latest",
            "nginx:1.27",
        ),
        encoding="utf-8",
    )
    output = tmp_path / "review.json"

    def mock_model(config, prompt, sanitized_yaml):
        response = {
            "review_summary": "The container image was reviewed.",
            "findings": [
                {
                    "finding_id": "F001",
                    "issue_id": "K8S-CFG-001",
                    "severity": "Medium",
                    "category": "Configuration",
                    "resource_kind": "Deployment",
                    "resource_name": "sample-app",
                    "title": "Container image uses a mutable tag",
                    "explanation": "The image uses a mutable tag.",
                    "evidence": {
                        "field_path": (
                            "spec.template.spec.containers[0].image"
                        ),
                        "observed_value": "nginx:1.27",
                        "observation": "The configured image is nginx:1.27.",
                    },
                    "remediation": "Use a specifically pinned container image.",
                },
                {
                    "finding_id": "F002",
                    "issue_id": "K8S-CFG-002",
                    "severity": "Low",
                    "category": "Configuration",
                    "resource_kind": "Deployment",
                    "resource_name": "sample-app",
                    "title": "Service port mapping needs review",
                    "explanation": "The service port mapping needs review.",
                    "evidence": {
                        "field_path": (
                            "spec.template.spec.containers[0].image"
                        ),
                        "observed_value": "nginx:1.27",
                        "observation": "The configured image is nginx:1.27.",
                    },
                    "remediation": "Review the service and container port mapping.",
                },
            ],
        }
        return OllamaResult(
            content=json.dumps(response),
            model="qwen3:4b",
            temperature=0.2,
            duration_ms=1500,
        )

    report = review_manifest(
        manifest,
        output,
        config=OllamaConfig(),
        model_call=mock_model,
    )

    issue_ids = [finding["issue_id"] for finding in report["findings"]]
    assert "K8S-CFG-001" not in issue_ids
    assert issue_ids == ["K8S-CFG-002"]


def test_case_020_rejects_unestablished_service_port_mismatch_finding(
    tmp_path,
):
    project_root = Path(__file__).parents[1]
    dataset = json.loads(
        (project_root / "evals" / "dataset-v1.0.4.json").read_text(
            encoding="utf-8"
        )
    )
    case = next(
        item for item in dataset["cases"]
        if item["case_id"] == "K8S-EVAL-020"
    )
    manifest = tmp_path / "case-020.yaml"
    manifest.write_text(case["input_manifest"], encoding="utf-8")
    output = tmp_path / "review.json"

    def mock_model(config, prompt, sanitized_yaml):
        response = {
            "review_summary": "A service port mismatch was identified.",
            "findings": [
                {
                    "finding_id": "F001",
                    "issue_id": "K8S-CFG-002",
                    "severity": "Medium",
                    "category": "Configuration",
                    "resource_kind": "Service",
                    "resource_name": "frontend-service",
                    "title": "Service target port does not match container port",
                    "explanation": (
                        "The Service target port differs from the intended "
                        "container port."
                    ),
                    "evidence": {
                        "field_path": "spec.ports[0].targetPort",
                        "observed_value": "8080",
                        "observation": (
                            "The Service target port is 8080."
                        ),
                    },
                    "remediation": (
                        "Configure the Service target port to match the "
                        "intended container port."
                    ),
                }
            ],
        }
        return OllamaResult(
            content=json.dumps(response),
            model="qwen3:4b",
            temperature=0.2,
            duration_ms=10,
        )

    manifest_text = case["input_manifest"]
    assert "targetPort: 8080" in manifest_text
    assert "containerPort: 8080" in manifest_text
    assert "app: frontend" in manifest_text
    assert "app: backend" in manifest_text

    report = review_manifest(
        manifest,
        output,
        config=OllamaConfig(),
        model_call=mock_model,
    )

    assert "K8S-CFG-002" not in {
        finding["issue_id"] for finding in report["findings"]
    }


def test_secret_values_are_redacted_before_model_call(tmp_path):
    """Original Secret values must never reach the model."""
    manifest = create_manifest(tmp_path)
    output = tmp_path / "review.json"
    captured = {}

    def mock_model(config, prompt, sanitized_yaml):
        captured["input"] = sanitized_yaml
        return controlled_model_response()

    review_manifest(
        manifest,
        output,
        config=OllamaConfig(),
        model_call=mock_model,
    )

    assert "KNOWN_SECRET_MARKER_123" not in captured["input"]
    assert "[REDACTED]" in captured["input"]
    report_text = output.read_text(encoding="utf-8")
    assert "KNOWN_SECRET_MARKER_123" not in report_text
    report = json.loads(report_text)
    assert "KNOWN_SECRET_MARKER_123" not in json.dumps(report)


def test_invalid_model_schema_is_rejected(tmp_path):
    """A model response missing required fields must be rejected."""
    manifest = create_manifest(tmp_path)
    output = tmp_path / "review.json"

    def mock_model(config, prompt, sanitized_yaml):
        return OllamaResult(
            content='{"findings": []}',
            model="qwen3:4b",
            temperature=0.2,
            duration_ms=100,
        )

    with pytest.raises(ReviewApplicationError, match="Invalid model response schema"):
        review_manifest(
            manifest,
            output,
            config=OllamaConfig(),
            model_call=mock_model,
        )

    assert not output.exists()


def test_invalid_manifest_is_rejected(tmp_path):
    """A structurally invalid Kubernetes document must be rejected."""
    manifest = tmp_path / "invalid.yaml"
    manifest.write_text(
        "kind: Deployment\nmetadata:\n  name: sample-app\n",
        encoding="utf-8",
    )

    with pytest.raises(ReviewApplicationError, match="Invalid manifest document"):
        review_manifest(
            manifest,
            tmp_path / "review.json",
            model_call=lambda *args: controlled_model_response(),
        )


def test_unsupported_resource_is_recorded_without_model_call(tmp_path):
    """A valid unsupported resource should be recorded, not rejected."""
    manifest = tmp_path / "unsupported.yaml"
    manifest.write_text(
        "apiVersion: example.com/v1\n"
        "kind: CustomWorkload\n"
        "metadata:\n"
        "  name: custom-app\n",
        encoding="utf-8",
    )

    def unexpected_model_call(*args):
        pytest.fail("The model must not be called for unsupported-only input.")

    report = review_manifest(
        manifest,
        tmp_path / "review.json",
        model_call=unexpected_model_call,
    )

    assert report["resources_reviewed"] == []
    assert len(report["unsupported_resources"]) == 1
    assert report["unsupported_resources"][0]["kind"] == "CustomWorkload"


def test_malformed_yaml_is_rejected_before_model_call(tmp_path):
    """Malformed YAML must be rejected before AI review."""
    from k8s_review.manifest import ManifestParseError

    manifest = tmp_path / "malformed.yaml"
    manifest.write_text(
        "apiVersion: apps/v1\nkind: Deployment\nmetadata: [invalid\n",
        encoding="utf-8",
    )

    def unexpected_model_call(*args):
        pytest.fail("The model must not be called for malformed YAML.")

    with pytest.raises(ManifestParseError):
        review_manifest(
            manifest,
            tmp_path / "review.json",
            model_call=unexpected_model_call,
        )
