# Implementation Plan: CloudOps Deployment Management & Readiness Tracker

**Branch**: `001-deployment-readiness-tracker` | **Date**: 2026-11-07 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/001-deployment-readiness-tracker/spec.md`

## Summary

Build a local-only Python CLI for recording deployment requests, evaluating evidence against fixed readiness checks, enforcing an explicit lifecycle transition table, and retaining audit history in JSON. The CLI will use standard-library facilities, a single local state document, and domain functions that enforce gates independently from user-facing commands. It will never contact external deployment platforms or execute deployments.

## Technical Context

**Language/Version**: Python 3.11+ (the available environment is Python 3.13.17; no project minimum is currently declared)

**Primary Dependencies**: Python standard library only; `argparse` for CLI parsing, `dataclasses` and `enum` for domain records, `json` and `pathlib` for persistence

**Storage**: One versioned, project-local JSON state file by default; allow an explicit local file path for test isolation and operator selection

**Testing**: Author tests with standard-library `unittest` and run/collect them through Pytest in the mandatory harness; use isolated temporary JSON files and deterministic injected clock/ID sources. Ruff, Bandit, and Pytest are independent harness checks, and any failed or skipped mandatory check fails the overall run.

**Target Platform**: Local command-line use on supported Python platforms; no network or external services required

**Project Type**: Single Python CLI application

**Performance Goals**: Interactive completion for ordinary local tracking use; no throughput or latency service-level objective is specified

**Constraints**: Local simulation only; no AWS, Kubernetes, Jenkins, external deployment integrations, or actual deployment execution. No secrets or credentials. Readiness checks and approval gates are mandatory and cannot be bypassed. A missing JSON store starts empty; malformed, schema-invalid, or partially invalid stores fail closed, are preserved unchanged, and are never partially recovered or overwritten. Harness failures, including skipped tests, cannot yield overall PASS.

**Scale/Scope**: Single local operator workflow and a modest number of deployment records in one JSON file. Initial design assumes one writer at a time; concurrent multi-process edits are not guaranteed.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Spec-driven delivery**: PASS — requirements, user journeys, edge cases, and measurable outcomes are documented in the feature spec.
- **Evidence-based engineering and test-first quality**: PASS — the design retains evidence for every readiness PASS, documents executable validation scenarios, and requires unit, persistence, CLI, and state-transition tests before implementation is accepted.
- **Security and compliance by design**: PASS — no credentials are collected or persisted; no external service connections or deployment side effects are in scope.
- **Maintainability and observability**: PASS — domain rules, CLI, persistence, and output are separated; errors are explicit and lifecycle/readiness actions are auditable.
- **Deployment integrity and readiness**: PASS — the clarified fixed transition table, active duplicate statuses, mandatory evidence gates, and separate human decision are preserved in domain rules.
- **Evidence and human oversight**: PASS — audit events retain timestamps, reasons, decisions, test results, logs, and evidence references; automated PASS cannot replace ACCEPT/REJECT.
- **Local-only scope**: PASS — the application records and evaluates user-entered evidence only; it performs no real AWS deployment and does not interact with Kubernetes.
- **Harness integrity**: PASS — acceptance criteria and mandatory checks remain fixed; any future change requires documented rationale and human approval.

No constitution violations or exceptions are required.

## Project Structure

### Documentation (this feature)

```text
specs/001-deployment-readiness-tracker/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── cli.md
└── tasks.md

.harness/
├── README.md
├── run_harness.py
├── requirements.txt
├── ruff.toml
├── bandit.yaml
└── pytest.ini

evidence/
├── initial-generation/
└── final-generation/
    ├── harness-runs/
    ├── failures/
    ├── human-review.md
    └── evidence-manifest.md

harness-log.md
```

### Source Code (repository root)

```text
src/
└── cloudops_tracker/
    ├── __init__.py
    ├── __main__.py
    ├── cli.py
    ├── domain.py
    ├── readiness.py
    ├── service.py
    └── storage.py

tests/
├── test_cli.py
├── test_domain.py
├── test_readiness.py
├── test_service.py
└── test_storage.py
```

**Structure Decision**: Use one importable package under the existing `src/` directory, with a thin CLI layer, pure lifecycle/readiness rules, service operations, and JSON storage. Tests are organized by behavior and use temporary directories. The project currently has empty `src/` and `tests/` directories, so this layout adds structure without introducing a second application or external dependency.

The independent `.harness/` runner invokes Ruff, Bandit, and Pytest using checked-in configuration, captures each command and its timestamp, output, exit code, and result, and exits nonzero if any mandatory check fails or tests are skipped. Application tests use `unittest` and are collected by Pytest; harness tooling remains separate from application runtime dependencies. Initial and final evidence are stored in their respective `evidence/` directories, and every run/failure/repair/rerun is recorded in `harness-log.md`. The initial baseline runner execution must be logged before it starts.

## Complexity Tracking

No constitution violations; no complexity exceptions requested.
