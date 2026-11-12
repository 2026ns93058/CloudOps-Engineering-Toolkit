"""Tests for the end-to-end evaluation runner."""

import json

import pytest

from k8s_review.evaluation_runner import run_evaluation
from k8s_review.ollama_client import OllamaResult


def write_dataset(tmp_path, cases):
    dataset = {
        "dataset_version": "1.0.0",
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
    )

    assert results[0]["resource_identity_pass"] is False
    assert results[0]["case_pass"] is False
    assert any(
        "resource identities" in reason
        for reason in results[0]["failure_reasons"]
    )
