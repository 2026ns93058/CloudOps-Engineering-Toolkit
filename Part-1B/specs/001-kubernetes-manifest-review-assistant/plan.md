# Implementation Plan: Kubernetes Manifest Review Assistant

## 1. Overview

Build a local Python CLI application that reviews Kubernetes YAML manifests using a locally running Large Language Model (LLM).

The application will use Ollama with Qwen 3 4B as its initial AI model. It will not require a paid external AI API or a live Kubernetes cluster.

The implementation will follow a specification-first approach. Application code, prompts, tests, evaluation cases, and harness checks will be derived from the approved feature specification.

## 2. Technical Context

- Language: Python 3.13
- Operating environment: macOS Apple Silicon initially
- AI runtime: Ollama
- Initial model: qwen3:4b
- Application interface: Command-line interface
- Input format: Kubernetes YAML
- YAML parser: PyYAML
- Output format: JSON
- Automated tests: pytest
- Code quality: Ruff
- Security analysis: Bandit
- AI evaluation: Custom Python evaluation harness
- Persistence: Local files for evaluation results and evidence
- External infrastructure: None required

## 3. Proposed Architecture

The application will use the following processing pipeline:

1. CLI receives a Kubernetes YAML file.
2. Input validation checks file availability, readability, and size.
3. YAML parser reads one or multiple YAML documents.
4. Resource validation identifies supported and unsupported Kubernetes resources.
5. Secret redaction removes original values from Secret resources before model processing.
6. Prompt builder prepares the sanitised manifest and review instructions.
7. Ollama client sends the prompt to the local Qwen model.
8. Response parser extracts and validates the JSON response.
9. Finding validator checks resource identity, evidence, severity, category, and required fields.
10. CLI displays the validated findings and optionally writes a JSON report.

The evaluation harness will independently assess the application output.

## 4. Application Components

### 4.1 CLI Layer

Responsibilities:
- Accept a manifest file path.
- Support an output destination for JSON reports.
- Display readable review results.
- Display actionable errors for invalid input and model failures.
- Provide a help command describing available options.

### 4.2 YAML Parser

Responsibilities:
- Parse single-document and multi-document YAML.
- Reject malformed YAML safely.
- Reject empty documents where appropriate.
- Validate mandatory Kubernetes resource identity fields.
- Identify supported and unsupported resource kinds.
- Preserve resource identity for later finding validation.

The parser MUST NOT execute YAML tags or embedded content.

### 4.3 Secret Redaction Layer

Responsibilities:
- Identify Kubernetes Secret resources.
- Redact values under data and stringData.
- Preserve non-sensitive resource metadata and structural information.
- Ensure original Secret values are not included in the prompt or evidence.
- Provide independently testable redaction behaviour.

Redaction MUST happen before prompt construction and model invocation.

### 4.4 Ollama Client

Responsibilities:
- Communicate with the local Ollama HTTP API.
- Use the configured qwen3:4b model.
- Apply documented generation settings.
- Request JSON-formatted output.
- Handle unavailable services, timeouts, and model errors.
- Record model execution duration and configuration.

The initial implementation will use Python's standard HTTP facilities where practical to minimise dependencies.

### 4.5 Prompt Management

Responsibilities:
- Keep system instructions separate from application code.
- Explain the supported Kubernetes resource types.
- Define the expected JSON response structure, including finding identifiers and structured evidence.
- Require `issue_id` to use a controlled issue catalogue identifier or null.
- Instruct the model to treat manifest content as untrusted data.
- Require findings to cite manifest-grounded evidence using `field_path`, `observed_value`, and `observation`.
- Prevent unsupported claims about live cluster state or deployment execution.
- Keep trusted model execution metadata outside the model-generated response; the application MUST attach it to the final report.

Prompt changes MUST be versioned and recorded during evaluation.

### 4.6 Output Validation

Responsibilities:
- Parse the model response as JSON.
- Validate required fields and data types.
- Enforce allowed severity and category values.
- Verify that referenced resources exist in the submitted manifest.
- Reject duplicate findings.
- Check evidence against the sanitised manifest.
- Prevent Secret values from appearing in the output.

Invalid responses MUST be reported as failures, not silently repaired into passing results.

### 4.7 Evaluation Harness

The harness will execute the following layers:

**Layer 1 - Application and input validation**
- Verify valid YAML is parsed.
- Verify malformed and empty inputs are rejected.
- Verify unsupported resources are reported.

**Layer 2 - Schema validation**
- Validate JSON structure.
- Check required fields and allowed values, including `issue_id` and structured evidence.
- Verify known issue identifiers against the controlled issue catalogue.
- Reject malformed model output.
- Attach trusted model execution metadata to the final report after validating the model response.

**Layer 3 - Invariant and safety validation**
- Check resource identity.
- Check evidence grounding.
- Detect duplicate findings.
- Check Secret redaction.
- Check prompt-injection resistance.

**Layer 4 - Semantic evaluation**
- Compare generated findings with expected evaluation findings.
- Measure issue identification.
- Evaluate severity and evidence correctness.
- Assess remediation relevance.
- Penalise unsupported findings and false positives.

**Layer 5 - Aggregate evaluation**
- Calculate per-case and overall scores.
- Apply the documented acceptance threshold.
- Produce a machine-readable evaluation report.
- Return PASS or FAIL.

Schema and safety invariants must pass independently and cannot be compensated for by the semantic score.

## 5. Proposed Project Structure

```text
Part-1B/
├── .harness/
│   ├── README.md
│   ├── run_harness.py
│   ├── schema_validator.py
│   ├── invariant_validator.py
│   ├── semantic_evaluator.py
│   └── scoring.py
├── artifacts/
├── evals/
│   └── dataset.json
├── evidence/
│   ├── initial-generation/
│   └── final-generation/
├── prompts/
│   └── manifest_review_v1.txt
├── specs/
│   └── 001-kubernetes-manifest-review-assistant/
│       ├── spec.md
│       ├── plan.md
│       ├── research.md
│       ├── data-model.md
│       ├── tasks.md
│       └── quickstart.md
├── src/
│   └── manifest_review/
│       ├── __init__.py
│       ├── __main__.py
│       ├── cli.py
│       ├── parser.py
│       ├── redaction.py
│       ├── ollama_client.py
│       ├── prompt_builder.py
│       ├── reviewer.py
│       └── output_validator.py
├── tests/
│   ├── test_parser.py
│   ├── test_redaction.py
│   ├── test_ollama_client.py
│   ├── test_output_validator.py
│   ├── test_cli.py
│   └── test_harness.py
├── pyproject.toml
├── README.md
└── harness-log.md
```

The final file structure may be refined during implementation, provided all required responsibilities remain covered.

## 6. Data Flow

### Input

A user supplies a Kubernetes YAML file containing one or more resources.

### Processing

- Validate and parse the YAML.
- Identify supported resources.
- Redact Secret values.
- Prepare the review prompt.
- Invoke the local model.
- Parse and validate the generated response.
- Evaluate the findings independently.

### Output

The application returns a JSON report containing:
- Review summary.
- Resources reviewed.
- Unsupported resources.
- Structured findings.
- Model execution metadata where appropriate.

The original input file MUST remain unchanged.

## 7. Evaluation Dataset Design

The evaluation dataset will contain at least 15 meaningful cases.

Proposed coverage:

1. Correct Deployment with no known issue.
2. Deployment with privileged container configuration.
3. Deployment using a latest image tag.
4. Deployment missing resource requests and limits.
5. Deployment missing readiness probe.
6. Deployment missing liveness probe.
7. Service with incorrect selector.
8. Service with inconsistent target port.
9. Secret with sensitive data values.
10. ConfigMap with valid configuration.
11. StatefulSet with missing required configuration.
12. Multi-document YAML containing multiple resource types.
13. Resource missing mandatory metadata.
14. Malformed YAML.
15. Unsupported Kubernetes resource.
16. Ambiguous configuration with insufficient evidence.
17. Adversarial instruction embedded in a YAML comment.

The dataset will define expected outcomes and findings for each case. Cases will be versioned and remain unchanged during an evaluation run.

## 8. Scoring and Acceptance

The initial target is an aggregate semantic score of at least 80%.

### 8.1 Semantic Score Components

Each AI-eligible evaluation case will use the following weighted score:

| Component | Weight |
|---|---:|
| Correct issue identification | 50% |
| Severity correctness | 20% |
| Evidence accuracy | 20% |
| Remediation relevance | 10% |
| Total | 100% |

### 8.2 Issue Identification

Issue identification will use precision, recall, and F1 score.

- True Positive (TP): An expected issue correctly identified for the correct resource.
- False Positive (FP): A reported issue that is not supported by the expected evaluation findings.
- False Negative (FN): An expected issue that the assistant failed to identify.

Precision = TP / (TP + FP)

Recall = TP / (TP + FN)

F1 = 2 * Precision * Recall / (Precision + Recall)

When both expected and generated findings are empty, issue identification receives 100%.
When the F1 denominator is zero in any other situation, the score is zero.

Issue matching MUST use the stable issue identifier and resource identity. Each expected issue can be matched only once.

### 8.3 Finding Quality

For correctly matched findings:

- Severity correctness measures whether the assigned severity matches the expected severity or permitted range.
- Evidence accuracy measures whether the evidence identifies the expected manifest field and accurately describes its value or absence.
- Remediation relevance measures whether the recommendation addresses the identified issue.

Each quality component is scored between 0 and 100.

Unmatched expected findings receive no quality credit. Unsupported findings receive no additional credit and reduce issue-identification precision.

### 8.4 Per-Case and Aggregate Scoring

The per-case semantic score is:

`(F1 * 0.50) + (Severity * 0.20) + (Evidence * 0.20) + (Remediation * 0.10)`

All component scores are expressed on a 0–100 scale.

For a correctly empty review with no expected or generated findings, the semantic score is 100%.

Malformed YAML and rejected input cases are evaluated against their expected application behaviour and are not assigned an AI semantic score.

The aggregate semantic score is the arithmetic mean of the semantic scores for all AI-eligible cases. A model execution failure on an AI-eligible case receives a semantic score of zero and is recorded as a model failure.

### 8.5 Acceptance Requirements

- Aggregate semantic score MUST be at least 80%.
- Schema validation MUST achieve 100% compliance for accepted model responses.
- Safety and structural invariants MUST achieve 100% compliance.
- Duplicate findings MUST NOT receive additional scoring credit.
- Model failures and missing results MUST remain visible in evaluation results.
- Input rejection cases MUST be checked against their expected application outcomes.
- A semantic score MUST NOT compensate for a schema or safety failure.

The final acceptance decision will be recorded separately by a human reviewer.

## 9. Failure Handling and Repair

The application and harness will distinguish:

- YAML parsing failures.
- Input validation failures.
- Ollama connection failures.
- Model execution timeouts.
- Invalid model JSON.
- Schema validation failures.
- Invariant failures.
- Semantic evaluation failures.

Harness-driven repair may modify application code, prompt instructions, or evaluation logic when justified by genuine failures.

Every initial failure and repair attempt MUST be preserved. Acceptance criteria and evaluation thresholds MUST NOT be weakened merely to obtain a passing score.

## 10. Security and Privacy

- No paid external AI API is required for the initial implementation.
- No credentials or API keys will be committed to Git.
- Original Kubernetes Secret values will be redacted before model processing.
- Model responses will be treated as untrusted data.
- Manifest content will not be executed.
- No shell commands or Kubernetes operations will be triggered from model output.
- Local evaluation evidence will not contain original Secret values.
- The application will not connect to a live Kubernetes cluster.

## 11. Implementation Sequence

1. Review and approve the feature specification.
2. Finalise architecture and technical research.
3. Define the data model and JSON output contract.
4. Define implementation and evaluation tasks.
5. Create the Python project configuration.
6. Implement YAML parsing and resource validation.
7. Implement Secret redaction.
8. Implement the prompt and Ollama integration.
9. Implement output schema and invariant validation.
10. Implement the CLI.
11. Create at least 15 evaluation cases.
12. Implement the evaluation harness.
13. Run the initial evaluation and preserve failures.
14. Repair genuine implementation or prompt issues.
15. Run the final evaluation and preserve results.
16. Conduct final human review and record acceptance.

## 12. Risks and Limitations

- A small local model may miss complex Kubernetes issues.
- Model outputs may vary between executions.
- Semantic matching requires carefully designed expected findings.
- Some Kubernetes configurations require cluster context that is unavailable from static YAML alone.
- YAML parsing success does not prove Kubernetes API validity.
- The assistant is an educational review tool, not a replacement for production security scanners, policy engines, or live cluster validation.

All findings MUST be presented as static-manifest review observations rather than claims about actual cluster behaviour.
