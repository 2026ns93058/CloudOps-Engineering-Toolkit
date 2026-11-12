"""Evaluate AI review responses against the required output schema."""

from typing import Any

from k8s_review.schema_validation import validate_review_response


def evaluate_output_schema(response: Any) -> dict[str, Any]:
    """Return schema pass/fail status and validation errors."""
    errors = validate_review_response(response)

    return {
        "schema_pass": not errors,
        "schema_errors": errors,
    }
