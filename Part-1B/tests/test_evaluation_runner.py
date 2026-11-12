"""Tests for the end-to-end evaluation runner."""

import json
from datetime import datetime
from pathlib import Path

import pytest

from k8s_review.ollama_client import OllamaRequestError

from k8s_review.evaluation_runner import (
    RawResponseCaptureError,
    run_evaluation,
)
from k8s_review.ollama_client import OllamaConfig, OllamaResult


def write_dataset(tmp_path, cases, dataset_version="1.0.0"):
    dataset = {
        "dataset_version": dataset_version,
        "total_cases": len(cases),
        "cases": cases,
    }
    path = tmp_path / "dataset.json"
    path.write_text(json.dumps(dataset), encoding="utf-8")
    return path


def test_runner_evaluates_successful_ai_case(tmp_path):
    case = {
        "case_id": "TEST-001",
        "description": "Valid Deployment",
        "category": "Normal",
        "input_manifest": (
            "apiVersion: apps/v1\n"
            "kind: Deployment\n"
            "metadata:\n"
            "  name: secure-app\n"
        ),
        "expected_outcome": "SUCCESS",
        "expected_findings": [],
        "expected_resources": [{"kind": "Deployment", "name": "secure-app"}],
    }

    def mock_model(config, prompt, sanitized_manifest):
        return OllamaResult(
            content=json.dumps({
                "review_summary": "No issues found.",
                "findings": [],
            }),
            model="qwen3:4b",
            temperature=0.2,
            duration_ms=10,
        )

    results = run_evaluation(
        write_dataset(tmp_path, [case]),
        model_call=mock_model,
        capture_raw_responses=False,
    )

    assert len(results) == 1
    assert results[0]["application_status"] == "SUCCESS"
    assert results[0]["semantic_score"] == pytest.approx(1.0)
    assert results[0]["case_pass"] is True


def test_runner_confirms_invalid_input_is_rejected(tmp_path):
    case = {
        "case_id": "TEST-002",
        "description": "Missing resource name",
        "category": "Invalid",
        "input_manifest": (
            "apiVersion: apps/v1\n"
            "kind: Deployment\n"
            "metadata: {}\n"
        ),
        "expected_outcome": "INPUT_REJECTED",
        "expected_findings": [],
        "expected_resources": [],
    }

    def unexpected_model_call(*args):
        raise AssertionError("Model must not be called for invalid input.")

    results = run_evaluation(
        write_dataset(tmp_path, [case]),
        model_call=unexpected_model_call,
        capture_raw_responses=False,
    )

    assert results[0]["application_status"] == "INPUT_REJECTED"
    assert results[0]["case_pass"] is True


def test_runner_records_unsupported_resource_without_model_call(tmp_path):
    case = {
        "case_id": "TEST-003",
        "description": "Unsupported resource",
        "category": "Unsupported",
        "input_manifest": (
            "apiVersion: example.com/v1\n"
            "kind: CustomWorkload\n"
            "metadata:\n"
            "  name: custom-app\n"
        ),
        "expected_outcome": "UNSUPPORTED_RESOURCE_RECORDED",
        "expected_findings": [],
        "expected_resources": [
            {"kind": "CustomWorkload", "name": "custom-app"}
        ],
    }

    def unexpected_model_call(*args):
        raise AssertionError("Model must not be called for unsupported resources.")

    results = run_evaluation(
        write_dataset(tmp_path, [case]),
        model_call=unexpected_model_call,
        capture_raw_responses=False,
    )

    assert results[0]["application_status"] == "UNSUPPORTED_RESOURCE_RECORDED"
    assert results[0]["case_pass"] is True
    assert results[0]["semantic_score"] is None


def test_runner_fails_when_resource_identity_does_not_match(tmp_path):
    case = {
        "case_id": "TEST-004",
        "description": "Resource identity mismatch",
        "category": "Normal",
        "input_manifest": (
            "apiVersion: apps/v1\n"
            "kind: Deployment\n"
            "metadata:\n"
            "  name: actual-app\n"
        ),
        "expected_outcome": "SUCCESS",
        "expected_findings": [],
        "expected_resources": [
            {"kind": "Deployment", "name": "different-app"}
        ],
    }

    def mock_model(config, prompt, sanitized_manifest):
        return OllamaResult(
            content=json.dumps({
                "review_summary": "No issues found.",
                "findings": [],
            }),
            model="qwen3:4b",
            temperature=0.2,
            duration_ms=10,
        )

    results = run_evaluation(
        write_dataset(tmp_path, [case]),
        model_call=mock_model,
        capture_raw_responses=False,
    )

    assert results[0]["resource_identity_pass"] is False
    assert results[0]["case_pass"] is False
    assert any(
        "resource identities" in reason
        for reason in results[0]["failure_reasons"]
    )


def _successful_case(case_id, resource_name):
    return {
        "case_id": case_id,
        "description": "Valid Deployment",
        "category": "Normal",
        "input_manifest": (
            "apiVersion: apps/v1\n"
            "kind: Deployment\n"
            "metadata:\n"
            f"  name: {resource_name}\n"
        ),
        "expected_outcome": "SUCCESS",
        "expected_findings": [],
        "expected_resources": [
            {"kind": "Deployment", "name": resource_name}
        ],
    }


def _mock_model_response(*args):
    return OllamaResult(
        content=(
            '{\n  "review_summary": "No issues found.",\n'
            '  "findings": []\n}\n'
        ),
        model="qwen3:4b",
        temperature=0.2,
        duration_ms=10,
    )


def test_failure_record_does_not_persist_raw_exception_message(tmp_path):
    secret_marker = "SENSITIVE-EXCEPTION-MARKER-987"
    case = _successful_case("TEST-006", "secure-app")

    def failing_model(*args):
        raise OllamaRequestError(f"Model failed while processing {secret_marker}")

    results = run_evaluation(
        write_dataset(tmp_path, [case]),
        model_call=failing_model,
        capture_raw_responses=False,
    )

    failure_text = json.dumps(results[0])
    assert results[0]["application_status"] == "FAILED"
    assert "MODEL_EXECUTION_FAILURE" in failure_text
    assert "OllamaRequestError" in failure_text
    assert "Failure details withheld" in failure_text
    assert secret_marker not in failure_text


def test_capture_saves_exact_response_for_every_model_reviewed_case(tmp_path):
    cases = [
        _successful_case("TEST-101", "first-app"),
        _successful_case("TEST-102", "second-app"),
    ]
    capture_root = tmp_path / "evaluation-runs"
    response = _mock_model_response().content

    results = run_evaluation(
        write_dataset(tmp_path, cases, dataset_version="1.0.4"),
        config=OllamaConfig(model="test-model:7b", temperature=0.35),
        model_call=_mock_model_response,
        capture_root=capture_root,
    )

    assert len(results) == 2
    assert all(result["application_status"] == "SUCCESS" for result in results)
    run_directories = list(capture_root.iterdir())
    assert len(run_directories) == 1
    run_directory = run_directories[0]
    raw_responses = run_directory / "raw-responses"
    assert {
        path.name for path in raw_responses.iterdir()
    } == {
        "TEST-101-raw-response.txt",
        "TEST-102-raw-response.txt",
    }
    assert all(
        (raw_responses / f"{case['case_id']}-raw-response.txt").read_text(
            encoding="utf-8"
        ) == response
        for case in cases
    )

    metadata = json.loads(
        (run_directory / "run-metadata.json").read_text(encoding="utf-8")
    )
    assert metadata == {
        "run_id": run_directory.name,
        "started_at": metadata["started_at"],
        "completed_at": metadata["completed_at"],
        "dataset_filename": "dataset.json",
        "dataset_version": "1.0.4",
        "model_provider": "Ollama",
        "model_name": "test-model:7b",
        "temperature": 0.35,
        "total_cases_processed": 2,
    }
    assert datetime.fromisoformat(metadata["started_at"]).tzinfo is not None
    assert datetime.fromisoformat(metadata["completed_at"]).tzinfo is not None


def test_capture_creates_separate_runs_without_overwriting_existing_files(
    tmp_path,
    monkeypatch,
):
    cases = [_successful_case("TEST-103", "sample-app")]
    dataset_path = write_dataset(tmp_path, cases)
    capture_root = tmp_path / "evaluation-runs"
    diagnostic_path = (
        tmp_path
        / "artifacts"
        / "debug-current"
        / "TEST-103-raw-response.txt"
    )
    diagnostic_path.parent.mkdir(parents=True)
    diagnostic_path.write_text("existing diagnostic", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    first_results = run_evaluation(
        dataset_path,
        model_call=_mock_model_response,
        capture_root=capture_root,
    )
    second_results = run_evaluation(
        dataset_path,
        model_call=_mock_model_response,
        capture_root=capture_root,
    )

    run_directories = list(capture_root.iterdir())
    assert len(first_results) == len(second_results) == 1
    assert len(run_directories) == 2
    assert run_directories[0] != run_directories[1]
    assert diagnostic_path.read_text(encoding="utf-8") == "existing diagnostic"
    assert all(
        (run_directory / "raw-responses" / "TEST-103-raw-response.txt").exists()
        for run_directory in run_directories
    )


def test_capture_failure_aborts_instead_of_changing_case_score(
    tmp_path,
    monkeypatch,
):
    original_open = Path.open

    def fail_raw_response_open(path, mode="r", *args, **kwargs):
        if path.parent.name == "raw-responses" and mode == "x":
            raise OSError("simulated storage failure")
        return original_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_raw_response_open)

    with pytest.raises(RawResponseCaptureError, match="Unable to save raw model"):
        run_evaluation(
            write_dataset(
                tmp_path,
                [_successful_case("TEST-104", "sample-app")],
            ),
            model_call=_mock_model_response,
            capture_root=tmp_path / "evaluation-runs",
        )


def test_capture_can_be_disabled_without_creating_evaluation_artifacts(tmp_path):
    results = run_evaluation(
        write_dataset(
            tmp_path,
            [_successful_case("TEST-105", "sample-app")],
        ),
        model_call=_mock_model_response,
        capture_raw_responses=False,
        capture_root=tmp_path / "evaluation-runs",
    )

    assert results[0]["application_status"] == "SUCCESS"
    assert not (tmp_path / "evaluation-runs").exists()
