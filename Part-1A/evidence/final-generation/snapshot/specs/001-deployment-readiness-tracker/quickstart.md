# Quickstart: Deployment Tracker Validation

This guide describes end-to-end checks for the planned local application. It contains commands and expected behavior, not implementation code.

## Prerequisites

- Python 3.11 or newer is available.
- Run commands from the repository root.
- The default state file is `data/deployments.json`. Use a disposable `--store` path for validation so existing operator data is not changed.
- The application has no AWS, Kubernetes, Jenkins, or other external service prerequisites.

## Automated validation

Run the independent harness (Ruff, Bandit, and Pytest; Pytest collects the `unittest`-based application tests):

```sh
python3 .harness/run_harness.py
```

Expected: each mandatory tool has its own timestamped command, exit code, output, and PASS/FAIL record. Any tool failure, inability to run a mandatory tool, skipped test, or empty test collection fails the overall harness. Application tests use temporary storage and do not require external services.

## End-to-end CLI scenarios

The command examples below assume the CLI contract in [contracts/cli.md](./contracts/cli.md). Replace `<store>` with a disposable local JSON path and `<id>` with the ID printed by creation.

### Create, retrieve, filter, and sort

```sh
python -m cloudops_tracker --store <store> deploy create \
  --application inventory-api --version 2.4.1 --image registry.local/inventory-api:2.4.1 \
  --environment Staging --priority P1 --requester operator
python -m cloudops_tracker --store <store> deploy view <id>
python -m cloudops_tracker --store <store> deploy list --environment Staging --sort priority
```

Expected: the request is created in DRAFT with a unique ID and all mandatory checks initially NOT_CHECKED. Viewing shows the record and history; listing filters to Staging and places P1 before lower priorities.

### Reject duplicates and invalid values

Attempt to create another active request with the same application, environment, and version, and attempt creation with an unsupported environment or priority.

Expected: each invalid request exits nonzero with an actionable diagnostic and does not alter the stored record. After the original request reaches FAILED, REJECTED, DEPLOYED, or ROLLED_BACK, a new request with that identity is permitted.

### Enforce readiness, evidence, and separate human approval

```sh
python -m cloudops_tracker --store <store> deploy status <id> --to VALIDATING --reason "Begin validation"
python -m cloudops_tracker --store <store> deploy status <id> --to APPROVED --reason "Request approval"
```

Expected: the approval attempt is rejected while any mandatory check is NOT_CHECKED or FAIL, or when a PASS lacks evidence. A valid ACCEPT decision must be separately recorded with actor and reason before the status can become APPROVED; the APPROVED state itself cannot satisfy that gate. An invalid or omitted transition is rejected without changing the prior status.

After supplying valid evidence for every check and recording a separate ACCEPT decision, an allowed transition to APPROVED and then DEPLOYING may be recorded. DEPLOYING remains a local simulated status and triggers no deployment.

### Preserve audit history and JSON across restarts

Record a metadata or readiness update with a reason, then run a second CLI process and view the deployment.

Expected: the updated values, evidence, human decision, and timestamped audit events remain present. Invalid JSON or an unsupported schema version produces a visible error and leaves the original state file unchanged.

### Exercise failure and rollback paths

From DEPLOYING, record FAILED with failure details or ROLLED_BACK with rollback details and a reason. From DEPLOYED, exercise the allowed FAILED or ROLLED_BACK path. Attempt an unlisted transition from terminal REJECTED or ROLLED_BACK.

Expected: allowed transitions preserve their details and audit events; all unlisted transitions fail without changing status. No actual deployment or rollback operation is performed.

## Validation scope

The acceptance run must verify all mandatory checks independently, exact active/inactive duplicate statuses, every row in the [lifecycle transition table](./data-model.md#lifecycle-states-and-transitions), recoverable behavior for invalid storage, and explicit human decision records. Acceptance criteria and mandatory checks must not be weakened to obtain passing results.
