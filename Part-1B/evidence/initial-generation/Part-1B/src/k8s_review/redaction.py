"""Redact sensitive values from Kubernetes Secret resources."""

from copy import deepcopy
from typing import Any


REDACTED_VALUE = "[REDACTED]"


def redact_secret_data(document: Any) -> Any:
    """Return a copy with Kubernetes Secret values redacted."""
    redacted = deepcopy(document)

    if not isinstance(redacted, dict) or redacted.get("kind") != "Secret":
        return redacted

    for field in ("data", "stringData"):
        values = redacted.get(field)

        if isinstance(values, dict):
            redacted[field] = {
                key: REDACTED_VALUE for key in values
            }

    return redacted
