from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from typing import Callable, Mapping
from uuid import uuid4

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
    validate_deployment_transition,
    validate_transition,
)
from cloudops_tracker.readiness import ReadinessEligibility, evaluate_check, evaluate_eligibility
from cloudops_tracker.storage import JsonStore


class ServiceError(ValueError):
    """Raised when a deployment service operation violates its contract."""


class DuplicateDeploymentError(ServiceError):
    """Raised when an active deployment has the same identity."""


class DeploymentNotFoundError(ServiceError):
    """Raised when a deployment ID is absent from the local state."""


_ACTIVE_STATUSES = frozenset(
    {
        DeploymentStatus.DRAFT,
        DeploymentStatus.VALIDATING,
        DeploymentStatus.BLOCKED,
        DeploymentStatus.APPROVED,
        DeploymentStatus.DEPLOYING,
    }
)
_PRIORITY_ORDER = {
    Priority.P1: 1,
    Priority.P2: 2,
    Priority.P3: 3,
    Priority.P4: 4,
}
_METADATA_FIELDS = frozenset(
    {
        "application_name",
        "application_version",
        "container_image",
        "environment",
        "priority",
        "requester",
    }
)


def _as_environment(value: Environment | str) -> Environment:
    try:
        return Environment(value)
    except (TypeError, ValueError) as exc:
        supported = ", ".join(item.value for item in Environment)
        raise ServiceError(
            f"Unsupported environment {value!r}; choose one of: {supported}"
        ) from exc


def _as_priority(value: Priority | str) -> Priority:
    try:
        return Priority(value)
    except (TypeError, ValueError) as exc:
        supported = ", ".join(item.value for item in Priority)
        raise ServiceError(
            f"Unsupported priority {value!r}; choose one of: {supported}"
        ) from exc


def _nonempty_text(field: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ServiceError(f"{field} must be a non-empty value")
    return value.strip()


class DeploymentService:
    """Applies request-management rules to complete local JSON snapshots."""

    def __init__(
        self,
        store: JsonStore,
        *,
        id_generator: Callable[[], str] | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._store = store
        self._id_generator = id_generator or (lambda: uuid4().hex)
        self._event_id_generator: Callable[[], str] = lambda: uuid4().hex
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _new_event(self, deployment_id: str, event_type: AuditEventType, *,
                   actor: str | None, reason: str | None,
                   details: dict[str, object]) -> AuditEvent:
        return AuditEvent(
            event_id=self._event_id_generator(),
            deployment_id=deployment_id,
            event_type=event_type,
            occurred_at=self._clock(),
            actor=actor,
            reason=reason,
            details=details,
        )

    def _deployment_id(self, state: StateDocument) -> str:
        existing_ids = {item.deployment_id for item in state.deployments}
        for _ in range(10):
            candidate = self._id_generator()
            if isinstance(candidate, str) and candidate.strip() and candidate not in existing_ids:
                return candidate
        raise ServiceError("Could not generate a unique deployment ID after 10 attempts")

    @staticmethod
    def _identity_matches(left: Deployment, right: Deployment) -> bool:
        return (
            left.application_name.strip().casefold()
            == right.application_name.strip().casefold()
            and left.environment is right.environment
            and left.application_version.strip() == right.application_version.strip()
        )

    def _reject_duplicate(
        self,
        deployments: list[Deployment],
        candidate: Deployment,
        *,
        exclude_id: str | None = None,
    ) -> None:
        for existing in deployments:
            if (
                existing.deployment_id != exclude_id
                and existing.status in _ACTIVE_STATUSES
                and self._identity_matches(existing, candidate)
            ):
                raise DuplicateDeploymentError(
                    "duplicate active deployment exists for the same application, "
                    "environment, and version"
                )

    def create_deployment(
        self,
        *,
        application_name: str,
        application_version: str,
        container_image: str,
        environment: Environment | str,
        priority: Priority | str,
        requester: str,
    ) -> Deployment:
        state = self._store.load()
        created_at = self._clock()
        deployment = Deployment(
            deployment_id=self._deployment_id(state),
            application_name=_nonempty_text("application_name", application_name),
            application_version=_nonempty_text(
                "application_version", application_version
            ),
            container_image=_nonempty_text("container_image", container_image),
            environment=_as_environment(environment),
            priority=_as_priority(priority),
            requester=_nonempty_text("requester", requester),
            created_at=created_at,
            updated_at=created_at,
            status=DeploymentStatus.DRAFT,
            readiness_checks={
                name: ReadinessCheck(
                    check_name=name,
                    status=CheckStatus.NOT_CHECKED,
                    evidence=None,
                    reason="Not checked at creation",
                    updated_at=created_at,
                )
                for name in MANDATORY_CHECK_NAMES
            },
        )
        self._reject_duplicate(state.deployments, deployment)
        event = self._new_event(
            deployment.deployment_id,
            AuditEventType.CREATION,
            actor=deployment.requester,
            reason=None,
            details={
                "application_name": deployment.application_name,
                "application_version": deployment.application_version,
                "container_image": deployment.container_image,
                "environment": deployment.environment.value,
                "priority": deployment.priority.value,
                "status": deployment.status.value,
            },
        )
        self._store.save(
            StateDocument(
                schema_version=state.schema_version,
                deployments=[*state.deployments, deployment],
                audit_events=[*state.audit_events, event],
            )
        )
        return deployment

    def get_deployment(self, deployment_id: str) -> Deployment:
        requested_id = _nonempty_text("deployment_id", deployment_id)
        state = self._store.load()
        for deployment in state.deployments:
            if deployment.deployment_id == requested_id:
                return deployment
        raise DeploymentNotFoundError(f"Deployment {requested_id!r} not found")

    def list_deployments(
        self,
        *,
        environment: Environment | str | None = None,
        sort_by_priority: bool = False,
    ) -> list[Deployment]:
        state = self._store.load()
        deployments = list(state.deployments)
        if environment is not None:
            selected_environment = _as_environment(environment)
            deployments = [
                deployment
                for deployment in deployments
                if deployment.environment is selected_environment
            ]
        if sort_by_priority:
            deployments.sort(key=lambda deployment: _PRIORITY_ORDER[deployment.priority])
        return deployments

    def list_audit_events(self, deployment_id: str) -> list[AuditEvent]:
        requested_id = _nonempty_text("deployment_id", deployment_id)
        state = self._store.load()
        if not any(item.deployment_id == requested_id for item in state.deployments):
            raise DeploymentNotFoundError(f"Deployment {requested_id!r} not found")
        return [
            event for event in state.audit_events if event.deployment_id == requested_id
        ]

    def update_metadata(
        self,
        deployment_id: str,
        updates: Mapping[str, object],
        *,
        actor: str,
        reason: str,
    ) -> Deployment:
        requested_id = _nonempty_text("deployment_id", deployment_id)
        operator = _nonempty_text("actor", actor)
        update_reason = _nonempty_text("reason", reason)
        if not isinstance(updates, Mapping) or not updates:
            raise ServiceError("At least one metadata field must be provided")
        unknown_fields = set(updates) - _METADATA_FIELDS
        if unknown_fields:
            raise ServiceError(
                f"Metadata fields cannot be updated: {', '.join(sorted(unknown_fields))}"
            )

        state = self._store.load()
        index = next(
            (
                position
                for position, item in enumerate(state.deployments)
                if item.deployment_id == requested_id
            ),
            None,
        )
        if index is None:
            raise DeploymentNotFoundError(f"Deployment {requested_id!r} not found")

        current = state.deployments[index]
        normalized_updates: dict[str, object] = {}
        for field, value in updates.items():
            if field == "environment":
                normalized_updates[field] = _as_environment(value)  # type: ignore[arg-type]
            elif field == "priority":
                normalized_updates[field] = _as_priority(value)  # type: ignore[arg-type]
            else:
                normalized_updates[field] = _nonempty_text(field, value)
        updated = replace(
            current,
            **normalized_updates,
            updated_at=self._clock(),
        )
        if updated.status in _ACTIVE_STATUSES:
            self._reject_duplicate(
                state.deployments, updated, exclude_id=updated.deployment_id
            )
        old_values = {
            field: getattr(current, field).value
            if isinstance(getattr(current, field), (Environment, Priority))
            else getattr(current, field)
            for field in normalized_updates
        }
        new_values = {
            field: getattr(updated, field).value
            if isinstance(getattr(updated, field), (Environment, Priority))
            else getattr(updated, field)
            for field in normalized_updates
        }
        event = self._new_event(
            updated.deployment_id,
            AuditEventType.METADATA_UPDATE,
            actor=operator,
            reason=update_reason,
            details={"old_values": old_values, "new_values": new_values},
        )
        deployments = list(state.deployments)
        deployments[index] = updated
        self._store.save(
            StateDocument(
                schema_version=state.schema_version,
                deployments=deployments,
                audit_events=[*state.audit_events, event],
            )
        )
        return updated

    def set_readiness(
        self,
        deployment_id: str,
        *,
        check_name: str,
        status: CheckStatus | str,
        actor: str,
        reason: str | None = None,
        evidence: str | None = None,
    ) -> Deployment:
        requested_id = _nonempty_text("deployment_id", deployment_id)
        operator = _nonempty_text("actor", actor)
        try:
            normalized_status = CheckStatus(status)
        except (TypeError, ValueError) as exc:
            raise ServiceError(f"Unsupported readiness status {status!r}") from exc
        check_reason = (
            _nonempty_text("reason", reason) if reason is not None else None
        )
        if normalized_status is not CheckStatus.PASS and check_reason is None:
            raise ServiceError(
                f"{normalized_status.value} readiness results require a reason"
            )
        event_reason = check_reason or "Readiness check recorded as PASS"
        state = self._store.load()
        index = next(
            (
                position
                for position, item in enumerate(state.deployments)
                if item.deployment_id == requested_id
            ),
            None,
        )
        if index is None:
            raise DeploymentNotFoundError(f"Deployment {requested_id!r} not found")

        current = state.deployments[index]
        check = evaluate_check(
            check_name,
            status=normalized_status,
            evidence=evidence,
            reason=check_reason if normalized_status is not CheckStatus.PASS else None,
            updated_at=self._clock(),
        )
        checks = dict(current.readiness_checks)
        checks[check.check_name] = check
        updated = replace(current, readiness_checks=checks, updated_at=check.updated_at)
        event = self._new_event(
            requested_id,
            AuditEventType.READINESS_UPDATE,
            actor=operator,
            reason=event_reason,
            details={
                "check_name": check.check_name,
                "status": check.status.value,
                "evidence": check.evidence,
                "check_reason": check.reason,
            },
        )
        deployments = list(state.deployments)
        deployments[index] = updated
        self._store.save(
            StateDocument(
                schema_version=state.schema_version,
                deployments=deployments,
                audit_events=[*state.audit_events, event],
            )
        )
        return updated

    def readiness_eligibility(self, deployment_id: str) -> ReadinessEligibility:
        deployment = self.get_deployment(deployment_id)
        return evaluate_eligibility(deployment.readiness_checks)

    def approved_gate_eligibility(self, deployment_id: str) -> ReadinessEligibility:
        deployment = self.get_deployment(deployment_id)
        readiness = evaluate_eligibility(deployment.readiness_checks)
        unmet_checks = list(readiness.unmet_checks)
        if (
            deployment.approval_decision is None
            or deployment.approval_decision.decision is not DecisionType.ACCEPT
        ):
            unmet_checks.append("final-operator-ACCEPT")
        return ReadinessEligibility(
            eligible=not unmet_checks,
            unmet_checks=tuple(unmet_checks),
        )

    def record_decision(
        self,
        deployment_id: str,
        *,
        decision: DecisionType | str,
        actor: str,
        reason: str,
    ) -> Deployment:
        requested_id = _nonempty_text("deployment_id", deployment_id)
        operator = _nonempty_text("actor", actor)
        decision_reason = _nonempty_text("reason", reason)
        try:
            normalized_decision = DecisionType(decision)
        except (TypeError, ValueError) as exc:
            raise ServiceError(f"Unsupported decision {decision!r}") from exc

        state = self._store.load()
        index = next(
            (
                position
                for position, item in enumerate(state.deployments)
                if item.deployment_id == requested_id
            ),
            None,
        )
        if index is None:
            raise DeploymentNotFoundError(f"Deployment {requested_id!r} not found")

        current = state.deployments[index]
        if normalized_decision is DecisionType.REJECT:
            validate_transition(current.status, DeploymentStatus.REJECTED)
        now = self._clock()
        recorded_decision = HumanApprovalDecision(
            decision=normalized_decision,
            actor=operator,
            decided_at=now,
            reason=decision_reason,
        )
        updated = replace(
            current,
            approval_decision=recorded_decision,
            status=(
                DeploymentStatus.REJECTED
                if normalized_decision is DecisionType.REJECT
                else current.status
            ),
            updated_at=now,
        )
        event = self._new_event(
            requested_id,
            AuditEventType.HUMAN_DECISION,
            actor=operator,
            reason=decision_reason,
            details={
                "decision": normalized_decision.value,
                "status_before": current.status.value,
                "status_after": updated.status.value,
            },
        )
        deployments = list(state.deployments)
        deployments[index] = updated
        self._store.save(
            StateDocument(
                schema_version=state.schema_version,
                deployments=deployments,
                audit_events=[*state.audit_events, event],
            )
        )
        return updated

    def transition_status(
        self,
        deployment_id: str,
        *,
        target: DeploymentStatus | str,
        actor: str,
        reason: str,
        failure_details: str | None = None,
        rollback_details: str | None = None,
    ) -> Deployment:
        requested_id = _nonempty_text("deployment_id", deployment_id)
        operator = _nonempty_text("actor", actor)
        transition_reason = _nonempty_text("reason", reason)
        try:
            target_status = DeploymentStatus(target)
        except (TypeError, ValueError) as exc:
            raise ServiceError(f"Unsupported deployment status {target!r}") from exc

        state = self._store.load()
        index = next(
            (
                position
                for position, item in enumerate(state.deployments)
                if item.deployment_id == requested_id
            ),
            None,
        )
        if index is None:
            raise DeploymentNotFoundError(f"Deployment {requested_id!r} not found")

        current = state.deployments[index]
        try:
            validate_deployment_transition(
                current,
                target_status,
                failure_details=failure_details,
                rollback_details=rollback_details,
            )
        except ValueError as exc:
            raise ServiceError(str(exc)) from exc

        new_failure_details = current.failure_details
        new_rollback_details = current.rollback_details
        if target_status is DeploymentStatus.FAILED:
            new_failure_details = failure_details
        if target_status is DeploymentStatus.ROLLED_BACK:
            new_rollback_details = rollback_details

        now = self._clock()
        updated = replace(
            current,
            status=target_status,
            updated_at=now,
            failure_details=new_failure_details,
            rollback_details=new_rollback_details,
        )
        events = [
            self._new_event(
                requested_id,
                AuditEventType.STATUS_TRANSITION,
                actor=operator,
                reason=transition_reason,
                details={
                    "from": current.status.value,
                    "to": target_status.value,
                },
            )
        ]
        if target_status is DeploymentStatus.FAILED:
            events.append(
                self._new_event(
                    requested_id,
                    AuditEventType.FAILURE,
                    actor=operator,
                    reason=transition_reason,
                    details={"failure_details": new_failure_details},
                )
            )
        elif target_status is DeploymentStatus.ROLLED_BACK:
            events.append(
                self._new_event(
                    requested_id,
                    AuditEventType.ROLLBACK,
                    actor=operator,
                    reason=transition_reason,
                    details={"rollback_details": new_rollback_details},
                )
            )
        deployments = list(state.deployments)
        deployments[index] = updated
        self._store.save(
            StateDocument(
                schema_version=state.schema_version,
                deployments=deployments,
                audit_events=[*state.audit_events, *events],
            )
        )
        return updated
