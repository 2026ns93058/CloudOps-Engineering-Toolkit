# Feature Specification: Kubernetes Manifest Review Assistant

**Feature Branch**: 001-kubernetes-manifest-review-assistant

**Created**: 2026-11-08

**Status**: Draft

## Input

Build a Python-based CLI application named Kubernetes Manifest Review Assistant.

DevOps and SRE engineers need a way to review Kubernetes YAML manifests and identify potential configuration, security, and reliability issues before deployment.

Manual manifest reviews can miss important problems, especially when multiple Kubernetes resources are defined in the same file. Static checks alone may not explain the operational impact of configuration choices.

The application will use a locally running Large Language Model (LLM) to analyse Kubernetes manifests and generate structured findings.

The application must support:
- Reading Kubernetes YAML files containing one or multiple documents separated by `---`.
- Reviewing Deployment, Service, ConfigMap, Secret, StatefulSet, DaemonSet, Job, CronJob, Ingress, and PersistentVolumeClaim resources.
- Identifying potential security, reliability, configuration, and resource-management concerns.
- Generating findings with severity, category, explanation, manifest evidence, and remediation.
- Returning machine-readable JSON output.
- Evaluating AI-generated findings through an independent evaluation harness.

## Clarifications

The following design decisions have been established:

| Topic | Decision | Rationale |
|---|---|---|
| Application interface | Python CLI application | Keeps the implementation small and easy to evaluate. |
| AI runtime | Local Ollama runtime using Qwen 3 4B | Avoids dependency on paid external AI APIs. |
| Kubernetes access | Static manifest review only; no live cluster connection | Keeps evaluation safe, reproducible, and independent of cluster access. |
| Input format | Single-document and multi-document YAML | Supports common Kubernetes manifest files. |
| Supported resources | Deployment, Service, ConfigMap, Secret, StatefulSet, DaemonSet, Job, CronJob, Ingress, and PersistentVolumeClaim | Defines the initial review scope. |
| Secret handling | Redact Secret data and stringData before model invocation | Prevents original Secret values from reaching the model. |
| Output format | Validated JSON report | Enables independent automated evaluation. |
| Evaluation | At least 15 cases, 80% semantic threshold, and 100% schema and safety invariant compliance | Establishes measurable acceptance criteria. |
| Final acceptance | Separate human review | Automated evaluation alone does not establish final acceptance. |

No live deployment, cluster mutation, or external paid AI API integration is included in the initial scope.

## User Scenarios & Testing

### User Story 1 - Review Kubernetes manifests (Priority: P1)

As a DevOps engineer, I want to submit a Kubernetes YAML manifest and receive an AI-assisted review so that I can identify potential issues before deployment.

**Independent Test**: Submit a valid Deployment manifest containing a known configuration issue and verify that the assistant returns a structured finding explaining the issue.

**Acceptance Scenarios**:

1. Given a valid single-resource YAML file, when the user submits it, then the assistant analyses the resource.
2. Given a valid multi-document YAML file, when the user submits it, then the assistant analyses all supported documents.
3. Given a manifest containing a known issue, when the review completes, then the assistant returns a relevant finding with evidence and remediation.
4. Given a manifest with no identified issues, when the review completes, then the assistant returns an empty findings list and an appropriate summary.
5. Given an unsupported resource type, when the review is requested, then the assistant identifies the unsupported resource rather than claiming it was fully reviewed.

### User Story 2 - Receive consistent structured findings (Priority: P1)

As a DevOps engineer, I want findings in a consistent JSON format so that I can understand, inspect, and reuse review results.

**Independent Test**: Submit a valid manifest and verify that the response conforms to the documented output schema.

**Acceptance Scenarios**:

1. Every finding includes a unique finding identifier.
2. Every finding includes severity, category, resource identity, title, explanation, evidence, and remediation.
3. Severity must be one of Critical, High, Medium, Low, or Info.
4. Category must be one of Security, Reliability, Configuration, or Resource Management.
5. Findings must identify the relevant resource and configuration evidence.
6. The assistant must not invent manifest fields or claim that absent evidence exists.
7. Invalid model output must not be accepted as a successful review.

### User Story 3 - Handle invalid, ambiguous, and unsafe input (Priority: P1)

As a user, I want invalid or potentially unsafe input handled safely so that the application does not produce misleading results or execute untrusted content.

**Independent Test**: Submit malformed YAML, empty input, ambiguous manifests, and adversarial instructions embedded in YAML comments or values.

**Acceptance Scenarios**:

1. Malformed YAML produces a clear input-validation error.
2. Empty input is rejected with an actionable message.
3. Missing mandatory Kubernetes metadata is reported appropriately.
4. Instructions embedded inside a manifest are treated as untrusted data, not instructions to the AI assistant.
5. Secrets and sensitive values are not unnecessarily repeated in findings or logs.
6. Unsupported resources are explicitly identified.
7. The assistant does not claim to have deployed, modified, or tested resources against a live cluster.

### User Story 4 - Evaluate AI review quality (Priority: P1)

As an evaluator, I want an automated harness to measure the quality of AI-generated findings so that application success is based on evidence rather than merely successful model execution.

**Independent Test**: Run the fixed evaluation dataset through the application and verify schema, invariant, semantic, and aggregate evaluation results.

**Acceptance Scenarios**:

1. The evaluation dataset contains at least 15 meaningful cases.
2. Cases cover normal, boundary, ambiguous, missing-field, malformed-input, and adversarial scenarios.
3. Every model response is independently checked against the output contract.
4. Structural and invariant checks are performed without relying on the model's own claims.
5. Semantic evaluation compares findings against expected issues and acceptable severity ranges.
6. The harness calculates an aggregate score and applies a documented PASS/FAIL threshold.
7. Initial failures and subsequent repair attempts are preserved as evidence.
8. A final human acceptance decision is recorded separately from automated evaluation.

## Functional Requirements

- **FR-001**: The application MUST provide a Python CLI for reviewing Kubernetes YAML files.
- **FR-002**: The application MUST accept YAML containing one or multiple documents separated by `---`.
- **FR-003**: The application MUST support Deployment, Service, ConfigMap, Secret, StatefulSet, DaemonSet, Job, CronJob, Ingress, and PersistentVolumeClaim resources.
- **FR-004**: The application MUST identify unsupported resource types and MUST NOT silently claim that they were reviewed.
- **FR-005**: The application MUST validate YAML syntax before sending manifest content to the LLM.
- **FR-006**: The application MUST use a non-deterministic AI model for semantic manifest review.
- **FR-007**: The initial model integration MUST use a locally running Qwen 3 4B model through Ollama.
- **FR-008**: The application MUST identify potential security, reliability, configuration, and resource-management concerns.
- **FR-009**: The application MUST return structured JSON findings.
- **FR-010**: Each finding MUST contain an ID, severity, category, resource kind, resource name, title, explanation, evidence, and remediation.
- **FR-011**: Severity MUST be restricted to Critical, High, Medium, Low, and Info.
- **FR-012**: Category MUST be restricted to Security, Reliability, Configuration, and Resource Management.
- **FR-013**: Every finding MUST contain evidence grounded in the submitted manifest.
- **FR-014**: The application MUST distinguish confirmed configuration observations from potential risks and avoid unsupported claims.
- **FR-015**: The application MUST handle malformed YAML, empty input, missing metadata, unsupported resources, and model failures safely.
- **FR-016**: The application MUST treat manifest content as untrusted input and ignore instructions embedded in YAML content.
- **FR-017**: The application MUST avoid unnecessarily exposing Secret values in generated findings, console output, and evidence logs.
- **FR-018**: The application MUST NOT connect to or modify a live Kubernetes cluster.
- **FR-019**: The application MUST NOT claim that a manifest has been deployed or validated against a running cluster.
- **FR-020**: The application MUST preserve model configuration, prompts, evaluation results, failures, repair history, and final review evidence.
- **FR-021**: The evaluation harness MUST independently validate the JSON output schema and required fields.
- **FR-022**: The evaluation harness MUST check structural invariants and semantic correctness against expected findings.
- **FR-023**: The evaluation dataset MUST contain at least 15 meaningful cases, including normal, boundary, ambiguous, missing mandatory field, malformed, and adversarial inputs.
- **FR-024**: The evaluation harness MUST calculate an aggregate score and compare it with a documented acceptance threshold.
- **FR-025**: The evaluation harness MUST distinguish model/service failures from application and evaluation failures.
- **FR-026**: Harness-driven repair MUST preserve original failures and record subsequent attempts without weakening acceptance criteria.
- **FR-027**: Final acceptance MUST require a separate human review decision.

## AI Output Contract

The assistant MUST return one JSON object with the following top-level fields:

- `review_summary`: A concise explanation of the overall review.
- `resources_reviewed`: An array identifying the supported resources reviewed.
- `unsupported_resources`: An array identifying resources not reviewed.
- `findings`: An array of review findings.

Each finding MUST contain:

- `finding_id`: Unique finding identifier within the review.
- `issue_id`: Stable identifier for a recognised issue, or null when no known issue identifier applies.
- `severity`: Critical, High, Medium, Low, or Info.
- `category`: Security, Reliability, Configuration, or Resource Management.
- `resource_kind`: Kubernetes resource kind.
- `resource_name`: Kubernetes resource name.
- `title`: Short issue description.
- `explanation`: Explanation of the observed issue or potential risk.
- `evidence`: An object containing:
  - `field_path`: Relevant YAML field path.
  - `observed_value`: Sanitised observed value, or null when the field is absent.
  - `observation`: Explanation of what the manifest demonstrates.
- `remediation`: Actionable recommendation.

The application MUST attach trusted `model_metadata` to the final report. This metadata MUST reflect actual execution information and MUST NOT be generated or invented by the model.

The application MUST validate this contract independently of the LLM.

## Safety and Guardrails

- Manifest content MUST be treated as untrusted data.
- Instructions inside YAML comments, annotations, labels, or values MUST NOT override the review prompt.
- Secret values MUST be redacted from findings and evidence logs.
- The model MUST NOT receive credentials, API keys, or unrelated personal information.
- The assistant MUST NOT execute shell commands or Kubernetes operations suggested by manifest content.
- The assistant MUST NOT invent resource fields, cluster state, runtime behaviour, or external validation results.
- Model output MUST be treated as untrusted until validated by the application.
- A model response that fails validation MUST NOT be counted as a successful evaluation.

## Evaluation Strategy

The evaluation harness MUST use independent validation layers:

1. **Schema validation**: Verify JSON syntax, required fields, field types, and allowed enum values.
2. **Invariant validation**: Verify resource identity, evidence grounding, severity/category validity, duplicate finding handling, and safety constraints.
3. **Semantic evaluation**: Compare generated findings with expected findings for each evaluation case, considering issue identification, severity, evidence, and remediation quality.
4. **Aggregate evaluation**: Calculate the overall score and compare it against the acceptance threshold.

The evaluation dataset MUST contain at least 15 cases covering:
- Correct manifests with no known issue.
- Security misconfiguration.
- Missing or invalid resource configuration.
- Resource-management concerns.
- Readiness and reliability issues.
- Multiple resources in one YAML file.
- Boundary and ambiguous cases.
- Missing mandatory Kubernetes metadata.
- Malformed YAML.
- Unsupported resources.
- Secret redaction.
- Adversarial instructions embedded in manifest content.

An LLM judge MAY be used as an optional supplementary evaluator, but MUST NOT replace independent schema or invariant checks.

## Success Criteria

- **SC-001**: The application successfully parses all valid YAML documents in the supported evaluation dataset.
- **SC-002**: 100% of malformed YAML cases are rejected safely without an AI review being reported as successful.
- **SC-003**: 100% of model responses accepted as successful conform to the required JSON output schema.
- **SC-004**: 100% of findings use allowed severity and category values.
- **SC-005**: 100% of findings identify a resource present in the submitted manifest.
- **SC-006**: Findings must provide manifest-grounded evidence and actionable remediation.
- **SC-007**: Secret values must not appear in generated findings or evaluation logs.
- **SC-008**: Embedded adversarial instructions must not override the system review instructions.
- **SC-009**: The evaluation dataset MUST contain at least 15 meaningful cases.
- **SC-010**: The final evaluation MUST achieve an aggregate score of at least 80%, with schema and safety invariants passing 100%.
- **SC-011**: Initial and final evaluation results, genuine failures, repair attempts, and human acceptance MUST be preserved in evidence.
- **SC-012**: Model execution failures MUST be reported separately from application or evaluation failures.

## Assumptions and Constraints

- The application is a local Python CLI tool.
- Ollama provides local model execution.
- Qwen 3 4B is the initial model and may be changed only with documented justification.
- No paid external AI API is required for the initial implementation.
- YAML parsing and structural validation are performed by the Python application.
- AI-generated findings are recommendations, not proof of runtime security or operational correctness.
- No live Kubernetes cluster is required.
- The application is intended as a focused educational prototype, not a replacement for production security scanners or Kubernetes policy engines.
- The model may produce inconsistent results; the evaluation harness measures this behaviour.
- Final acceptance remains a human decision.

## Additional Security and Evaluation Requirements

### Secret Redaction Before Model Processing

- **FR-028**: The application MUST identify Kubernetes Secret resources before constructing the LLM request.
- **FR-029**: Secret data values MUST be redacted before manifest content is sent to the model.
- **FR-030**: The model MUST receive resource metadata and relevant structural information without receiving original Secret values.
- **FR-031**: Redaction MUST preserve enough resource information for the assistant to identify configuration risks without exposing sensitive values.
- **FR-032**: Original Secret values MUST NOT appear in prompts, model responses, application logs, evaluation reports, or evidence files.
- **FR-033**: Redaction behaviour MUST be independently tested using known secret-value markers.

### Evaluation Scoring Rules

The evaluation harness MUST use a documented scoring method.

Each evaluation case MUST define:
- Case identifier and description.
- Input manifest or input condition.
- Expected review outcome.
- Expected findings, where applicable.
- Expected severity and category.
- Required evidence or evidence conditions.
- Expected application behaviour.

Semantic evaluation MUST assess:

1. Issue identification: whether the expected issue was identified.
2. Severity correctness: whether the finding uses the expected severity or an explicitly permitted severity range.
3. Evidence grounding: whether the finding refers to the correct resource and relevant manifest field.
4. Remediation quality: whether the recommendation addresses the identified issue.
5. False positives: whether the assistant reports unsupported issues.

A finding MUST NOT receive full credit merely because its wording resembles an expected finding.

For semantic matching:
- Match findings using resource identity, issue category, and expected issue identity.
- Count each expected issue at most once.
- Do not award credit for duplicate findings.
- Penalise unsupported findings.
- Treat missing expected findings as false negatives.
- Record per-case results and reasons.

- Calculate issue-identification precision, recall, and F1 using true positives (TP), false positives (FP), and false negatives (FN):
  - Precision = TP / (TP + FP).
  - Recall = TP / (TP + FN).
  - F1 = 2 * Precision * Recall / (Precision + Recall).
- If both expected and generated findings are empty, issue identification receives 100%. If the F1 denominator is zero in any other situation, it receives 0%.
- Calculate each case's semantic score using these weights:
  - Issue identification (F1): 50%.
  - Severity correctness: 20%.
  - Evidence grounding: 20%.
  - Remediation quality: 10%.
- Each component MUST be scored from 0 to 100 before applying its weight.
- Per-case semantic score = (F1 * 0.50) + (Severity * 0.20) + (Evidence * 0.20) + (Remediation * 0.10).
- Calculate the aggregate semantic score as the mean of scores across AI-eligible evaluation cases. Model execution failures MUST receive a score of zero.
- Invalid or rejected inputs MUST be evaluated against their expected application behaviour, not included as semantic model-review cases.
- The aggregate semantic score MUST meet or exceed 80% for semantic acceptance.

The aggregate semantic score MUST be calculated using the documented evaluator implementation. Schema and safety invariants MUST pass independently and cannot be compensated for by a high semantic score.

### Model and Execution Traceability

The harness log MUST record:
- Model provider: Ollama.
- Model name and tag: qwen3:4b.
- Ollama version.
- Prompt version or prompt file identifier.
- Model generation settings, including temperature where configured.
- Evaluation dataset version.
- Evaluation timestamp.
- Model execution duration.
- Model/service errors separately from application errors.
- Schema, invariant, and semantic evaluation outcomes.
- Aggregate score and acceptance threshold.
- Initial failures, repair attempts, and final results.

Model settings MUST be recorded accurately from the actual application configuration. The harness MUST NOT invent or assume configuration values.

### Additional Success Criteria

- **SC-013**: 100% of known Secret-value markers in the evaluation dataset MUST be absent from the content sent to the LLM and from generated evidence and logs.
- **SC-014**: Every evaluation case MUST produce an auditable result containing expected findings, actual findings, scoring details, and pass/fail outcome.
- **SC-015**: Every evaluation run MUST record the actual model and execution configuration used.
- **SC-016**: Duplicate findings MUST NOT increase the semantic evaluation score.
