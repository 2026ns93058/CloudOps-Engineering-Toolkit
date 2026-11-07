# Final-Generation Evidence Manifest

## Purpose and status

This manifest indexes the approved design artifacts, implementation snapshot,
test suite, harness configuration, execution records, failures, repairs, and
final automated validation for the local CloudOps Deployment Management &
Readiness Tracker.

The manifest is preparatory evidence, not a human acceptance decision. The
final-generation `human-review.md` record is **pending** and has not been
created because no human ACCEPT or REJECT decision was provided. Task T039
remains incomplete. Since T040 requires that human-review record to be present
and verified, T040 also remains incomplete; the missing prerequisite is
recorded here rather than represented as a pass. See [the task list](../../specs/001-deployment-readiness-tracker/tasks.md).

## Evidence locations

- [Initial-generation evidence](../initial-generation/) contains the pre-harness
  source/test/design-input snapshot, baseline test output, the initial harness
  run, and the original launcher failure.
- [Initial-generation inventory](../initial-generation/initial-inventory.json)
  records 20 files: 12 source/test files and 8 input files.
- [Initial-generation snapshot](../initial-generation/snapshot/) preserves the
  initial source, tests, README, project metadata, specification, plan, task
  list, data model, CLI contract, and constitution.
- [Final-generation evidence](./) contains the curated final snapshot,
  inventory, and four final-generation harness runs, including the Stage 4
  failed attempt and successful rerun.
- [Curated final inventory](./final-inventory.json) records 30 files: 19
  source/test/harness files and 11 input files. Its entries include SHA-256
  hashes and paths into the [curated final snapshot](./snapshot/). Generated
  cache directories and Python bytecode are excluded.
- The original harness run directories and their logs, result JSON, manifests,
  and JUnit reports are preserved under [initial harness runs](../initial-generation/harness-runs/)
  and [final harness runs](./harness-runs/). The original launcher failure is
  preserved under [initial failure evidence](../initial-generation/failures/).

## Spec Kit artifacts and governance

The approved design and governance inputs are available in the repository:

- [Project constitution](../../.specify/memory/constitution.md) defines the
  local-only scope, deployment integrity, readiness gates, evidence
  preservation, harness integrity, and separate human oversight.
- [Feature specification](../../specs/001-deployment-readiness-tracker/spec.md)
  contains user stories, acceptance scenarios, and measurable outcomes.
- [Implementation plan](../../specs/001-deployment-readiness-tracker/plan.md)
  records architecture, technical constraints, test approach, evidence
  structure, and local-only scope.
- [Research decisions](../../specs/001-deployment-readiness-tracker/research.md)
  documents the standard-library application design, fail-closed JSON
  persistence, audit approach, and deterministic testability.
- [Data model](../../specs/001-deployment-readiness-tracker/data-model.md)
  defines records, lifecycle transitions, mandatory readiness checks, human
  decisions, audit events, and storage guarantees.
- [CLI contract](../../specs/001-deployment-readiness-tracker/contracts/cli.md)
  defines command behavior, validation, status/readiness gates, and error
  guarantees.
- [Quickstart](../../specs/001-deployment-readiness-tracker/quickstart.md)
  documents automated validation and disposable-store CLI scenarios.
- [Task list](../../specs/001-deployment-readiness-tracker/tasks.md) records
  task IDs, dependencies, and completion state. T039 and T040 remain unchecked.

## Application, tests, and harness

The final snapshot inventory gives the complete path, byte size, and SHA-256
for every curated file. It includes:

- Application modules: [`__init__.py`](./snapshot/src/cloudops_tracker/__init__.py),
  [`__main__.py`](./snapshot/src/cloudops_tracker/__main__.py),
  [`cli.py`](./snapshot/src/cloudops_tracker/cli.py),
  [`domain.py`](./snapshot/src/cloudops_tracker/domain.py),
  [`readiness.py`](./snapshot/src/cloudops_tracker/readiness.py),
  [`service.py`](./snapshot/src/cloudops_tracker/service.py), and
  [`storage.py`](./snapshot/src/cloudops_tracker/storage.py).
- Tests: [`test_cli.py`](./snapshot/tests/test_cli.py),
  [`test_domain.py`](./snapshot/tests/test_domain.py),
  [`test_harness.py`](./snapshot/tests/test_harness.py),
  [`test_readiness.py`](./snapshot/tests/test_readiness.py),
  [`test_service.py`](./snapshot/tests/test_service.py), and
  [`test_storage.py`](./snapshot/tests/test_storage.py).
- Harness: [runner](./snapshot/.harness/run_harness.py),
  [Ruff configuration](./snapshot/.harness/ruff.toml),
  [Bandit configuration](./snapshot/.harness/bandit.yaml),
  [Pytest configuration](./snapshot/.harness/pytest.ini),
  [harness-only requirements](./snapshot/.harness/requirements.txt), and
  [harness instructions](../../.harness/README.md).
- Project documentation and metadata: [application README](../../README.md),
  [project configuration](./snapshot/pyproject.toml),
  [ignore rules](./snapshot/.gitignore), and the
  [execution log](../../harness-log.md).

The application is a local Python deployment-management and readiness tracker.
It models lifecycle state only and does not perform AWS deployments or interact
with a Kubernetes cluster. The harness is local and does not contact external
deployment services.

## Failure, feedback, and repair chronology

All commands below were executed from the repository root. Original run
artifacts were not overwritten by repairs or reruns; the detailed record and
actual outputs are in the [execution log](../../harness-log.md) and linked run
directories.

| Time (UTC) | Command / evidence | Actual result |
|---|---|---|
| 2026-11-07 17:38:51 | `python .harness/run_harness.py --evidence-dir evidence/initial-generation/harness-runs/phase9-initial-20261107T173851Z` | Launcher exited 127 because `python` was unavailable; the harness did not start. Preserved in [launcher result](../initial-generation/failures/phase9-python-launcher.result.json) and [stderr](../initial-generation/failures/phase9-python-launcher.stderr.txt). |
| 2026-11-07 17:39:34 | `python3 .harness/run_harness.py --evidence-dir evidence/initial-generation/harness-runs/phase9-initial-python3-20261107T173934Z` | Overall FAIL: compilation PASS (0), Ruff FAIL (1; 86 E501 findings), Bandit FAIL (1; B105 on readiness literal `PASS`), Pytest PASS (0; 60 collected, 0 failures/errors/skips). See [initial run directory](../initial-generation/harness-runs/phase9-initial-python3-20261107T173934Z) and [manifest](../initial-generation/harness-runs/phase9-initial-python3-20261107T173934Z/manifest.json). |
| 2026-11-07 17:41:24 | `python3 .harness/run_harness.py --evidence-dir evidence/final-generation/harness-runs/phase9-format-repair-rerun-20261107T174124Z` | After formatting and line wraps, compilation, Ruff, and Pytest passed; Bandit still failed on the same B105. Overall FAIL. See [format-repair rerun](./harness-runs/phase9-format-repair-rerun-20261107T174124Z) and [manifest](./harness-runs/phase9-format-repair-rerun-20261107T174124Z/manifest.json). |
| 2026-11-07 17:42:27 | User-approved narrow B105 disposition, as recorded in the execution log | A single-line `# nosec B105` annotation with rationale was authorized for the readiness result literal. The Bandit configuration, scan scope, enabled checks, and thresholds were not changed. This specific approval is not the final human ACCEPT/REJECT decision. |
| 2026-11-07 17:42:48 | `python3 .harness/run_harness.py --evidence-dir evidence/final-generation/harness-runs/phase9-final-20261107T174248Z` | Overall PASS; all four required checks passed and Pytest reported no failures, errors, or skips. See [final run directory](./harness-runs/phase9-final-20261107T174248Z) and [manifest](./harness-runs/phase9-final-20261107T174248Z/manifest.json). |
| 2026-11-07 18:40:15.958 | `python3 .harness/run_harness.py --evidence-dir evidence/final-generation/harness-runs/phase9-stage4-20261107T184006Z` | Overall FAIL (exit 1): compile PASS, Ruff FAIL (exit 1; 12 E501 findings in `.harness/run_harness.py` and `tests/test_harness.py`), Bandit PASS, Pytest PASS (87 passed; 398 reported JUnit events; 87 identities; 0 failures, errors, or skips). See [failed Stage 4 manifest](./harness-runs/phase9-stage4-20261107T184006Z/manifest.json), [Ruff output](./harness-runs/phase9-stage4-20261107T184006Z/ruff.stdout.txt), [Pytest JUnit report](./harness-runs/phase9-stage4-20261107T184006Z/pytest-junit.xml), and [run directory](./harness-runs/phase9-stage4-20261107T184006Z). |
| 2026-11-07 18:43:33.879 | `python3 .harness/run_harness.py --evidence-dir evidence/final-generation/harness-runs/phase9-stage4-rerun-20261107T184321Z` | Overall PASS (exit 0): compile PASS, Ruff PASS, Bandit PASS, Pytest PASS; 87 passed, 398 reported JUnit execution events, 87 identities, 0 failures, 0 errors, and 0 skips. See [successful Stage 4 manifest](./harness-runs/phase9-stage4-rerun-20261107T184321Z/manifest.json), [compile result](./harness-runs/phase9-stage4-rerun-20261107T184321Z/compile.result.json), [Ruff result](./harness-runs/phase9-stage4-rerun-20261107T184321Z/ruff.result.json), [Bandit result](./harness-runs/phase9-stage4-rerun-20261107T184321Z/bandit.result.json), [Pytest result](./harness-runs/phase9-stage4-rerun-20261107T184321Z/pytest.result.json), [Pytest output](./harness-runs/phase9-stage4-rerun-20261107T184321Z/pytest.stdout.txt), and [JUnit report](./harness-runs/phase9-stage4-rerun-20261107T184321Z/pytest-junit.xml). Bandit stderr includes five informational parser warnings: `readiness`, `result`, `not`, `a`, and `credential` in the line-specific `# nosec` comment were not recognized as test names or IDs; the scan reported no potential issues. |

## Final validation result

The latest complete Stage 4 validation started at **2026-11-07
18:43:33.879302 UTC** and completed at **2026-11-07 18:43:36.119088 UTC**.
The exact command was
`python3 .harness/run_harness.py --evidence-dir evidence/final-generation/harness-runs/phase9-stage4-rerun-20261107T184321Z`
(harness exit code **0**). Per-check commands, timestamps, output files, exit
codes, and results are recorded in the [successful Stage 4 run manifest](./harness-runs/phase9-stage4-rerun-20261107T184321Z/manifest.json).

| Required check | Exit code | Result |
|---|---:|---|
| Python compilation | 0 | PASS |
| Ruff | 0 | PASS |
| Bandit security scan | 0 | PASS |
| Complete Pytest suite | 0 | PASS |

Pytest collected and passed **87 tests**. The JUnit report records **398
execution events** and **87 testcase identities**, with **0 failures, 0
errors, and 0 skips**. The actual per-check argument arrays, including the
resolved Python executable and JUnit output path, are authoritative in the
manifest. All check result JSON, stdout/stderr logs, and the
[JUnit report](./harness-runs/phase9-stage4-rerun-20261107T184321Z/pytest-junit.xml)
remain preserved alongside it. Bandit emitted the five informational parser
warnings listed in the chronology; no potential security issues were found.

The curated [final inventory](./final-inventory.json) was regenerated after
excluding generated caches and bytecode from the final snapshot. This evidence
curation refreshes the six existing snapshot entries that changed after the
earlier inventory capture. It does not include the harness-runs directory in
the curated source snapshot; run evidence remains separately preserved and
linked above. The successful validation result refers to the exact preserved
Stage 4 rerun.

## Required human review and T040 status

| Evidence item | Status |
|---|---|
| Initial and curated final inventories/snapshots | Present and linked |
| Initial/final harness manifests, per-check outputs, and JUnit reports | Present and linked |
| Failure and repair chronology | Present in the [execution log](../../harness-log.md) and summarized above |
| Harness execution instructions | Present in the [harness README](../../.harness/README.md) |
| `evidence/final-generation/human-review.md` | **Pending / absent**; no decision, reviewer identity, or rationale was supplied |
| T039 | **Incomplete**; requires an explicit human ACCEPT or REJECT |
| T040 | **Incomplete**; the required human-review record cannot yet be verified |

No human decision or rationale is inferred from automated PASS. Once a human
review decision is supplied and recorded under T039, verify that record and
update this manifest before considering T040 complete. Until then, the absent
review record is an outstanding requirement, not a passing evidence item.

## Known limitations

- This manifest does not substitute for the pending human review.
- The harness validates local source/tests only; no real AWS deployment,
  Kubernetes interaction, or external deployment action is performed.
- The application has no user authentication and relies on operator-provided
  actor labels; the local JSON store assumes one writer at a time.
- Automated PASS confirms only the checks and test suite recorded in the
  preserved final run; it is not operational deployment evidence or final
  project acceptance.
