"""Schema validation for structured Kubernetes review responses."""

from typing import Any

FINDING_FIELDS = {
    "finding_id": str,
    "issue_id": (str, type(None)),
    "severity": str,
    "category": str,
    "resource_kind": str,
    "resource_name": str,
    "title": str,
    "explanation": str,
    "evidence": dict,
    "remediation": str,
}

EVIDENCE_FIELDS = {
    "field_path": str,
    "observed_value": (str, type(None)),
    "observation": str,
}

def validate_review_response(response: Any) -> list[str]:
    
    """Return schema validation errors for a model-generated response."""
    errors: list[str] = []

    if not isinstance(response, dict):
        return ["Review response must be a JSON object."]

    if "review_summary" not in response:
        errors.append("Missing required field: review_summary.")
    elif not isinstance(response["review_summary"], str):
        errors.append("Field 'review_summary' must be a string.")

    if "findings" not in response:
        errors.append("Missing required field: findings.")
        return errors

    findings = response["findings"]

    if not isinstance(findings, list):
        errors.append("Field 'findings' must be a list.")
        return errors

    for index, finding in enumerate(findings):
        prefix = f"Finding at index {index}"

        if not isinstance(finding, dict):
            errors.append(f"{prefix} must be a JSON object.")
            continue

        for field, expected_type in FINDING_FIELDS.items():
            if field not in finding:
                errors.append(f"{prefix} is missing required field '{field}'.")
            elif not isinstance(finding[field], expected_type):
                errors.append(
                    f"{prefix} field '{field}' has an invalid data type."
                )

        evidence = finding.get("evidence")

        if isinstance(evidence, dict):
            for field, expected_type in EVIDENCE_FIELDS.items():
                if field not in evidence:
                    errors.append(
                        f"{prefix} evidence is missing required field '{field}'."
                    )
                elif not isinstance(evidence[field], expected_type):
                    errors.append(
                        f"{prefix} evidence field '{field}' has an invalid data type."
                    )

    return errors
