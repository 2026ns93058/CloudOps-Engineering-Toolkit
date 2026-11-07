from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

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
)
from cloudops_tracker.storage import JsonStore, StorageError


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


def utc(hour: int) -> datetime:
    return datetime(2026, 11, 7, hour, 0, tzinfo=timezone.utc)


def checks() -> dict[str, ReadinessCheck]:
    return {
        name: ReadinessCheck(
            check_name=name,
            status=CheckStatus.PASS,
            evidence=f"evidence://{name}",
            reason=None,
            updated_at=utc(11),
        )
        for name in CHECK_NAMES
    }


def deployment(
    deployment_id: str,
    status: DeploymentStatus,
    *,
    failure_details: str | None = None,
    rollback_details: str | None = None,
) -> Deployment:
    return Deployment(
        deployment_id=deployment_id,
        application_name="inventory-api",
        application_version="2.4.1",
        container_image="registry.local/inventory-api:2.4.1",
        environment=Environment.STAGING,
        priority=Priority.P1,
        requester="operator",
        created_at=utc(9),
        updated_at=utc(11),
        status=status,
        readiness_checks=checks(),
        approval_decision=HumanApprovalDecision(
            decision=DecisionType.ACCEPT,
            actor="reviewer",
            decided_at=utc(10),
            reason="Readiness evidence reviewed",
        ),
        failure_details=failure_details,
        rollback_details=rollback_details,
    )


def sample_state() -> StateDocument:
    failed = deployment(
        "dep-failed",
        DeploymentStatus.FAILED,
        failure_details="Health check timed out",
    )
    rolled_back = deployment(
        "dep-rolled-back",
        DeploymentStatus.ROLLED_BACK,
        rollback_details="Restored version 2.4.0",
    )
    return StateDocument(
        schema_version=1,
        deployments=[failed, rolled_back],
        audit_events=[
            AuditEvent(
                event_id="event-001",
                deployment_id="dep-failed",
                event_type="creation",
                occurred_at=utc(9),
                actor="operator",
                reason=None,
                details={"application": "inventory-api"},
            ),
            AuditEvent(
                event_id="event-002",
                deployment_id="dep-failed",
                event_type="readiness_update",
                occurred_at=utc(10),
                actor="operator",
                reason="Test result recorded",
                details={
                    "check": "test-result",
                    "evidence_refs": ["evidence/final-generation/test-results.txt"],
                },
            ),
            AuditEvent(
                event_id="event-003",
                deployment_id="dep-failed",
                event_type="human_decision",
                occurred_at=utc(10),
                actor="reviewer",
                reason="Readiness evidence reviewed",
                details={"decision": "ACCEPT"},
            ),
            AuditEvent(
                event_id="event-004",
                deployment_id="dep-failed",
                event_type="failure",
                occurred_at=utc(11),
                actor="operator",
                reason="Health check failed",
                details={"failure_details": "Health check timed out"},
            ),
            AuditEvent(
                event_id="event-005",
                deployment_id="dep-rolled-back",
                event_type="rollback",
                occurred_at=utc(11),
                actor="operator",
                reason="Rollback required",
                details={"rollback_details": "Restored version 2.4.0"},
            ),
        ],
    )


class PersistenceRoundTripTests(unittest.TestCase):
    def test_save_and_reload_preserves_records_checks_decisions_and_audit_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = JsonStore(Path(directory) / "deployments.json")
            original = sample_state()

            store.save(original)
            reloaded = store.load()

            self.assertEqual(reloaded, original)
            self.assertEqual(
                {item.deployment_id for item in reloaded.deployments},
                {item.deployment_id for item in original.deployments},
            )
            self.assertEqual(
                [event.event_id for event in reloaded.audit_events],
                ["event-001", "event-002", "event-003", "event-004", "event-005"],
            )
            loaded_failed = next(item for item in reloaded.deployments if item.deployment_id == "dep-failed")
            loaded_rollback = next(item for item in reloaded.deployments if item.deployment_id == "dep-rolled-back")
            self.assertEqual(loaded_failed.failure_details, "Health check timed out")
            self.assertEqual(loaded_rollback.rollback_details, "Restored version 2.4.0")
            self.assertEqual(
                loaded_failed.readiness_checks["test-result"].evidence,
                "evidence://test-result",
            )
            self.assertEqual(loaded_failed.approval_decision.actor, "reviewer")
            self.assertEqual(loaded_failed.approval_decision.reason, "Readiness evidence reviewed")
            self.assertEqual(
                reloaded.audit_events[1].details["evidence_refs"],
                ["evidence/final-generation/test-results.txt"],
            )

    def test_pre_shutdown_and_post_restart_deployment_id_sets_match_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = JsonStore(Path(directory) / "deployments.json")
            before_shutdown = sample_state()
            expected_ids = {item.deployment_id for item in before_shutdown.deployments}

            store.save(before_shutdown)
            del store
            reloaded = JsonStore(Path(directory) / "deployments.json").load()
            actual_ids = {item.deployment_id for item in reloaded.deployments}

            self.assertEqual(actual_ids, expected_ids)
            self.assertEqual(len(actual_ids), len(expected_ids))


class StorageFailurePreservationTests(unittest.TestCase):
    def test_missing_store_loads_as_an_empty_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            state = JsonStore(Path(directory) / "missing.json").load()

            self.assertEqual(state.deployments, [])
            self.assertEqual(state.audit_events, [])

    def test_empty_and_malformed_files_are_rejected_without_modification(self) -> None:
        cases = (b"", b'{"schema_version":')
        for index, original_bytes in enumerate(cases):
            with self.subTest(index=index), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "invalid.json"
                path.write_bytes(original_bytes)

                with self.assertRaises(StorageError):
                    JsonStore(path).load()

                self.assertEqual(path.read_bytes(), original_bytes)

    def test_schema_invalid_document_is_rejected_without_modification(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            original_bytes = b'{"schema_version": 1, "deployments": [], "audit_events": "not-a-list"}'
            path.write_bytes(original_bytes)

            with self.assertRaises(StorageError):
                JsonStore(path).load()

            self.assertEqual(path.read_bytes(), original_bytes)

    def test_partially_invalid_record_set_is_rejected_as_a_whole(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "mixed.json"
            store = JsonStore(path)
            valid_state = sample_state()
            store.save(valid_state)
            document = json.loads(path.read_text(encoding="utf-8"))
            document["deployments"].append(
                {
                    "deployment_id": "invalid-record",
                    "application_name": " ",
                    "status": "NOT_A_STATUS",
                }
            )
            original_bytes = json.dumps(document, sort_keys=True).encode("utf-8")
            path.write_bytes(original_bytes)

            with self.assertRaises(StorageError):
                store.load()

            self.assertEqual(path.read_bytes(), original_bytes)

    def test_unsupported_schema_version_is_rejected_without_modification(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "future.json"
            document = {
                "schema_version": 999,
                "deployments": [],
                "audit_events": [],
            }
            original_bytes = json.dumps(document).encode("utf-8")
            path.write_bytes(original_bytes)

            with self.assertRaises(StorageError):
                JsonStore(path).load()

            self.assertEqual(path.read_bytes(), original_bytes)

    def test_failed_atomic_replacement_keeps_the_previous_valid_store_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "deployments.json"
            store = JsonStore(path)
            store.save(sample_state())
            original_bytes = path.read_bytes()

            with mock.patch(
                "cloudops_tracker.storage.os.replace",
                side_effect=OSError("simulated replacement failure"),
            ):
                with self.assertRaises(StorageError):
                    store.save(sample_state())

            self.assertEqual(path.read_bytes(), original_bytes)


if __name__ == "__main__":
    unittest.main()
