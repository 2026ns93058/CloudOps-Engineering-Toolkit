from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
import unittest

from cloudops_tracker.domain import (
    AuditEvent,
    CheckStatus,
    DecisionType,
    Deployment,
    DeploymentStatus,
    Environment,
    HumanApprovalDecision,
    Priority,
    ReadinessCheck,
    StateDocument,
    validate_transition,
)


UTC = timezone.utc
CHECK_NAMES = (
    "application-version",
    "container-image",
    "image-tag-not-latest",
    "resource-configuration",
    "health-probes",
    "test-result",
    "human-approval",
    "rollback-plan",
)


def timestamp(hour: int = 12) -> datetime:
    return datetime(2026, 11, 7, hour, 0, tzinfo=UTC)


def make_checks(status: CheckStatus = CheckStatus.NOT_CHECKED) -> dict[str, ReadinessCheck]:
    return {
        name: ReadinessCheck(
            check_name=name,
            status=status,
            evidence="evidence://readiness" if status is CheckStatus.PASS else None,
            reason="Awaiting validation" if status is CheckStatus.NOT_CHECKED else None,
            updated_at=timestamp(),
        )
        for name in CHECK_NAMES
    }


def make_deployment(**overrides: object) -> Deployment:
    fields: dict[str, object] = {
        "deployment_id": "dep-001",
        "application_name": "inventory-api",
        "application_version": "2.4.1",
        "container_image": "registry.local/inventory-api:2.4.1",
        "environment": Environment.STAGING,
        "priority": Priority.P1,
        "requester": "operator",
        "created_at": timestamp(),
        "updated_at": timestamp(),
        "status": DeploymentStatus.DRAFT,
        "readiness_checks": make_checks(),
        "approval_decision": None,
        "failure_details": None,
        "rollback_details": None,
    }
    fields.update(overrides)
    return Deployment(**fields)  # type: ignore[arg-type]


class DeploymentRecordTests(unittest.TestCase):
    def test_enumerations_match_the_documented_fixed_values(self) -> None:
        self.assertEqual(
            {item.value for item in Environment},
            {"Development", "Staging", "Production"},
        )
        self.assertEqual({item.value for item in Priority}, {"P1", "P2", "P3", "P4"})
        self.assertEqual(
            {item.value for item in DeploymentStatus},
            {
                "DRAFT",
                "VALIDATING",
                "BLOCKED",
                "APPROVED",
                "DEPLOYING",
                "DEPLOYED",
                "FAILED",
                "REJECTED",
                "ROLLED_BACK",
            },
        )
        self.assertEqual({item.value for item in CheckStatus}, {"PASS", "FAIL", "NOT_CHECKED"})
        self.assertEqual({item.value for item in DecisionType}, {"ACCEPT", "REJECT"})

    def test_valid_deployment_has_exactly_the_eight_fixed_checks(self) -> None:
        deployment = make_deployment()

        self.assertEqual(set(deployment.readiness_checks), set(CHECK_NAMES))
        self.assertEqual(len(deployment.readiness_checks), 8)
        self.assertEqual(deployment.status, DeploymentStatus.DRAFT)

    def test_required_text_fields_must_not_be_blank_after_trimming(self) -> None:
        for field in (
            "deployment_id",
            "application_name",
            "application_version",
            "container_image",
            "requester",
        ):
            with self.subTest(field=field):
                with self.assertRaises((TypeError, ValueError)):
                    make_deployment(**{field: "  "})

    def test_environment_priority_and_status_are_restricted_to_documented_values(self) -> None:
        invalid_values = (
            ("environment", "Production-Blue"),
            ("priority", "P0"),
            ("status", "IN_PROGRESS"),
        )
        for field, value in invalid_values:
            with self.subTest(field=field):
                with self.assertRaises((TypeError, ValueError)):
                    make_deployment(**{field: value})

    def test_deployment_creation_and_update_timestamps_must_be_utc(self) -> None:
        naive = datetime(2026, 11, 7, 12, 0)
        with self.assertRaises((TypeError, ValueError)):
            make_deployment(created_at=naive)
        with self.assertRaises((TypeError, ValueError)):
            make_deployment(updated_at=naive)

    def test_deployment_id_and_creation_timestamp_are_immutable(self) -> None:
        deployment = make_deployment()

        with self.assertRaises((AttributeError, FrozenInstanceError, TypeError)):
            deployment.deployment_id = "dep-changed"
        with self.assertRaises((AttributeError, FrozenInstanceError, TypeError)):
            deployment.created_at = timestamp(13)

    def test_readiness_check_names_and_result_evidence_rules_are_enforced(self) -> None:
        with self.assertRaises((TypeError, ValueError)):
            ReadinessCheck(
                check_name="custom-check",
                status=CheckStatus.PASS,
                evidence="evidence://custom",
                reason=None,
                updated_at=timestamp(),
            )

        for status, evidence, reason in (
            (CheckStatus.PASS, None, None),
            (CheckStatus.PASS, "  ", None),
            (CheckStatus.FAIL, None, None),
            (CheckStatus.NOT_CHECKED, None, "  "),
        ):
            with self.subTest(status=status, evidence=evidence, reason=reason):
                with self.assertRaises((TypeError, ValueError)):
                    ReadinessCheck(
                        check_name="test-result",
                        status=status,
                        evidence=evidence,
                        reason=reason,
                        updated_at=timestamp(),
                    )

    def test_human_decision_requires_a_supported_decision_actor_and_reason(self) -> None:
        with self.assertRaises((TypeError, ValueError)):
            HumanApprovalDecision(
                decision="MAYBE",
                actor="operator",
                decided_at=timestamp(),
                reason="Decision",
            )

        for actor, reason in (("  ", "Accept"), ("operator", "  ")):
            with self.subTest(actor=actor, reason=reason):
                with self.assertRaises((TypeError, ValueError)):
                    HumanApprovalDecision(
                        decision=DecisionType.ACCEPT,
                        actor=actor,
                        decided_at=timestamp(),
                        reason=reason,
                    )

    def test_failure_and_rollback_states_require_their_details(self) -> None:
        for status, field in (
            (DeploymentStatus.FAILED, "failure_details"),
            (DeploymentStatus.ROLLED_BACK, "rollback_details"),
        ):
            with self.subTest(status=status):
                with self.assertRaises((TypeError, ValueError)):
                    make_deployment(status=status, **{field: None})


class LifecycleTransitionTests(unittest.TestCase):
    ALLOWED = {
        DeploymentStatus.DRAFT: {DeploymentStatus.VALIDATING, DeploymentStatus.REJECTED},
        DeploymentStatus.VALIDATING: {
            DeploymentStatus.BLOCKED,
            DeploymentStatus.APPROVED,
            DeploymentStatus.FAILED,
            DeploymentStatus.REJECTED,
        },
        DeploymentStatus.BLOCKED: {DeploymentStatus.VALIDATING, DeploymentStatus.REJECTED},
        DeploymentStatus.APPROVED: {
            DeploymentStatus.DEPLOYING,
            DeploymentStatus.BLOCKED,
            DeploymentStatus.REJECTED,
        },
        DeploymentStatus.DEPLOYING: {
            DeploymentStatus.DEPLOYED,
            DeploymentStatus.FAILED,
            DeploymentStatus.ROLLED_BACK,
        },
        DeploymentStatus.DEPLOYED: {
            DeploymentStatus.FAILED,
            DeploymentStatus.ROLLED_BACK,
        },
        DeploymentStatus.FAILED: {DeploymentStatus.ROLLED_BACK},
        DeploymentStatus.REJECTED: set(),
        DeploymentStatus.ROLLED_BACK: set(),
    }

    def test_every_transition_pair_matches_the_documented_table(self) -> None:
        statuses = tuple(DeploymentStatus)

        self.assertEqual(set(self.ALLOWED), set(statuses))
        for current in statuses:
            for target in statuses:
                with self.subTest(current=current, target=target):
                    if target in self.ALLOWED[current]:
                        self.assertIsNone(validate_transition(current, target))
                    else:
                        details: dict[str, str] = {}
                        if current is DeploymentStatus.FAILED:
                            details["failure_details"] = "Transition matrix fixture"
                        elif current is DeploymentStatus.ROLLED_BACK:
                            details["rollback_details"] = "Transition matrix fixture"
                        deployment = make_deployment(status=current, **details)
                        with self.assertRaises(ValueError):
                            validate_transition(current, target)
                        self.assertEqual(deployment.status, current)

    def test_rejected_and_rolled_back_are_terminal(self) -> None:
        for terminal in (DeploymentStatus.REJECTED, DeploymentStatus.ROLLED_BACK):
            with self.subTest(terminal=terminal):
                for target in DeploymentStatus:
                    with self.assertRaises(ValueError):
                        validate_transition(terminal, target)


class AuditAndStateDocumentTests(unittest.TestCase):
    def test_audit_event_requires_a_supported_type_utc_time_and_details(self) -> None:
        deployment = make_deployment()
        event_fields: dict[str, object] = {
            "event_id": "event-001",
            "deployment_id": deployment.deployment_id,
            "event_type": "creation",
            "occurred_at": timestamp(),
            "actor": "operator",
            "reason": "Created request",
            "details": {"application": "inventory-api"},
        }
        self.assertIsInstance(AuditEvent(**event_fields), AuditEvent)  # type: ignore[arg-type]

        invalid_cases = (
            {"event_type": "unknown-action"},
            {"occurred_at": datetime(2026, 11, 7, 12, 0)},
            {"details": {}},
        )
        for overrides in invalid_cases:
            with self.subTest(overrides=overrides):
                with self.assertRaises((TypeError, ValueError)):
                    AuditEvent(**(event_fields | overrides))  # type: ignore[arg-type]

    def test_audit_updates_require_actor_and_reason(self) -> None:
        for field in ("actor", "reason"):
            with self.subTest(field=field):
                fields: dict[str, object] = {
                    "event_id": "event-001",
                    "deployment_id": "dep-001",
                    "event_type": "metadata_update",
                    "occurred_at": timestamp(),
                    "actor": "operator",
                    "reason": "Updated requester",
                    "details": {"requester": "release-operator"},
                }
                fields[field] = None
                with self.assertRaises((TypeError, ValueError)):
                    AuditEvent(**fields)  # type: ignore[arg-type]

    def test_state_document_rejects_duplicate_ids_and_dangling_audit_references(self) -> None:
        deployment = make_deployment()
        duplicate = make_deployment()
        with self.assertRaises((TypeError, ValueError)):
            StateDocument(
                schema_version=1,
                deployments=[deployment, duplicate],
                audit_events=[],
            )

        dangling_event = AuditEvent(
            event_id="event-001",
            deployment_id="missing-deployment",
            event_type="creation",
            occurred_at=timestamp(),
            actor=None,
            reason=None,
            details={"application": "inventory-api"},
        )
        with self.assertRaises((TypeError, ValueError)):
            StateDocument(
                schema_version=1,
                deployments=[deployment],
                audit_events=[dangling_event],
            )

    def test_state_document_rejects_duplicate_audit_event_ids(self) -> None:
        deployment = make_deployment()
        event_fields = {
            "event_id": "event-001",
            "deployment_id": deployment.deployment_id,
            "event_type": "creation",
            "occurred_at": timestamp(),
            "actor": "operator",
            "reason": None,
            "details": {"application": "inventory-api"},
        }
        first = AuditEvent(**event_fields)
        second = AuditEvent(**event_fields)

        with self.assertRaises((TypeError, ValueError)):
            StateDocument(
                schema_version=1,
                deployments=[deployment],
                audit_events=[first, second],
            )


if __name__ == "__main__":
    unittest.main()
