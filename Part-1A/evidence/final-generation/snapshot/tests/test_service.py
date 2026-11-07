from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from cloudops_tracker.domain import DeploymentStatus, StateDocument
from cloudops_tracker.service import DeploymentService
from cloudops_tracker.storage import JsonStore
from cloudops_tracker.domain import (
    CheckStatus,
    DecisionType,
    Deployment,
    HumanApprovalDecision,
    MANDATORY_CHECK_NAMES,
    ReadinessCheck,
)


class UserStory1ServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.store_path = Path(self.directory.name) / "deployments.json"
        self.store = JsonStore(self.store_path)
        self.id_counter = 0
        self.clock_hour = 8

        def next_id() -> str:
            self.id_counter += 1
            return f"deployment-{self.id_counter:03d}"

        def clock() -> datetime:
            self.clock_hour += 1
            return datetime(2026, 11, 7, 8, 0, tzinfo=timezone.utc) + timedelta(
                hours=self.clock_hour - 8
            )

        self.service = DeploymentService(
            self.store,
            id_generator=next_id,
            clock=clock,
        )

    def tearDown(self) -> None:
        self.directory.cleanup()

    def create_request(self, **overrides: str):
        fields = {
            "application_name": "inventory-api",
            "application_version": "2.4.1",
            "container_image": "registry.local/inventory-api:2.4.1",
            "environment": "Staging",
            "priority": "P2",
            "requester": "operator",
        }
        fields.update(overrides)
        return self.service.create_deployment(**fields)

    def test_creation_assigns_unique_id_utc_timestamps_draft_and_all_unchecked_gates(
        self,
    ) -> None:
        first = self.create_request()
        second = self.create_request(
            application_name="payments-api",
            application_version="1.0.0",
            container_image="registry.local/payments-api:1.0.0",
        )

        self.assertNotEqual(first.deployment_id, second.deployment_id)
        self.assertEqual(first.status, DeploymentStatus.DRAFT)
        self.assertEqual(first.created_at.tzinfo, timezone.utc)
        self.assertEqual(first.updated_at.tzinfo, timezone.utc)
        self.assertEqual(first.created_at, first.updated_at)
        self.assertEqual(len(first.readiness_checks), 8)
        for check in first.readiness_checks.values():
            self.assertEqual(check.status.value, "NOT_CHECKED")
            self.assertTrue(check.reason)
        creation_events = [
            event
            for event in self.store.load().audit_events
            if event.deployment_id == first.deployment_id
        ]
        self.assertEqual(len(creation_events), 1)
        self.assertEqual(creation_events[0].event_type.value, "creation")

    def test_creation_accepts_every_documented_environment_and_priority(self) -> None:
        for index, environment in enumerate(("Development", "Staging", "Production")):
            for priority in ("P1", "P2", "P3", "P4"):
                with self.subTest(environment=environment, priority=priority):
                    deployment = self.create_request(
                        application_name=f"app-{index}-{priority}",
                        application_version="1.0",
                        container_image=f"registry.local/app-{index}-{priority}:1.0",
                        environment=environment,
                        priority=priority,
                    )
                    self.assertEqual(deployment.environment.value, environment)
                    self.assertEqual(deployment.priority.value, priority)

    def test_invalid_required_fields_environment_and_priority_are_rejected(
        self,
    ) -> None:
        invalid_requests = (
            {"application_name": "  "},
            {"application_version": ""},
            {"container_image": " "},
            {"requester": "  "},
            {"environment": "Production-Blue"},
            {"priority": "P0"},
        )
        for overrides in invalid_requests:
            with self.subTest(overrides=overrides):
                with self.assertRaises((TypeError, ValueError)):
                    self.create_request(**overrides)
        self.assertEqual(self.store.load().deployments, [])
        self.assertEqual(self.store.load().audit_events, [])

    def test_duplicate_application_is_case_insensitive_and_version_sensitive(
        self,
    ) -> None:
        self.create_request(
            application_name=" Inventory-API ", application_version="2.4.1"
        )

        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.create_request(
                application_name="inventory-api", application_version="2.4.1"
            )

        case_distinct_version = self.create_request(
            application_name="inventory-api",
            application_version="2.4.1+Build",
            container_image="registry.local/inventory-api:2.4.1+Build",
        )
        self.assertEqual(case_distinct_version.application_version, "2.4.1+Build")

    def test_every_active_status_blocks_a_matching_duplicate(self) -> None:
        active_statuses = (
            DeploymentStatus.DRAFT,
            DeploymentStatus.VALIDATING,
            DeploymentStatus.BLOCKED,
            DeploymentStatus.APPROVED,
            DeploymentStatus.DEPLOYING,
        )
        for status in active_statuses:
            with (
                self.subTest(status=status),
                tempfile.TemporaryDirectory() as directory,
            ):
                store = JsonStore(Path(directory) / "deployments.json")
                service = DeploymentService(
                    store,
                    id_generator=lambda: f"new-{status.value.lower()}",
                )
                existing = service.create_deployment(
                    application_name=f"active-{status.value.lower()}",
                    application_version="1.0",
                    container_image=f"registry.local/active-{status.value.lower()}:1.0",
                    environment="Staging",
                    priority="P2",
                    requester="operator",
                )
                state = store.load()
                state.deployments[0] = replace(existing, status=status)
                store.save(state)
                service_for_store = DeploymentService(
                    store,
                    id_generator=lambda: f"duplicate-{status.value.lower()}",
                )
                with self.assertRaisesRegex(ValueError, "duplicate"):
                    service_for_store.create_deployment(
                        application_name=existing.application_name,
                        application_version=existing.application_version,
                        container_image=existing.container_image,
                        environment=existing.environment,
                        priority=existing.priority,
                        requester="operator",
                    )

    def test_lookup_list_filter_sort_and_hundred_retrievals_after_restart(self) -> None:
        records = []
        for priority, environment in (
            ("P3", "Staging"),
            ("P1", "Development"),
            ("P4", "Staging"),
            ("P2", "Staging"),
        ):
            records.append(
                self.create_request(
                    application_name=f"inventory-{priority}",
                    application_version="1.0",
                    container_image=f"registry.local/inventory-{priority}:1.0",
                    environment=environment,
                    priority=priority,
                )
            )

        restarted_service = DeploymentService(self.store)
        for _ in range(100):
            result = restarted_service.get_deployment(records[0].deployment_id)
            self.assertEqual(result, records[0])

        listed = restarted_service.list_deployments()
        self.assertEqual(len(listed), 4)
        self.assertEqual(
            [
                item.priority.value
                for item in restarted_service.list_deployments(sort_by_priority=True)
            ],
            ["P1", "P2", "P3", "P4"],
        )
        filtered = restarted_service.list_deployments(environment="Staging")
        self.assertEqual(len(filtered), 3)
        self.assertTrue(all(item.environment.value == "Staging" for item in filtered))

        with self.assertRaisesRegex(ValueError, "not found"):
            restarted_service.get_deployment("missing-id")

    def test_inactive_statuses_do_not_block_creation_for_the_same_identity(
        self,
    ) -> None:
        inactive_statuses = (
            DeploymentStatus.FAILED,
            DeploymentStatus.REJECTED,
            DeploymentStatus.DEPLOYED,
            DeploymentStatus.ROLLED_BACK,
        )
        for status in inactive_statuses:
            with (
                self.subTest(status=status),
                tempfile.TemporaryDirectory() as directory,
            ):
                store = JsonStore(Path(directory) / "deployments.json")
                service = DeploymentService(
                    store,
                    id_generator=lambda: f"original-{status.value.lower()}",
                )
                original = service.create_deployment(
                    application_name=f"inactive-{status.value.lower()}",
                    application_version="1.0",
                    container_image=f"registry.local/inactive-{status.value.lower()}:1.0",
                    environment="Staging",
                    priority="P2",
                    requester="operator",
                )

                details = {}
                if status is DeploymentStatus.FAILED:
                    details["failure_details"] = "Failure for duplicate fixture"
                elif status is DeploymentStatus.ROLLED_BACK:
                    details["rollback_details"] = "Rollback for duplicate fixture"
                updated = replace(original, status=status, **details)
                store.save(
                    StateDocument(
                        schema_version=1, deployments=[updated], audit_events=[]
                    )
                )
                replacement_service = DeploymentService(
                    store,
                    id_generator=lambda: f"replacement-{status.value.lower()}",
                )

                replacement = replacement_service.create_deployment(
                    application_name=original.application_name,
                    application_version=original.application_version,
                    container_image=original.container_image,
                    environment=original.environment,
                    priority=original.priority,
                    requester="operator",
                )
                self.assertNotEqual(replacement.deployment_id, original.deployment_id)
                self.assertEqual(replacement.status, DeploymentStatus.DRAFT)

    def test_metadata_updates_audit_changes_and_preserve_immutable_fields(
        self,
    ) -> None:
        original = self.create_request()
        updated = self.service.update_metadata(
            original.deployment_id,
            {"application_name": "inventory-api-v2", "priority": "P1"},
            actor="operator",
            reason="Application rename approved",
        )

        self.assertEqual(updated.deployment_id, original.deployment_id)
        self.assertEqual(updated.created_at, original.created_at)
        self.assertEqual(updated.application_name, "inventory-api-v2")
        self.assertEqual(updated.priority.value, "P1")
        self.assertGreater(updated.updated_at, original.updated_at)
        event = self.store.load().audit_events[-1]
        self.assertEqual(event.event_type.value, "metadata_update")
        self.assertEqual(event.reason, "Application rename approved")
        self.assertEqual(event.actor, "operator")
        self.assertEqual(
            event.details["old_values"]["application_name"], "inventory-api"
        )
        self.assertEqual(
            event.details["new_values"]["application_name"], "inventory-api-v2"
        )

        for immutable_update in (
            {"deployment_id": "changed-id"},
            {"created_at": original.created_at},
            {"unknown_field": "value"},
        ):
            with self.subTest(immutable_update=immutable_update):
                with self.assertRaises(ValueError):
                    self.service.update_metadata(
                        original.deployment_id,
                        immutable_update,
                        actor="operator",
                        reason="Invalid metadata change",
                    )
        persisted = self.service.get_deployment(original.deployment_id)
        self.assertEqual(persisted.deployment_id, original.deployment_id)
        self.assertEqual(persisted.created_at, original.created_at)

    def test_metadata_update_rejects_duplicate_and_invalid_values_without_mutation(
        self,
    ) -> None:
        first = self.create_request()
        second = self.create_request(
            application_name="payments-api",
            application_version="2.4.1",
            container_image="registry.local/payments-api:2.4.1",
        )
        event_count = len(self.store.load().audit_events)

        with self.assertRaisesRegex(ValueError, "duplicate"):
            self.service.update_metadata(
                second.deployment_id,
                {"application_name": first.application_name},
                actor="operator",
                reason="Attempt duplicate identity",
            )
        with self.assertRaises(ValueError):
            self.service.update_metadata(
                second.deployment_id,
                {"priority": "P0"},
                actor="operator",
                reason="Invalid priority",
            )

        self.assertEqual(self.service.get_deployment(second.deployment_id), second)
        self.assertEqual(len(self.store.load().audit_events), event_count)


class UserStory2ServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.store = JsonStore(Path(self.directory.name) / "deployments.json")
        self.id_counter = 0
        self.clock_minute = 0

        def next_id() -> str:
            self.id_counter += 1
            return f"us2-deployment-{self.id_counter:03d}"

        def clock() -> datetime:
            self.clock_minute += 1
            return datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc) + timedelta(
                minutes=self.clock_minute
            )

        self.service = DeploymentService(
            self.store,
            id_generator=next_id,
            clock=clock,
        )

    def tearDown(self) -> None:
        self.directory.cleanup()

    def create_request(self):
        return self.service.create_deployment(
            application_name=f"app-{self.id_counter}",
            application_version="1.0",
            container_image="registry.local/app:1.0",
            environment="Staging",
            priority="P2",
            requester="operator",
        )

    def set_all_checks_passing(self, deployment_id: str) -> None:
        for name in MANDATORY_CHECK_NAMES:
            self.service.set_readiness(
                deployment_id,
                check_name=name,
                status=CheckStatus.PASS,
                evidence=f"evidence://{name}",
                actor="operator",
                reason=f"{name} verified",
            )

    def put_deployment_in_state(
        self,
        deployment: Deployment,
        status: DeploymentStatus,
        *,
        include_accept: bool = True,
    ) -> None:
        details: dict[str, str] = {}
        decision = deployment.approval_decision
        if status is DeploymentStatus.FAILED:
            details["failure_details"] = "Failure fixture"
        elif status is DeploymentStatus.ROLLED_BACK:
            details["rollback_details"] = "Rollback fixture"
        if status in (DeploymentStatus.APPROVED, DeploymentStatus.DEPLOYING):
            checks = {
                name: ReadinessCheck(
                    check_name=name,
                    status=CheckStatus.PASS,
                    evidence=f"evidence://{name}",
                    reason=None,
                    updated_at=deployment.updated_at,
                )
                for name in MANDATORY_CHECK_NAMES
            }
            if include_accept:
                decision = HumanApprovalDecision(
                    decision=DecisionType.ACCEPT,
                    actor="reviewer",
                    decided_at=deployment.updated_at,
                    reason="Gate fixture accepted",
                )
        else:
            checks = deployment.readiness_checks
        replacement = Deployment(
            deployment_id=deployment.deployment_id,
            application_name=deployment.application_name,
            application_version=deployment.application_version,
            container_image=deployment.container_image,
            environment=deployment.environment,
            priority=deployment.priority,
            requester=deployment.requester,
            created_at=deployment.created_at,
            updated_at=deployment.updated_at,
            status=status,
            readiness_checks=checks,
            approval_decision=decision,
            failure_details=details.get("failure_details"),
            rollback_details=details.get("rollback_details"),
        )
        state = self.store.load()
        deployments = [
            replacement if item.deployment_id == deployment.deployment_id else item
            for item in state.deployments
        ]
        self.store.save(
            StateDocument(
                schema_version=state.schema_version,
                deployments=deployments,
                audit_events=state.audit_events,
            )
        )

    def test_approved_gate_rejects_each_missing_failed_unchecked_or_evidenceless_check(
        self,
    ) -> None:
        self.assertTrue(MANDATORY_CHECK_NAMES)
        for check_name in MANDATORY_CHECK_NAMES:
            for status in (CheckStatus.FAIL, CheckStatus.NOT_CHECKED):
                with self.subTest(check_name=check_name, status=status):
                    deployment = self.create_request()
                    self.set_all_checks_passing(deployment.deployment_id)
                    self.service.transition_status(
                        deployment.deployment_id,
                        target=DeploymentStatus.VALIDATING,
                        actor="operator",
                        reason="Begin validation",
                    )
                    self.service.set_readiness(
                        deployment.deployment_id,
                        check_name=check_name,
                        status=status,
                        reason=f"{check_name} did not pass",
                        actor="operator",
                    )
                    self.service.record_decision(
                        deployment.deployment_id,
                        decision=DecisionType.ACCEPT,
                        actor="reviewer",
                        reason="Approval gate test",
                    )
                    with self.assertRaisesRegex(ValueError, "readiness"):
                        self.service.transition_status(
                            deployment.deployment_id,
                            target=DeploymentStatus.APPROVED,
                            actor="operator",
                            reason="Attempt approval",
                        )
                    self.assertEqual(
                        self.service.get_deployment(deployment.deployment_id).status,
                        DeploymentStatus.VALIDATING,
                    )

        deployment = self.create_request()
        self.service.transition_status(
            deployment.deployment_id,
            target=DeploymentStatus.VALIDATING,
            actor="operator",
            reason="Begin validation",
        )
        self.service.record_decision(
            deployment.deployment_id,
            decision=DecisionType.ACCEPT,
            actor="reviewer",
            reason="Approval gate test",
        )
        with self.assertRaises(ValueError):
            self.service.transition_status(
                deployment.deployment_id,
                target=DeploymentStatus.APPROVED,
                actor="operator",
                reason="Attempt approval with missing checks",
            )
        with self.assertRaises(ValueError):
            self.service.set_readiness(
                deployment.deployment_id,
                check_name=MANDATORY_CHECK_NAMES[0],
                status=CheckStatus.PASS,
                evidence=" ",
                actor="operator",
                reason="Evidence is blank",
            )

    def test_approved_gate_requires_separate_accept_decision_after_all_checks_pass(
        self,
    ) -> None:
        deployment = self.create_request()
        self.set_all_checks_passing(deployment.deployment_id)
        self.service.transition_status(
            deployment.deployment_id,
            target=DeploymentStatus.VALIDATING,
            actor="operator",
            reason="Begin validation",
        )
        with self.assertRaisesRegex(ValueError, "ACCEPT"):
            self.service.transition_status(
                deployment.deployment_id,
                target=DeploymentStatus.APPROVED,
                actor="operator",
                reason="Attempt approval without decision",
            )
        self.service.record_decision(
            deployment.deployment_id,
            decision=DecisionType.ACCEPT,
            actor="reviewer",
            reason="Readiness reviewed",
        )
        approved = self.service.transition_status(
            deployment.deployment_id,
            target=DeploymentStatus.APPROVED,
            actor="operator",
            reason="Approval authorized",
        )
        self.assertEqual(approved.status, DeploymentStatus.APPROVED)

    def test_pass_evidence_can_omit_reason_but_nonpassing_results_cannot(self) -> None:
        deployment = self.create_request()
        self.service.set_readiness(
            deployment.deployment_id,
            check_name="test-result",
            status=CheckStatus.PASS,
            evidence="evidence://test-results",
            actor="operator",
        )
        event = self.store.load().audit_events[-1]
        self.assertEqual(event.reason, "Readiness check recorded as PASS")
        self.assertIn("evidence://test-results", str(event.details))

        with self.assertRaisesRegex(ValueError, "require a reason"):
            self.service.set_readiness(
                deployment.deployment_id,
                check_name="rollback-plan",
                status=CheckStatus.FAIL,
                actor="operator",
            )

    def test_approved_gate_blocks_missing_results_and_evidenceless_passes(
        self,
    ) -> None:
        for missing_name in MANDATORY_CHECK_NAMES:
            with self.subTest(missing_name=missing_name):
                deployment = self.create_request()
                for check_name in MANDATORY_CHECK_NAMES:
                    if check_name != missing_name:
                        self.service.set_readiness(
                            deployment.deployment_id,
                            check_name=check_name,
                            status=CheckStatus.PASS,
                            evidence=f"evidence://{check_name}",
                            actor="operator",
                            reason=f"{check_name} verified",
                        )
                self.service.transition_status(
                    deployment.deployment_id,
                    target=DeploymentStatus.VALIDATING,
                    actor="operator",
                    reason="Begin validation",
                )
                self.service.record_decision(
                    deployment.deployment_id,
                    decision=DecisionType.ACCEPT,
                    actor="reviewer",
                    reason="Gate test",
                )
                with self.assertRaisesRegex(ValueError, "readiness"):
                    self.service.transition_status(
                        deployment.deployment_id,
                        target=DeploymentStatus.APPROVED,
                        actor="operator",
                        reason="Attempt approval with missing check result",
                    )

        for check_name in MANDATORY_CHECK_NAMES:
            with self.subTest(evidenceless_pass=check_name):
                deployment = self.create_request()
                for other_name in MANDATORY_CHECK_NAMES:
                    if other_name != check_name:
                        self.service.set_readiness(
                            deployment.deployment_id,
                            check_name=other_name,
                            status=CheckStatus.PASS,
                            evidence=f"evidence://{other_name}",
                            actor="operator",
                            reason=f"{other_name} verified",
                        )
                with self.assertRaises(ValueError):
                    self.service.set_readiness(
                        deployment.deployment_id,
                        check_name=check_name,
                        status=CheckStatus.PASS,
                        evidence=None,
                        actor="operator",
                        reason="Evidence is absent",
                    )
                self.service.transition_status(
                    deployment.deployment_id,
                    target=DeploymentStatus.VALIDATING,
                    actor="operator",
                    reason="Begin validation",
                )
                self.service.record_decision(
                    deployment.deployment_id,
                    decision=DecisionType.ACCEPT,
                    actor="reviewer",
                    reason="Gate test",
                )
                with self.assertRaisesRegex(ValueError, "readiness"):
                    self.service.transition_status(
                        deployment.deployment_id,
                        target=DeploymentStatus.APPROVED,
                        actor="operator",
                        reason="Attempt approval with missing evidence",
                    )

    def test_deploying_gate_rejects_each_missing_failed_unchecked_or_evidenceless_check(
        self,
    ) -> None:
        for check_name in MANDATORY_CHECK_NAMES:
            for status in (CheckStatus.FAIL, CheckStatus.NOT_CHECKED):
                with self.subTest(check_name=check_name, status=status):
                    deployment = self.create_request()
                    self.put_deployment_in_state(
                        deployment,
                        DeploymentStatus.APPROVED,
                        include_accept=False,
                    )
                    self.service.set_readiness(
                        deployment.deployment_id,
                        check_name=check_name,
                        status=status,
                        reason=f"{check_name} did not pass",
                        actor="operator",
                    )
                    with self.assertRaisesRegex(ValueError, "readiness"):
                        self.service.transition_status(
                            deployment.deployment_id,
                            target=DeploymentStatus.DEPLOYING,
                            actor="operator",
                            reason="Attempt simulated deployment",
                        )
                    self.assertEqual(
                        self.service.get_deployment(deployment.deployment_id).status,
                        DeploymentStatus.APPROVED,
                    )

        deployment = self.create_request()
        self.put_deployment_in_state(
            deployment,
            DeploymentStatus.APPROVED,
            include_accept=False,
        )
        self.service.transition_status(
            deployment.deployment_id,
            target=DeploymentStatus.DEPLOYING,
            actor="operator",
            reason="All checks allow simulated deployment",
        )
        self.assertEqual(
            self.service.get_deployment(deployment.deployment_id).status,
            DeploymentStatus.DEPLOYING,
        )

    def test_final_reject_matches_allowed_and_disallowed_transitions_for_all_statuses(
        self,
    ) -> None:
        allowed = {
            DeploymentStatus.DRAFT,
            DeploymentStatus.VALIDATING,
            DeploymentStatus.BLOCKED,
            DeploymentStatus.APPROVED,
        }
        self.assertEqual(len(DeploymentStatus), 9)
        for status in DeploymentStatus:
            with self.subTest(status=status):
                deployment = self.create_request()
                self.put_deployment_in_state(deployment, status)
                before = self.store.load()
                before_deployment = next(
                    item
                    for item in before.deployments
                    if item.deployment_id == deployment.deployment_id
                )
                before_events = [
                    event
                    for event in before.audit_events
                    if event.deployment_id == deployment.deployment_id
                ]

                if status in allowed:
                    self.service.record_decision(
                        deployment.deployment_id,
                        decision=DecisionType.REJECT,
                        actor="reviewer",
                        reason="Final rejection",
                    )
                    after = self.store.load()
                    rejected = next(
                        item
                        for item in after.deployments
                        if item.deployment_id == deployment.deployment_id
                    )
                    decision_events = [
                        event
                        for event in after.audit_events
                        if event.deployment_id == deployment.deployment_id
                        and event.event_type.value == "human_decision"
                    ]
                    self.assertEqual(rejected.status, DeploymentStatus.REJECTED)
                    self.assertEqual(
                        rejected.approval_decision.decision, DecisionType.REJECT
                    )
                    self.assertEqual(len(decision_events), 1)
                    self.assertEqual(decision_events[0].reason, "Final rejection")
                else:
                    with self.assertRaises(ValueError):
                        self.service.record_decision(
                            deployment.deployment_id,
                            decision=DecisionType.REJECT,
                            actor="reviewer",
                            reason="Disallowed final rejection",
                        )
                    after = self.store.load()
                    after_deployment = next(
                        item
                        for item in after.deployments
                        if item.deployment_id == deployment.deployment_id
                    )
                    after_events = [
                        event
                        for event in after.audit_events
                        if event.deployment_id == deployment.deployment_id
                    ]
                    self.assertEqual(after_deployment, before_deployment)
                    self.assertEqual(after_deployment.status, status)
                    self.assertEqual(
                        after_deployment.approval_decision,
                        before_deployment.approval_decision,
                    )
                    self.assertEqual(after_events, before_events)
                    self.assertFalse(
                        any(
                            event.event_type.value == "human_decision"
                            for event in after_events
                        )
                    )


class ServiceAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.store = JsonStore(Path(self.directory.name) / "deployments.json")
        self._id = 0
        self._minute = 0

        def next_id() -> str:
            self._id += 1
            return f"dep-{self._id:03d}"

        def clock() -> datetime:
            self._minute += 1
            return datetime(2026, 11, 7, 9, 0, tzinfo=timezone.utc) + timedelta(
                minutes=self._minute
            )

        self.service = DeploymentService(
            self.store,
            id_generator=next_id,
            clock=clock,
        )

    def tearDown(self) -> None:
        self.directory.cleanup()

    def create_request(self) -> str:
        deployment = self.service.create_deployment(
            application_name="inventory-api",
            application_version="2.4.1",
            container_image="registry.local/inventory-api:2.4.1",
            environment="Staging",
            priority="P1",
            requester="operator",
        )
        return deployment.deployment_id

    def events_for(self, deployment_id: str):
        state = self.store.load()
        return [
            event
            for event in state.audit_events
            if event.deployment_id == deployment_id
        ]

    def assert_utc_timestamp(self, value: datetime) -> None:
        self.assertIsNotNone(value.tzinfo)
        self.assertEqual(value.utcoffset(), timezone.utc.utcoffset(value))

    def test_creation_metadata_readiness_and_status_changes_create_auditable_events(
        self,
    ) -> None:
        deployment_id = self.create_request()
        created_events = self.events_for(deployment_id)
        self.assertEqual([event.event_type for event in created_events], ["creation"])
        self.assert_utc_timestamp(created_events[0].occurred_at)

        self.service.update_metadata(
            deployment_id,
            {"requester": "release-operator"},
            actor="operator",
            reason="Corrected requester label",
        )
        metadata_event = self.events_for(deployment_id)[-1]
        self.assertEqual(metadata_event.event_type, "metadata_update")
        self.assertEqual(metadata_event.reason, "Corrected requester label")
        self.assertEqual(metadata_event.actor, "operator")
        self.assertIn("old_values", metadata_event.details)
        self.assertIn("new_values", metadata_event.details)
        self.assert_utc_timestamp(metadata_event.occurred_at)

        evidence_ref = "evidence/initial-generation/test-results.txt"
        self.service.set_readiness(
            deployment_id,
            check_name="test-result",
            status="PASS",
            evidence=evidence_ref,
            actor="operator",
            reason="Required test suite passed",
        )
        readiness_event = self.events_for(deployment_id)[-1]
        self.assertEqual(readiness_event.event_type, "readiness_update")
        self.assertEqual(readiness_event.reason, "Required test suite passed")
        self.assertIn(evidence_ref, str(readiness_event.details))
        self.assert_utc_timestamp(readiness_event.occurred_at)

        self.service.transition_status(
            deployment_id,
            target=DeploymentStatus.VALIDATING,
            actor="operator",
            reason="Begin validation",
        )
        transition_event = self.events_for(deployment_id)[-1]
        self.assertEqual(transition_event.event_type, "status_transition")
        self.assertEqual(transition_event.reason, "Begin validation")
        self.assertEqual(transition_event.actor, "operator")
        self.assert_utc_timestamp(transition_event.occurred_at)
        self.assertEqual(
            self.store.load().deployments[0].status,
            DeploymentStatus.VALIDATING,
        )

    def test_accept_decision_is_separate_audited_evidence_before_approved_status(
        self,
    ) -> None:
        deployment_id = self.create_request()
        self.service.record_decision(
            deployment_id,
            decision="ACCEPT",
            actor="reviewer",
            reason="Reviewed readiness evidence",
        )

        state = self.store.load()
        deployment = state.deployments[0]
        decision_events = [
            event
            for event in state.audit_events
            if event.event_type == "human_decision"
        ]
        self.assertEqual(deployment.status, DeploymentStatus.DRAFT)
        self.assertEqual(deployment.approval_decision.decision, "ACCEPT")
        self.assertEqual(len(decision_events), 1)
        self.assertEqual(decision_events[0].actor, "reviewer")
        self.assertEqual(decision_events[0].reason, "Reviewed readiness evidence")
        self.assert_utc_timestamp(decision_events[0].occurred_at)

    def test_allowed_and_disallowed_reject_decisions_have_atomic_audit_behavior(
        self,
    ) -> None:
        allowed_id = self.create_request()
        self.service.record_decision(
            allowed_id,
            decision="REJECT",
            actor="reviewer",
            reason="Risk identified",
        )
        allowed_state = self.store.load()
        allowed_deployment = next(
            item
            for item in allowed_state.deployments
            if item.deployment_id == allowed_id
        )
        self.assertEqual(allowed_deployment.status, DeploymentStatus.REJECTED)
        self.assertEqual(allowed_deployment.approval_decision.decision, "REJECT")
        self.assertEqual(
            sum(
                event.event_type == "human_decision"
                for event in allowed_state.audit_events
            ),
            1,
        )

        disallowed_id = self.create_request()
        for check_name in (
            "application-version",
            "container-image",
            "image-tag-not-latest",
            "resource-configuration",
            "health-probes",
            "test-result",
            "human-approval",
            "rollback-plan",
        ):
            self.service.set_readiness(
                disallowed_id,
                check_name=check_name,
                status="PASS",
                evidence=f"evidence://{check_name}",
                actor="operator",
                reason=f"{check_name} verified",
            )
        self.service.record_decision(
            disallowed_id,
            decision="ACCEPT",
            actor="reviewer",
            reason="All mandatory checks reviewed",
        )
        self.service.transition_status(
            disallowed_id,
            target=DeploymentStatus.VALIDATING,
            actor="operator",
            reason="Begin validation",
        )
        self.service.transition_status(
            disallowed_id,
            target=DeploymentStatus.APPROVED,
            actor="operator",
            reason="Test disallowed decision state",
        )
        self.service.transition_status(
            disallowed_id,
            target=DeploymentStatus.DEPLOYING,
            actor="operator",
            reason="Begin simulated deployment",
        )
        before_state = self.store.load()
        before_deployment = next(
            item
            for item in before_state.deployments
            if item.deployment_id == disallowed_id
        )
        before_events = [
            event
            for event in before_state.audit_events
            if event.deployment_id == disallowed_id
        ]

        with self.assertRaises(ValueError):
            self.service.record_decision(
                disallowed_id,
                decision="REJECT",
                actor="reviewer",
                reason="Reject after deployment began",
            )

        after_state = self.store.load()
        after_deployment = next(
            item
            for item in after_state.deployments
            if item.deployment_id == disallowed_id
        )
        after_events = [
            event
            for event in after_state.audit_events
            if event.deployment_id == disallowed_id
        ]
        self.assertEqual(after_deployment, before_deployment)
        self.assertEqual(after_deployment.status, DeploymentStatus.DEPLOYING)
        self.assertEqual(
            after_deployment.approval_decision, before_deployment.approval_decision
        )
        self.assertEqual(after_events, before_events)
        self.assertEqual(
            sum(event.event_type == "human_decision" for event in after_events),
            sum(event.event_type == "human_decision" for event in before_events),
        )

    def test_failure_and_rollback_record_details_reasons_and_timestamped_events(
        self,
    ) -> None:
        deployment_id = self.create_request()
        self.service.transition_status(
            deployment_id,
            target=DeploymentStatus.VALIDATING,
            actor="operator",
            reason="Begin validation",
        )
        self.service.transition_status(
            deployment_id,
            target=DeploymentStatus.FAILED,
            actor="operator",
            reason="Health probe failed",
            failure_details="Readiness endpoint timed out",
        )
        failure_event = self.events_for(deployment_id)[-1]
        self.assertEqual(failure_event.event_type, "failure")
        self.assertEqual(failure_event.reason, "Health probe failed")
        self.assertIn("Readiness endpoint timed out", str(failure_event.details))
        self.assert_utc_timestamp(failure_event.occurred_at)

        self.service.transition_status(
            deployment_id,
            target=DeploymentStatus.ROLLED_BACK,
            actor="operator",
            reason="Restore last known good version",
            rollback_details="Restored version 2.4.0",
        )
        rollback_event = self.events_for(deployment_id)[-1]
        self.assertEqual(rollback_event.event_type, "rollback")
        self.assertEqual(rollback_event.reason, "Restore last known good version")
        self.assertIn("Restored version 2.4.0", str(rollback_event.details))
        self.assert_utc_timestamp(rollback_event.occurred_at)
        self.assertEqual(
            self.store.load().deployments[0].status,
            DeploymentStatus.ROLLED_BACK,
        )


if __name__ == "__main__":
    unittest.main()
