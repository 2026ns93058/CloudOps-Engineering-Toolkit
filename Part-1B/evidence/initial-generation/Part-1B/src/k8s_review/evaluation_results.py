"""Build and write machine-readable evaluation results."""

import json
from pathlib import Path
from typing import Any

from k8s_review.acceptance import evaluate_quality_gates
from k8s_review.aggregate_scoring import calculate_aggregate_score


def build_evaluation_results(
    case_results: list[dict[str, Any]],
    dataset_version: str,
    model_metadata: dict[str, Any],
    started_at: str,
    completed_at: str,
) -> dict[str, Any]:
    """Combine per-case results into a complete evaluation summary."""
    eligible_results = [
        result for result in case_results
        if result.get("semantic_score") is not None
    ]

    case_scores = [result["semantic_score"] for result in eligible_results]

    aggregate = (
        calculate_aggregate_score(case_scores)
        if case_scores
        else {
            "aggregate_semantic_score": 0.0,
            "evaluated_case_count": 0,
        }
    )

    schema_pass_rate = (
        sum(bool(result.get("schema_pass")) for result in eligible_results)
        / len(eligible_results)
        if eligible_results else 0.0
    )

    invariant_pass_rate = (
        sum(bool(result.get("invariant_pass")) for result in eligible_results)
        / len(eligible_results)
        if eligible_results else 0.0
    )

    gates = evaluate_quality_gates(
        aggregate["aggregate_semantic_score"],
        schema_pass_rate,
        invariant_pass_rate,
    )

    failed_cases = [
        result["case_id"] for result in case_results
        if not result.get("case_pass", False)
    ]

    completed_cases = [
        result for result in case_results
        if result.get("application_status") != "FAILED"
    ]

    execution_failures = [
        result for result in case_results
        if result.get("application_status") == "FAILED"
    ]

    return {
        "dataset_version": dataset_version,
        "started_at": started_at,
        "completed_at": completed_at,
        "model_metadata": model_metadata,
        "total_cases": len(case_results),
        "processed_cases": len(case_results),
        "completed_cases": len(completed_cases),
        "passed_cases": sum(
            bool(result.get("case_pass")) for result in case_results
        ),
        "failed_case_count": len(failed_cases),
        "failed_cases": failed_cases,
        "execution_failure_count": len(execution_failures),
        "execution_failures": [
            result["case_id"] for result in execution_failures
        ],
        "evaluated_case_count": aggregate["evaluated_case_count"],
        "aggregate_semantic_score": round(
            aggregate["aggregate_semantic_score"], 6
        ),
        "acceptance_threshold": gates["acceptance_threshold"],
        "schema_pass_rate": gates["schema_pass_rate"],
        "invariant_pass_rate": gates["invariant_pass_rate"],
        "schema_requirement_pass": gates["schema_requirement_pass"],
        "safety_requirement_pass": gates["safety_requirement_pass"],
        "semantic_threshold_pass": gates["semantic_threshold_pass"],
        "overall_status": gates["overall_status"],
        "case_results": case_results,
    }


def write_evaluation_results(
    results: dict[str, Any],
    output_path: Path,
) -> None:
    """Write evaluation results as formatted JSON."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(results, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
