"""Tests for the command-line interface."""

import pytest

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
