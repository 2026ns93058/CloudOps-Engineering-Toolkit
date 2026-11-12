"""Tests for Ollama connectivity and request error handling."""

import pytest
import requests

from k8s_review.ollama_client import (
    OllamaConfig,
    OllamaRequestError,
    generate_review,
)


@pytest.fixture
def config():
    """Provide a test Ollama configuration."""
    return OllamaConfig(timeout_seconds=5)


def test_unavailable_ollama_service(monkeypatch, config):
    """An unavailable Ollama service should raise a clear error."""

    def mock_post(*args, **kwargs):
        raise requests.ConnectionError("Service unavailable")

    monkeypatch.setattr(requests, "post", mock_post)

    with pytest.raises(OllamaRequestError, match="request failed"):
        generate_review(config, "Review prompt", "kind: Deployment")


def test_model_request_timeout(monkeypatch, config):
    """A model request timeout should raise a clear error."""

    def mock_post(*args, **kwargs):
        raise requests.Timeout("Request timed out")

    monkeypatch.setattr(requests, "post", mock_post)

    with pytest.raises(OllamaRequestError, match="request timed out"):
        generate_review(config, "Review prompt", "kind: Deployment")


def test_invalid_ollama_response(monkeypatch, config):
    """An unexpected response structure should raise a clear error."""

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"unexpected": "response"}

    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: MockResponse(),
    )

    with pytest.raises(OllamaRequestError, match="Invalid response"):
        generate_review(config, "Review prompt", "kind: Deployment")


def test_empty_model_response(monkeypatch, config):
    """An empty model response should be rejected."""

    class MockResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"message": {"content": ""}}

    monkeypatch.setattr(
        requests,
        "post",
        lambda *args, **kwargs: MockResponse(),
    )

    with pytest.raises(OllamaRequestError, match="empty model response"):
        generate_review(config, "Review prompt", "kind: Deployment")


def test_missing_model_returns_specific_error(monkeypatch, config):
    """A missing Ollama model should produce a specific error."""

    def mock_post(*args, **kwargs):
        response = requests.Response()
        response.status_code = 404
        response.url = "http://localhost:11434/api/chat"
        raise requests.HTTPError("Model not found", response=response)

    monkeypatch.setattr(requests, "post", mock_post)

    with pytest.raises(
        OllamaRequestError,
        match="Configured Ollama model 'qwen3:4b' is unavailable",
    ):
        generate_review(config, "Review prompt", "kind: Deployment")
