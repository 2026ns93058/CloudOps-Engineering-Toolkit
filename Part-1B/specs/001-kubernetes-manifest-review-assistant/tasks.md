# Implementation Tasks: Kubernetes Manifest Review Assistant

## Phase 1: Project Setup

- [x] T001 Create the Part 1B Python project structure.
- [x] T002 Configure Python project dependencies and development tools.
- [x] T003 Configure Ruff, Bandit, and pytest.
- [x] T004 Create application entry point and CLI argument handling.
- [x] T005 Create initial unit tests and project run instructions.

## Phase 2: Manifest Input and Processing

- [x] T006 Implement YAML file input and multi-document parsing.
- [x] T007 Use safe YAML parsing and handle malformed input.
- [x] T008 Extract Kubernetes resource identity and metadata.
- [x] T009 Identify supported and unsupported resource kinds.
- [x] T010 Implement Kubernetes Secret detection.
- [x] T011 Redact Secret data and stringData before any model request.
- [ ] T012 Add tests proving original Secret values do not appear in model input, output, logs, or evidence.

## Phase 3: AI Review Application

- [x] T013 Create a versioned AI review prompt.
- [x] T014 Implement local Ollama connectivity and model configuration.
- [x] T015 Implement the model request and response handling.
- [x] T016 Handle unavailable model, timeout, and invalid response errors.
- [x] T017 Implement JSON response parsing.
- [x] T018 Implement review output schema validation.
- [x] T019 Validate finding severity, category, resource identity, and evidence.
- [x] T020 Attach trusted model execution metadata.
- [x] T021 Implement JSON report output.
- [x] T022 Add application tests using controlled model responses.

## Phase 4: Evaluation Dataset

- [x] T023 Define stable issue identifiers for supported review checks.
- [x] T024 Create at least 15 meaningful evaluation cases.
- [x] T025 Include normal and correctly configured manifests.
- [x] T026 Include boundary, ambiguous, and missing-mandatory-field cases.
- [x] T027 Include malformed YAML and unsupported resource cases.
- [x] T028 Include adversarial and prompt-injection cases.
- [x] T029 Include Secret redaction test cases.
- [x] T030 Validate evaluation dataset structure and uniqueness.

## Phase 5: Evaluation Harness

- [x] T031 Implement evaluation dataset loading.
- [x] T032 Implement output schema evaluation.
- [x] T033 Implement structural and safety invariant checks.
- [x] T034 Implement semantic issue matching.
- [x] T035 Penalise false positives and record false negatives.
- [x] T036 Detect duplicate findings and prevent duplicate scoring.
- [x] T037 Calculate per-case semantic scores.
- [x] T038 Calculate aggregate evaluation score.
- [x] T039 Enforce the 80% semantic acceptance threshold.
- [x] T040 Enforce 100% schema and safety invariant requirements.
- [x] T041 Distinguish model execution failures from application and evaluation failures.
- [x] T042 Generate machine-readable evaluation results, including per-case precision, recall, F1, component scores, failure reasons, and aggregate results.
- [x] T043 Add tests for evaluator behaviour and acceptance decisions.

## Phase 6: Harness Execution and Repair

- [x] T044 Implement a single command to run the evaluation pipeline.
- [ ] T045 Run the initial evaluation and preserve its complete evidence.
- [ ] T046 Analyse failed cases and identify root causes.
- [ ] T047 Make targeted prompt or application repairs based on recorded failures.
- [x] T048 Rerun the complete evaluation after repairs.
- [x] T049 Preserve initial and final evaluation results separately.
- [ ] T050 Record commands, timestamps, errors, repairs, and outcomes in the harness log.
- [ ] T051 Verify that no Secret values or credentials appear in evidence.

## Phase 7: Quality Checks and Human Review

- [x] T052 Run Python compilation checks.
- [x] T053 Run Ruff lint checks.
- [x] T054 Run Bandit security checks.
- [x] T055 Run the complete pytest suite.
- [ ] T056 Review all final evaluation failures and limitations.
- [ ] T057 Perform final human review of application output and evidence.
- [ ] T058 Record human acceptance or rejection with reviewer and timestamp.

## Phase 8: Documentation and Submission Readiness

- [x] T059 Complete the Part 1B README with setup and execution instructions.
- [x] T060 Document Ollama installation, model setup, and local execution.
- [ ] T061 Document the output contract and evaluation methodology.
- [x] T062 Document known limitations and model failure handling.
- [ ] T063 Verify all required specification and harness artifacts are present.
- [ ] T064 Verify no API keys, passwords, or other secrets are committed.
- [ ] T065 Verify the repository is ready for the final GitHub submission.

## Completion Rules

1. Tasks MUST be completed in dependency order unless a documented dependency requires otherwise.
2. A task is complete only after its implementation or artifact has been checked.
3. Tests MUST be added for application behaviour and evaluation logic.
4. Initial failures MUST be preserved; they MUST NOT be overwritten by final results.
5. Repairs MUST be traceable to observed failures.
6. Final acceptance requires the evaluation thresholds and safety invariants defined in the specification.
7. Human acceptance MUST be recorded separately from automated evaluation.
8. No task may claim a successful live Kubernetes deployment because this application performs static manifest review only.
