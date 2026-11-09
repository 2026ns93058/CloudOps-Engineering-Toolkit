"""Tests for evaluation failure classification."""

from k8s_review.application import ReviewApplicationError
from k8s_review.eval_dataset import EvaluationDatasetError
from k8s_review.failure_classification import (
    EvaluationFailureError,
    classify_failure,
)
from k8s_review.manifest import ManifestParseError
from k8s_review.ollama_client import OllamaRequestError


def test_ollama_error_is_model_execution_failure():
    result = classify_failure(OllamaRequestError("Model timeout"))

    assert result["failure_type"] == "MODEL_EXECUTION_FAILURE"
    assert result["error_type"] == "OllamaRequestError"


def test_application_error_is_classified():
    result = classify_failure(ReviewApplicationError("Invalid response"))

    assert result["failure_type"] == "APPLICATION_FAILURE"


def test_manifest_parse_error_is_application_failure():
    result = classify_failure(ManifestParseError("Invalid YAML"))

    assert result["failure_type"] == "APPLICATION_FAILURE"


def test_dataset_error_is_evaluation_failure():
    result = classify_failure(EvaluationDatasetError("Invalid dataset"))

    assert result["failure_type"] == "EVALUATION_FAILURE"


def test_evaluation_processing_error_is_classified():
    result = classify_failure(EvaluationFailureError("Scoring failed"))

    assert result["failure_type"] == "EVALUATION_FAILURE"


def test_unknown_error_is_classified():
    result = classify_failure(RuntimeError("Unexpected error"))

    assert result["failure_type"] == "UNCLASSIFIED_FAILURE"


def test_error_details_are_preserved():
    result = classify_failure(OllamaRequestError("Connection refused"))

    assert result["error_message"] == "Connection refused"
