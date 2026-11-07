from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from cloudops_tracker.domain import (
    AuditEvent,
    AuditEventType,
    CheckStatus,
    DecisionType,
    Deployment,
    DeploymentStatus,
    Environment,
    HumanApprovalDecision,
    MANDATORY_CHECK_NAMES,
    Priority,
    ReadinessCheck,
    StateDocument,
)


class StorageError(Exception):
    """Raised when a local state file cannot be safely loaded or persisted."""


def _timestamp_to_json(value: datetime) -> str:
    return value.isoformat()


def _timestamp_from_json(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be an ISO 8601 timestamp string")
    try:
        result = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} is not a valid ISO 8601 timestamp") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError(f"{field_name} must include a UTC timezone")
    if result.utcoffset().total_seconds() != 0:
        raise ValueError(f"{field_name} must be expressed in UTC")
    return result


def _require_mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ValueError(f"{name} must be a JSON object with string keys")
    return value


def _require_list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be a JSON array")
    return value


def _require_keys(
    value: dict[str, Any], required: set[str], optional: set[str], name: str
) -> None:
    missing = required - value.keys()
    unknown = value.keys() - required - optional
    if missing:
        raise ValueError(f"{name} is missing fields: {', '.join(sorted(missing))}")
    if unknown:
        raise ValueError(f"{name} contains unknown fields: {', '.join(sorted(unknown))}")


def _readiness_to_json(check: ReadinessCheck) -> dict[str, Any]:
    return {
        "check_name": check.check_name,
        "status": check.status.value,
        "evidence": check.evidence,
        "reason": check.reason,
        "updated_at": _timestamp_to_json(check.updated_at),
    }


def _readiness_from_json(value: Any) -> ReadinessCheck:
    data = _require_mapping(value, "readiness check")
    _require_keys(
        data,
        {"check_name", "status", "updated_at"},
        {"evidence", "reason"},
        "readiness check",
    )
    return ReadinessCheck(
        check_name=data["check_name"],
        status=CheckStatus(data["status"]),
        evidence=data.get("evidence"),
        reason=data.get("reason"),
        updated_at=_timestamp_from_json(data["updated_at"], "readiness.updated_at"),
    )


def _decision_to_json(decision: HumanApprovalDecision) -> dict[str, Any]:
    return {
        "decision": decision.decision.value,
        "actor": decision.actor,
        "decided_at": _timestamp_to_json(decision.decided_at),
        "reason": decision.reason,
    }


def _decision_from_json(value: Any) -> HumanApprovalDecision:
    data = _require_mapping(value, "approval_decision")
    _require_keys(
        data,
        {"decision", "actor", "decided_at", "reason"},
        set(),
        "approval_decision",
    )
    return HumanApprovalDecision(
        decision=DecisionType(data["decision"]),
        actor=data["actor"],
        decided_at=_timestamp_from_json(data["decided_at"], "decision.decided_at"),
        reason=data["reason"],
    )


def _deployment_to_json(deployment: Deployment) -> dict[str, Any]:
    return {
        "deployment_id": deployment.deployment_id,
        "application_name": deployment.application_name,
        "application_version": deployment.application_version,
        "container_image": deployment.container_image,
        "environment": deployment.environment.value,
        "priority": deployment.priority.value,
        "requester": deployment.requester,
        "created_at": _timestamp_to_json(deployment.created_at),
        "updated_at": _timestamp_to_json(deployment.updated_at),
        "status": deployment.status.value,
        "readiness_checks": {
            name: _readiness_to_json(deployment.readiness_checks[name])
            for name in MANDATORY_CHECK_NAMES
        },
        "approval_decision": (
            _decision_to_json(deployment.approval_decision)
            if deployment.approval_decision is not None
            else None
        ),
        "failure_details": deployment.failure_details,
        "rollback_details": deployment.rollback_details,
    }


def _deployment_from_json(value: Any) -> Deployment:
    data = _require_mapping(value, "deployment")
    required = {
        "deployment_id",
        "application_name",
        "application_version",
        "container_image",
        "environment",
        "priority",
        "requester",
        "created_at",
        "updated_at",
        "status",
        "readiness_checks",
    }
    optional = {"approval_decision", "failure_details", "rollback_details"}
    _require_keys(data, required, optional, "deployment")
    raw_checks = _require_mapping(data["readiness_checks"], "readiness_checks")
    checks = {
        name: _readiness_from_json(raw_checks[name])
        for name in raw_checks
    }
    raw_decision = data.get("approval_decision")
    return Deployment(
        deployment_id=data["deployment_id"],
        application_name=data["application_name"],
        application_version=data["application_version"],
        container_image=data["container_image"],
        environment=Environment(data["environment"]),
        priority=Priority(data["priority"]),
        requester=data["requester"],
        created_at=_timestamp_from_json(data["created_at"], "deployment.created_at"),
        updated_at=_timestamp_from_json(data["updated_at"], "deployment.updated_at"),
        status=DeploymentStatus(data["status"]),
        readiness_checks=checks,
        approval_decision=(
            _decision_from_json(raw_decision) if raw_decision is not None else None
        ),
        failure_details=data.get("failure_details"),
        rollback_details=data.get("rollback_details"),
    )


def _audit_to_json(event: AuditEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "deployment_id": event.deployment_id,
        "event_type": event.event_type.value,
        "occurred_at": _timestamp_to_json(event.occurred_at),
        "actor": event.actor,
        "reason": event.reason,
        "details": event.details,
    }


def _audit_from_json(value: Any) -> AuditEvent:
    data = _require_mapping(value, "audit event")
    _require_keys(
        data,
        {
            "event_id",
            "deployment_id",
            "event_type",
            "occurred_at",
            "details",
        },
        {"actor", "reason"},
        "audit event",
    )
    details = _require_mapping(data["details"], "audit details")
    return AuditEvent(
        event_id=data["event_id"],
        deployment_id=data["deployment_id"],
        event_type=AuditEventType(data["event_type"]),
        occurred_at=_timestamp_from_json(data["occurred_at"], "audit.occurred_at"),
        actor=data.get("actor"),
        reason=data.get("reason"),
        details=details,
    )


def _state_to_json(state: StateDocument) -> dict[str, Any]:
    return {
        "schema_version": state.schema_version,
        "deployments": [_deployment_to_json(item) for item in state.deployments],
        "audit_events": [_audit_to_json(item) for item in state.audit_events],
    }


def _state_from_json(value: Any) -> StateDocument:
    document = _require_mapping(value, "state document")
    _require_keys(
        document,
        {"schema_version", "deployments", "audit_events"},
        set(),
        "state document",
    )
    version = document["schema_version"]
    if isinstance(version, bool) or not isinstance(version, int):
        raise ValueError("schema_version must be an integer")
    deployments = [
        _deployment_from_json(item)
        for item in _require_list(document["deployments"], "deployments")
    ]
    audit_events = [
        _audit_from_json(item)
        for item in _require_list(document["audit_events"], "audit_events")
    ]
    return StateDocument(
        schema_version=version,
        deployments=deployments,
        audit_events=audit_events,
    )


class JsonStore:
    """Loads and atomically persists one versioned local JSON state document."""

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = Path(path)

    def load(self) -> StateDocument:
        if not self.path.exists():
            return StateDocument(schema_version=1, deployments=[], audit_events=[])
        try:
            raw = self.path.read_text(encoding="utf-8")
            parsed = json.loads(raw)
            return _state_from_json(parsed)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
            raise StorageError(f"Invalid state file {self.path}: {exc}") from exc

    def save(self, state: StateDocument) -> None:
        if not isinstance(state, StateDocument):
            raise StorageError("Only a validated StateDocument can be saved")
        try:
            snapshot = _state_from_json(_state_to_json(state))
            payload = json.dumps(
                _state_to_json(snapshot),
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                allow_nan=False,
            )
        except (AttributeError, TypeError, ValueError) as exc:
            raise StorageError(f"State cannot be serialized: {exc}") from exc

        temp_path: Path | None = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            descriptor, temp_name = tempfile.mkstemp(
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                dir=self.path.parent,
                text=True,
            )
            temp_path = Path(temp_name)
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(payload)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_path, self.path)
            temp_path = None
        except OSError as exc:
            cleanup_error: OSError | None = None
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                    temp_path = None
                except OSError as cleanup_exc:
                    cleanup_error = cleanup_exc
            if cleanup_error is not None:
                raise StorageError(
                    f"Could not persist state file {self.path}: {exc}; "
                    f"temporary file cleanup also failed: {cleanup_error}"
                ) from exc
            raise StorageError(f"Could not persist state file {self.path}: {exc}") from exc
