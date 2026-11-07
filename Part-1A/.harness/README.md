# Independent Quality Harness

The harness validates the local Python tracker; it does not run deployment commands, contact AWS, Kubernetes, Jenkins, or any other external service.

## Setup

Install the harness-only tools without adding application runtime dependencies:

```sh
python3 -m pip install -r .harness/requirements.txt
```

The required independent checks are:

1. `compileall` for Python syntax/bytecode compilation of `src`, `tests`, and `.harness`.
2. Ruff for lint checks across application source, tests, and the runner.
3. Bandit for security findings in application code under `src`.
4. Pytest for collection and execution of all `tests/test_*.py` tests, including the `unittest`-based suite.

No mandatory check is skipped or configured as optional. A command that cannot run, exits nonzero, or is absent from the result manifest fails the overall run. Pytest must collect at least one test and may not report skipped tests, failures, or errors.

The harness deliberately pins Pytest to 9.2.0 because the reviewed JUnit execution-event baseline for this suite is 398. `PYTEST_DISABLE_PLUGIN_AUTOLOAD` is supported starting in Pytest 8.4; this exact pin also fixes the reporter behavior against which the reviewed baseline was validated. Do not automatically regenerate the expected execution count to make a run pass. Any future Pytest version change requires deliberate review, targeted validation, and full-suite JUnit execution-count revalidation before changing either this pin or the expected count. Plugin isolation must not be disabled or bypassed. For the Pytest subprocess, the runner removes inherited `PYTHON*` and `PYTEST*` environment variables, then sets `PYTHONPATH` to the project `src/`, `PYTHONOPTIMIZE=0`, and `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`. This prevents inherited optimization, warnings/hash/import settings, Pytest options, and external plugin autoload from changing test execution. Other environment variables, including `PATH`, `HOME`, `VIRTUAL_ENV`, and temporary-directory settings, are retained for the local Python/tool environment. Pytest's built-in JUnit XML reporter remains available; repository-defined `conftest.py` or explicit `pytest_plugins` remain part of the checked-in test configuration.

The expected-test inventory lists 87 JUnit testcase identities (`classname::name`), not individual execution events. The preserved original Pytest 9.2.0 report declared `tests="342"` and emitted 60 testcase elements. This is consistent with the suite's `unittest.subTest` usage: Pytest counts subtest reports as execution events while the JUnit output groups them under their parent unittest method identity. The current reviewed suite therefore expects 398 reported execution events and 87 parent testcase identities; these are recorded and validated separately. The runner requires the exact reviewed execution-event count, validates failure/error/skip totals against structurally valid direct testcase outcomes, checks aggregate counts against suite totals, and independently requires an exact match to the reviewed identity inventory. It does not require execution-event counts to equal testcase identities.

## Run

From the project directory:

```sh
python3 .harness/run_harness.py
```

Each run gets a new directory under `evidence/final-generation/harness-runs/`. To select a different new evidence directory, use:

```sh
python3 .harness/run_harness.py --evidence-dir evidence/initial-generation/harness-runs/<run-id>
```

The runner refuses to overwrite an existing evidence directory. Each check records its exact argument-vector command, UTC start/end timestamps, exit code, PASS/FAIL state, stdout, stderr, and a JSON result file. The run manifest records every required check, Pytest JUnit counts, overall result, and fail-closed reasons. Pytest skipped/empty collection is detected from the JUnit report independently of the exit status.

## Evidence and repair workflow

- Keep initial-generation and final-generation evidence in their separate directories.
- Initialize the repository-root `harness-log.md` with the exact command, UTC start time, and evidence path before each harness run; append the actual outcomes immediately after it completes.
- Preserve failed outputs. Fix the underlying source/configuration issue without weakening tests, security checks, evaluation inputs, or thresholds, then rerun into a new evidence directory.
- Record feedback and repairs truthfully in the log. Use “none observed” when no failure or repair occurred.
- A harness PASS is automated evidence only. A designated human must record a separate ACCEPT or REJECT after final review.

The evidence manifest and review record belong under `evidence/final-generation/`. Never represent missing checks, skipped tests, an empty collection, or a failed command as PASS.
