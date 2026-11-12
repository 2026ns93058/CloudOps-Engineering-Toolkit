"""Validate AI-generated findings against sanitised Kubernetes manifests."""

import re
from typing import Any

ALLOWED_SEVERITIES = {
    "Critical",
    "High",
    "Medium",
    "Low",
    "Info",
}

ALLOWED_CATEGORIES = {
    "Security",
    "Reliability",
    "Configuration",
    "Resource Management",
}


def _resource_identity(document: dict[str, Any]) -> tuple[str, str] | None:
    """Return the kind and name identifying a manifest resource."""
    metadata = document.get("metadata")
    if not isinstance(metadata, dict):
        return None

    kind = document.get("kind")
    name = metadata.get("name")
    if not isinstance(kind, str) or not isinstance(name, str):
        return None

    return kind, name


def _resolve_field_path(document: Any, field_path: str) -> tuple[bool, Any]:
    """Resolve dotted YAML paths with optional list indices."""
    if not field_path or not isinstance(field_path, str):
        return False, None

    parts = re.findall(r"[^.\[\]]+|\[\d+\]", field_path)
    if not parts:
        return False, None

    current = document
    for part in parts:
        if part.startswith("[") and part.endswith("]"):
            if not isinstance(current, list):
                return False, None
            index = int(part[1:-1])
            if index >= len(current):
                return False, None
            current = current[index]
        else:
            if not isinstance(current, dict) or part not in current:
                return False, None
            current = current[part]

    return True, current


def validate_findings(
    findings: Any,
    sanitized_documents: list[Any],
) -> list[str]:
    """Validate finding enums, resource identities, and evidence grounding."""
    errors: list[str] = []
    if not isinstance(findings, list):
        return ["Findings must be a list."]

    resource_identities = {
        identity
        for document in sanitized_documents
        if isinstance(document, dict)
        if (identity := _resource_identity(document)) is not None
    }

    for index, finding in enumerate(findings):
        prefix = f"Finding at index {index}"
        if not isinstance(finding, dict):
            errors.append(f"{prefix} must be an object.")
            continue

        severity = finding.get("severity")
        if severity not in ALLOWED_SEVERITIES:
            errors.append(f"{prefix} has an invalid severity.")

        category = finding.get("category")
        if category not in ALLOWED_CATEGORIES:
            errors.append(f"{prefix} has an invalid category.")

        identity = (
            finding.get("resource_kind"),
            finding.get("resource_name"),
        )
        if identity not in resource_identities:
            errors.append(f"{prefix} refers to an unknown resource.")
            continue

        evidence = finding.get("evidence")
        if not isinstance(evidence, dict):
            errors.append(f"{prefix} must provide an evidence object.")
            continue

        field_path = evidence.get("field_path")
        observation = evidence.get("observation")

        if not isinstance(field_path, str) or not field_path.strip():
            errors.append(f"{prefix} must provide a non-empty evidence field path.")

        if not isinstance(observation, str) or not observation.strip():
            errors.append(f"{prefix} must provide a non-empty evidence observation.")

        document = next(
            (
                item
                for item in sanitized_documents
                if isinstance(item, dict)
                and _resource_identity(item) == identity
            ),
            {},
        )

        exists, observed_value = _resolve_field_path(document, field_path)

        if not exists and evidence.get("observed_value") is not None:
            errors.append(
                f"{prefix} provides an observed value for a field "
                "that does not exist."
            )
        elif exists and evidence.get("observed_value") != (
            "true" if observed_value is True
            else "false" if observed_value is False
            else str(observed_value) if observed_value is not None
            else None
        ):
            errors.append(
                f"{prefix} observed value does not match the sanitised manifest."
            )

    return errors
