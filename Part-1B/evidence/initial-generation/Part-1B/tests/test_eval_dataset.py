"""Tests for evaluation dataset loading."""

import json

import pytest

from k8s_review.eval_dataset import (
    EvaluationDatasetError,
    load_evaluation_dataset,
)


def test_load_valid_evaluation_dataset():
    """The project dataset should load all 20 cases."""
    from pathlib import Path

    path = Path(__file__).parents[1] / "evals" / "dataset.json"
    dataset = load_evaluation_dataset(path)

    assert len(dataset["cases"]) == 20
    assert dataset["total_cases"] == 20


def test_missing_dataset_is_rejected(tmp_path):
    """A missing dataset file should raise a clear error."""
    with pytest.raises(EvaluationDatasetError, match="not found"):
        load_evaluation_dataset(tmp_path / "missing.json")


def test_invalid_json_is_rejected(tmp_path):
    """Invalid JSON should raise a dataset error."""
    path = tmp_path / "invalid.json"
    path.write_text("{invalid json", encoding="utf-8")

    with pytest.raises(EvaluationDatasetError, match="invalid JSON"):
        load_evaluation_dataset(path)


def test_duplicate_case_ids_are_rejected(tmp_path):
    """Duplicate evaluation case IDs must not be accepted."""
    case = {
        "case_id": "CASE-001",
        "description": "Test case",
        "category": "Security",
        "input_manifest": "apiVersion: v1",
        "expected_outcome": "SUCCESS",
        "expected_findings": [],
        "expected_resources": [],
    }
    dataset = {
        "total_cases": 2,
        "cases": [case, case],
    }
    path = tmp_path / "duplicate.json"
    path.write_text(json.dumps(dataset), encoding="utf-8")

    with pytest.raises(EvaluationDatasetError, match="duplicate"):
        load_evaluation_dataset(path)
