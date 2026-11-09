"""Write Kubernetes review reports to JSON files."""

import json
from pathlib import Path
from typing import Any


def write_review_report(
    report: dict[str, Any],
    output_path: Path,
) -> Path:
    """Write a review report as formatted JSON and return its path."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    return output_path
