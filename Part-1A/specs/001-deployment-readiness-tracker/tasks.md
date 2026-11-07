# Tasks: CloudOps Deployment Management & Readiness Tracker

**Input**: Design documents from `specs/001-deployment-readiness-tracker/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/cli.md](./contracts/cli.md), [quickstart.md](./quickstart.md)

**Tests**: Tests are included because the constitution, implementation plan, and acceptance criteria require test-first validation of lifecycle, readiness, persistence, and CLI behavior.

**Organization**: Tasks are grouped by user story to enable incremental implementation and validation. Shared package setup and domain/storage foundations precede the stories.

## Phase 1: Setup

**Purpose**: Establish the Python package and test entry point without external dependencies.

- [X] T001 [P] Define Python 3.11+ package metadata, `src` package discovery, and the `cloudops-tracker` console entry point in `pyproject.toml`; declare no runtime dependencies.
- [X] T002 [P] Create the importable package entry files `src/cloudops_tracker/__init__.py` and `src/cloudops_tracker/__main__.py`; route module execution to `cloudops_tracker.cli.main` without implementing CLI behavior yet.

---

## Phase 2: Foundational Test Authoring

**Purpose**: Author the foundational domain and persistence tests before their implementations. These test files may initially fail because the implementation they exercise has not yet been created.

- [X] T012 [P] [US2] Write `tests/test_domain.py` tests for domain-record invariants and every row of the transition table in `specs/001-deployment-readiness-tracker/data-model.md`; assert invalid records and unlisted transitions are rejected, `REJECTED` and `ROLLED_BACK` are terminal, and transitions preserve the last valid state.
- [X] T017 [US3] Write persistence and audit round-trip tests in `tests/test_storage.py` for deployment records, readiness evidence, final operator decisions, timestamps, reasons, status history, failure details, rollback details, and audit event ordering across save/load cycles; compare pre-shutdown and post-restart deployment ID sets and assert 100% inventory preservation for SC-006, independently of repeated retrieval-command success in SC-001.
- [X] T018 [US3] Write storage failure-preservation tests in `tests/test_storage.py` for missing, empty, malformed, schema-invalid (including a syntactically valid file containing both valid and invalid records), unsupported-version, and simulated write-failure inputs; assert a missing store starts empty, every invalid store is rejected as a whole without partial recovery, and original invalid or prior valid JSON bytes remain unchanged on failure.
- [X] T019 [P] [US3] Write service audit tests in `tests/test_service.py` before the corresponding implementation tasks; prove creation, metadata updates, readiness changes, status transitions, allowed approval decisions, failure, and rollback produce timestamped audit events with required reasons and retained evidence references. Prove a disallowed REJECT creates no decision audit event or other mutation. Tests may initially fail until the corresponding implementations are available.

**Checkpoint**: Foundational domain and storage tests are authored before their corresponding implementation tasks.

---

## Phase 3: Foundational Implementation

**Purpose**: Implement the domain and JSON-store behavior against the foundational tests authored in Phase 2.

- [X] T003 Define `Deployment`, `ReadinessCheck`, `HumanApprovalDecision`, `AuditEvent`, and `StateDocument` records plus environment, priority, status, check-status, and decision enums in `src/cloudops_tracker/domain.py`; preserve the data-model constraints verbatim: `deployment_id` is “Unique within the state store; immutable”; `application_name` and `application_version` are “Non-empty after trimming”; `container_image` is “Non-empty after trimming; readiness also requires a non-`latest` tag”; `environment` is “One of `Development`, `Staging`, `Production`”; `priority` is “One of `P1`, `P2`, `P3`, `P4`”; `requester` is a “Non-empty operator-provided name/label”; `created_at` is a “UTC timestamp set when the record is created; immutable”; and `updated_at` is a “UTC timestamp updated on each meaningful record change”. Enforce one of the eight fixed check names per check, status `PASS|FAIL|NOT_CHECKED`, evidence required for PASS, reason required for FAIL/NOT_CHECKED, and a fixed `ACCEPT|REJECT` decision with non-empty actor and reason; enforce the documented audit event ID uniqueness, deployment reference, event types, UTC timestamp, conditional actor/reason, and required details. Require failure details entering `FAILED` and rollback details entering `ROLLED_BACK`.
- [X] T004 Implement versioned JSON decoding and schema/field validation in `src/cloudops_tracker/storage.py`; reject invalid records, duplicate IDs, unknown enum values, and unsupported schema versions with explicit errors instead of resetting the state.
- [X] T005 Implement a storage interface in `src/cloudops_tracker/storage.py` that loads the configured local JSON file and persists a complete snapshot through a same-directory temporary file, file flush/sync, and atomic replacement; treat a missing file as an empty state and preserve the original file on parse, validation, or write failure.

**Checkpoint**: Shared domain and storage implementations are complete. Run tests whose covered implementation is available; complete the T017 persistence/audit round-trip after T020/T021, as specified in the dependencies.

---

## Phase 4: User Story 1 - Create and retrieve deployment requests (Priority: P1) 🎯 MVP

**Goal**: Create unique requests, prevent active duplicates, retrieve records, list/filter/sort them, and update request metadata.

**Independent Test**: Create a valid request, view it by ID, list/filter/sort records, update permitted metadata, reject a duplicate active request, and permit a new request when the matching prior request is inactive.

### Tests for User Story 1

- [X] T006 [US1] Write service tests in `tests/test_service.py` for request creation, generated unique IDs and timestamps, required fields, supported environment/priority values, initialized `DRAFT` state, and rejection of an active duplicate with the same application/environment/version.
- [X] T007 [US1] Add service tests in `tests/test_service.py` for retrieval by ID, listing, environment filtering, P1-to-P4 sorting, metadata updates with reasons, and allowing a duplicate identity when all earlier matching requests are in `FAILED|REJECTED|DEPLOYED|ROLLED_BACK`; include 100 retrieval-command attempts using valid IDs after create/restart and assert at least 99 return the complete matching record for SC-001.

### Implementation for User Story 1

- [X] T008 [US1] Implement request creation and duplicate identity rules in `src/cloudops_tracker/service.py`; treat `DRAFT|VALIDATING|BLOCKED|APPROVED|DEPLOYING` as active and `FAILED|REJECTED|DEPLOYED|ROLLED_BACK` as inactive, compare application names case-insensitively and versions case-sensitively after trimming surrounding whitespace, initialize all eight mandatory checks to `NOT_CHECKED`, and record creation audit evidence.
- [X] T009 [US1] Implement retrieve, list, environment filter, and priority sort operations in `src/cloudops_tracker/service.py`; sort priorities in the documented order P1, P2, P3, P4 and return actionable not-found errors.
- [X] T010 [US1] Implement metadata updates in `src/cloudops_tracker/service.py`; allow only the CLI-contract fields, preserve immutable `deployment_id` and `created_at`, reject invalid values or a resulting active duplicate, and record old/new values, reason, and timestamp.

**Checkpoint**: User Story 1 supports deployment request management independently of status progression.

---

## Phase 5: User Story 2 - Enforce deterministic lifecycle and readiness gates (Priority: P1)

**Goal**: Evaluate mandatory checks independently and enforce the fixed status transition table, evidence gates, and separate final operator decision.

**Independent Test**: Verify each check result, reject PASS without evidence, reject every unlisted lifecycle transition, and confirm APPROVED/DEPLOYING are blocked unless all mandatory checks are PASS with evidence; APPROVED additionally requires a separately recorded final operator ACCEPT.

### Tests for User Story 2

- [X] T011 [P] [US2] Write readiness tests in `tests/test_readiness.py` for all eight checks: application version present, container image present, image tag not `latest`, CPU/memory requests and limits, readiness/liveness probes, test result, upstream/team approval evidence, and rollback plan/version; assert each check has `PASS|FAIL|NOT_CHECKED`, PASS requires evidence, and FAIL/NOT_CHECKED require a reason.
- [X] T013 [US2] Write service tests in `tests/test_service.py` proving the APPROVED gate blocks attempts independently for each mandatory check that is missing, FAIL, NOT_CHECKED, or PASS without evidence, and requires final operator ACCEPT; separately prove the DEPLOYING gate blocks attempts independently for each such check state and does not require final ACCEPT. Test the final REJECT operation from all nine statuses (`DRAFT`, `VALIDATING`, `BLOCKED`, `APPROVED`, `DEPLOYING`, `DEPLOYED`, `FAILED`, `REJECTED`, `ROLLED_BACK`): for DRAFT, VALIDATING, BLOCKED, and APPROVED, verify the decision is recorded and status changes to REJECTED; for DEPLOYING, DEPLOYED, FAILED, REJECTED, and ROLLED_BACK, verify no decision is recorded, no decision audit event is added, and status is unchanged.

### Implementation for User Story 2

- [X] T014 [US2] Implement the eight fixed, deterministic readiness evaluations in `src/cloudops_tracker/readiness.py`; require each PASS to have supporting evidence and each FAIL or NOT_CHECKED result to have a reason, and define `human-approval` only as evidence of required upstream/team approval.
- [X] T015 [US2] Implement the exact lifecycle transition table and transition validator in `src/cloudops_tracker/domain.py`; reject unlisted transitions without changing state, require failure/rollback details when entering `FAILED`/`ROLLED_BACK`, and require all checks PASS with evidence before either `APPROVED` or `DEPLOYING`.
- [X] T016 [US2] Implement readiness updates, readiness eligibility output, and separate final operator ACCEPT/REJECT recording in `src/cloudops_tracker/service.py`; capture actor, timestamp, and reason for decisions, require final ACCEPT before `APPROVED`, transition final REJECT to `REJECTED` only when allowed, and reject a disallowed REJECT entirely without recording a decision or audit event or changing status; ensure the readiness check cannot create/substitute for the final decision.

**Checkpoint**: User Story 2 enforces readiness and lifecycle rules regardless of which CLI command requests a transition.

---

## Phase 6: User Story 3 - Preserve evidence, audit history, and persistent records (Priority: P1)

**Goal**: Retain creation/update/status/readiness/decision/failure/rollback events and safely reload complete local JSON state across restarts.

**Independent Test**: Create and mutate a deployment, restart the application, and verify all records, evidence and audit events remain; malformed or unsupported JSON must produce a visible error without overwriting the original file.

### Tests for User Story 3

### Implementation for User Story 3

- [X] T020 [US3] Implement append-only audit event creation and persistence integration in `src/cloudops_tracker/service.py`; save each deployment mutation and its audit events in the same complete state snapshot, and retain initial/final-generation artifacts, execution logs, test results, and failure/repair evidence as references or recorded evidence.
- [X] T021 [US3] Complete resilient JSON restart behavior in `src/cloudops_tracker/storage.py`; treat a missing store as empty, reject malformed/schema-invalid/unsupported stores in full (including partially invalid record sets), report actionable errors, and never partially recover, silently reset, discard, or overwrite existing records after a failed load or write.

**Checkpoint**: User Story 3 preserves an auditable local record and safely survives application restarts.

---

## Phase 7: User Story 4 - Use the CLI to manage deployment requests and readiness decisions (Priority: P2)

**Goal**: Expose the request, readiness, approval, and lifecycle workflows through the documented `deploy` CLI commands with clear output and safe errors.

**Independent Test**: Run the documented CLI workflows using a disposable store; verify create/view/list/filter/sort/update/readiness/approval/status commands and ensure invalid inputs fail nonzero without corrupting saved data.

### Tests for User Story 4

- [X] T022 [US4] Write CLI contract tests in `tests/test_cli.py` for `deploy create|view|list|update|readiness set|readiness show|approval|status`, including flags, output, exit codes, store-path selection, and stderr diagnostics specified in `specs/001-deployment-readiness-tracker/contracts/cli.md`; execute exactly the fixed C01-C20 matrix in `spec.md`, count a case as passing only when its output marker, output stream, and exit status all match, and assert at least 19/20 (95%) pass for SC-009.
- [X] T023 [US4] Add CLI tests in `tests/test_cli.py` for invalid environments/priorities/IDs, duplicate requests, invalid transitions, missing PASS evidence, missing approval gates, final ACCEPT/REJECT separation, and corrupt JSON; verify a disallowed REJECT from DEPLOYING fails without a decision, decision audit event, or status mutation, and verify `deploy view` displays the exact recorded failure details for a FAILED request and exact recorded rollback details for a ROLLED_BACK request; verify no failed command persists a partial mutation.

### Implementation for User Story 4

- [X] T024 [US4] Implement the `argparse` command tree and `cloudops_tracker.cli.main` in `src/cloudops_tracker/cli.py` for all commands in `specs/001-deployment-readiness-tracker/contracts/cli.md`; keep parsing/output separate from domain rules and route all mutations through `service.py`.
- [X] T025 [US4] Implement readable success output and actionable error reporting in `src/cloudops_tracker/cli.py`; write diagnostics to stderr, return nonzero for invalid input, missing records, duplicate requests, failed gates, invalid transitions, and corrupt storage, and never report success after a failed write.

**Checkpoint**: User Story 4 exposes the completed local management workflow without external deployment actions.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Verify the design against the constitution, acceptance criteria, and user-facing contract.

- [X] T026 [P] Add package usage and local-only scope documentation in `README.md`; document Python 3.11+, CLI invocation, default JSON path, `--store`, and that no AWS/Kubernetes/Jenkins integration or real deployment occurs.
- [X] T027 Run every scenario in `specs/001-deployment-readiness-tracker/quickstart.md` against a disposable JSON store and record results; confirm no external connections or deployment side effects occur.
- [X] T028 Review acceptance checks, test coverage, logs/errors, and evidence retention against `.specify/memory/constitution.md` and `specs/001-deployment-readiness-tracker/spec.md`; document any remaining risk without weakening criteria or deleting/skipping checks.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; T001 and T002 can run in parallel.
- **Foundational Test Authoring (Phase 2)**: T012, T017, T018, and T019 are authored after setup and before their implementation tasks. Authoring does not require the implementation to exist; these tests may initially fail and must not be skipped or weakened.
- **Foundational Implementation (Phase 3)**: Depends on test authoring. T003 follows T012; T004 and T005 follow T017/T018 authoring and T003. The authored tests may be executed as their covered implementation becomes available; the complete T017 persistence/audit round-trip is executed after T020/T021.
- **User Story 1 (Phase 4)**: Depends on Phase 3 implementation. T006/T007 tests are authored before T008-T010; run them after the corresponding service behavior is implemented.
- **User Story 2 (Phase 5)**: Depends on User Story 1. T011/T013 tests are authored before T014-T016; run them after their corresponding readiness, gate, and decision behavior is implemented.
- **User Story 3 (Phase 6)**: T019 audit tests are authored in Phase 2 before audited application behavior is implemented, then executed after the relevant US1/US2 operations and T020 are available. T021 remains covered by the earlier-authored T017/T018.
- **User Story 4 (Phase 7)**: Depends on US1-US3 service and storage behavior. T022/T023 tests are authored before T024/T025 CLI implementation; run them after the corresponding CLI behavior is implemented.
- **Polish (Phase 8)**: Depends on all desired stories being complete.
- **Harness Engineering, Evidence & Final Validation (Phase 9)**: Depends on application implementation and its tests; harness execution and evidence capture occur only after the runner is implemented and documented.

Task IDs are stable identifiers, not a substitute for dependency order. The phase order above governs execution. Tests are authored before implementation; test execution may occur later when its required implementation exists.

### User Story Dependencies

- **User Story 1 (P1)**: Starts after Phase 3; no dependency on another story.
- **User Story 2 (P1)**: Starts after US1 provides deployment records and service operations.
- **User Story 3 (P1)**: T019 audit tests are authored in Phase 2; execute them and complete the US3 persistence/audit behavior after US1/US2 mutations exist.
- **User Story 4 (P2)**: Starts after US1-US3 service and storage behavior is available.

### Parallel Opportunities

- T001 and T002 can run in parallel because they touch separate setup files.
- T012, T017, and T019 can be authored after setup and before foundational implementation because they touch separate test files; T017 and T018 touch the same test file and must be authored sequentially.
- Within US2, T011 and T013 cover separate test files and can be authored in parallel after US1; implementations follow their authored tests.
- T019 audit tests are authored before T008/T010/T014/T015/T016/T020, which implement the audited creation, metadata, readiness, lifecycle, decision, failure, and rollback behavior. Run the tests after those implementations are available.
- Within US4, T022 and T023 both touch `tests/test_cli.py`, so execute sequentially. Implementation follows both.
- Story phases otherwise remain sequential because service and storage files are shared and later stories depend on earlier behavior.

## Parallel Example: Setup

```text
Task: T001 Define package metadata in pyproject.toml
Task: T002 Create package entry files in src/cloudops_tracker/__init__.py and src/cloudops_tracker/__main__.py
```

## Parallel Example: Foundational Tests

```text
Task: T012 Test domain records and lifecycle transitions in tests/test_domain.py
Task: T017 Test persistence/audit round trips in tests/test_storage.py
```

## Implementation Strategy

### MVP First (User Story 1)

1. Complete Setup, author foundational tests, then implement the foundation.
2. Complete US1 request creation, duplicate prevention, retrieval, listing/filtering/sorting, and metadata updates.
3. Validate US1 independently with its service tests and a temporary JSON store.
4. Do not treat US1 as deployment approval or execution; proceed with lifecycle/readiness before a complete tracker release.

### Incremental Delivery

1. Setup + Foundation: package, domain, and safe storage primitives.
2. US1: deployment request management MVP.
3. US2: mandatory readiness evidence, separate final operator decision, lifecycle transitions, and approval gates.
4. US3: complete audit retention, corruption handling, and restart guarantees.
5. US4: CLI workflows and actionable errors.
6. Polish: quickstart validation and constitution/acceptance review.

### Test-First Execution

Author tests before the corresponding implementation tasks. The tests may initially fail because the implementation is missing; that expected red state is not a reason to skip, weaken, or delete them. Execute each test set once its required implementation is available, retain the initial failure and subsequent results as evidence, and require passing results before the dependent phase is accepted. Specifically, author T012/T017/T018/T019 before T003-T005; author T006/T007 before T008-T010; author T011/T013 before T014-T016; and author T022/T023 before T024/T025. T019 is authored before T008/T010/T014/T015/T016/T020, which implement the audited creation, metadata, readiness, lifecycle, decision, failure, and rollback behavior; execute T019 after those relevant implementations. T017/T018 are run sequentially after T020/T021 provide the full persistence and audit behavior. Tests and acceptance thresholds must not be bypassed or weakened to obtain PASS.

## Notes

- Every task uses the required checkbox, sequential ID, optional parallel marker, story label where applicable, and concrete file path.
- `[P]` means tasks touch separate files and have no dependency on incomplete work.
- Story labels map to the four prioritized user stories in `spec.md`.
- `DEPLOYING` and rollback statuses are local record states only; no actual deployment or rollback command is executed.
- Preserve all mandatory readiness checks and acceptance criteria.

---

## Phase 9: Harness Engineering, Evidence & Final Validation

**Purpose**: Add an independent, fail-closed quality harness and preserve a truthful, reviewable record of initial/final generation, failures, repairs, validation outcomes, and human acceptance. The harness validates the local application only and must never perform AWS, Kubernetes, or Jenkins deployment actions.

- [X] T029 Create dedicated tool configuration files `.harness/ruff.toml`, `.harness/bandit.yaml`, and `.harness/pytest.ini`; configure Ruff and Bandit to scan the application and tests as applicable, configure Pytest to collect `tests/`, and verify no mandatory source/tests are excluded, ignored, or weakened.
- [X] T030 Create `.harness/requirements.txt` listing Ruff, Bandit, and Pytest as harness-only tools; verify application runtime dependencies and deployment integrations are not added by this file.
- [X] T031 Implement the repeatable independent runner `.harness/run_harness.py` to invoke Ruff, Bandit, and Pytest against the application using the dedicated configs; verify it executes no application deployment command and contacts no AWS, Kubernetes, or Jenkins service.
- [X] T032 Extend `.harness/run_harness.py` to record each tool's exact command, UTC start/end timestamp, exit code, stdout, stderr, and individual PASS/FAIL result under a configurable evidence directory, defaulting to `evidence/final-generation/harness-runs/<run-id>/`; verify one result record and output log exist for each invoked command.
- [X] T033 Implement fail-closed aggregation in `.harness/run_harness.py`; return nonzero overall if any mandatory tool fails, cannot run, or reports skipped Pytest tests, and verify missing checks, ignored failures, skip/ignore options, or an empty test collection can never produce overall PASS.
- [X] T034 Document tool setup, repeatable invocation, expected outputs, failure behavior, and local-only scope in `.harness/README.md`; verify the documented commands run the harness and explicitly state that no real AWS, Kubernetes, or Jenkins deployments occur.
- [X] T035 Capture truthful initial-generation inputs and baseline validation evidence under `evidence/initial-generation/`; include the actual initial source/test inventory and generation inputs/outputs required by the assignment, initialize `harness-log.md` with the run's UTC timestamp, exact command, and evidence destination before invoking the runner, run `.harness/run_harness.py` with the initial evidence directory, then append actual command outputs and exit codes and verify every recorded result corresponds to an executed command or existing artifact.
- [X] T036 Capture final-generation artifacts and final harness results under `evidence/final-generation/`; include the final source/test inventory, per-command logs and result manifest from `.harness/run_harness.py`, append the final run's timestamp, command, evidence path, and actual outcome to `harness-log.md` immediately after the run, and verify the evidence matches the final tested revision without fabricated outcomes.
- [X] T037 Record and reconcile every harness execution, genuine failure, feedback supplied to the coding agent, repair, rerun, and outcome in repository-root `harness-log.md`; verify each execution has a timestamped entry linked to its evidence path and truthful result, and use explicit “none observed” rather than inventing an event when no failure or repair occurred.
- [X] T038 Preserve original failure outputs and artifacts unchanged under `evidence/initial-generation/` or `evidence/final-generation/failures/` and reference them from `harness-log.md`; verify repairs and reruns create new evidence instead of overwriting or deleting the original failure record, and do not fabricate failures or successes.
- [X] T039 Complete final human review and record an explicit ACCEPT or REJECT decision in `evidence/final-generation/human-review.md` after all required validation; include reviewer identity, UTC timestamp, rationale, harness result, and any unresolved issues, and verify automated PASS alone is not represented as final acceptance.
- [X] T040 Verify evidence structure and documentation completeness in `evidence/final-generation/evidence-manifest.md`; check required initial/final artifacts, per-command results, `harness-log.md`, `.harness/README.md`, and `human-review.md` are present, linked, truthful, and consistent, and record any absent item as a failure rather than claiming completion.

**Checkpoint**: Harness, evidence, log, and final human decision are independently inspectable; a successful application validation cannot hide a mandatory harness failure or missing evidence.
