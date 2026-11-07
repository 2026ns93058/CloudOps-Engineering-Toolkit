# CLI Contract

## Scope and conventions

- The command-line interface manages local records only. It never invokes a deployment platform or executes a deployment.
- Invocation form: `python -m cloudops_tracker deploy <command> ...`.
- The default state file is `data/deployments.json` relative to the current working directory. A global `--store PATH` option selects another local JSON file.
- Successful commands exit with code `0`. Invalid arguments, missing records, duplicate active requests, invalid transitions, failed readiness gates, and invalid/corrupt state exit nonzero, print an actionable diagnostic to standard error, and do not persist a partial change.
- List output may be filtered by environment and sorted by priority, in order P1, P2, P3, P4.
- Every meaningful mutation requires or records a reason and creates a timestamped audit event.

## Commands

### Create a deployment request

```text
python -m cloudops_tracker deploy create
  --application NAME
  --version VERSION
  --image IMAGE
  --environment Development|Staging|Production
  --priority P1|P2|P3|P4
  --requester NAME
```

Creates a uniquely identified request in `DRAFT`, initializes all mandatory checks to `NOT_CHECKED`, records a creation event, and prints the new deployment ID. Reject a duplicate if an active request has the same application, environment, and version.

### List requests

```text
python -m cloudops_tracker deploy list [--environment Development|Staging|Production] [--sort priority]
```

Lists requests; when priority sorting is selected, P1 precedes P2, P3, then P4.

### View a request

```text
python -m cloudops_tracker deploy view DEPLOYMENT_ID
```

Displays request fields, status, readiness checks and evidence/reasons, human decision, audit history, and any recorded failure details or rollback details.

### Update request metadata

```text
python -m cloudops_tracker deploy update DEPLOYMENT_ID
  [--application NAME]
  [--version VERSION]
  [--image IMAGE]
  [--environment Development|Staging|Production]
  [--priority P1|P2|P3|P4]
  [--requester NAME]
  --reason REASON
```

Updates only supplied fields. Reject invalid values and any resulting duplicate active request. Record old/new values, reason, and timestamp. Immutable deployment ID and creation time cannot be changed.

### Record a readiness result

```text
python -m cloudops_tracker deploy readiness set DEPLOYMENT_ID
  --check CHECK_NAME
  --status PASS|FAIL|NOT_CHECKED
  [--evidence TEXT]
  [--reason TEXT]
```

PASS requires non-empty supporting evidence. FAIL and NOT_CHECKED require a reason. For `--check human-approval`, this evidence records an upstream or team approval required for readiness; it is not the final operator decision. The command records the result and audit event and cannot remove, disable, or bypass a mandatory check.

### Inspect readiness

```text
python -m cloudops_tracker deploy readiness show DEPLOYMENT_ID
```

Shows every mandatory check and whether the request is eligible for APPROVED or DEPLOYING, including unmet check names and reasons.

### Record a human decision

```text
python -m cloudops_tracker deploy approval DEPLOYMENT_ID
  --decision ACCEPT|REJECT
  --actor NAME
  --reason REASON
```

Records the final operator's separate decision with actor, timestamp, and reason. This decision is independent of the `human-approval` readiness check, which represents required upstream/team approval evidence. A final ACCEPT is recorded before the lifecycle transition to APPROVED and does not change lifecycle status by itself. A final REJECT moves the request to `REJECTED` only when that transition is allowed. If the current status does not allow transition to `REJECTED`, the command fails without recording the decision, adding a decision audit event, or changing lifecycle status. Neither upstream/team evidence nor automated readiness results can create or substitute for this final operator decision.

### Change lifecycle status

```text
python -m cloudops_tracker deploy status DEPLOYMENT_ID
  --to STATUS
  --reason REASON
  [--failure-details TEXT]
  [--rollback-details TEXT]
```

Accepts only transitions in the [lifecycle table](../data-model.md#lifecycle-states-and-transitions). Rejects all other transitions without changing state. Transitions into APPROVED or DEPLOYING require every mandatory readiness check PASS with evidence; APPROVED also requires a separately recorded human ACCEPT. DEPLOYING is a tracked simulated state, not an actual deployment action.

## Fixed readiness check names

- `application-version`
- `container-image`
- `image-tag-not-latest`
- `resource-configuration`
- `health-probes`
- `test-result`
- `human-approval` — evidence of required upstream/team approval; not the final operator ACCEPT/REJECT decision
- `rollback-plan`

## State and error guarantees

- JSON is validated on load, including the schema version and record fields.
- Missing state starts an empty local store. Malformed or unsupported state produces a clear error and is not overwritten.
- A mutation is written as a complete state snapshot using a temporary file and atomic replacement. A failed write does not report success.
- The initial implementation assumes one writer at a time; it does not promise conflict-free concurrent CLI processes.
