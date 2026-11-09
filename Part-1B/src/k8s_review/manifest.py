"""Kubernetes YAML manifest file loading and parsing."""

from pathlib import Path
from typing import Any

import yaml


class ManifestParseError(ValueError):
    """Raised when a Kubernetes manifest contains invalid YAML."""


def load_manifest_documents(file_path: Path) -> list[Any]:
    """Safely load all YAML documents from a manifest file."""
    try:
        content = file_path.read_text(encoding="utf-8")
        return list(yaml.safe_load_all(content))
    except yaml.YAMLError as exc:
        raise ManifestParseError(
            f"Invalid YAML in manifest '{file_path}': {exc}"
        ) from exc
