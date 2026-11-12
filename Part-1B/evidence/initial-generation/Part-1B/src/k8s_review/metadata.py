"""Build trusted model execution metadata for review reports."""

from typing import Any

from k8s_review.ollama_client import OllamaResult


PROVIDER = "Ollama"
PROMPT_VERSION = "1.0.1"


def build_model_metadata(result: OllamaResult) -> dict[str, Any]:
    """Build metadata using trusted application and execution values."""
    return {
        "provider": PROVIDER,
        "model": result.model,
        "prompt_version": PROMPT_VERSION,
        "temperature": result.temperature,
        "duration_ms": result.duration_ms,
    }
