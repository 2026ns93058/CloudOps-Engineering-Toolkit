"""Configuration and request handling for the local Ollama runtime."""

import os
import time
from dataclasses import dataclass

import requests


@dataclass(frozen=True)
class OllamaConfig:
    """Settings used to connect to a local Ollama instance."""

    base_url: str = "http://localhost:11434"
    model: str = "qwen3:4b"
    temperature: float = 0.2
    timeout_seconds: int = 180

    @classmethod
    def from_environment(cls) -> "OllamaConfig":
        """Build configuration using environment variables and defaults."""
        return cls(
            base_url=os.getenv(
                "OLLAMA_BASE_URL", "http://localhost:11434"
            ).rstrip("/"),
            model=os.getenv("OLLAMA_MODEL", "qwen3:4b"),
            temperature=float(os.getenv("OLLAMA_TEMPERATURE", "0.2")),
            timeout_seconds=int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "180")),
        )


def check_ollama_connection(config: OllamaConfig) -> bool:
    """Return True when the Ollama service responds successfully."""
    try:
        response = requests.get(
            f"{config.base_url}/api/tags",
            timeout=config.timeout_seconds,
        )
        response.raise_for_status()
        return True
    except requests.RequestException:
        return False


def check_model_available(config: OllamaConfig) -> bool:
    """Return True when the configured model is available in Ollama."""
    try:
        response = requests.get(
            f"{config.base_url}/api/tags",
            timeout=config.timeout_seconds,
        )
        response.raise_for_status()
        models = response.json().get("models", [])
        return any(
            model.get("name") == config.model for model in models
        )
    except (requests.RequestException, ValueError):
        return False


@dataclass(frozen=True)
class OllamaResult:
    """Model response and actual execution metadata."""

    content: str
    model: str
    temperature: float
    duration_ms: int


class OllamaRequestError(RuntimeError):
    """Raised when an Ollama model request fails."""


def generate_review(
    config: OllamaConfig,
    prompt: str,
    sanitized_manifest: str,
) -> OllamaResult:
    """Send a sanitized manifest to Ollama and return its response."""
    started_at = time.perf_counter()

    try:
        response = requests.post(
            f"{config.base_url}/api/chat",
            json={
                "model": config.model,
                "messages": [
                    {"role": "system", "content": prompt},
                    {
                        "role": "user",
                        "content": (
                            "Review the following sanitized Kubernetes YAML:\n\n"
                            f"{sanitized_manifest}"
                        ),
                    },
                ],
                "think": False,
                "format": "json",
                "stream": False,
                "options": {
                    "temperature": config.temperature,
                    "num_predict": 2048,
                },
            },
            timeout=config.timeout_seconds,
        )
        response.raise_for_status()
        response_data = response.json()
        content = response_data["message"]["content"]

        if not isinstance(content, str) or not content.strip():
            raise OllamaRequestError("Ollama returned an empty model response.")

        duration_ms = round(
            (time.perf_counter() - started_at) * 1000
        )

        return OllamaResult(
            content=content,
            model=config.model,
            temperature=config.temperature,
            duration_ms=duration_ms,
        )

    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code == 404:
            message = f"Configured Ollama model '{config.model}' is unavailable."
        else:
            message = f"Ollama returned HTTP error {status_code}: {exc}"
        raise OllamaRequestError(message) from exc
    except requests.Timeout as exc:
        raise OllamaRequestError(
            f"Ollama request timed out after {config.timeout_seconds} seconds."
        ) from exc
    except requests.RequestException as exc:
        raise OllamaRequestError(
            f"Ollama request failed: {exc}"
        ) from exc
    except (ValueError, KeyError, TypeError) as exc:
        raise OllamaRequestError(
            f"Invalid response received from Ollama: {exc}"
        ) from exc
