# Data Model: CloudOps Deployment Management & Readiness Tracker

## Conventions

- Timestamps are ISO 8601 UTC values.
- IDs are unique, opaque strings. ID generation is deterministic in tests through an injected generator; production IDs must not collide with existing records.
- Enumerated values are serialized as their documented strings.
- The JSON state document has a schema version. Unknown future schema versions and invalid records are rejected without overwriting the source file.
- Each write persists the deployment change and corresponding audit events in the same complete state snapshot.

## Deployment Request

Represents one local deployment request and its current modeled lifecycle state.

| Field | Required | Rules |
|---|---:|---|
| deployment_id | Yes | Unique within the state store; immutable |
| application_name | Yes | Non-empty after trimming |
| application_version | Yes | Non-empty after trimming |
| container_image | Yes | Non-empty after trimming; readiness also requires a non-`latest` tag |
| environment | Yes | One of `Development`, `Staging`, `Production` |
| priority | Yes | One of `P1`, `P2`, `P3`, `P4`; list ordering uses P1 as highest priority |
| requester | Yes | Non-empty operator-provided name/label |
| created_at | Yes | UTC timestamp set when the record is created; immutable |
| updated_at | Yes | UTC timestamp updated on each meaningful record change |
| status | Yes | One of the lifecycle states below; changes only through the transition rule |
| readiness_checks | Yes | Exactly one record for each required check |
| approval_decision | No | Separate human decision; never inferred from lifecycle status |
| failure_details | No | Required when entering `FAILED` |
| rollback_details | No | Required when entering `ROLLED_BACK` |

### Duplicate identity

An active duplicate is another request with the same application name, environment, and application version while its status is `DRAFT`, `VALIDATING`, `BLOCKED`, `APPROVED`, or `DEPLOYING`. Requests in `FAILED`, `REJECTED`, `DEPLOYED`, or `ROLLED_BACK` do not block a new request. Comparison trims surrounding whitespace and compares application names case-insensitively; application versions are compared case-sensitively because version identifiers may distinguish case.

### Lifecycle states and transitions

Only the following transitions are valid. All other transitions are rejected without changing the last valid status.

| Current status | Allowed next status(es) |
|---|---|
| DRAFT | VALIDATING, REJECTED |
| VALIDATING | BLOCKED, APPROVED, FAILED, REJECTED |
| BLOCKED | VALIDATING, REJECTED |
| APPROVED | DEPLOYING, BLOCKED, REJECTED |
| DEPLOYING | DEPLOYED, FAILED, ROLLED_BACK |
| DEPLOYED | FAILED, ROLLED_BACK |
| FAILED | ROLLED_BACK |
| REJECTED | None |
| ROLLED_BACK | None |

Entering `APPROVED` or `DEPLOYING` requires every mandatory check to be PASS with evidence. Entering `APPROVED` additionally requires a separate human ACCEPT decision recorded before the status change. A human REJECT decision leads to `REJECTED` through an allowed transition.

## Readiness Check

Each deployment has exactly one independent check for each item below:

1. Application version is present.
2. Container image is present.
3. Container image tag is not `latest`.
4. CPU and memory requests and limits are recorded.
5. Readiness and liveness probes are confirmed.
6. Required test result is PASS.
7. Required upstream/team approval evidence is recorded.
8. Rollback plan and rollback version are documented.

| Field | Required | Rules |
|---|---:|---|
| check_name | Yes | One of the eight fixed mandatory check names |
| status | Yes | `PASS`, `FAIL`, or `NOT_CHECKED` |
| evidence | Conditional | Non-empty supporting evidence is mandatory for `PASS` |
| reason | Conditional | Non-empty explanation is mandatory for `FAIL` or `NOT_CHECKED` |
| updated_at | Yes | UTC time of the latest check result |

No missing, failed, unchecked, or evidence-free PASS result satisfies an approval gate.

## Human Approval Decision

Represents an explicit decision separate from deployment lifecycle status.

| Field | Required | Rules |
|---|---:|---|
| decision | Yes | `ACCEPT` or `REJECT` |
| actor | Yes | Non-empty operator-provided name/label; no authentication is provided by this local tool |
| decided_at | Yes | UTC decision timestamp |
| reason | Yes | Non-empty rationale |

The final operator's ACCEPT decision must exist before transition to `APPROVED`, in addition to every mandatory readiness check being PASS with evidence. A REJECT decision leads to `REJECTED` when permitted by the transition table. The `human-approval` readiness check records required upstream/team approval evidence and is independent of this final operator decision. Automated readiness PASS is not a human decision.

## Audit Event

Append-only application record of a meaningful action.

| Field | Required | Rules |
|---|---:|---|
| event_id | Yes | Unique within the state store |
| deployment_id | Yes | References an existing deployment |
| event_type | Yes | Creation, metadata update, readiness update, status transition, human decision, failure, or rollback |
| occurred_at | Yes | UTC timestamp |
| actor | Conditional | Required for operator decisions and updates |
| reason | Conditional | Required for status transitions, readiness outcomes, metadata updates, failure, rollback, and human decisions |
| details | Yes | Structured summary and/or evidence reference sufficient to audit the action |

Audit events are retained with deployment records across application restarts and are not edited or deleted by normal application commands.

## State Document

One local JSON document contains:

- `schema_version`: supported format version.
- `deployments`: deployment records and their readiness/decision data.
- `audit_events`: append-only events for all recorded deployment actions.
- Evidence references or text sufficient to locate and explain supporting artifacts, test results, logs, failures, and repairs.

Missing state means an empty initial store. Malformed JSON, a syntactically valid document containing any invalid or incomplete record, or an unsupported version causes an explicit load error for the whole store and leaves the original file byte-for-byte untouched. The loader does not partially recover valid records from an invalid store.
