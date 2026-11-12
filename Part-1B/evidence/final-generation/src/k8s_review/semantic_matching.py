"""Match AI-generated findings against expected evaluation findings."""

from typing import Any


def _finding_identity(finding: dict[str, Any]) -> tuple[Any, ...]:
    """Return the stable identity used for semantic issue matching."""
    return (
        finding.get("issue_id"),
        finding.get("resource_kind"),
        finding.get("resource_name"),
        finding.get("category"),
    )


def match_findings(
    expected_findings: list[dict[str, Any]],
    generated_findings: list[dict[str, Any]],
) -> dict[str, Any]:
    """Match findings one-to-one and identify duplicate generated findings."""
    unmatched_generated = set(range(len(generated_findings)))
    matched = []
    unmatched_expected = []
    seen_identities = set()
    duplicate_indices = []

    for index, finding in enumerate(generated_findings):
        identity = _finding_identity(finding)
        if identity in seen_identities:
            duplicate_indices.append(index)
        else:
            seen_identities.add(identity)

    for expected_index, expected in enumerate(expected_findings):
        expected_identity = _finding_identity(expected)

        generated_index = next(
            (
                index
                for index in sorted(unmatched_generated)
                if _finding_identity(generated_findings[index])
                == expected_identity
            ),
            None,
        )

        if generated_index is None:
            unmatched_expected.append(expected_index)
        else:
            matched.append({
                "expected_index": expected_index,
                "generated_index": generated_index,
            })
            unmatched_generated.remove(generated_index)

    return {
        "matched": matched,
        "unmatched_expected": unmatched_expected,
        "unmatched_generated": sorted(unmatched_generated),
        "matched_count": len(matched),
        "duplicate_indices": duplicate_indices,
        "duplicate_count": len(duplicate_indices),
    }
