# Feature Specification: CloudOps Deployment Management & Readiness Tracker

**Feature Branch**: 001-deployment-readiness-tracker

**Created**: 2026-11-07

**Status**: Draft

**Input**: User description: "Build a Python-based CLI application named CloudOps Deployment Management & Readiness Tracker. Problem: DevOps and SRE teams need a reliable way to record deployment requests, track deployment lifecycle states, verify readiness evidence, and prevent deployments from progressing when mandatory checks have not passed. Informal tracking can lead to duplicate deployment requests, incomplete evidence, invalid status transitions, and deployments proceeding without required approvals or rollback plans. The application must provide the following capabilities: 1. Deployment request management - Create a deployment request with a unique deployment ID. - Record application name, application version, container image, environment, priority, requester, and creation timestamp. - Support Development, Staging, and Production environments. - Support priorities P1, P2, P3, and P4. - Prevent duplicate active deployment requests for the same application, environment, and version. - View a deployment by ID. - List deployment requests. - Filter deployment requests by environment. - Sort deployment requests by priority. 1. Deployment lifecycle management - Define documented and deterministic deployment status transitions. - Support statuses such as DRAFT, VALIDATING, BLOCKED, APPROVED, DEPLOYING, DEPLOYED, FAILED, REJECTED, and ROLLED_BACK. - Reject invalid status transitions. - Record every status change with a timestamp and reason. - Do not allow APPROVED or DEPLOYING unless all mandatory readiness checks pass. 1. Deployment readiness tracking Track these mandatory checks independently: - Application version is present. - Container image is present. - Container image tag is not latest. - CPU and memory requests and limits are recorded. - Readiness and liveness probes are confirmed. - Required test result is PASS. - Required approval is recorded. - Rollback plan and rollback version are documented. Each readiness check must have PASS, FAIL, or NOT_CHECKED status and supporting evidence or a reason. A deployment must remain ineligible for approval when any mandatory check is FAIL or NOT_CHECKED. 1. History and audit - Record deployment creation and updates. - Maintain an audit history of status changes and readiness-check changes. - Track failure and rollback details. - Preserve timestamps and reasons for important actions. 1. Data persistence - Store deployment information locally in JSON format. - Load saved records when the application starts. - Preserve deployment and audit history between application executions. - Handle missing or invalid JSON data safely without silently losing existing records. 1. CLI experience - Provide clear commands and readable output. - Validate user input and display actionable error messages. - Support creating, viewing, listing, updating, checking readiness, and managing deployment status. Constraints: - Use Python. - Keep the implementation modular and maintainable. - Use deterministic business rules for lifecycle transitions and readiness checks. - Do not connect to AWS, Kubernetes clusters, Jenkins, or external deployment systems. - Do not execute actual deployments. - This is a local simulation that evaluates evidence entered by the user. - Do not store credentials, secrets, or tokens. - Do not allow application logic to bypass mandatory readiness checks. - Do not weaken acceptance criteria or remove required checks to obtain a passing result. Acceptance expectations: - Valid deployment requests can be created and retrieved. - Duplicate active requests are rejected. - Invalid environments, priorities, and status transitions are rejected. - All mandatory readiness checks are independently evaluated. - Approval and deployment progression are blocked until all mandatory checks pass. - Audit history records meaningful changes with timestamps. - JSON persistence survives application restarts. - Invalid or incomplete input produces clear errors without corrupting saved records. Before implementation, identify ambiguities and ask clarification questions. Do not generate application code during this specification stage."

## Clarifications

### Session 2026-11-07

- Q: Must human approval be recorded independently of the APPROVED lifecycle status? → A: Yes. Record a separate human ACCEPT or REJECT decision with actor, timestamp, and reason; record it before any transition to APPROVED, so the status does not determine its own approval evidence.
- Q: Which lifecycle transitions are allowed, including failure and rollback paths? → A: Only transitions in the explicit lifecycle table are allowed; all omitted transitions are rejected.
- Q: Which statuses count as active for duplicate prevention? → A: DRAFT, VALIDATING, BLOCKED, APPROVED, and DEPLOYING are active; FAILED, REJECTED, DEPLOYED, and ROLLED_BACK are inactive. This definition is appropriate for allowing a new request after a prior request reaches a terminal outcome.
- Q: What evidence is required for readiness-check results? → A: Each check records PASS, FAIL, or NOT_CHECKED; PASS requires supporting evidence, while FAIL and NOT_CHECKED require a reason.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Create and retrieve deployment requests (Priority: P1)

DevOps and SRE teams need a structured way to record a deployment request with all required metadata and retrieve it later for review or follow-up. This ensures every deployment has a unique record and that duplicate requests are prevented before work proceeds.

**Why this priority**: Without a reliable record, teams cannot prevent duplicate requests or determine which deployment is active for a particular application, environment, and version.

**Independent Test**: A user can create a valid deployment request, retrieve it by ID, and see that duplicate active requests for the same application, environment, and version are rejected.

**Acceptance Scenarios**:

1. **Given** a valid application and environment, **When** a deployment request is created with unique metadata, **Then** the system stores the request and returns the deployment ID.
2. **Given** an active deployment record already exists for the same application, environment, and version, **When** a second request is created, **Then** the system rejects the request with a clear duplicate-error message.
3. **Given** a deployment record exists, **When** the user requests the record by ID, **Then** the system returns the stored metadata and current status.
4. **Given** the existing request for the same application, environment, and version is FAILED, REJECTED, DEPLOYED, or ROLLED_BACK, **When** the user creates a new request, **Then** the inactive request does not block creation.

---

### User Story 2 - Enforce deterministic deployment lifecycle and readiness gates (Priority: P1)

Operators need deterministic lifecycle rules so that a deployment cannot advance to APPROVED or DEPLOYING without evidence that all mandatory checks have passed. This prevents accidental promotions and keeps the process auditable.

**Why this priority**: The highest-risk operational failure is allowing a deployment to proceed without approved readiness evidence, rollback planning, or required checks.

**Independent Test**: Place a request in VALIDATING, a state from which APPROVED is allowed, and test that APPROVED is blocked until every mandatory readiness check is PASS with evidence and a separate human ACCEPT is recorded. Separately place a request in APPROVED, a state from which DEPLOYING is allowed, and test that DEPLOYING is blocked until every mandatory readiness check is PASS with evidence. Test invalid transitions, including DRAFT to APPROVED and DRAFT to DEPLOYING, separately from readiness-gate tests.

**Acceptance Scenarios**:

1. **Given** a deployment in VALIDATING with every mandatory readiness check PASS and a separate human ACCEPT decision recorded, **When** the user requests approval, **Then** the system may transition it to APPROVED under the documented lifecycle rules.
2. **Given** any mandatory readiness check is FAIL or NOT_CHECKED, **When** the user attempts to mark the deployment APPROVED or DEPLOYING, **Then** the system rejects the transition and records the reason.
3. **Given** a status transition is not in the defined lifecycle state map, **When** the user attempts it, **Then** the system rejects the transition and keeps the last valid state.
4. **Given** a deployment has no separate human ACCEPT decision, **When** the user attempts to transition it to APPROVED, **Then** the system rejects the transition without treating the requested status as approval evidence.
5. **Given** a deployment is in any terminal state, **When** the user attempts an unlisted transition, **Then** the system rejects it; a new request may be created subject to duplicate-active rules.
6. **Given** a readiness check is marked PASS without supporting evidence, **When** the user records the result, **Then** the system rejects it and the check cannot satisfy an approval gate.
7. **Given** the current lifecycle state does not allow transition to REJECTED, **When** a final operator REJECT is requested, **Then** the operation is rejected without recording the decision, adding a decision audit event, or changing the lifecycle status.

---

### User Story 3 - Preserve evidence, audit history, and persistent records (Priority: P1)

Teams must retain deployment creation records, status updates, readiness changes, and failure or rollback details across application restarts without losing data or silently masking invalid JSON. Audit events ensure traceability for investigations and human approval decisions.

**Why this priority**: Without evidence retention and persistence, an organization cannot prove what happened, why a change was accepted, or whether a deployment should be rolled back.

**Independent Test**: A user records a deployment update, closes the application, reopens it, and verifies the record and audit history remain available and valid.

**Acceptance Scenarios**:

1. **Given** a deployment request is updated, **When** the status or readiness evidence changes, **Then** the system stores a timestamped audit record with a reason.
2. **Given** the system has persisted JSON data, **When** it starts again, **Then** it loads the saved deployments and their audit history without losing valid records.
3. **Given** the JSON data is missing or malformed, **When** the application starts, **Then** a missing store starts empty, while an invalid store is rejected in full, reported with an actionable error, and left unchanged without partial recovery.

---

### User Story 4 - Use the CLI to manage deployment requests and readiness decisions (Priority: P2)

Operators need clear command-driven workflows for creating, viewing, filtering, updating, and checking readiness without interacting with external systems. The CLI must provide actionable error messages and deterministic rules for valid input.

**Why this priority**: A command-line workflow is the primary interface for local deployment tracking, and usability directly affects operational accuracy.

**Independent Test**: A user can run create, view, list, filter, and update commands and receive clear validation feedback for invalid environment, priority, or lifecycle transitions.

**Acceptance Scenarios**:

1. **Given** a valid CLI command, **When** the user runs it, **Then** the system performs the requested action and prints readable output.
2. **Given** invalid environment or priority input, **When** the user submits the command, **Then** the system rejects the input and explains the valid options.
3. **Given** incomplete or invalid input, **When** the user attempts a save or transition, **Then** the system prevents corruption and reports the problem clearly.

---

### Edge Cases

- A user attempts to create a second active deployment for the same application, environment, and version while the original request is still active.
- A new request for the same application, environment, and version is attempted after the existing request is FAILED, REJECTED, DEPLOYED, or ROLLED_BACK; the inactive record does not block creation.
- A user attempts to move a deployment from DRAFT to APPROVED before all mandatory checks are PASS.
- A user attempts to enter APPROVED without a separately recorded human ACCEPT decision.
- A user changes a readiness check without recording supporting evidence or a reason.
- A user marks a readiness check PASS without supporting evidence.
- The local JSON file is missing, empty, invalid, or partially corrupted.
- A user enters an unsupported environment, invalid priority, or non-existent deployment ID.
- A user attempts to mark a deployment success while the rollback plan or rollback version is missing.
- A user records a PASS result for a readiness check that was previously FAIL or NOT_CHECKED without documenting the reason and evidence.
- The JSON document is syntactically valid but contains one invalid or incomplete record; the application must reject the entire document and preserve it, not silently load only the valid records.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST create a deployment request with a unique deployment ID and capture the application name, application version, container image, environment, priority, requester, and creation timestamp.
- **FR-002**: The system MUST support the environments Development, Staging, and Production and the priorities P1, P2, P3, and P4.
- **FR-003**: The system MUST reject duplicate active deployment requests for the same application, environment, and version.
- **FR-003a**: For duplicate prevention, DRAFT, VALIDATING, BLOCKED, APPROVED, and DEPLOYING MUST count as active; FAILED, REJECTED, DEPLOYED, and ROLLED_BACK MUST count as inactive. An inactive request MUST NOT prevent creation of a new request for the same application, environment, and version.
- **FR-004**: The system MUST allow users to view an individual deployment by ID and list all stored deployment requests.
- **FR-005**: The system MUST allow deployment requests to be filtered by environment and sorted by priority.
- **FR-006**: The system MUST define and enforce the following deterministic lifecycle transition table. Every transition not listed MUST be rejected, and REJECTED and ROLLED_BACK are terminal states.

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

- **FR-007**: The system MUST reject any invalid status transition and record the timestamp and reason for each successful change.
- **FR-008**: The system MUST prevent a deployment from entering APPROVED or DEPLOYING unless all mandatory readiness checks pass.
- **FR-009**: The system MUST track each mandatory readiness check independently as PASS, FAIL, or NOT_CHECKED. A PASS MUST include supporting evidence; a FAIL or NOT_CHECKED result MUST include a reason.
- **FR-010**: The system MUST require these readiness checks to be complete before approval: application version present, container image present, container image tag is not latest, CPU and memory requests and limits recorded, readiness and liveness probes confirmed, required test result is PASS, required upstream/team approval evidence is recorded, and rollback plan and rollback version are documented. Each check MUST be PASS with supporting evidence. Separately, the final operator's ACCEPT decision MUST be recorded independently of, and before, transition to APPROVED; APPROVED status MUST NOT serve as its own approval evidence. A human REJECT decision MUST result in REJECTED rather than APPROVED.
- **FR-011**: The system MUST keep a deployment ineligible for approval whenever any mandatory readiness check is FAIL or NOT_CHECKED.
- **FR-012**: The system MUST retain deployment creation records, updates, status changes, readiness-check changes, failure details, and rollback details in an audit history with timestamps and reasons.
- **FR-013**: The system MUST store deployment information locally in JSON format, load saved records on start, and preserve history between executions.
- **FR-014**: A missing JSON store MUST be treated as an empty initial store. For malformed JSON or a syntactically valid document containing any invalid or incomplete record, the system MUST reject the entire store, report an actionable error, preserve the original file unchanged, and MUST NOT silently discard invalid or valid records through partial recovery.
- **FR-015**: The system MUST provide a CLI with clear commands, readable output, input validation, and actionable errors for create, view, list, update, readiness checks, and deployment status management.
- **FR-016**: The system MUST avoid external deployment actions and treat the workflow as a local simulation that evaluates supplied evidence without executing real AWS, Kubernetes, Jenkins, or other platform operations.
- **FR-017**: The system MUST not allow logic, user input, or overrides to bypass mandatory readiness checks or weaken acceptance criteria to obtain a passing result.
- **FR-018**: The system MUST record the final operator's ACCEPT or REJECT decision separately from the `human-approval` readiness check, with actor, timestamp, and reason. The readiness check MUST represent required upstream/team approval evidence; it MUST NOT represent or substitute for the final operator decision. A final operator ACCEPT decision MUST be recorded before transition to APPROVED and MUST NOT depend on the deployment already being APPROVED. A final operator REJECT decision MUST transition the request to REJECTED when the current status allows that transition. If REJECTED is not an allowed next status, the REJECT operation MUST be rejected entirely without recording the decision, adding a decision audit event, or changing lifecycle status. Automated PASS is evidence only and MUST NOT substitute for the final operator decision.
- **FR-019**: The system MUST preserve initial-generation and final-generation artifacts, execution logs, failure and repair evidence, and test results as deployment evidence for auditability.
- **FR-020**: The system MUST record, retain, and display rollback details whenever a deployment is rolled back or marked as failed.

### Key Entities *(include if feature involves data)*

- **Deployment Request**: Represents a single deployment record, including unique ID, application identity, target environment, priority, requester, metadata, current lifecycle status, and creation timestamp.
- **Readiness Check**: Represents one mandatory validation item with a name, status (PASS/FAIL/NOT_CHECKED), supporting evidence for PASS, and a reason for FAIL or NOT_CHECKED. The `human-approval` check records required upstream/team approval evidence.
- **Human Approval Decision**: Represents the final operator's separate ACCEPT or REJECT decision with actor, timestamp, and reason; it is independent of readiness-check results and lifecycle status.
- **Audit Event**: Represents a timestamped record of changes to deployment state, readiness checks, human approval decisions, failure states, or rollback actions.
- **Deployment Evidence Bundle**: Represents the collection of artifacts, logs, test results, and supporting records used to justify a deployment decision.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a fixed acceptance run of 100 retrieval-command attempts using valid deployment IDs after creation and an application restart, at least 99 attempts MUST return the complete matching record. This measures retrieval-command success across attempts, not completeness of the persisted record inventory.
- **SC-002**: 100% of duplicate requests for the same application, environment, and version are rejected while an existing request is in DRAFT, VALIDATING, BLOCKED, APPROVED, or DEPLOYING; requests in FAILED, REJECTED, DEPLOYED, or ROLLED_BACK do not block a new request.
- **SC-003**: 100% of invalid environment, priority, and lifecycle transitions are rejected with a clear explanation and without modifying the last valid state.
- **SC-004**: 100% of transition attempts to APPROVED are blocked unless every mandatory readiness check is PASS with supporting evidence and a separate human ACCEPT decision is recorded. Independently, 100% of transition attempts to DEPLOYING are blocked unless every mandatory readiness check is PASS with supporting evidence.
- **SC-005**: 100% of status changes and readiness updates produce a timestamped audit record with a reason.
- **SC-006**: After each restart with a valid JSON store, 100% of distinct deployment IDs present before shutdown MUST be present in the loaded record inventory. Measure this by comparing the pre-shutdown and post-restart ID sets; this measures persistence completeness, not retrieval-command success across repeated attempts.
- **SC-007**: 100% of missing, malformed, or schema-invalid JSON stores MUST be handled safely: a missing store starts empty; an invalid store, including a syntactically valid file containing both valid and invalid records, is rejected in full, reports an actionable error, and remains byte-for-byte unchanged without partial recovery or silent record loss.
- **SC-008**: 100% of human deployment approval decisions are recorded as explicit ACCEPT or REJECT actions with actor, timestamp, and reason, separately from automated PASS evidence and before any APPROVED transition.
- **SC-009**: In the fixed 20-case CLI interaction acceptance matrix below, a case passes only when its specified output marker appears on the specified stream and the expected exit status is returned. The score is `(number of passing cases / 20) × 100`; at least 19 of 20 cases (95%) MUST pass.

| Case | Interaction | Expected result |
|---|---|---|
| C01 | Create a valid request | Exit 0; stdout contains `Created deployment` |
| C02 | View an existing ID | Exit 0; stdout contains `Deployment ID` |
| C03 | List requests | Exit 0; stdout contains an existing deployment ID |
| C04 | Filter list by environment | Exit 0; stdout contains the requested environment |
| C05 | Sort list by priority | Exit 0; stdout lists P1 before P2 when both are present |
| C06 | Update metadata with a reason | Exit 0; stdout contains `updated` |
| C07 | Show readiness | Exit 0; stdout contains all mandatory check names |
| C08 | Record PASS with evidence | Exit 0; stdout contains `readiness` and `PASS` |
| C09 | Record upstream approval evidence | Exit 0; stdout contains `human-approval` and `PASS` |
| C10 | Record final operator ACCEPT | Exit 0; stdout contains `ACCEPT` and `recorded` |
| C11 | Create with unsupported environment | Nonzero; stderr names valid environment values |
| C12 | Create with unsupported priority | Nonzero; stderr names valid priority values |
| C13 | View a missing ID | Nonzero; stderr contains `not found` |
| C14 | Create duplicate active request | Nonzero; stderr contains `duplicate` |
| C15 | Request an unlisted transition | Nonzero; stderr contains `transition` |
| C16 | Record PASS without evidence | Nonzero; stderr contains `evidence` |
| C17 | Request APPROVED with incomplete checks | Nonzero; stderr identifies unmet readiness checks |
| C18 | Load malformed or schema-invalid JSON | Nonzero; stderr identifies invalid state; original store is unchanged |
| C19 | Update without the required reason | Nonzero; stderr contains usage/required-argument guidance |
| C20 | Record final operator REJECT | Exit 0; stdout contains `REJECT` and `recorded` |

## Assumptions

- Users interact with the system as local operators and project stakeholders, not as external platform administrators.
- The system is a local simulator that evaluates evidence entered by the user and does not perform real deployments.
- External systems such as AWS, Kubernetes, Jenkins, or other deployment platforms are out of scope.
- Local JSON persistence is the primary storage mechanism for records and audit history.
- A deployment may be edited after creation when the change is legitimate and documented, but all lifecycle and readiness transitions remain governed by deterministic rules and mandatory evidence checks.
- Human approval is required for final acceptance, even when automated evidence suggests the deployment is ready.
