from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from cloudops_tracker.domain import (
    CheckStatus,
    MANDATORY_CHECK_NAMES,
    ReadinessCheck,
)


@dataclass(frozen=True)
class ReadinessEligibility:
    eligible: bool
    unmet_checks: tuple[str, ...]


def evaluate_check(
    check_name: str,
    *,
    status: CheckStatus | str,
    evidence: str | None,
    reason: str | None,
    updated_at: datetime,
) -> ReadinessCheck:
    """Validate one operator-reported result for a fixed mandatory check."""
    try:
        normalized_status = CheckStatus(status)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Unsupported readiness status: {status!r}") from exc
    try:
        return ReadinessCheck(
            check_name=check_name,
            status=normalized_status,
            evidence=evidence,
            reason=reason,
            updated_at=updated_at,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid result for readiness check {check_name!r}: {exc}") from exc


def evaluate_eligibility(
    readiness_checks: Mapping[str, ReadinessCheck],
) -> ReadinessEligibility:
    """Return all missing or non-passing mandatory checks in fixed order."""
    if not isinstance(readiness_checks, Mapping):
        raise ValueError("readiness_checks must be a mapping")

    unmet: list[str] = []
    for name in MANDATORY_CHECK_NAMES:
        check = readiness_checks.get(name)
        if (
            not isinstance(check, ReadinessCheck)
            or check.check_name != name
            or check.status is not CheckStatus.PASS
            or not isinstance(check.evidence, str)
            or not check.evidence.strip()
        ):
            unmet.append(name)

    unmet.extend(sorted(set(readiness_checks) - set(MANDATORY_CHECK_NAMES)))
    return ReadinessEligibility(eligible=not unmet, unmet_checks=tuple(unmet))
