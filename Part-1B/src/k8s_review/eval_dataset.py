"""Load and validate the evaluation dataset."""

import json
from pathlib import Path
from typing import Any


class EvaluationDatasetError(ValueError):
    """Raised when the evaluation dataset is invalid."""


REQUIRED_CASE_FIELDS = {
    "case_id",
    "description",
    "category",
    "input_manifest",
    "expected_outcome",
    "expected_findings",
    "expected_resources",
}


def load_evaluation_dataset(
    file_path: Path,
) -> dict[str, Any]:
    """Load the evaluation dataset and validate its basic structure."""
    file_path = Path(file_path)

    try:
        dataset = json.loads(file_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise EvaluationDatasetError(
            f"Evaluation dataset not found: {file_path}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise EvaluationDatasetError(
            f"Evaluation dataset contains invalid JSON: {exc.msg}"
        ) from exc

    if not isinstance(dataset, dict):
        raise EvaluationDatasetError(
            "Evaluation dataset must be a JSON object."
        )

    cases = dataset.get("cases")
    if not isinstance(cases, list) or not cases:
        raise EvaluationDatasetError(
            "Evaluation dataset must contain a non-empty cases list."
        )

    declared_count = dataset.get("total_cases")
    if declared_count != len(cases):
        raise EvaluationDatasetError(
            "Declared total_cases does not match the actual case count."
        )

    case_ids = []
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            raise EvaluationDatasetError(
                f"Evaluation case at index {index} must be an object."
            )

        missing_fields = REQUIRED_CASE_FIELDS - case.keys()
        if missing_fields:
            raise EvaluationDatasetError(
                f"Evaluation case at index {index} is missing fields: "
                f"{', '.join(sorted(missing_fields))}."
            )

        case_id = case["case_id"]
        if not isinstance(case_id, str) or not case_id.strip():
            raise EvaluationDatasetError(
                f"Evaluation case at index {index} has an invalid case_id."
            )

        case_ids.append(case_id)

    if len(case_ids) != len(set(case_ids)):
        raise EvaluationDatasetError(
            "Evaluation dataset contains duplicate case IDs."
        )

    return dataset
