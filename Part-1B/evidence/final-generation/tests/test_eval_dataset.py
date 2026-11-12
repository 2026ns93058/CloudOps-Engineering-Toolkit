"""Tests for evaluation dataset loading."""

import json
from pathlib import Path

import pytest

from k8s_review.eval_dataset import (
    EvaluationDatasetError,
    load_evaluation_dataset,
)


def test_load_valid_evaluation_dataset():
    """The project dataset should load all 20 cases."""
    path = Path(__file__).parents[1] / "evals" / "dataset.json"
    dataset = load_evaluation_dataset(path)

    assert len(dataset["cases"]) == 20
    assert dataset["total_cases"] == 20


def test_v105_dataset_only_changes_version_and_approved_expected_findings():
    project_root = Path(__file__).parents[1]
    original = load_evaluation_dataset(
        project_root / "evals" / "dataset-v1.0.4.json"
    )
    revised = load_evaluation_dataset(
        project_root / "evals" / "dataset-v1.0.5.json"
    )

    assert revised["dataset_version"] == "1.0.5"
    assert len(revised["cases"]) == 20
    assert [
        case["case_id"] for case in revised["cases"]
    ] == [case["case_id"] for case in original["cases"]]
    assert {
        key: value
        for key, value in revised.items()
        if key not in {"dataset_version", "cases"}
    } == {
        key: value
        for key, value in original.items()
        if key not in {"dataset_version", "cases"}
    }

    original_by_id = {case["case_id"]: case for case in original["cases"]}
    revised_by_id = {case["case_id"]: case for case in revised["cases"]}
    expected_issue_ids = {
        "K8S-EVAL-002": [
            "K8S-CFG-001",
            "K8S-REL-001",
            "K8S-REL-002",
            "K8S-SEC-001",
        ],
        "K8S-EVAL-003": [
            "K8S-SEC-002",
            "K8S-REL-001",
            "K8S-REL-002",
            "K8S-SEC-001",
        ],
        "K8S-EVAL-004": [
            "K8S-REL-001",
            "K8S-REL-002",
            "K8S-SEC-001",
        ],
        "K8S-EVAL-005": [
            "K8S-RES-002",
            "K8S-REL-001",
            "K8S-REL-002",
            "K8S-SEC-001",
        ],
        "K8S-EVAL-009": [
            "K8S-SEC-003",
            "K8S-REL-001",
            "K8S-REL-002",
        ],
        "K8S-EVAL-010": [
            "K8S-CFG-003",
            "K8S-REL-001",
            "K8S-REL-002",
            "K8S-SEC-001",
        ],
        "K8S-EVAL-012": [
            "K8S-SEC-001",
            "K8S-REL-001",
            "K8S-REL-002",
        ],
        "K8S-EVAL-018": [
            "K8S-CFG-001",
            "K8S-REL-001",
            "K8S-REL-002",
            "K8S-SEC-001",
        ],
        "K8S-EVAL-019": [
            "K8S-RES-003",
            "K8S-REL-001",
            "K8S-REL-002",
            "K8S-SEC-001",
        ],
    }

    for case_id, expected_ids in expected_issue_ids.items():
        revised_case = revised_by_id[case_id]
        assert [
            finding["issue_id"]
            for finding in revised_case["expected_findings"]
        ] == expected_ids
        original_case = original_by_id[case_id]
        assert revised_case["expected_findings"][
            :len(original_case["expected_findings"])
        ] == original_case["expected_findings"]
        assert {
            key: value
            for key, value in revised_case.items()
            if key != "expected_findings"
        } == {
            key: value
            for key, value in original_case.items()
            if key != "expected_findings"
        }

    assert revised_by_id["K8S-EVAL-003"]["expected_findings"][-1][
        "issue_id"
    ] == "K8S-SEC-001"
    assert "K8S-SEC-003" not in {
        finding["issue_id"]
        for finding in revised_by_id["K8S-EVAL-003"]["expected_findings"]
    }
    assert revised_by_id["K8S-EVAL-020"]["expected_findings"] == []

    for case_id in set(original_by_id) - set(expected_issue_ids):
        assert revised_by_id[case_id] == original_by_id[case_id]


def test_v106_dataset_only_adds_non_root_findings_to_cases_006_and_007():
    project_root = Path(__file__).parents[1]
    original = load_evaluation_dataset(
        project_root / "evals" / "dataset-v1.0.5.json"
    )
    revised = load_evaluation_dataset(
        project_root / "evals" / "dataset-v1.0.6.json"
    )

    assert revised["dataset_version"] == "1.0.6"
    assert len(revised["cases"]) == 20
    original_by_id = {case["case_id"]: case for case in original["cases"]}
    revised_by_id = {case["case_id"]: case for case in revised["cases"]}
    assert revised_by_id.keys() == original_by_id.keys()

    for case_id in revised_by_id:
        old_case = original_by_id[case_id]
        new_case = revised_by_id[case_id]
        if case_id in {"K8S-EVAL-006", "K8S-EVAL-007"}:
            assert [
                finding["issue_id"] for finding in new_case["expected_findings"]
            ] == [
                finding["issue_id"] for finding in old_case["expected_findings"]
            ] + ["K8S-SEC-001"]
            assert new_case["expected_findings"][:-1] == (
                old_case["expected_findings"]
            )
            sec001 = new_case["expected_findings"][-1]
            assert sec001["resource_name"] == old_case["expected_resources"][0]["name"]
            assert sec001["severity"] == "Medium"
            assert sec001["evidence_field_path"] == (
                "spec.template.spec.containers[0].securityContext.runAsNonRoot"
            )
            assert {
                key: value
                for key, value in new_case.items()
                if key != "expected_findings"
            } == {
                key: value
                for key, value in old_case.items()
                if key != "expected_findings"
            }
        else:
            assert new_case == old_case

    assert revised_by_id["K8S-EVAL-003"]["expected_findings"] == (
        original_by_id["K8S-EVAL-003"]["expected_findings"]
    )


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
