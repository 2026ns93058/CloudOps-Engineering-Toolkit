"""Classify failures during AI review and evaluation."""

from typing import Any

from k8s_review.application import ReviewApplicationError
from k8s_review.eval_dataset import EvaluationDatasetError
from k8s_review.manifest import ManifestParseError
from k8s_review.ollama_client import OllamaRequestError


class EvaluationFailureError(RuntimeError):
    """Raised when evaluation processing or scoring fails."""


def classify_failure(error: Exception) -> dict[str, Any]:
    """Classify an exception by the stage where the failure occurred."""
    if isinstance(error, OllamaRequestError):
        failure_type = "MODEL_EXECUTION_FAILURE"
    elif isinstance(
        error,
        (ReviewApplicationError, ManifestParseError),
    ):
        failure_type = "APPLICATION_FAILURE"
    elif isinstance(error, (EvaluationDatasetError, EvaluationFailureError)):
        failure_type = "EVALUATION_FAILURE"
    else:
        failure_type = "UNCLASSIFIED_FAILURE"

    return {
        "failure_type": failure_type,
        "error_type": type(error).__name__,
        "error_message": str(error),
    }
