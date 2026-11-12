"""Tests for machine-readable evaluation results."""

import json

from k8s_review.evaluation_results import (
    build_evaluation_results,
    write_evaluation_results,
)


def sample_cases():
    return [
        {
            "case_id": "CASE-001",
            "semantic_score": 0.90,
            "schema_pass": True,
            "invariant_pass": True,
            "case_pass": True,
            "precision": 1.0,
            "recall": 0.8,
            "f1": 0.89,
            "severity_score": 1.0,
            "evidence_score": 0.8,
            "remediation_score": 0.9,
            "failure_reasons": [],
        },
        {
            "case_id": "CASE-002",
            "semantic_score": 0.70,
            "schema_pass": True,
            "invariant_pass": True,
            "case_pass": False,
            "precision": 0.7,
            "recall": 0.7,
            "f1": 0.7,
            "severity_score": 0.7,
            "evidence_score": 0.7,
            "remediation_score": 0.7,
            "failure_reasons": ["Semantic score below target"],
        },
    ]


def test_build_evaluation_results_calculates_aggregate():
    results = build_evaluation_results(
        sample_cases(),
        "1.0.0",
        {"provider": "Ollama", "model": "qwen3:4b"},
        "2026-11-08T10:00:00Z",
        "2026-11-08T10:01:00Z",
    )

    assert results["total_cases"] == 2
    assert results["evaluated_case_count"] == 2
    assert results["aggregate_semantic_score"] == 0.8
    assert results["overall_status"] == "PASS"


def test_build_evaluation_results_identifies_failed_cases():
    results = build_evaluation_results(
        sample_cases(),
        "1.0.0",
        {},
        "start",
        "end",
    )

    assert results["failed_case_count"] == 1
    assert results["failed_cases"] == ["CASE-002"]
    assert results["case_results"][1]["failure_reasons"]


def test_build_evaluation_results_fails_when_schema_fails():
    cases = sample_cases()
    cases[0]["schema_pass"] = False

    results = build_evaluation_results(cases, "1.0.0", {}, "start", "end")

    assert results["schema_requirement_pass"] is False
    assert results["overall_status"] == "FAIL"


def test_build_evaluation_results_fails_when_invariant_fails():
    cases = sample_cases()
    cases[0]["invariant_pass"] = False

    results = build_evaluation_results(cases, "1.0.0", {}, "start", "end")

    assert results["safety_requirement_pass"] is False
    assert results["overall_status"] == "FAIL"


def test_build_evaluation_results_handles_no_eligible_cases():
    cases = [
        {
            "case_id": "CASE-INVALID",
            "semantic_score": None,
            "schema_pass": False,
            "invariant_pass": False,
            "case_pass": False,
            "failure_reasons": ["Invalid input"],
        }
    ]

    results = build_evaluation_results(cases, "1.0.0", {}, "start", "end")

    assert results["evaluated_case_count"] == 0
    assert results["overall_status"] == "FAIL"


def test_write_evaluation_results_creates_json_file(tmp_path):
    results = build_evaluation_results(
        sample_cases(),
        "1.0.0",
        {"provider": "Ollama"},
        "start",
        "end",
    )
    output_path = tmp_path / "artifacts" / "results.json"

    write_evaluation_results(results, output_path)

    saved = json.loads(output_path.read_text(encoding="utf-8"))
    assert saved["overall_status"] == results["overall_status"]
    assert len(saved["case_results"]) == 2
