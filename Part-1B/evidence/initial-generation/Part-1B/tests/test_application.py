"""Integration tests for the Kubernetes review application."""

import json

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
                "issue_id": None,
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
        finding["title"] == "Container image uses latest tag"
        for finding in report["findings"]
    )
    assert len({
        finding["finding_id"] for finding in report["findings"]
    }) == 1

    assert report["model_metadata"]["provider"] == "Ollama"
    assert json.loads(output.read_text(encoding="utf-8")) == report


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
    assert "KNOWN_SECRET_MARKER_123" not in output.read_text(encoding="utf-8")


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
