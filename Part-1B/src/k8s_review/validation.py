"""Structural validation for Kubernetes YAML documents."""

from typing import Any

REQUIRED_FIELDS = ("apiVersion", "kind", "metadata")

SUPPORTED_KINDS = {
    "Deployment",
    "Service",
    "ConfigMap",
    "Secret",
    "StatefulSet",
    "DaemonSet",
    "Job",
    "CronJob",
    "Ingress",
    "PersistentVolumeClaim",
}


def validate_manifest_document(document: Any) -> list[str]:
    """Return structural validation errors for one YAML document."""
    errors: list[str] = []

    if not isinstance(document, dict):
        return ["Document must be a YAML mapping."]

    for field in REQUIRED_FIELDS:
        if field not in document:
            errors.append(f"Missing required field: {field}.")

    metadata = document.get("metadata")

    if "metadata" in document:
        if not isinstance(metadata, dict):
            errors.append("Field 'metadata' must be a YAML mapping.")
        elif not isinstance(metadata.get("name"), str) or not metadata["name"].strip():
            errors.append("Field 'metadata.name' must be a non-empty string.")

    kind = document.get("kind")

    if "kind" in document and not isinstance(kind, str):
        errors.append("Field 'kind' must be a string.")

    return errors


def is_secret_resource(document: Any) -> bool:
    """Return True when a YAML document represents a Kubernetes Secret."""
    return isinstance(document, dict) and document.get("kind") == "Secret"
