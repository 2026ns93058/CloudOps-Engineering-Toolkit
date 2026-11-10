"""Run the Kubernetes manifest evaluation dataset."""

import json
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from k8s_review.application import ReviewApplicationError, review_manifest
from k8s_review.case_scoring import calculate_case_score
from k8s_review.eval_dataset import load_evaluation_dataset
from k8s_review.failure_classification import (
    EvaluationFailureError,
    classify_failure,
)
from k8s_review.manifest import ManifestParseError
from k8s_review.ollama_client import OllamaConfig, generate_review
from k8s_review.semantic_matching import match_findings


class RawResponseCaptureError(EvaluationFailureError):
    """Raised when an evaluation response or run metadata cannot be saved."""


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _create_run_directory(capture_root: Path) -> tuple[str, Path]:
    """Create a new run directory without reusing an existing run ID."""
    try:
        capture_root.mkdir(parents=True, exist_ok=True)
        for _ in range(10):
            run_id = (
                datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
                + f"-{uuid4().hex}"
            )
            run_directory = capture_root / run_id
            try:
                run_directory.mkdir()
            except FileExistsError:
                continue
            return run_id, run_directory
    except OSError as exc:
        raise RawResponseCaptureError(
            f"Unable to create evaluation capture directory: {exc}"
        ) from exc

    raise RawResponseCaptureError(
        "Unable to allocate a unique evaluation capture directory."
    )


def _write_run_metadata(
    metadata_path: Path,
    metadata: dict[str, Any],
    *,
    create: bool = False,
) -> None:
    """Write metadata for the run, creating the file only once."""
    mode = "x" if create else "w"
    try:
        with metadata_path.open(
            mode,
            encoding="utf-8",
            newline="",
        ) as metadata_file:
            json.dump(metadata, metadata_file, indent=2)
            metadata_file.write("\n")
    except (OSError, UnicodeError, TypeError) as exc:
        raise RawResponseCaptureError(
            f"Unable to write evaluation run metadata: {exc}"
        ) from exc


def _write_raw_response(
    raw_responses_dir: Path,
    case_id: str,
    content: str,
) -> None:
    """Persist response content exactly, without replacing an existing file."""
    filename = f"{quote(case_id, safe='')}-raw-response.txt"
    response_path = raw_responses_dir / filename
    try:
        with response_path.open(
            "x",
            encoding="utf-8",
            newline="",
        ) as response_file:
            response_file.write(content)
    except (OSError, UnicodeError, TypeError) as exc:
        raise RawResponseCaptureError(
            f"Unable to save raw model response for case {case_id}: {exc}"
        ) from exc


def _evaluate_expected_findings(
    expected: list[dict[str, Any]],
    generated: list[dict[str, Any]],
) -> dict[str, Any]:
    """Calculate semantic metrics for one successful AI review."""
    matching = match_findings(expected, generated)
    severity_correct = 0
    evidence_grounded = 0
    remediation_quality = 0

    for pair in matching["matched"]:
        expected_finding = expected[pair["expected_index"]]
        generated_finding = generated[pair["generated_index"]]

        if expected_finding.get("severity") == generated_finding.get("severity"):
            severity_correct += 1

        expected_path = expected_finding.get("evidence_field_path")
        actual_path = generated_finding.get("evidence", {}).get("field_path")
        if expected_path and expected_path == actual_path:
            evidence_grounded += 1

        remediation = generated_finding.get("remediation", "")
        if isinstance(remediation, str) and len(remediation.strip()) >= 20:
            remediation_quality += 1

    scores = calculate_case_score(
        expected_count=len(expected),
        generated_count=len(generated),
        matched_count=matching["matched_count"],
        severity_correct_count=severity_correct,
        evidence_grounded_count=evidence_grounded,
        remediation_quality_count=remediation_quality,
    )

    return {
        **scores,
        "expected_issue_count": len(expected),
        "generated_issue_count": len(generated),
        "matched_issue_count": matching["matched_count"],
        "duplicate_count": matching["duplicate_count"],
    }


def _case_failure(case_id: str, error: Exception) -> dict[str, Any]:
    """Create a safe failure record without persisting raw exception text."""
    classification = classify_failure(error)
    return {
        "case_id": case_id,
        "application_status": "FAILED",
        "schema_pass": False,
        "invariant_pass": False,
        "semantic_score": 0.0,
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
        "severity_score": 0.0,
        "evidence_score": 0.0,
        "remediation_score": 0.0,
        "false_positive_count": 0,
        "false_negative_count": 0,
        "duplicate_count": 0,
        "case_pass": False,
        "failure_reasons": [
            classification["failure_type"],
            classification["error_type"],
            classification["error_message"],  # TEMPORARY DEBUG
        ],
    }


def run_evaluation(
    dataset_path: Path,
    config: OllamaConfig | None = None,
    model_call: Callable[..., Any] | None = None,
    *,
    capture_raw_responses: bool = True,
    capture_root: Path = Path("artifacts/evaluation-runs"),
) -> list[dict[str, Any]]:
    """Execute every dataset case and return individual evaluation results."""
    dataset_path = Path(dataset_path)
    dataset = load_evaluation_dataset(dataset_path)
    results = []
    active_config = config or OllamaConfig()
    capture_directory = None
    run_metadata = None
    raw_responses_dir = None

    if capture_raw_responses:
        run_id, capture_directory = _create_run_directory(Path(capture_root))
        raw_responses_dir = capture_directory / "raw-responses"
        try:
            raw_responses_dir.mkdir()
        except OSError as exc:
            raise RawResponseCaptureError(
                f"Unable to create raw response directory: {exc}"
            ) from exc

        run_metadata = {
            "run_id": run_id,
            "started_at": _timestamp(),
            "completed_at": None,
            "dataset_filename": dataset_path.name,
            "dataset_version": dataset.get("dataset_version"),
            "model_provider": "Ollama",
            "model_name": active_config.model,
            "temperature": active_config.temperature,
            "total_cases_processed": 0,
        }
        _write_run_metadata(
            capture_directory / "run-metadata.json",
            run_metadata,
            create=True,
        )

    execute_model = model_call or generate_review

    try:
        with tempfile.TemporaryDirectory(prefix="k8s-review-eval-") as temp_dir:
            temp_root = Path(temp_dir)

            for case in dataset["cases"]:
                case_id = case["case_id"]
                expected_outcome = case["expected_outcome"]
                if run_metadata is not None:
                    run_metadata["total_cases_processed"] += 1
                manifest_path = temp_root / f"{quote(case_id, safe='')}.yaml"
                report_path = temp_root / f"{quote(case_id, safe='')}.json"

                manifest_path.write_text(
                    case["input_manifest"],
                    encoding="utf-8",
                )

                def capture_model_response(
                    call_config,
                    prompt,
                    sanitized_yaml,
                    response_case_id=case_id,
                ):
                    result = execute_model(
                        call_config,
                        prompt,
                        sanitized_yaml,
                    )
                    if raw_responses_dir is not None:
                        _write_raw_response(
                            raw_responses_dir,
                            response_case_id,
                            result.content,
                        )
                    return result

                try:
                    report = review_manifest(
                        manifest_path,
                        report_path,
                        config=config,
                        model_call=capture_model_response,
                    )

                    if expected_outcome == "INPUT_REJECTED":
                        results.append({
                            "case_id": case_id,
                            "application_status": "UNEXPECTED_SUCCESS",
                            "semantic_score": None,
                            "schema_pass": True,
                            "invariant_pass": True,
                            "case_pass": False,
                            "failure_reasons": [
                                "Expected input rejection but review succeeded."
                            ],
                        })
                        continue

                    if expected_outcome == "UNSUPPORTED_RESOURCE_RECORDED":
                        unsupported = report["unsupported_resources"]
                        expected_resources = case["expected_resources"]
                        actual_resources = [
                            {
                                "kind": item["kind"],
                                "name": item["name"],
                                "supported": False,
                            }
                            for item in unsupported
                        ]
                        passed = all(
                            any(
                                all(
                                    actual.get(key) == value
                                    for key, value in expected.items()
                                )
                                for actual in actual_resources
                            )
                            for expected in expected_resources
                        ) and len(actual_resources) == len(expected_resources)
                        results.append({
                            "case_id": case_id,
                            "application_status": "UNSUPPORTED_RESOURCE_RECORDED",
                            "semantic_score": None,
                            "schema_pass": True,
                            "invariant_pass": True,
                            "case_pass": passed,
                            "failure_reasons": [] if passed else [
                                "Unsupported resource record did not match expectation."
                            ],
                        })
                        continue

                    actual_resources = [
                        {"kind": item["kind"], "name": item["name"]}
                        for item in report["resources_reviewed"]
                    ]
                    expected_resources = case["expected_resources"]
                    resource_identity_pass = actual_resources == expected_resources

                    generated = report["findings"]
                    metrics = _evaluate_expected_findings(
                        case["expected_findings"],
                        generated,
                    )

                    safety_markers = case.get("safety_markers", [])
                    report_text = json.dumps(report, ensure_ascii=False)
                    marker_detected = any(
                        marker and marker in report_text
                        for marker in safety_markers
                    )

                    invariant_pass = not marker_detected
                    case_pass = (
                        metrics["semantic_score"] + 1e-9 >= 0.80
                        and invariant_pass
                        and resource_identity_pass
                    )

                    failure_reasons = []
                    if metrics["false_positive_count"]:
                        failure_reasons.append("Unexpected findings were generated.")
                    if metrics["false_negative_count"]:
                        failure_reasons.append("Expected findings were missed.")
                    if metrics["duplicate_count"]:
                        failure_reasons.append("Duplicate findings were generated.")
                    if marker_detected:
                        failure_reasons.append(
                            "A protected safety marker was detected."
                        )
                    if not resource_identity_pass:
                        failure_reasons.append(
                            "Reviewed resource identities did not match expectations."
                        )

                    results.append({
                        "case_id": case_id,
                        "application_status": "SUCCESS",
                        "schema_pass": True,
                        "invariant_pass": invariant_pass,
                        "resource_identity_pass": resource_identity_pass,
                        **metrics,
                        "case_pass": case_pass,
                        "failure_reasons": failure_reasons,
                    })

                except RawResponseCaptureError:
                    raise

                except (ReviewApplicationError, ManifestParseError) as exc:
                    if expected_outcome == "INPUT_REJECTED":
                        results.append({
                            "case_id": case_id,
                            "application_status": "INPUT_REJECTED",
                            "semantic_score": None,
                            "schema_pass": True,
                            "invariant_pass": True,
                            "case_pass": True,
                            "failure_reasons": [],
                        })
                    else:
                        results.append(_case_failure(case_id, exc))

                except Exception as exc:
                    results.append(_case_failure(case_id, exc))
    finally:
        if run_metadata is not None and capture_directory is not None:
            run_metadata["completed_at"] = _timestamp()
            _write_run_metadata(
                capture_directory / "run-metadata.json",
                run_metadata,
            )

    return results
