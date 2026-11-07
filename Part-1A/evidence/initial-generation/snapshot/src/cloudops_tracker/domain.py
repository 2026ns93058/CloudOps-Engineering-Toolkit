from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class Environment(StringEnum):
    DEVELOPMENT = "Development"
    STAGING = "Staging"
    PRODUCTION = "Production"


class Priority(StringEnum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


class DeploymentStatus(StringEnum):
    DRAFT = "DRAFT"
    VALIDATING = "VALIDATING"
    BLOCKED = "BLOCKED"
    APPROVED = "APPROVED"
    DEPLOYING = "DEPLOYING"
    DEPLOYED = "DEPLOYED"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    ROLLED_BACK = "ROLLED_BACK"


class CheckStatus(StringEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_CHECKED = "NOT_CHECKED"


class DecisionType(StringEnum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"


class AuditEventType(StringEnum):
    CREATION = "creation"
    METADATA_UPDATE = "metadata_update"
    READINESS_UPDATE = "readiness_update"
    STATUS_TRANSITION = "status_transition"
    HUMAN_DECISION = "human_decision"
    FAILURE = "failure"
    ROLLBACK = "rollback"


MANDATORY_CHECK_NAMES = (
    "application-version",
    "container-image",
    "image-tag-not-latest",
    "resource-configuration",
    "health-probes",
    "test-result",
    "human-approval",
    "rollback-plan",
)

LIFECYCLE_TRANSITIONS: dict[DeploymentStatus, frozenset[DeploymentStatus]] = {
    DeploymentStatus.DRAFT: frozenset(
        {DeploymentStatus.VALIDATING, DeploymentStatus.REJECTED}
    ),
    DeploymentStatus.VALIDATING: frozenset(
        {
            DeploymentStatus.BLOCKED,
            DeploymentStatus.APPROVED,
            DeploymentStatus.FAILED,
            DeploymentStatus.REJECTED,
        }
    ),
    DeploymentStatus.BLOCKED: frozenset(
        {DeploymentStatus.VALIDATING, DeploymentStatus.REJECTED}
    ),
    DeploymentStatus.APPROVED: frozenset(
        {
            DeploymentStatus.DEPLOYING,
            DeploymentStatus.BLOCKED,
            DeploymentStatus.REJECTED,
        }
    ),
    DeploymentStatus.DEPLOYING: frozenset(
        {
            DeploymentStatus.DEPLOYED,
            DeploymentStatus.FAILED,
            DeploymentStatus.ROLLED_BACK,
        }
    ),
    DeploymentStatus.DEPLOYED: frozenset(
        {DeploymentStatus.FAILED, DeploymentStatus.ROLLED_BACK}
    ),
    DeploymentStatus.FAILED: frozenset({DeploymentStatus.ROLLED_BACK}),
    DeploymentStatus.REJECTED: frozenset(),
    DeploymentStatus.ROLLED_BACK: frozenset(),
}

_AUDIT_REQUIRES_ACTOR = frozenset(
    {
        AuditEventType.METADATA_UPDATE,
        AuditEventType.READINESS_UPDATE,
        AuditEventType.STATUS_TRANSITION,
        AuditEventType.HUMAN_DECISION,
        AuditEventType.FAILURE,
        AuditEventType.ROLLBACK,
    }
)
_AUDIT_REQUIRES_REASON = frozenset(
    {
        AuditEventType.METADATA_UPDATE,
        AuditEventType.READINESS_UPDATE,
        AuditEventType.STATUS_TRANSITION,
        AuditEventType.HUMAN_DECISION,
        AuditEventType.FAILURE,
        AuditEventType.ROLLBACK,
    }
)


def _require_text(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")


def _require_utc(name: str, value: datetime) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError(f"{name} must be a timezone-aware UTC datetime")
    offset = value.utcoffset()
    if offset != timedelta(0):
        raise ValueError(f"{name} must be a UTC datetime")


def _enum_value(enum_type: type[StringEnum], value: Any, name: str) -> StringEnum:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} has unsupported value {value!r}") from exc


@dataclass(frozen=True)
class ReadinessCheck:
    check_name: str
    status: CheckStatus
    evidence: str | None
    reason: str | None
    updated_at: datetime

    def __post_init__(self) -> None:
        if self.check_name not in MANDATORY_CHECK_NAMES:
            raise ValueError(f"Unknown mandatory readiness check: {self.check_name!r}")
        status = _enum_value(CheckStatus, self.status, "readiness status")
        object.__setattr__(self, "status", status)
        _require_utc("readiness updated_at", self.updated_at)
        if status is CheckStatus.PASS:
            if self.evidence is None:
                raise ValueError("PASS readiness checks require supporting evidence")
            _require_text("readiness evidence", self.evidence)
        elif self.reason is None:
            raise ValueError(f"{status.value} readiness checks require a reason")
        else:
            _require_text("readiness reason", self.reason)
        if self.evidence is not None:
            _require_text("readiness evidence", self.evidence)
        if self.reason is not None:
            _require_text("readiness reason", self.reason)


@dataclass(frozen=True)
class HumanApprovalDecision:
    decision: DecisionType
    actor: str
    decided_at: datetime
    reason: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "decision", _enum_value(DecisionType, self.decision, "decision")
        )
        _require_text("decision actor", self.actor)
        _require_utc("decision decided_at", self.decided_at)
        _require_text("decision reason", self.reason)


@dataclass(frozen=True)
class Deployment:
    deployment_id: str
    application_name: str
    application_version: str
    container_image: str
    environment: Environment
    priority: Priority
    requester: str
    created_at: datetime
    updated_at: datetime
    status: DeploymentStatus
    readiness_checks: dict[str, ReadinessCheck]
    approval_decision: HumanApprovalDecision | None = None
    failure_details: str | None = None
    rollback_details: str | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "deployment_id",
            "application_name",
            "application_version",
            "container_image",
            "requester",
        ):
            _require_text(field_name, getattr(self, field_name))
        object.__setattr__(
            self,
            "environment",
            _enum_value(Environment, self.environment, "environment"),
        )
        object.__setattr__(
            self, "priority", _enum_value(Priority, self.priority, "priority")
        )
        status = _enum_value(DeploymentStatus, self.status, "deployment status")
        object.__setattr__(self, "status", status)
        _require_utc("deployment created_at", self.created_at)
        _require_utc("deployment updated_at", self.updated_at)
        if not isinstance(self.readiness_checks, dict):
            raise ValueError("readiness_checks must be a mapping")
        if set(self.readiness_checks) != set(MANDATORY_CHECK_NAMES):
            raise ValueError(
                "readiness_checks must contain exactly the eight mandatory checks"
            )
        for check_name, check in self.readiness_checks.items():
            if not isinstance(check, ReadinessCheck) or check.check_name != check_name:
                raise ValueError(
                    f"readiness check key {check_name!r} does not match its record"
                )
        if self.approval_decision is not None and not isinstance(
            self.approval_decision, HumanApprovalDecision
        ):
            raise ValueError("approval_decision must be a HumanApprovalDecision")
        if self.failure_details is not None:
            _require_text("failure_details", self.failure_details)
        if self.rollback_details is not None:
            _require_text("rollback_details", self.rollback_details)
        if status is DeploymentStatus.FAILED and self.failure_details is None:
            raise ValueError("FAILED deployments require failure_details")
        if status is DeploymentStatus.ROLLED_BACK and self.rollback_details is None:
            raise ValueError("ROLLED_BACK deployments require rollback_details")


@dataclass(frozen=True)
class AuditEvent:
    event_id: str
    deployment_id: str
    event_type: AuditEventType | str
    occurred_at: datetime
    actor: str | None
    reason: str | None
    details: dict[str, Any]

    def __post_init__(self) -> None:
        _require_text("audit event_id", self.event_id)
        _require_text("audit deployment_id", self.deployment_id)
        event_type = _enum_value(AuditEventType, self.event_type, "audit event_type")
        object.__setattr__(self, "event_type", event_type)
        _require_utc("audit occurred_at", self.occurred_at)
        if not isinstance(self.details, dict) or not self.details:
            raise ValueError("audit details must be a non-empty structured mapping")
        if self.actor is not None:
            _require_text("audit actor", self.actor)
        if self.reason is not None:
            _require_text("audit reason", self.reason)
        if event_type in _AUDIT_REQUIRES_ACTOR and self.actor is None:
            raise ValueError(f"{event_type.value} audit events require an actor")
        if event_type in _AUDIT_REQUIRES_REASON and self.reason is None:
            raise ValueError(f"{event_type.value} audit events require a reason")


@dataclass(frozen=True)
class StateDocument:
    schema_version: int
    deployments: list[Deployment]
    audit_events: list[AuditEvent]

    def __post_init__(self) -> None:
        if (
            isinstance(self.schema_version, bool)
            or not isinstance(self.schema_version, int)
            or self.schema_version != 1
        ):
            raise ValueError(f"Unsupported state schema version: {self.schema_version!r}")
        if not isinstance(self.deployments, list) or not isinstance(
            self.audit_events, list
        ):
            raise ValueError("deployments and audit_events must be lists")
        if any(not isinstance(item, Deployment) for item in self.deployments):
            raise ValueError("state contains an invalid deployment record")
        if any(not isinstance(item, AuditEvent) for item in self.audit_events):
            raise ValueError("state contains an invalid audit event")
        deployment_ids = [item.deployment_id for item in self.deployments]
        if len(set(deployment_ids)) != len(deployment_ids):
            raise ValueError("deployment IDs must be unique within the state store")
        event_ids = [item.event_id for item in self.audit_events]
        if len(set(event_ids)) != len(event_ids):
            raise ValueError("audit event IDs must be unique within the state store")
        known_deployment_ids = set(deployment_ids)
        for event in self.audit_events:
            if event.deployment_id not in known_deployment_ids:
                raise ValueError(
                    f"audit event {event.event_id!r} references an unknown deployment"
                )


def validate_transition(
    current: DeploymentStatus | str, target: DeploymentStatus | str
) -> None:
    current_status = _enum_value(DeploymentStatus, current, "current status")
    target_status = _enum_value(DeploymentStatus, target, "target status")
    allowed = LIFECYCLE_TRANSITIONS[current_status]
    if target_status not in allowed:
        raise ValueError(
            f"Transition from {current_status.value} to {target_status.value} is not allowed"
        )


def validate_deployment_transition(
    deployment: Deployment,
    target: DeploymentStatus | str,
    *,
    failure_details: str | None = None,
    rollback_details: str | None = None,
) -> DeploymentStatus:
    target_status = _enum_value(DeploymentStatus, target, "target status")
    validate_transition(deployment.status, target_status)
    if target_status in (DeploymentStatus.APPROVED, DeploymentStatus.DEPLOYING):
        unmet_checks = [
            name
            for name in MANDATORY_CHECK_NAMES
            if deployment.readiness_checks[name].status is not CheckStatus.PASS
            or not deployment.readiness_checks[name].evidence
        ]
        if unmet_checks:
            raise ValueError(
                "readiness requirements are unmet: " + ", ".join(unmet_checks)
            )
    if target_status is DeploymentStatus.APPROVED and (
        deployment.approval_decision is None
        or deployment.approval_decision.decision is not DecisionType.ACCEPT
    ):
        raise ValueError("APPROVED requires a separate human ACCEPT decision")
    if target_status is DeploymentStatus.FAILED:
        _require_text("failure_details", failure_details)
    if target_status is DeploymentStatus.ROLLED_BACK:
        _require_text("rollback_details", rollback_details)
    return target_status
