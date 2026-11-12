"""Tests for JSON review report output."""

import json

from k8s_review.report_writer import write_review_report


def test_write_review_report(tmp_path):
    """A report should be written as valid JSON."""
    report = {
        "review_summary": "One issue identified.",
        "resources_reviewed": [],
        "unsupported_resources": [],
        "findings": [],
        "model_metadata": {"provider": "Ollama"},
    }

    output_path = tmp_path / "review.json"

    result = write_review_report(report, output_path)

    assert result == output_path
    assert output_path.exists()
    assert json.loads(output_path.read_text(encoding="utf-8")) == report


def test_write_report_creates_parent_directories(tmp_path):
    """Missing output directories should be created."""
    report = {"review_summary": "Complete", "findings": []}
    output_path = tmp_path / "reports" / "nested" / "review.json"

    write_review_report(report, output_path)

    assert output_path.exists()


def test_write_report_preserves_unicode(tmp_path):
    """Unicode characters should remain readable in the JSON file."""
    report = {"review_summary": "Review completed — सुरक्षित"}
    output_path = tmp_path / "review.json"

    write_review_report(report, output_path)

    content = output_path.read_text(encoding="utf-8")

    assert "सुरक्षित" in content
    assert json.loads(content) == report


def test_write_report_uses_readable_indentation(tmp_path):
    """The JSON output should use two-space indentation."""
    report = {"review_summary": "Complete", "findings": []}
    output_path = tmp_path / "review.json"

    write_review_report(report, output_path)

    content = output_path.read_text(encoding="utf-8")

    assert '\n  "review_summary"' in content
