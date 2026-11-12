"""Evaluate structural and safety invariants for AI review findings."""

import json
from typing import Any

from k8s_review.finding_validation import validate_findings


def evaluate_invariants(
    findings: Any,
    sanitized_documents: list[Any],
    safety_markers: list[str] | None = None,
) -> dict[str, Any]:
    """Check finding structure, evidence grounding, and secret protection."""
    errors = validate_findings(findings, sanitized_documents)

    try:
        generated_content = json.dumps(findings, ensure_ascii=False)
    except (TypeError, ValueError):
        generated_content = ""

    for marker in safety_markers or []:
        if marker and marker in generated_content:
            errors.append("A protected sensitive marker was detected in findings.")

    return {
        "invariant_pass": not errors,
        "invariant_errors": errors,
    }
