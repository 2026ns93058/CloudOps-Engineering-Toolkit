# CloudOps Deployment Management & Readiness Tracker

A local Python application for recording deployment requests, readiness evidence, lifecycle decisions, and audit history. It models deployment progress only; it does not deploy software.

## Requirements

- Python 3.11 or newer
- No application runtime dependencies beyond the Python standard library

## Run the CLI

From this directory, invoke the module:

```sh
python -m cloudops_tracker --store data/deployments.json deploy create \
  --application inventory-api \
  --version 2.4.1 \
  --image registry.local/inventory-api:2.4.1 \
  --environment Staging \
  --priority P1 \
  --requester operator
```

The default JSON state file is `data/deployments.json`, relative to the current working directory. Supply `--store PATH` before `deploy` to select another local JSON file, such as a disposable file for testing:

```sh
python -m cloudops_tracker --store /tmp/deployments.json deploy list
```

Available commands are `deploy create`, `view`, `list`, `update`, `readiness set`, `readiness show`, `approval`, and `status`. Use `python -m cloudops_tracker --help` or `python -m cloudops_tracker deploy --help` for command help. The full command contract and validation scenarios are in [the CLI contract](specs/001-deployment-readiness-tracker/contracts/cli.md) and [the quickstart](specs/001-deployment-readiness-tracker/quickstart.md).

Commands report invalid input and failed readiness or lifecycle gates to standard error and return a nonzero exit status. State changes and their audit events are saved together to the local JSON store. Invalid existing JSON is rejected rather than replaced.

## Scope and operational limits

- This is a local request-management and readiness tracker, not a deployment executor.
- It has no AWS, Kubernetes, Jenkins, or other external deployment integration and makes no deployment or rollback calls.
- Readiness results are based on evidence supplied by the operator; the application does not independently verify external systems.
- Human decisions are recorded as operator-provided actor labels. This application does not authenticate users.
- JSON persistence assumes one writer at a time; concurrent multi-process edits are not guaranteed.

## Validation status

Phase 8 validation used disposable local JSON stores. The documented CLI workflows passed for create/view/list/filter/sort, duplicate and invalid-input rejection, metadata updates, readiness and approval gates, audit retention across separate CLI processes, failure and rollback details, inactive duplicate reuse, terminal transition rejection, and corrupt-store preservation. No external deployment calls were made.

The fixed CLI acceptance matrix passed 20 of 20 cases, and full `unittest` discovery passed 54 tests. The quickstart's `python .harness/run_harness.py` command could not run because the runner does not exist yet; harness implementation and execution are Phase 9 tasks. Ruff is not installed in the current environment. These are validation-tooling limitations, not changes to acceptance criteria.
