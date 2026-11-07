from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import re
import tempfile
import unittest

from cloudops_tracker.cli import main
from cloudops_tracker.domain import (
    CheckStatus,
    DecisionType,
    DeploymentStatus,
    MANDATORY_CHECK_NAMES,
)
from cloudops_tracker.service import DeploymentService
from cloudops_tracker.storage import JsonStore


class CliTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.store_path = self.root / "state.json"

    def tearDown(self) -> None:
        self.directory.cleanup()

    def invoke(self, *arguments: str) -> tuple[int, str, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = main(["--store", str(self.store_path), "deploy", *arguments])
        return result, stdout.getvalue(), stderr.getvalue()

    def create_args(
        self,
        *,
        application: str = "inventory-api",
        version: str = "2.4.1",
        environment: str = "Staging",
        priority: str = "P2",
    ) -> tuple[str, ...]:
        return (
            "create",
            "--application",
            application,
            "--version",
            version,
            "--image",
            f"registry.local/{application}:{version}",
            "--environment",
            environment,
            "--priority",
            priority,
            "--requester",
            "operator",
        )

    def create_deployment_id(self, **overrides: str) -> str:
        code, stdout, stderr = self.invoke(*self.create_args(**overrides))
        self.assertEqual(code, 0, stderr)
        match = re.search(r"Created deployment:\s*(\S+)", stdout)
        self.assertIsNotNone(match, stdout)
        return match.group(1)

    def make_deploying_record(self) -> str:
        store = JsonStore(self.store_path)
        service = DeploymentService(store)
        deployment = service.create_deployment(
            application_name="deployment-gate",
            application_version="1.0",
            container_image="registry.local/deployment-gate:1.0",
            environment="Staging",
            priority="P2",
            requester="operator",
        )
        for check_name in MANDATORY_CHECK_NAMES:
            service.set_readiness(
                deployment.deployment_id,
                check_name=check_name,
                status=CheckStatus.PASS,
                evidence=f"evidence://{check_name}",
                actor="operator",
                reason=f"{check_name} verified",
            )
        service.record_decision(
            deployment.deployment_id,
            decision=DecisionType.ACCEPT,
            actor="reviewer",
            reason="Readiness accepted",
        )
        service.transition_status(
            deployment.deployment_id,
            target=DeploymentStatus.VALIDATING,
            actor="operator",
            reason="Begin validation",
        )
        service.transition_status(
            deployment.deployment_id,
            target=DeploymentStatus.APPROVED,
            actor="operator",
            reason="Checks passed",
        )
        service.transition_status(
            deployment.deployment_id,
            target=DeploymentStatus.DEPLOYING,
            actor="operator",
            reason="Start simulated deployment",
        )
        return deployment.deployment_id


class CliAcceptanceMatrixTests(CliTestCase):
    def test_fixed_twenty_case_cli_acceptance_matrix(self) -> None:
        cases: list[tuple[str, tuple[str, ...], int, str, str, str]] = []
        observed: dict[str, tuple[int, str, str]] = {}

        code, stdout, stderr = self.invoke(*self.create_args())
        observed["C01"] = (code, stdout, stderr)
        cases.append(("C01", self.create_args(), 0, "stdout", "Created deployment", ""))
        self.assertEqual(code, 0, stderr)
        deployment_id_match = re.search(r"Created deployment:\s*(\S+)", stdout)
        self.assertIsNotNone(deployment_id_match, stdout)
        deployment_id = deployment_id_match.group(1)

        self.create_deployment_id(application="priority-api", version="1.0", priority="P1")
        view_args = ("view", deployment_id)
        cases.append(("C02", view_args, 0, "stdout", "Deployment ID", ""))

        list_args = ("list",)
        cases.append(("C03", list_args, 0, "stdout", deployment_id, ""))
        filter_args = ("list", "--environment", "Staging")
        cases.append(("C04", filter_args, 0, "stdout", "Staging", ""))
        sort_args = ("list", "--sort", "priority")
        cases.append(("C05", sort_args, 0, "stdout", "P1", "P2"))

        update_args = ("update", deployment_id, "--requester", "release-operator", "--reason", "Correct requester")
        cases.append(("C06", update_args, 0, "stdout", "updated", ""))
        readiness_show_args = ("readiness", "show", deployment_id)
        cases.append(("C07", readiness_show_args, 0, "stdout", "rollback-plan", ""))
        readiness_set_args = (
            "readiness",
            "set",
            deployment_id,
            "--check",
            "test-result",
            "--status",
            "PASS",
            "--evidence",
            "evidence://tests",
        )
        cases.append(("C08", readiness_set_args, 0, "stdout", "readiness", "PASS"))
        human_approval_args = (
            "readiness",
            "set",
            deployment_id,
            "--check",
            "human-approval",
            "--status",
            "PASS",
            "--evidence",
            "evidence://team-approval",
        )
        cases.append(("C09", human_approval_args, 0, "stdout", "human-approval", "PASS"))
        accept_args = ("approval", deployment_id, "--decision", "ACCEPT", "--actor", "reviewer", "--reason", "Reviewed evidence")
        cases.append(("C10", accept_args, 0, "stdout", "ACCEPT", "recorded"))

        invalid_environment = self.create_args(application="bad-environment", environment="Production-Blue")
        cases.append(("C11", invalid_environment, 2, "stderr", "Development", "Production"))
        invalid_priority = self.create_args(application="bad-priority", priority="P0")
        cases.append(("C12", invalid_priority, 2, "stderr", "P1", "P4"))

        missing_view = ("view", "missing-deployment")
        cases.append(("C13", missing_view, 1, "stderr", "not found", ""))
        duplicate = self.create_args()
        cases.append(("C14", duplicate, 1, "stderr", "duplicate", ""))
        invalid_transition = ("status", deployment_id, "--to", "DEPLOYED", "--reason", "Invalid direct deployment")
        cases.append(("C15", invalid_transition, 1, "stderr", "transition", ""))
        missing_evidence = (
            "readiness",
            "set",
            deployment_id,
            "--check",
            "resource-configuration",
            "--status",
            "PASS",
        )
        cases.append(("C16", missing_evidence, 1, "stderr", "evidence", ""))
        begin_validation = ("status", deployment_id, "--to", "VALIDATING", "--reason", "Begin validation")
        self.assertEqual(self.invoke(*begin_validation)[0], 0)
        incomplete_approval = ("status", deployment_id, "--to", "APPROVED", "--reason", "Attempt approval")
        cases.append(("C17", incomplete_approval, 1, "stderr", "readiness", ""))

        corrupt_path = self.root / "corrupt.json"
        corrupt_bytes = b'{"schema_version": 1, "deployments": ['
        corrupt_path.write_bytes(corrupt_bytes)
        original_store = self.store_path
        self.store_path = corrupt_path
        corrupt_state = ("list",)
        observed["C18"] = self.invoke(*corrupt_state)
        cases.append(("C18", corrupt_state, 1, "stderr", "invalid state", ""))
        self.store_path = original_store
        self.assertEqual(corrupt_path.read_bytes(), corrupt_bytes)

        missing_reason = ("update", deployment_id, "--requester", "someone")
        cases.append(("C19", missing_reason, 2, "stderr", "reason", "required"))
        reject_args = ("approval", deployment_id, "--decision", "REJECT", "--actor", "reviewer", "--reason", "Risk identified")
        cases.append(("C20", reject_args, 0, "stdout", "REJECT", "recorded"))

        self.assertEqual(len(cases), 20)
        passed = 0
        failures: list[str] = []
        for case_id, arguments, expected_code, stream, marker_a, marker_b in cases:
            with self.subTest(case=case_id):
                if case_id in observed:
                    actual_code, actual_stdout, actual_stderr = observed[case_id]
                else:
                    actual_code, actual_stdout, actual_stderr = self.invoke(*arguments)
                actual_stream = actual_stdout if stream == "stdout" else actual_stderr
                passed_case = actual_code == expected_code and marker_a.casefold() in actual_stream.casefold()
                if marker_b:
                    passed_case = passed_case and marker_b.casefold() in actual_stream.casefold()
                if case_id == "C05":
                    p1 = actual_stdout.find("P1")
                    p2 = actual_stdout.find("P2")
                    passed_case = passed_case and p1 >= 0 and p2 >= 0 and p1 < p2
                if case_id == "C07":
                    passed_case = passed_case and all(
                        name in actual_stdout for name in MANDATORY_CHECK_NAMES
                    )
                if case_id == "C17":
                    passed_case = passed_case and "application-version" in actual_stderr
                if not passed_case:
                    failures.append(
                        f"{case_id}: exit={actual_code}, stdout={actual_stdout!r}, stderr={actual_stderr!r}"
                    )
                passed += int(passed_case)

        score = passed / len(cases) * 100
        self.assertGreaterEqual(score, 95, "\n".join(failures))


class CliValidationTests(CliTestCase):
    def test_all_documented_commands_accept_store_selection_and_service_inputs(self) -> None:
        deployment_id = self.create_deployment_id()
        commands = (
            ("view", deployment_id),
            ("list", "--environment", "Staging", "--sort", "priority"),
            ("update", deployment_id, "--application", "inventory-api", "--reason", "Metadata reason"),
            ("readiness", "show", deployment_id),
            (
                "readiness",
                "set",
                deployment_id,
                "--check",
                "test-result",
                "--status",
                "FAIL",
                "--reason",
                "Tests failed",
            ),
            ("approval", deployment_id, "--decision", "ACCEPT", "--actor", "reviewer", "--reason", "Decision"),
            (
                "status",
                deployment_id,
                "--to",
                "VALIDATING",
                "--reason",
                "Begin validation",
            ),
        )
        for arguments in commands:
            with self.subTest(command=arguments):
                code, _, stderr = self.invoke(*arguments)
                self.assertEqual(code, 0, stderr)

    def test_approved_status_requires_final_accept_separate_from_human_approval_evidence(self) -> None:
        deployment_id = self.create_deployment_id()
        for check_name in MANDATORY_CHECK_NAMES:
            code, _, stderr = self.invoke(
                "readiness",
                "set",
                deployment_id,
                "--check",
                check_name,
                "--status",
                "PASS",
                "--evidence",
                f"evidence://{check_name}",
            )
            self.assertEqual(code, 0, stderr)

        code, stdout, stderr = self.invoke("readiness", "show", deployment_id)
        self.assertEqual(code, 0, stderr)
        self.assertIn("APPROVED readiness gate eligible: no", stdout)
        self.assertIn("DEPLOYING readiness gate eligible: yes", stdout)
        self.assertIn("final-operator-ACCEPT", stdout)

        code, _, stderr = self.invoke(
            "status",
            deployment_id,
            "--to",
            "VALIDATING",
            "--reason",
            "Begin validation",
        )
        self.assertEqual(code, 0, stderr)

        code, _, stderr = self.invoke(
            "status",
            deployment_id,
            "--to",
            "APPROVED",
            "--reason",
            "Attempt approval without final decision",
        )
        self.assertNotEqual(code, 0)
        self.assertIn("accept", stderr.lower())

        code, stdout, stderr = self.invoke(
            "approval",
            deployment_id,
            "--decision",
            "ACCEPT",
            "--actor",
            "reviewer",
            "--reason",
            "Reviewed all readiness evidence",
        )
        self.assertEqual(code, 0, stderr)
        self.assertIn("ACCEPT", stdout)
        self.assertIn("recorded", stdout)

        code, _, stderr = self.invoke(
            "status",
            deployment_id,
            "--to",
            "APPROVED",
            "--reason",
            "All gates passed",
        )
        self.assertEqual(code, 0, stderr)

    def test_view_displays_exact_failure_and_rollback_details(self) -> None:
        service = DeploymentService(JsonStore(self.store_path))
        failed = service.create_deployment(
            application_name="failed-app",
            application_version="1.0",
            container_image="registry.local/failed-app:1.0",
            environment="Staging",
            priority="P2",
            requester="operator",
        )
        service.transition_status(
            failed.deployment_id,
            target=DeploymentStatus.VALIDATING,
            actor="operator",
            reason="Validate",
        )
        service.transition_status(
            failed.deployment_id,
            target=DeploymentStatus.FAILED,
            actor="operator",
            reason="Health check failed",
            failure_details="Exact failure detail: readiness endpoint timed out.",
        )
        rolled_back = service.create_deployment(
            application_name="rollback-app",
            application_version="1.0",
            container_image="registry.local/rollback-app:1.0",
            environment="Staging",
            priority="P2",
            requester="operator",
        )
        service.transition_status(
            rolled_back.deployment_id,
            target=DeploymentStatus.VALIDATING,
            actor="operator",
            reason="Validate",
        )
        service.transition_status(
            rolled_back.deployment_id,
            target=DeploymentStatus.FAILED,
            actor="operator",
            reason="Failure before rollback",
            failure_details="Initial failure",
        )
        service.transition_status(
            rolled_back.deployment_id,
            target=DeploymentStatus.ROLLED_BACK,
            actor="operator",
            reason="Restore previous version",
            rollback_details="Exact rollback detail: restored version 0.9.9.",
        )

        failure_code, failure_stdout, failure_stderr = self.invoke("view", failed.deployment_id)
        rollback_code, rollback_stdout, rollback_stderr = self.invoke("view", rolled_back.deployment_id)
        self.assertEqual(failure_code, 0, failure_stderr)
        self.assertEqual(rollback_code, 0, rollback_stderr)
        self.assertIn("Exact failure detail: readiness endpoint timed out.", failure_stdout)
        self.assertIn("Exact rollback detail: restored version 0.9.9.", rollback_stdout)

    def test_disallowed_reject_during_deploying_preserves_store_and_audit(self) -> None:
        deployment_id = self.make_deploying_record()
        before_bytes = self.store_path.read_bytes()
        before_state = JsonStore(self.store_path).load()

        code, _, stderr = self.invoke(
            "approval",
            deployment_id,
            "--decision",
            "REJECT",
            "--actor",
            "reviewer",
            "--reason",
            "Reject after deployment began",
        )

        after_state = JsonStore(self.store_path).load()
        self.assertNotEqual(code, 0)
        self.assertIn("transition", stderr.lower())
        self.assertEqual(after_state, before_state)
        self.assertEqual(self.store_path.read_bytes(), before_bytes)

    def test_failed_cli_mutations_preserve_the_snapshot(self) -> None:
        deployment_id = self.create_deployment_id()
        before = self.store_path.read_bytes()
        code, _, stderr = self.invoke(
            "readiness",
            "set",
            deployment_id,
            "--check",
            "test-result",
            "--status",
            "PASS",
        )
        self.assertNotEqual(code, 0)
        self.assertIn("evidence", stderr.lower())
        self.assertEqual(self.store_path.read_bytes(), before)

    def test_corrupt_json_is_not_overwritten(self) -> None:
        invalid_bytes = b'{"schema_version": 1, "deployments": "invalid", "audit_events": []}'
        self.store_path.write_bytes(invalid_bytes)
        code, _, stderr = self.invoke("list")
        self.assertNotEqual(code, 0)
        self.assertIn("invalid state", stderr.lower())
        self.assertEqual(self.store_path.read_bytes(), invalid_bytes)


if __name__ == "__main__":
    unittest.main()
