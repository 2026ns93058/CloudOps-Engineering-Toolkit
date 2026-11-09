"""Security tests for Kubernetes Secret redaction."""

from k8s_review.redaction import redact_secret_data


def test_secret_data_and_string_data_are_redacted():
    secret = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {"name": "app-secret"},
        "data": {"password": "TOP-SECRET-123"},
        "stringData": {"token": "TOKEN-MARKER-456"},
    }

    result = redact_secret_data(secret)

    assert result["data"]["password"] == "[REDACTED]"
    assert result["stringData"]["token"] == "[REDACTED]"


def test_original_secret_values_are_absent_from_model_input():
    secret = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {"name": "app-secret"},
        "data": {"password": "TOP-SECRET-123"},
        "stringData": {"token": "TOKEN-MARKER-456"},
    }

    model_input = redact_secret_data(secret)

    assert "TOP-SECRET-123" not in str(model_input)
    assert "TOKEN-MARKER-456" not in str(model_input)


def test_original_manifest_remains_unchanged():
    secret = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {"name": "app-secret"},
        "data": {"password": "TOP-SECRET-123"},
        "stringData": {"token": "TOKEN-MARKER-456"},
    }

    redact_secret_data(secret)

    assert secret["data"]["password"] == "TOP-SECRET-123"
    assert secret["stringData"]["token"] == "TOKEN-MARKER-456"


def test_non_secret_resource_remains_unchanged():
    deployment = {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "web-app"},
        "data": {"config": "ordinary-value"},
    }

    result = redact_secret_data(deployment)

    assert result == deployment
