from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import importlib.util
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / ".harness" / "run_harness.py"
SPEC = importlib.util.spec_from_file_location("cloudops_harness_runner", RUNNER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Could not load harness runner at {RUNNER_PATH}")
RUNNER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = RUNNER
SPEC.loader.exec_module(RUNNER)


def passing_results() -> dict[str, dict[str, object]]:
    return {name: {"status": "PASS", "exit_code": 0} for name in RUNNER.REQUIRED_CHECKS}


def valid_junit_report(identity: str = "sample::expected") -> str:
    classname, name = identity.split("::", maxsplit=1)
    return (
        '<testsuites><testsuite tests="1" failures="0" errors="0" skipped="0">'
        f'<testcase classname="{classname}" name="{name}"/>'
        "</testsuite></testsuites>"
    )


class HarnessAggregationTests(unittest.TestCase):
    def test_all_required_successful_checks_and_nonempty_pytest_collection_pass(
        self,
    ) -> None:
        passed, problems = RUNNER.aggregate_results(
            passing_results(),
            RUNNER.PytestMetrics(collected=54, failures=0, errors=0, skipped=0),
        )

        self.assertTrue(passed)
        self.assertEqual(problems, [])

    def test_missing_check_fails_closed(self) -> None:
        results = passing_results()
        del results["bandit"]

        passed, problems = RUNNER.aggregate_results(
            results,
            RUNNER.PytestMetrics(collected=1, failures=0, errors=0, skipped=0),
        )

        self.assertFalse(passed)
        self.assertTrue(
            any("Missing mandatory checks: bandit" in item for item in problems)
        )

    def test_nonzero_command_exit_fails_closed(self) -> None:
        results = passing_results()
        results["ruff"] = {"status": "FAIL", "exit_code": 1}

        passed, problems = RUNNER.aggregate_results(
            results,
            RUNNER.PytestMetrics(collected=1, failures=0, errors=0, skipped=0),
        )

        self.assertFalse(passed)
        self.assertIn("ruff did not pass", problems)

    def test_skipped_or_empty_pytest_collection_fails_closed(self) -> None:
        for metrics in (
            RUNNER.PytestMetrics(collected=2, failures=0, errors=0, skipped=1),
            RUNNER.PytestMetrics(collected=0, failures=0, errors=0, skipped=0),
        ):
            with self.subTest(metrics=metrics):
                passed, problems = RUNNER.aggregate_results(passing_results(), metrics)
                self.assertFalse(passed)
                self.assertTrue(problems)

    def test_failed_tests_and_unavailable_pytest_metrics_fail_closed(self) -> None:
        for metrics in (
            RUNNER.PytestMetrics(collected=3, failures=1, errors=0, skipped=0),
            None,
        ):
            with self.subTest(metrics=metrics):
                passed, problems = RUNNER.aggregate_results(passing_results(), metrics)
                self.assertFalse(passed)
                self.assertTrue(problems)

    def test_unexpected_check_result_fails_closed(self) -> None:
        results = passing_results()
        results["extra"] = {"status": "PASS", "exit_code": 0}

        passed, problems = RUNNER.aggregate_results(
            results,
            RUNNER.PytestMetrics(collected=1, failures=0, errors=0, skipped=0),
        )

        self.assertFalse(passed)
        self.assertIn("Unexpected check results: extra", problems)

    def test_junit_parser_counts_cases_and_skips_from_actual_report(self) -> None:
        report = """<?xml version="1.0"?>
<testsuites><testsuite tests="3" failures="1" errors="0" skipped="1">
  <testcase classname="sample" name="pass"/>
  <testcase classname="sample" name="skip"><skipped/></testcase>
  <testcase classname="sample" name="failure"><failure/></testcase>
</testsuite></testsuites>"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.xml"
            path.write_text(report, encoding="utf-8")

            metrics = RUNNER._parse_junit(path)

        self.assertEqual(metrics.collected, 3)
        self.assertEqual(metrics.failures, 1)
        self.assertEqual(metrics.skipped, 1)


class HarnessEnvironmentIsolationTests(unittest.TestCase):
    def test_pytest_environment_removes_inherited_options_and_disables_optimization(
        self,
    ) -> None:
        inherited = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
            "PYTEST_ADDOPTS": "--ignore=tests/test_service.py",
            "PYTEST_PLUGINS": "hostile_plugin",
            "PYTHONOPTIMIZE": "2",
            "PYTHONPATH": "/untrusted/path",
            "CUSTOM_HARNESS_ENV": "preserved",
        }
        with patch.dict(os.environ, inherited, clear=True):
            environment, controls = RUNNER._check_environment("pytest")

        self.assertNotIn("PYTEST_ADDOPTS", environment)
        self.assertNotIn("PYTEST_PLUGINS", environment)
        self.assertEqual(environment["PYTHONOPTIMIZE"], "0")
        self.assertEqual(environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"], "1")
        self.assertEqual(environment["PYTHONPATH"], str(ROOT / "src"))
        self.assertEqual(environment["CUSTOM_HARNESS_ENV"], "preserved")
        self.assertIn("PATH", environment)
        self.assertIn("PYTHONOPTIMIZE=0", controls)
        self.assertIn("PYTEST_DISABLE_PLUGIN_AUTOLOAD=1", controls)
        assertions_enabled = subprocess.run(
            [sys.executable, "-c", "assert __debug__; print(__debug__)"],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(assertions_enabled.returncode, 0)
        self.assertEqual(assertions_enabled.stdout.strip(), "True")

    def test_pytest_command_retains_builtin_junit_reporting_and_full_test_root(
        self,
    ) -> None:
        evidence_dir = Path("/tmp/harness-evidence")

        command = RUNNER._commands(evidence_dir)["pytest"]

        self.assertEqual(command[1:4], ["-m", "pytest", "-c"])
        self.assertIn(".harness/pytest.ini", command)
        self.assertIn(f"--junitxml={evidence_dir / 'pytest-junit.xml'}", command)
        self.assertEqual(command[-1], "tests")


class HarnessInventoryTests(unittest.TestCase):
    def test_expected_test_inventory_exact_match(self) -> None:
        expected = frozenset({"sample::first", "sample::second"})
        metrics = RUNNER.PytestMetrics(
            collected=2,
            failures=0,
            errors=0,
            skipped=0,
            identities=expected,
        )

        self.assertEqual(RUNNER._validate_test_inventory(metrics, expected), [])

    def test_missing_expected_test_identity_is_reported(self) -> None:
        metrics = RUNNER.PytestMetrics(
            collected=1,
            failures=0,
            errors=0,
            skipped=0,
            identities=frozenset({"sample::present"}),
        )

        problems = RUNNER._validate_test_inventory(
            metrics, frozenset({"sample::present", "sample::missing"})
        )

        self.assertEqual(
            problems, ["Missing expected pytest cases: sample::missing"]
        )

    def test_unexpected_test_identity_is_reported(self) -> None:
        metrics = RUNNER.PytestMetrics(
            collected=2,
            failures=0,
            errors=0,
            skipped=0,
            identities=frozenset({"sample::expected", "sample::unexpected"}),
        )

        problems = RUNNER._validate_test_inventory(
            metrics, frozenset({"sample::expected"})
        )

        self.assertEqual(
            problems, ["Unexpected pytest cases: sample::unexpected"]
        )

    def test_duplicate_expected_inventory_identity_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            inventory_path = Path(directory) / "expected-tests.txt"
            inventory_path.write_text(
                "sample::duplicate\nsample::duplicate\n", encoding="utf-8"
            )
            with patch.object(RUNNER, "EXPECTED_TESTS_PATH", inventory_path):
                with self.assertRaisesRegex(ValueError, "duplicate identities"):
                    RUNNER._load_expected_tests()


class HarnessJUnitValidationTests(unittest.TestCase):
    def parse_report(self, report: str) -> RUNNER.PytestMetrics:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.xml"
            path.write_text(report, encoding="utf-8")
            return RUNNER._parse_junit(path)

    def test_valid_single_suite_separates_reported_executions_from_identities(
        self,
    ) -> None:
        metrics = self.parse_report(
            """<testsuite tests="5" failures="0" errors="0" skipped="0">
<testcase classname="sample" name="parent-one"/>
<testcase classname="sample" name="parent-two"/>
</testsuite>"""
        )

        self.assertEqual(metrics.collected, 2)
        self.assertEqual(metrics.reported_tests, 5)
        self.assertEqual(
            metrics.identities,
            frozenset({"sample::parent-one", "sample::parent-two"}),
        )

    def test_preserved_subtest_execution_count_is_distinct_from_identities(
        self,
    ) -> None:
        cases = "".join(
            f'<testcase classname="sample" name="parent-{index}"/>'
            for index in range(60)
        )
        metrics = self.parse_report(
            '<testsuite tests="342" failures="0" errors="0" skipped="0">'
            f"{cases}</testsuite>"
        )

        self.assertEqual(metrics.collected, 60)
        self.assertEqual(metrics.reported_tests, 342)

    def test_execution_count_must_match_the_reviewed_expected_total(self) -> None:
        report = (
            '<testsuite tests="999" failures="0" errors="0" skipped="0">'
            '<testcase classname="sample" name="expected"/>'
            "</testsuite>"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.xml"
            path.write_text(report, encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "999.*expected 342"):
                RUNNER._parse_junit(path, expected_reported_tests=342)

    def test_valid_multi_suite_report_reconciles_suite_and_aggregate_counts(
        self,
    ) -> None:
        metrics = self.parse_report(
            """<testsuites tests="4" failures="1" errors="0" skipped="0">
<testsuite tests="2" failures="1" errors="0" skipped="0">
  <testcase classname="sample" name="failed"><failure/></testcase>
</testsuite>
<testsuite tests="2" failures="0" errors="0" skipped="0">
  <testcase classname="sample" name="passed"/>
</testsuite>
</testsuites>"""
        )

        self.assertEqual(metrics.collected, 2)
        self.assertEqual(metrics.reported_tests, 4)
        self.assertEqual(metrics.failures, 1)

    def test_malformed_xml_and_unsupported_root_are_rejected(self) -> None:
        for report in ("<testsuite>", "<unsupported/>"):
            with self.subTest(report=report):
                with self.assertRaises(ValueError):
                    self.parse_report(report)

    def test_missing_required_counts_and_testcase_identity_are_rejected(self) -> None:
        count_attributes = {
            "tests": 'failures="0" errors="0" skipped="0"',
            "failures": 'tests="1" errors="0" skipped="0"',
            "errors": 'tests="1" failures="0" skipped="0"',
            "skipped": 'tests="1" failures="0" errors="0"',
        }
        for missing_count, attributes in count_attributes.items():
            with self.subTest(missing_count=missing_count):
                report = (
                    f"<testsuite {attributes}><testcase classname='sample' "
                    "name='case'/></testsuite>"
                )
                with self.assertRaisesRegex(ValueError, f"missing its {missing_count}"):
                    self.parse_report(report)

        for attributes in ('name="case"', 'classname="sample"'):
            with self.subTest(attributes=attributes):
                with self.assertRaisesRegex(ValueError, "missing classname or name"):
                    self.parse_report(
                        "<testsuite tests='1' failures='0' errors='0' skipped='0'>"
                        f"<testcase {attributes}/></testsuite>"
                    )

    def test_inconsistent_suite_and_aggregate_counts_are_rejected(self) -> None:
        reports = (
            """<testsuite tests="0" failures="0" errors="0" skipped="0">
<testcase classname="sample" name="case"/></testsuite>""",
            """<testsuite tests="1" failures="1" errors="0" skipped="0">
<testcase classname="sample" name="case"/></testsuite>""",
            """<testsuite tests="1" failures="0" errors="1" skipped="0">
<testcase classname="sample" name="case"/></testsuite>""",
            """<testsuite tests="1" failures="0" errors="0" skipped="1">
<testcase classname="sample" name="case"/></testsuite>""",
            """<testsuites tests="2"><testsuite tests="1" failures="0"
errors="0" skipped="0"><testcase classname="sample" name="case"/>
</testsuite></testsuites>""",
        )
        for report in reports:
            with self.subTest(report=report):
                with self.assertRaises(ValueError):
                    self.parse_report(report)

    def test_failure_error_and_skip_outcomes_are_counted(self) -> None:
        metrics = self.parse_report(
            """<testsuite tests="3" failures="1" errors="1" skipped="1">
<testcase classname="sample" name="failed"><failure/></testcase>
<testcase classname="sample" name="errored"><error/></testcase>
<testcase classname="sample" name="skipped"><skipped/></testcase>
</testsuite>"""
        )

        self.assertEqual(metrics.failures, 1)
        self.assertEqual(metrics.errors, 1)
        self.assertEqual(metrics.skipped, 1)

    def test_duplicate_collected_testcase_identity_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Duplicate JUnit testcase identity"):
            self.parse_report(
                """<testsuite tests="2" failures="0" errors="0" skipped="0">
<testcase classname="sample" name="duplicate"/>
<testcase classname="sample" name="duplicate"/>
</testsuite>"""
            )

    def test_nested_or_multiple_outcome_elements_are_rejected(self) -> None:
        reports = (
            (
                '<testcase classname="sample" name="case">'
                "<wrapper><failure/></wrapper></testcase>"
            ),
            (
                '<testcase classname="sample" name="case">'
                "<wrapper><error/></wrapper></testcase>"
            ),
            (
                '<testcase classname="sample" name="case">'
                "<wrapper><skipped/></wrapper></testcase>"
            ),
            '<testcase classname="sample" name="case"><failure/><error/></testcase>',
        )
        for testcase in reports:
            with self.subTest(testcase=testcase):
                with self.assertRaisesRegex(ValueError, "outcome"):
                    self.parse_report(
                        '<testsuite tests="1" failures="0" errors="0" skipped="0">'
                        f"{testcase}</testsuite>"
                    )


class HarnessRunnerFailureTests(unittest.TestCase):
    def test_timeout_records_partial_output_and_failure(self) -> None:
        command = ["tool", "check"]
        timeout = subprocess.TimeoutExpired(
            command, RUNNER.CHECK_TIMEOUT_SECONDS, output=b"partial stdout",
            stderr=b"partial stderr",
        )
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            with patch.object(RUNNER.subprocess, "run", side_effect=timeout):
                result = RUNNER._run_check("compile", command, run_dir)

            self.assertEqual(result["status"], "FAIL")
            self.assertIsNone(result["exit_code"])
            self.assertTrue(result["timed_out"])
            self.assertEqual(result["timeout_seconds"], 300)
            self.assertIn("Timed out", result["exception"])
            self.assertEqual(
                (run_dir / "compile.stdout.txt").read_text(encoding="utf-8"),
                "partial stdout",
            )
            self.assertEqual(
                (run_dir / "compile.stderr.txt").read_text(encoding="utf-8"),
                "partial stderr",
            )
            recorded = json.loads(
                (run_dir / "compile.result.json").read_text(encoding="utf-8")
            )
            self.assertEqual(recorded["status"], "FAIL")
            self.assertTrue(recorded["timed_out"])
            self.assertTrue(recorded["started_at_utc"])
            self.assertTrue(recorded["completed_at_utc"])

    def test_subprocess_launch_failure_is_recorded_as_failure(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run_dir = Path(directory)
            with patch.object(
                RUNNER.subprocess, "run", side_effect=FileNotFoundError("missing tool")
            ):
                result = RUNNER._run_check("ruff", ["missing-tool"], run_dir)

            self.assertEqual(result["status"], "FAIL")
            self.assertIsNone(result["exit_code"])
            self.assertIn("FileNotFoundError", result["exception"])
            self.assertEqual(
                json.loads((run_dir / "ruff.result.json").read_text())["status"],
                "FAIL",
            )

    def test_timeout_fails_overall_but_runner_attempts_every_check(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            evidence_dir = Path(directory) / "run"
            attempts: list[str] = []
            expected = frozenset({"sample::expected"})
            original_run_check = RUNNER._run_check

            def run_check(
                name: str, command: list[str], run_dir: Path
            ) -> dict[str, object]:
                attempts.append(name)
                if name == "compile":
                    timeout = subprocess.TimeoutExpired(
                        command,
                        RUNNER.CHECK_TIMEOUT_SECONDS,
                        output=b"partial compile output",
                        stderr=b"compile timed out",
                    )
                    with patch.object(RUNNER.subprocess, "run", side_effect=timeout):
                        return original_run_check(name, command, run_dir)
                if name == "pytest":
                    (run_dir / "pytest-junit.xml").write_text(
                        valid_junit_report(), encoding="utf-8"
                    )
                status = "PASS"
                return {
                    "check": name,
                    "status": status,
                    "exit_code": 0,
                    "stdout_file": f"{name}.stdout.txt",
                    "stderr_file": f"{name}.stderr.txt",
                }

            with (
                patch.object(RUNNER, "_run_check", side_effect=run_check),
                patch.object(RUNNER, "_load_expected_tests", return_value=expected),
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
            ):
                exit_code = RUNNER.run(str(evidence_dir))

            self.assertEqual(attempts, list(RUNNER.REQUIRED_CHECKS))
            self.assertEqual(exit_code, 1)
            manifest = json.loads(
                (evidence_dir / "manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["overall"], "FAIL")
            self.assertEqual(manifest["checks"]["compile"]["status"], "FAIL")

    def test_missing_or_malformed_junit_report_fails_runner(self) -> None:
        for report in (None, "<testsuite>"):
            with (
                self.subTest(report=report),
                tempfile.TemporaryDirectory() as directory,
            ):
                evidence_dir = Path(directory) / "run"
                expected = frozenset({"sample::expected"})

                def run_check(
                    name: str, command: list[str], run_dir: Path
                ) -> dict[str, object]:
                    if name == "pytest" and report is not None:
                        (run_dir / "pytest-junit.xml").write_text(
                            report, encoding="utf-8"
                        )
                    return {
                        "check": name,
                        "status": "PASS",
                        "exit_code": 0,
                        "stdout_file": f"{name}.stdout.txt",
                        "stderr_file": f"{name}.stderr.txt",
                    }

                with (
                    patch.object(RUNNER, "_run_check", side_effect=run_check),
                    patch.object(RUNNER, "_load_expected_tests", return_value=expected),
                    redirect_stdout(io.StringIO()),
                    redirect_stderr(io.StringIO()),
                ):
                    exit_code = RUNNER.run(str(evidence_dir))

                self.assertEqual(exit_code, 1)
                manifest = json.loads(
                    (evidence_dir / "manifest.json").read_text(encoding="utf-8")
                )
                self.assertEqual(manifest["overall"], "FAIL")
                self.assertTrue(manifest["checks"]["pytest"]["report_error"])

    def test_inflated_junit_execution_count_fails_runner(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            evidence_dir = Path(directory) / "run"
            expected = frozenset({"sample::expected"})

            def run_check(
                name: str, command: list[str], run_dir: Path
            ) -> dict[str, object]:
                if name == "pytest":
                    (run_dir / "pytest-junit.xml").write_text(
                        '<testsuite tests="999" failures="0" errors="0" skipped="0">'
                        '<testcase classname="sample" name="expected"/>'
                        "</testsuite>",
                        encoding="utf-8",
                    )
                return {
                    "check": name,
                    "status": "PASS",
                    "exit_code": 0,
                    "stdout_file": f"{name}.stdout.txt",
                    "stderr_file": f"{name}.stderr.txt",
                }

            output = io.StringIO()
            with (
                patch.object(RUNNER, "_run_check", side_effect=run_check),
                patch.object(RUNNER, "_load_expected_tests", return_value=expected),
                patch.object(RUNNER, "EXPECTED_REPORTED_TESTS", 1, create=True),
                redirect_stdout(output),
                redirect_stderr(io.StringIO()),
            ):
                exit_code = RUNNER.run(str(evidence_dir))

            manifest = json.loads(
                (evidence_dir / "manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(exit_code, 1)
            self.assertEqual(manifest["overall"], "FAIL")
            self.assertEqual(manifest["checks"]["pytest"]["status"], "FAIL")
            self.assertIn("999", manifest["checks"]["pytest"]["report_error"])

    def test_junit_failure_error_and_skip_mark_pytest_check_failed(self) -> None:
        cases = (
            ("failure", 'failures="1" errors="0" skipped="0"', "<failure/>"),
            ("error", 'failures="0" errors="1" skipped="0"', "<error/>"),
            ("skipped", 'failures="0" errors="0" skipped="1"', "<skipped/>"),
        )
        for outcome, counts, result in cases:
            with (
                self.subTest(outcome=outcome),
                tempfile.TemporaryDirectory() as directory,
            ):
                evidence_dir = Path(directory) / "run"
                expected = frozenset({"sample::case"})

                def run_check(
                    name: str, command: list[str], run_dir: Path
                ) -> dict[str, object]:
                    if name == "pytest":
                        (run_dir / "pytest-junit.xml").write_text(
                            f'<testsuite tests="1" {counts}>'
                            f'<testcase classname="sample" name="case">{result}'
                            "</testcase></testsuite>",
                            encoding="utf-8",
                        )
                    return {
                        "check": name,
                        "status": "PASS",
                        "exit_code": 0,
                        "stdout_file": f"{name}.stdout.txt",
                        "stderr_file": f"{name}.stderr.txt",
                    }

                with (
                    patch.object(RUNNER, "_run_check", side_effect=run_check),
                    patch.object(RUNNER, "_load_expected_tests", return_value=expected),
                    patch.object(RUNNER, "EXPECTED_REPORTED_TESTS", 1, create=True),
                    redirect_stdout(io.StringIO()),
                    redirect_stderr(io.StringIO()),
                ):
                    exit_code = RUNNER.run(str(evidence_dir))

                manifest = json.loads(
                    (evidence_dir / "manifest.json").read_text(encoding="utf-8")
                )
                self.assertEqual(exit_code, 1)
                self.assertEqual(manifest["overall"], "FAIL")
                self.assertEqual(manifest["checks"]["pytest"]["status"], "FAIL")


class HarnessEvidenceFailureTests(unittest.TestCase):
    def test_stdout_stderr_and_result_write_failures_never_pass(self) -> None:
        cases = (("stdout", "_write_text"), ("stderr", "_write_text"),
                 ("result", "_write_json"))
        for target, writer_name in cases:
            with (
                self.subTest(target=target),
                tempfile.TemporaryDirectory() as directory,
            ):
                evidence_dir = Path(directory) / "run"
                original_writer = getattr(RUNNER, writer_name)

                def fail_selected_write(path: Path, value: object) -> None:
                    target_path = (
                        "compile.result.json"
                        if target == "result"
                        else f"compile.{target}.txt"
                    )
                    if path.name == target_path:
                        raise RUNNER.EvidencePersistenceError(f"unwritable {target}")
                    original_writer(path, value)

                output = io.StringIO()
                errors = io.StringIO()
                with (
                    patch.object(
                        RUNNER.subprocess,
                        "run",
                        return_value=subprocess.CompletedProcess(
                            ["tool"],
                            0,
                            stdout="captured output",
                            stderr="captured error",
                        ),
                    ),
                    patch.object(RUNNER, writer_name, side_effect=fail_selected_write),
                    redirect_stdout(output),
                    redirect_stderr(errors),
                ):
                    exit_code = RUNNER.run(str(evidence_dir))

                self.assertEqual(exit_code, 2)
                self.assertNotIn("Overall: PASS", output.getvalue())
                self.assertIn("Evidence persistence failed", errors.getvalue())

    def test_manifest_write_failure_returns_nonzero_without_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            evidence_dir = Path(directory) / "run"
            expected = frozenset({"sample::expected"})

            def run_check(
                name: str, command: list[str], run_dir: Path
            ) -> dict[str, object]:
                if name == "pytest":
                    (run_dir / "pytest-junit.xml").write_text(
                        valid_junit_report(), encoding="utf-8"
                    )
                return {
                    "check": name,
                    "status": "PASS",
                    "exit_code": 0,
                    "stdout_file": f"{name}.stdout.txt",
                    "stderr_file": f"{name}.stderr.txt",
                }

            original_write_json = RUNNER._write_json

            def fail_manifest_write(path: Path, value: object) -> None:
                if path.name == "manifest.json":
                    raise RUNNER.EvidencePersistenceError("manifest unavailable")
                original_write_json(path, value)

            output = io.StringIO()
            errors = io.StringIO()
            with (
                patch.object(RUNNER, "_run_check", side_effect=run_check),
                patch.object(RUNNER, "_load_expected_tests", return_value=expected),
                patch.object(RUNNER, "_write_json", side_effect=fail_manifest_write),
                redirect_stdout(output),
                redirect_stderr(errors),
            ):
                exit_code = RUNNER.run(str(evidence_dir))

            self.assertEqual(exit_code, 2)
            self.assertNotIn("Overall: PASS", output.getvalue())
            self.assertIn("Evidence persistence failed", errors.getvalue())
            self.assertFalse((evidence_dir / "manifest.json").exists())

    def test_evidence_directory_collision_preserves_existing_contents(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            evidence_dir = Path(directory) / "existing-run"
            evidence_dir.mkdir()
            marker = evidence_dir / "original.txt"
            marker.write_text("preserve me", encoding="utf-8")

            with (
                patch.object(RUNNER, "_run_check") as run_check,
                redirect_stdout(io.StringIO()),
                redirect_stderr(io.StringIO()),
            ):
                exit_code = RUNNER.run(str(evidence_dir))

            self.assertEqual(exit_code, 2)
            self.assertEqual(marker.read_text(encoding="utf-8"), "preserve me")
            run_check.assert_not_called()

    def test_real_filesystem_write_errors_never_pass(self) -> None:
        cases = (
            ("stdout", "_write_text", "compile.stdout.txt"),
            ("stderr", "_write_text", "compile.stderr.txt"),
            ("result", "_write_json", "compile.result.json"),
            ("manifest", "_write_json", "manifest.json"),
        )
        for target, writer_name, filename in cases:
            with (
                self.subTest(target=target),
                tempfile.TemporaryDirectory() as directory,
            ):
                evidence_dir = Path(directory) / "run"
                original_writer = getattr(RUNNER, writer_name)

                def create_directory_at_write_target(
                    path: Path, value: object
                ) -> None:
                    if path.name == filename:
                        path.mkdir()
                    original_writer(path, value)

                def mocked_subprocess_run(
                    command: list[str], **kwargs: object
                ) -> subprocess.CompletedProcess[str]:
                    if "-m" in command and "pytest" in command:
                        junit_argument = next(
                            item for item in command if item.startswith("--junitxml=")
                        )
                        report_path = Path(junit_argument.split("=", maxsplit=1)[1])
                        report_path.write_text(valid_junit_report(), encoding="utf-8")
                    return subprocess.CompletedProcess(
                        command, 0, stdout="ok", stderr=""
                    )

                output = io.StringIO()
                errors = io.StringIO()
                with (
                    patch.object(
                        RUNNER.subprocess, "run", side_effect=mocked_subprocess_run
                    ),
                    patch.object(
                        RUNNER,
                        writer_name,
                        side_effect=create_directory_at_write_target,
                    ),
                    patch.object(RUNNER, "_load_expected_tests",
                                 return_value=frozenset({"sample::expected"})),
                    patch.object(RUNNER, "EXPECTED_REPORTED_TESTS", 1, create=True),
                    redirect_stdout(output),
                    redirect_stderr(errors),
                ):
                    exit_code = RUNNER.run(str(evidence_dir))

                self.assertEqual(exit_code, 2)
                self.assertNotIn("Overall: PASS", output.getvalue())
                self.assertIn("Evidence persistence failed", errors.getvalue())
