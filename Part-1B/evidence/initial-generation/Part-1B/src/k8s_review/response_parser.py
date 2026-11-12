"""Parse structured JSON responses returned by the AI model."""

import json
from typing import Any


class ModelResponseParseError(ValueError):
    """Raised when the AI model returns invalid JSON."""


def parse_model_response(content: str) -> dict[str, Any]:
    """Parse a model response and require a JSON object."""
    if not isinstance(content, str) or not content.strip():
        raise ModelResponseParseError("Model response is empty.")

    try:
        parsed = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ModelResponseParseError(
            f"Model response contains invalid JSON: {exc.msg}."
        ) from exc

    if not isinstance(parsed, dict):
        raise ModelResponseParseError(
            "Model response must be a JSON object."
        )

    return parsed
