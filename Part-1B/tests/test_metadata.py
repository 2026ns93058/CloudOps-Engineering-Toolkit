"""Tests for trusted model execution metadata."""

from k8s_review.metadata import build_model_metadata
from k8s_review.ollama_client import OllamaResult


def test_metadata_contains_all_required_fields():
    """Metadata should contain all five documented fields."""
    result = OllamaResult(
        content='{"review_summary": "Complete", "findings": []}',
        model="qwen3:4b",
        temperature=0.2,
        duration_ms=2457,
    )

    metadata = build_model_metadata(result)

    assert metadata == {
        "provider": "Ollama",
        "model": "qwen3:4b",
        "prompt_version": "1.0.4",
        "temperature": 0.2,
        "duration_ms": 2457,
    }


def test_metadata_uses_actual_execution_values():
    """Model, temperature, and duration must come from the execution result."""
    result = OllamaResult(
        content="{}",
        model="another-model:latest",
        temperature=0.7,
        duration_ms=1200,
    )

    metadata = build_model_metadata(result)

    assert metadata["model"] == "another-model:latest"
    assert metadata["temperature"] == 0.7
    assert metadata["duration_ms"] == 1200


def test_metadata_does_not_include_model_generated_metadata():
    """Trusted metadata must not be copied from model-generated content."""
    result = OllamaResult(
        content='{"provider": "UntrustedProvider", "model": "fake-model"}',
        model="qwen3:4b",
        temperature=0.2,
        duration_ms=500,
    )

    metadata = build_model_metadata(result)

    assert metadata["provider"] == "Ollama"
    assert metadata["model"] == "qwen3:4b"
