"""Command-line interface for the Kubernetes Manifest Review Assistant."""

import argparse
from datetime import datetime, timezone
from pathlib import Path

from k8s_review.application import ReviewApplicationError, review_manifest
from k8s_review.eval_dataset import load_evaluation_dataset
from k8s_review.evaluation_results import (
    build_evaluation_results,
    write_evaluation_results,
)
from k8s_review.evaluation_runner import run_evaluation
from k8s_review.failure_classification import classify_failure
from k8s_review.ollama_client import OllamaConfig


def build_parser() -> argparse.ArgumentParser:
    """Build and return the application argument parser."""
    parser = argparse.ArgumentParser(
        prog="k8s-review",
        description="AI-assisted Kubernetes YAML manifest review.",
    )
    parser.add_argument(
        "manifest",
        nargs="?",
        type=Path,
        help="Path to a Kubernetes YAML manifest.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Path where the JSON review report will be saved.",
    )
    parser.add_argument(
        "--evaluate",
        action="store_true",
        help="Run the complete evaluation dataset.",
    )
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("evals/dataset.json"),
        help="Evaluation dataset JSON path.",
    )
    parser.add_argument(
        "--results",
        type=Path,
        default=Path("artifacts/evaluation-results.json"),
        help="Evaluation results JSON output path.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="Kubernetes Manifest Review Assistant 0.1.0",
    )
    return parser


def _run_evaluation(dataset_path: Path, results_path: Path) -> int:
    """Run the evaluation pipeline and save its results."""
    started_at = datetime.now(timezone.utc).isoformat()
    config = OllamaConfig()

    try:
        dataset = load_evaluation_dataset(dataset_path)
        dataset_results = run_evaluation(dataset_path, config=config)
        completed_at = datetime.now(timezone.utc).isoformat()

        evaluation = build_evaluation_results(
            case_results=dataset_results,
            dataset_version=dataset["dataset_version"],
            model_metadata={
                "provider": "Ollama",
                "model": config.model,
                "temperature": config.temperature,
            },
            started_at=started_at,
            completed_at=completed_at,
        )
        write_evaluation_results(evaluation, results_path)

    except Exception as exc:
        failure = classify_failure(exc)
        print(
            f"Evaluation could not be completed: "
            f"{failure['failure_type']} ({failure['error_type']})"
        )
        return 1

    print(f"Evaluation results saved to: {results_path}")
    print(f"Cases processed: {evaluation['total_cases']}")
    print(
        "Aggregate semantic score: "
        f"{evaluation['aggregate_semantic_score']:.2%}"
    )
    print(f"Overall status: {evaluation['overall_status']}")

    return 0 if evaluation["overall_status"] == "PASS" else 1


def main() -> int:
    """Run the command-line application."""
    parser = build_parser()
    args = parser.parse_args()

    if args.evaluate:
        if args.manifest is not None:
            parser.error("Do not provide a manifest path with --evaluate.")
        return _run_evaluation(args.dataset, args.results)

    if args.manifest is None:
        parser.print_help()
        return 0

    output_path = args.output or Path("review-report.json")

    try:
        review_manifest(args.manifest, output_path)
    except Exception as exc:
        failure = classify_failure(exc)
        print(
            f"Review failed: {failure['failure_type']} "
            f"({failure['error_type']})"
        )
        return 1

    print(f"Review report saved to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
