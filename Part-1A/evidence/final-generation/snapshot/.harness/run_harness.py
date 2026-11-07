from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parent.parent
REQUIRED_CHECKS = ("compile", "ruff", "bandit", "pytest")
EXPECTED_TESTS_PATH = ROOT / ".harness" / "expected-tests.txt"
CHECK_TIMEOUT_SECONDS = 300
EXPECTED_REPORTED_TESTS = 398


@dataclass(frozen=True)
class PytestMetrics:
    collected: int
    failures: int
    errors: int
    skipped: int
    reported_tests: int = 0
    identities: frozenset[str] = frozenset()


class EvidencePersistenceError(RuntimeError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def _parse_junit(
    path: Path,
    expected_reported_tests: int | None = None,
) -> PytestMetrics:
    if not path.is_file():
        raise ValueError(f"Pytest did not create its JUnit report: {path}")
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as exc:
        raise ValueError(f"Could not parse Pytest JUnit report: {exc}") from exc

    if root.tag == "testsuite":
        suites = [root]
    elif root.tag == "testsuites":
        suites = list(root)
        if not suites or any(suite.tag != "testsuite" for suite in suites):
            raise ValueError("JUnit testsuites report must contain testsuite elements")
    else:
        raise ValueError(f"Unsupported JUnit root element: {root.tag}")

    identities: set[str] = set()
    failures = 0
    errors = 0
    skipped = 0
    reported_tests = 0
    declared_totals = {name: 0 for name in ("tests", "failures", "errors", "skipped")}

    for suite in suites:
        cases = suite.findall("testcase")
        if len(list(suite.iter("testcase"))) != len(cases):
            raise ValueError("JUnit testcase elements must be direct suite children")
        suite_failures = 0
        suite_errors = 0
        suite_skipped = 0
        for case in cases:
            classname = case.get("classname", "").strip()
            name = case.get("name", "").strip()
            if not classname or not name:
                raise ValueError("JUnit testcase is missing classname or name")
            identity = f"{classname}::{name}"
            if identity in identities:
                raise ValueError(f"Duplicate JUnit testcase identity: {identity}")
            identities.add(identity)
            outcomes = [
                node
                for node in case.iter()
                if node is not case and node.tag in {"failure", "error", "skipped"}
            ]
            direct_outcomes = [
                node for node in case if node.tag in {"failure", "error", "skipped"}
            ]
            if len(outcomes) != len(direct_outcomes):
                raise ValueError(
                    "JUnit outcome elements must be direct testcase children"
                )
            if len(direct_outcomes) > 1:
                raise ValueError("JUnit testcase has multiple outcome elements")
            suite_failures += sum(node.tag == "failure" for node in direct_outcomes)
            suite_errors += sum(node.tag == "error" for node in direct_outcomes)
            suite_skipped += sum(node.tag == "skipped" for node in direct_outcomes)

        suite_values = {
            "tests": len(cases),
            "failures": suite_failures,
            "errors": suite_errors,
            "skipped": suite_skipped,
        }
        suite_counts: dict[str, int] = {}
        for name, observed in suite_values.items():
            value = suite.get(name)
            if value is None:
                raise ValueError(f"JUnit testsuite is missing its {name} count")
            try:
                declared = int(value)
            except ValueError as exc:
                raise ValueError(f"Invalid JUnit {name} count: {value!r}") from exc
            if declared < 0:
                raise ValueError(f"Inconsistent JUnit {name} count in testsuite")
            if name == "tests" and declared < len(cases):
                raise ValueError(
                    "JUnit execution count is lower than testcase elements"
                )
            if name != "tests" and declared != observed:
                raise ValueError(f"Inconsistent JUnit {name} count in testsuite")
            suite_counts[name] = declared
            declared_totals[name] += declared
        reported_tests += suite_counts["tests"]

        failures += suite_failures
        errors += suite_errors
        skipped += suite_skipped

    if root.tag == "testsuites":
        for name, total in declared_totals.items():
            value = root.get(name)
            if value is None:
                continue
            try:
                declared = int(value)
            except ValueError as exc:
                raise ValueError(f"Invalid JUnit {name} count: {value!r}") from exc
            if declared < 0:
                raise ValueError(f"Invalid JUnit {name} count: {declared}")
            if declared != total:
                raise ValueError(f"Inconsistent aggregate JUnit {name} count")

    if (
        expected_reported_tests is not None
        and reported_tests != expected_reported_tests
    ):
        raise ValueError(
            f"JUnit report declares {reported_tests} execution events; "
            f"expected {expected_reported_tests}"
        )

    return PytestMetrics(
        collected=len(identities),
        reported_tests=reported_tests,
        failures=failures,
        errors=errors,
        skipped=skipped,
        identities=frozenset(identities),
    )


def _load_expected_tests() -> frozenset[str]:
    try:
        lines = EXPECTED_TESTS_PATH.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ValueError(f"Could not read expected test inventory: {exc}") from exc

    entries = [
        line.strip()
        for line in lines
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not entries:
        raise ValueError("Expected test inventory is empty")
    if any("::" not in entry for entry in entries):
        raise ValueError("Expected test inventory entries must be JUnit identities")
    if len(entries) != len(set(entries)):
        raise ValueError("Expected test inventory contains duplicate identities")
    return frozenset(entries)


def _validate_test_inventory(
    metrics: PytestMetrics,
    expected_tests: frozenset[str],
) -> list[str]:
    problems: list[str] = []
    missing = sorted(expected_tests - metrics.identities)
    unexpected = sorted(metrics.identities - expected_tests)
    if missing:
        problems.append(f"Missing expected pytest cases: {', '.join(missing)}")
    if unexpected:
        problems.append(f"Unexpected pytest cases: {', '.join(unexpected)}")
    return problems


def aggregate_results(
    results: dict[str, dict[str, object]],
    pytest_metrics: PytestMetrics | None,
    expected_tests: frozenset[str] | None = None,
    expected_reported_tests: int | None = None,
) -> tuple[bool, list[str]]:
    problems: list[str] = []
    missing = sorted(set(REQUIRED_CHECKS) - results.keys())
    unexpected = sorted(results.keys() - set(REQUIRED_CHECKS))
    if missing:
        problems.append(f"Missing mandatory checks: {', '.join(missing)}")
    if unexpected:
        problems.append(f"Unexpected check results: {', '.join(unexpected)}")

    for name in REQUIRED_CHECKS:
        result = results.get(name)
        if result is None:
            continue
        if result.get("status") != "PASS" or result.get("exit_code") != 0:
            problems.append(f"{name} did not pass")

    if pytest_metrics is None:
        problems.append("Pytest result metrics are unavailable")
    else:
        if pytest_metrics.collected < 1:
            problems.append("Pytest collected no tests")
        if pytest_metrics.failures:
            problems.append(f"Pytest reported {pytest_metrics.failures} failure(s)")
        if pytest_metrics.errors:
            problems.append(f"Pytest reported {pytest_metrics.errors} error(s)")
        if pytest_metrics.skipped:
            problems.append(f"Pytest reported {pytest_metrics.skipped} skipped test(s)")
        if expected_tests is not None:
            problems.extend(_validate_test_inventory(pytest_metrics, expected_tests))
        if (
            expected_reported_tests is not None
            and pytest_metrics.reported_tests != expected_reported_tests
        ):
            problems.append(
                "Pytest reported "
                f"{pytest_metrics.reported_tests} execution events; expected "
                f"{expected_reported_tests}"
            )

    return not problems, problems


def _commands(evidence_dir: Path) -> dict[str, list[str]]:
    python = sys.executable
    return {
        "compile": [python, "-m", "compileall", "-q", "src", "tests", ".harness"],
        "ruff": [
            python,
            "-m",
            "ruff",
            "check",
            "--config",
            ".harness/ruff.toml",
            "src",
            "tests",
            ".harness/run_harness.py",
        ],
        "bandit": [
            python,
            "-m",
            "bandit",
            "-c",
            ".harness/bandit.yaml",
            "-r",
            "src",
        ],
        "pytest": [
            python,
            "-m",
            "pytest",
            "-c",
            ".harness/pytest.ini",
            f"--junitxml={evidence_dir / 'pytest-junit.xml'}",
            "tests",
        ],
    }


def _check_environment(name: str) -> tuple[dict[str, str], list[str]]:
    environment = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    controls: list[str] = []
    if name == "pytest":
        for key in tuple(environment):
            if key.startswith(("PYTHON", "PYTEST")):
                environment.pop(key)
        environment["PYTHONPATH"] = str(ROOT / "src")
        environment["PYTHONOPTIMIZE"] = "0"
        environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        controls = [
            "inherited PYTHON* and PYTEST* variables removed",
            f"PYTHONPATH={ROOT / 'src'}",
            "PYTHONOPTIMIZE=0",
            "PYTEST_DISABLE_PLUGIN_AUTOLOAD=1",
        ]
    return environment, controls


def _captured_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value


def _write_text(path: Path, content: str) -> None:
    try:
        path.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise EvidencePersistenceError(f"Could not write {path}: {exc}") from exc


def _write_json(path: Path, value: object) -> None:
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            stream.write(json.dumps(value, indent=2) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
    except OSError as exc:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise EvidencePersistenceError(f"Could not persist {path}: {exc}") from exc


def _run_check(name: str, command: list[str], run_dir: Path) -> dict[str, object]:
    started_at = _utc_now()
    environment, environment_controls = _check_environment(name)
    timed_out = False
    try:
        completed = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            errors="replace",
            check=False,
            shell=False,
            timeout=CHECK_TIMEOUT_SECONDS,
        )
        exit_code: int | None = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
        exception: str | None = None
    except subprocess.TimeoutExpired as exc:
        exit_code = None
        stdout = _captured_text(exc.stdout)
        stderr = _captured_text(exc.stderr)
        exception = f"Timed out after {CHECK_TIMEOUT_SECONDS} seconds"
        timed_out = True
    except OSError as exc:
        exit_code = None
        stdout = ""
        stderr = ""
        exception = f"{type(exc).__name__}: {exc}"

    result: dict[str, object] = {
        "check": name,
        "command": command,
        "started_at_utc": started_at,
        "completed_at_utc": _utc_now(),
        "exit_code": exit_code,
        "status": "PASS" if exit_code == 0 else "FAIL",
        "stdout_file": f"{name}.stdout.txt",
        "stderr_file": f"{name}.stderr.txt",
        "exception": exception,
        "timed_out": timed_out,
        "timeout_seconds": CHECK_TIMEOUT_SECONDS,
    }
    if environment_controls:
        result["environment_controls"] = environment_controls
    _write_text(run_dir / f"{name}.stdout.txt", stdout)
    _write_text(run_dir / f"{name}.stderr.txt", stderr)
    _write_json(run_dir / f"{name}.result.json", result)
    return result


def _resolve_evidence_dir(value: str | None) -> Path:
    if value:
        path = Path(value)
        return path if path.is_absolute() else ROOT / path
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id += f"-{uuid.uuid4().hex[:8]}"
    return ROOT / "evidence" / "final-generation" / "harness-runs" / run_id


def run(evidence_value: str | None) -> int:
    evidence_dir = _resolve_evidence_dir(evidence_value)
    try:
        evidence_dir.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        print(
            f"Evidence directory already exists; refusing to overwrite: "
            f"{_relative(evidence_dir)}",
            file=sys.stderr,
        )
        return 2
    except OSError as exc:
        print(f"Could not create evidence directory: {exc}", file=sys.stderr)
        return 2

    started_at = _utc_now()
    commands = _commands(evidence_dir)
    results: dict[str, dict[str, object]] = {}
    try:
        for name in REQUIRED_CHECKS:
            results[name] = _run_check(name, commands[name], evidence_dir)
    except EvidencePersistenceError as exc:
        print(
            f"Evidence persistence failed; harness cannot pass: {exc}",
            file=sys.stderr,
        )
        return 2

    pytest_metrics: PytestMetrics | None = None
    expected_tests: frozenset[str] | None = None
    inventory_error: str | None = None
    try:
        expected_tests = _load_expected_tests()
    except ValueError as exc:
        inventory_error = str(exc)

    try:
        pytest_metrics = _parse_junit(
            evidence_dir / "pytest-junit.xml",
            expected_reported_tests=EXPECTED_REPORTED_TESTS,
        )
    except ValueError as exc:
        pytest_parse_error = str(exc)
        pytest_result = results["pytest"]
        pytest_result["status"] = "FAIL"
        pytest_result["report_error"] = pytest_parse_error
        try:
            _write_json(evidence_dir / "pytest.result.json", pytest_result)
        except EvidencePersistenceError as write_error:
            print(
                f"Evidence persistence failed; harness cannot pass: {write_error}",
                file=sys.stderr,
            )
            return 2

    if pytest_metrics is not None:
        pytest_report_problems: list[str] = []
        if pytest_metrics.failures:
            pytest_report_problems.append(
                f"JUnit report contains {pytest_metrics.failures} failure(s)"
            )
        if pytest_metrics.errors:
            pytest_report_problems.append(
                f"JUnit report contains {pytest_metrics.errors} error(s)"
            )
        if pytest_metrics.skipped:
            pytest_report_problems.append(
                f"JUnit report contains {pytest_metrics.skipped} skipped test(s)"
            )
        if pytest_report_problems:
            pytest_result = results["pytest"]
            pytest_result["status"] = "FAIL"
            pytest_result["report_validation_errors"] = pytest_report_problems
            try:
                _write_json(evidence_dir / "pytest.result.json", pytest_result)
            except EvidencePersistenceError as write_error:
                print(
                    f"Evidence persistence failed; harness cannot pass: {write_error}",
                    file=sys.stderr,
                )
                return 2

    if inventory_error is not None:
        pytest_result = results["pytest"]
        pytest_result["status"] = "FAIL"
        pytest_result["inventory_error"] = inventory_error
        try:
            _write_json(evidence_dir / "pytest.result.json", pytest_result)
        except EvidencePersistenceError as write_error:
            print(
                f"Evidence persistence failed; harness cannot pass: {write_error}",
                file=sys.stderr,
            )
            return 2
    elif pytest_metrics is not None and expected_tests is not None:
        inventory_problems = _validate_test_inventory(pytest_metrics, expected_tests)
        if inventory_problems:
            pytest_result = results["pytest"]
            pytest_result["status"] = "FAIL"
            pytest_result["inventory_errors"] = inventory_problems
            try:
                _write_json(evidence_dir / "pytest.result.json", pytest_result)
            except EvidencePersistenceError as write_error:
                print(
                    f"Evidence persistence failed; harness cannot pass: {write_error}",
                    file=sys.stderr,
                )
                return 2

    passed, problems = aggregate_results(
        results, pytest_metrics, expected_tests, EXPECTED_REPORTED_TESTS
    )
    if inventory_error is not None:
        problems.append(inventory_error)
        passed = False
    manifest = {
        "schema_version": 1,
        "run_id": evidence_dir.name,
        "started_at_utc": started_at,
        "completed_at_utc": _utc_now(),
        "project_root": str(ROOT),
        "evidence_directory": _relative(evidence_dir),
        "checks": results,
        "expected_test_inventory": _relative(EXPECTED_TESTS_PATH),
        "expected_test_count": (
            len(expected_tests) if expected_tests is not None else None
        ),
        "expected_reported_test_count": EXPECTED_REPORTED_TESTS,
        "pytest_test_identities": (
            sorted(pytest_metrics.identities) if pytest_metrics is not None else None
        ),
        "pytest_metrics": (
            {
                "collected": pytest_metrics.collected,
                "reported_tests": pytest_metrics.reported_tests,
                "failures": pytest_metrics.failures,
                "errors": pytest_metrics.errors,
                "skipped": pytest_metrics.skipped,
            }
            if pytest_metrics is not None
            else None
        ),
        "overall": "PASS" if passed else "FAIL",
        "problems": problems,
    }
    try:
        _write_json(evidence_dir / "manifest.json", manifest)
    except EvidencePersistenceError as exc:
        print(
            f"Evidence persistence failed; harness cannot pass: {exc}",
            file=sys.stderr,
        )
        return 2

    for name in REQUIRED_CHECKS:
        print(f"{name}: {results[name]['status']}")
    if pytest_metrics is not None:
        print(
            "pytest collection: "
            f"{pytest_metrics.collected} collected, "
            f"{pytest_metrics.failures} failures, "
            f"{pytest_metrics.errors} errors, "
            f"{pytest_metrics.skipped} skipped"
        )
    print(f"Overall: {'PASS' if passed else 'FAIL'}")
    print(f"Evidence: {_relative(evidence_dir)}")
    for problem in problems:
        print(f"Reason: {problem}", file=sys.stderr)
    return 0 if passed else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run independent local Python validation checks."
    )
    parser.add_argument(
        "--evidence-dir",
        help="new, non-existing directory for this run's logs and result manifest",
    )
    arguments = parser.parse_args(argv)
    return run(arguments.evidence_dir)


if __name__ == "__main__":
    raise SystemExit(main())
