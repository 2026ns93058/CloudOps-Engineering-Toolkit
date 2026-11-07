# CloudOps Deployment Management & Readiness Tracker

A local Python application for recording deployment requests, readiness evidence, lifecycle decisions, and audit history. It models deployment progress only; it does not deploy software.

## Requirements

- Python 3.11 or newer
- No application runtime dependencies beyond the Python standard library

This project uses a Python `src` layout: the `cloudops_tracker` package is in
`src/cloudops_tracker`. From the `Part-1A` directory, set `PYTHONPATH=src` to
run the CLI without installing the package.

## Run the CLI

Show help:

```sh
PYTHONPATH=src python3 -m cloudops_tracker --help
```

The following examples use the same command prefix. Create a deployment
request:

```sh
PYTHONPATH=src python3 -m cloudops_tracker deploy create \
  --application inventory-api \
  --version 2.4.1 \
  --image registry.local/inventory-api:2.4.1 \
  --environment Staging \
  --priority P1 \
  --requester operator
```

The command prints the created deployment ID. Use it to view that deployment:

```sh
PYTHONPATH=src python3 -m cloudops_tracker deploy view <deployment-id>
```

List deployments, optionally filtering by environment or sorting by priority:

```sh
PYTHONPATH=src python3 -m cloudops_tracker deploy list
PYTHONPATH=src python3 -m cloudops_tracker deploy list \
  --environment Staging \
  --sort priority
```

Update deployment metadata; at least one metadata field may be supplied, and
`--reason` is required:

```sh
PYTHONPATH=src python3 -m cloudops_tracker deploy update <deployment-id> \
  --version 2.4.2 \
  --reason "Updating to the approved application version"
```

The default JSON store is the local file `data/deployments.json`, relative to
the current working directory. Use the global `--store PATH` option before
`deploy` to select another local JSON file, such as a disposable store:

```sh
PYTHONPATH=src python3 -m cloudops_tracker \
  --store /tmp/deployments.json deploy list
```

Available commands are `deploy create`, `deploy view`, `deploy list`,
`deploy update`, `deploy readiness set`, `deploy readiness show`,
`deploy approval`, and `deploy status`. Use
`PYTHONPATH=src python3 -m cloudops_tracker --help` or
`PYTHONPATH=src python3 -m cloudops_tracker deploy --help` for command help.
The full command contract and validation scenarios are in [the CLI contract](specs/001-deployment-readiness-tracker/contracts/cli.md) and [the quickstart](specs/001-deployment-readiness-tracker/quickstart.md).

Commands report invalid input and failed readiness or lifecycle gates to standard error and return a nonzero exit status. State changes and their audit events are saved together to the local JSON store. Invalid existing JSON is rejected rather than replaced.

## Scope and operational limits

- This tool simulates local deployment-readiness tracking; it does not deploy to AWS, Kubernetes, or any external infrastructure.
- It has no AWS, Kubernetes, Jenkins, or other external deployment integration and makes no deployment or rollback calls.
- Readiness results are based on evidence supplied by the operator; the application does not independently verify external systems.
- Human decisions are recorded as operator-provided actor labels. This application does not authenticate users.
- JSON persistence assumes one writer at a time; concurrent multi-process edits are not guaranteed.

## Validation status

Phase 8 validation used disposable local JSON stores. The documented CLI workflows passed for create/view/list/filter/sort, duplicate and invalid-input rejection, metadata updates, readiness and approval gates, audit retention across separate CLI processes, failure and rollback details, inactive duplicate reuse, terminal transition rejection, and corrupt-store preservation. No external deployment calls were made.

The fixed CLI acceptance matrix passed 20 of 20 cases, and the pre-harness `unittest` baseline passed 54 tests. An earlier historical initial-generation run passed 60 Pytest tests. The latest successful full Phase 9 harness run is documented in [.harness/README.md](.harness/README.md) and recorded in the evidence manifest: compilation, Ruff, Bandit, and Pytest passed; Pytest passed 87 test identities and reported 398 JUnit execution events, with zero failures, errors, or skips. This automated validation and the manual CLI walkthrough do not validate or perform real deployments; automated PASS remains subject to separate human acceptance.
