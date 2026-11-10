"""Tests for the command-line interface."""

import json
from pathlib import Path

import pytest

from k8s_review import cli
from k8s_review.cli import build_parser


def test_help_option(capsys):
    """The CLI should display help information."""
    parser = build_parser()

    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--help"])

    assert exc.value.code == 0
    assert "Kubernetes YAML manifest review" in capsys.readouterr().out


def test_version_option(capsys):
    """The CLI should display the application version."""
    parser = build_parser()

    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--version"])

    assert exc.value.code == 0
    assert "0.1.0" in capsys.readouterr().out


def test_manifest_argument():
    """The CLI should accept a manifest path."""
    parser = build_parser()
    args = parser.parse_args(["deployment.yaml"])

    assert args.manifest.name == "deployment.yaml"


def test_output_argument():
    """The CLI should accept a JSON output path."""
    parser = build_parser()
    args = parser.parse_args(
        ["deployment.yaml", "--output", "review.json"]
    )

    assert args.output.name == "review.json"


@pytest.mark.parametrize(
    ("dataset_name", "expected_version"),
    [
        ("dataset.json", "1.0.0"),
        ("dataset-v1.0.4.json", "1.0.4"),
    ],
)
def test_evaluation_results_record_selected_dataset_version(
    tmp_path,
    monkeypatch,
    dataset_name,
    expected_version,
):
    project_root = Path(__file__).parents[1]
    dataset_path = project_root / "evals" / dataset_name
    results_path = tmp_path / "evaluation-results.json"
    monkeypatch.setattr(
        cli,
        "run_evaluation",
        lambda dataset_path, config: [{
            "case_id": "MOCK-001",
            "application_status": "SUCCESS",
            "semantic_score": 1.0,
            "schema_pass": True,
            "invariant_pass": True,
            "case_pass": True,
        }],
    )

    exit_code = cli._run_evaluation(dataset_path, results_path)

    assert exit_code == 0
    result = json.loads(results_path.read_text(encoding="utf-8"))
    assert result["dataset_version"] == expected_version
