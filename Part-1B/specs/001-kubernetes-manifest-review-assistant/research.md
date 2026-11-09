# Research: Kubernetes Manifest Review Assistant

## 1. Research Objective

Identify suitable technologies and implementation approaches for a local AI-powered Kubernetes manifest review application.

The solution must:
- Run locally without requiring a paid AI API.
- Support Kubernetes YAML containing multiple resources.
- Generate structured and useful AI findings.
- Protect sensitive Kubernetes Secret values.
- Evaluate AI output independently and consistently.
- Preserve execution and evaluation evidence.

## 2. AI Runtime: Ollama

**Decision**: Use Ollama as the local model runtime.

**Reasoning**:
- Runs language models locally on the user's machine.
- Provides a local HTTP API that Python applications can call.
- Avoids per-request external AI API charges.
- Supports model selection and configurable generation parameters.
- Allows prompts and Kubernetes manifests to remain on the local machine.

**Trade-offs**:
- Requires downloading and storing model files.
- Model execution consumes local memory and processing resources.
- Model quality and response speed depend on the selected model and hardware.
- The application depends on the local Ollama service being available.

**Selected configuration**:
- Runtime: Ollama
- Initial model: qwen3:4b
- Model execution: Local
- External AI API: Not required

## 3. Language Model: Qwen 3 4B

**Decision**: Start with Qwen 3 4B.

**Reasoning**:
- A relatively small model suitable for local experimentation.
- Can generate explanations and structured review findings.
- Can be tested without purchasing API credits.
- The model has already been downloaded and successfully tested on the development machine.

**Initial hardware**:
- Processor: Apple M1
- Unified memory: 16 GB
- Operating system: macOS

**Observed initial test**:

The model successfully generated explanations for:
- Readiness probe failures.
- CPU and memory resource constraints.
- Kubernetes Service configuration problems.

The response also demonstrated a technical accuracy limitation: it incorrectly suggested that exceeding CPU limits immediately kills a pod. CPU limits generally cause throttling, whereas memory-limit exhaustion can cause OOM termination.

This observation supports the need for independent semantic evaluation rather than accepting model output at face value.

**Trade-offs**:
- A small model may miss complex Kubernetes configuration issues.
- Generated findings can vary between runs.
- Technical accuracy must be measured against known evaluation cases.
- Model limitations must be documented rather than hidden.

**Decision constraint**:

Qwen 3 4B will remain the initial model unless evaluation results demonstrate a genuine limitation that justifies a documented model change.

## 4. Programming Language: Python

**Decision**: Use Python 3.13.

**Reasoning**:
- Already installed on the development machine.
- Suitable for CLI applications and YAML processing.
- Provides standard libraries for JSON, HTTP requests, file operations, and testing.
- Supports integration with local model APIs.
- Consistent with the completed Part 1A application.

**Trade-offs**:
- Model response parsing and validation must be implemented carefully.
- External package versions must be controlled.
- The application must distinguish local model failures from Python application failures.

## 5. YAML Parsing: PyYAML

**Decision**: Use PyYAML with safe loading functions.

**Reasoning**:
- Supports Kubernetes YAML documents.
- Provides multi-document parsing through safe loading interfaces.
- Allows the application to inspect resource kinds, metadata, and specifications.
- Avoids executing arbitrary YAML constructors through unsafe loading.

**Implementation considerations**:
- Use safe multi-document parsing.
- Reject malformed YAML.
- Handle empty documents explicitly.
- Validate mandatory resource identity fields.
- Preserve document order and resource identity.
- Do not execute YAML content.

## 6. Local Model Communication: Ollama HTTP API

**Decision**: Use the local Ollama HTTP API from Python.

**Reasoning**:
- Avoids requiring a paid API provider.
- Supports local model invocation.
- Allows generation settings and response formats to be controlled.
- Makes model-service failures observable and testable.

**Implementation considerations**:
- Use the locally configured Ollama endpoint.
- Request JSON-formatted model output where supported.
- Apply explicit request timeouts.
- Handle connection errors and unsuccessful responses.
- Record model identity and generation settings.
- Never silently convert a failed model request into a successful review.

The exact API request and response handling will be verified against the installed Ollama version during implementation.

## 7. Output Format: JSON

**Decision**: Use JSON for AI findings and evaluation results.

**Reasoning**:
- Machine-readable and easy to validate.
- Supported by Python's standard library.
- Suitable for CLI output and saved reports.
- Allows required fields and allowed values to be enforced independently.

**Implementation considerations**:
- Validate required fields and data types.
- Enforce severity and category enumerations.
- Validate resource identity.
- Validate evidence grounding.
- Reject malformed or incomplete responses.
- Do not rely solely on the model's claim that its response is valid.

## 8. Prompt Management

**Decision**: Store model instructions in version-controlled prompt files.

**Reasoning**:
- Keeps AI instructions separate from application code.
- Allows prompt changes to be reviewed and versioned.
- Supports reproducible evaluation runs.
- Makes prompt-related failures easier to investigate.

**Implementation considerations**:
- Define supported Kubernetes resources.
- Define the JSON output contract.
- Require evidence-based findings.
- Treat manifest content as untrusted data.
- Prevent embedded YAML instructions from overriding system instructions.
- Avoid unsupported claims about live cluster state.

## 9. Secret Redaction

**Decision**: Redact Kubernetes Secret values before sending manifest content to the model.

**Reasoning**:
- Kubernetes manifests may contain sensitive configuration values.
- Local execution does not eliminate the need for data protection.
- Redaction must occur before prompt construction, not merely in the final output.

**Implementation considerations**:
- Identify Secret resources before model invocation.
- Redact values under data and stringData.
- Preserve resource metadata and structural information.
- Test redaction using unique known secret-value markers.
- Verify original values are absent from prompts, outputs, logs, and evidence.

## 10. Automated Testing: pytest

**Decision**: Use pytest.

**Reasoning**:
- Supports modular unit and integration tests.
- Allows temporary files and isolated test data.
- Supports mocking the Ollama HTTP service.
- Enables repeatable validation without requiring a live model for every unit test.

**Implementation considerations**:
- Test YAML parsing independently.
- Test Secret redaction independently.
- Test model request and error handling.
- Test output schema validation.
- Test CLI behaviour.
- Test harness scoring and failure handling.

Live-model evaluation will remain separate from deterministic unit tests.

## 11. Code Quality and Security: Ruff and Bandit

**Decision**: Use Ruff for linting and Bandit for Python security analysis.

**Reasoning**:
- Ruff identifies common Python code-quality problems.
- Bandit checks for common Python security issues.
- Both provide repeatable local checks.
- They are consistent with the tooling used in Part 1A.

These tools complement, but do not replace, application-specific AI evaluation.

## 12. Evaluation Strategy

**Decision**: Implement an independent Python evaluation harness.

The harness will use four principal evaluation layers:

1. Schema validation.
2. Structural and safety invariant validation.
3. Semantic evaluation against expected findings.
4. Aggregate scoring and PASS/FAIL determination.

**Semantic matching approach**:

Exact natural-language matching is unsuitable because the model may explain the same issue using different wording.

Instead, evaluation cases will define stable expected issue identifiers and resource identities. The evaluator will compare generated findings against expected issues and independently assess:
- Issue identification.
- Severity.
- Evidence grounding.
- Remediation relevance.
- False positives.
- Duplicate findings.

An optional LLM judge may provide supplementary feedback, but will not replace deterministic checks.

## 13. Evidence and Reproducibility

**Decision**: Preserve initial and final evaluation evidence separately.

Evidence will include:
- Model name and runtime version.
- Prompt version.
- Generation settings.
- Evaluation dataset version.
- Execution timestamp and duration.
- Per-case results.
- Schema and invariant outcomes.
- Semantic scores.
- Aggregate PASS/FAIL result.
- Initial failures and repair attempts.
- Final human acceptance decision.

Evidence must reflect actual execution results and must not be fabricated or modified merely to obtain a passing outcome.

## 14. Alternatives Considered

### External hosted AI API

Advantages:
- Potentially stronger models.
- No local model resource consumption.
- Straightforward API integration.

Disadvantages:
- May incur usage charges.
- Requires credentials and network access.
- Sends manifest content to an external service.
- Free-tier availability and limits may change.

**Decision**: Not selected for the initial implementation because local execution meets the zero-cost objective.

### Larger local model

Advantages:
- May improve technical reasoning and review quality.

Disadvantages:
- Higher memory requirements.
- Potentially slower execution.
- Larger download size.

**Decision**: Not selected initially. Reconsider only if the smaller model fails meaningful evaluation requirements.

### Static rules only

Advantages:
- Deterministic and repeatable.
- Easy to test.
- No model dependency.

Disadvantages:
- Cannot demonstrate non-deterministic AI reasoning.
- Limited ability to explain contextual configuration risks.

**Decision**: Static validation will complement the LLM but will not replace AI-generated semantic review.

## 15. Final Technology Decisions

| Area | Selected technology |
|---|---|
| Language | Python 3.13 |
| Local AI runtime | Ollama |
| Initial model | Qwen 3 4B |
| YAML parsing | PyYAML |
| Model communication | Ollama local HTTP API |
| Output format | JSON |
| CLI | Python |
| Automated tests | pytest |
| Linting | Ruff |
| Security analysis | Bandit |
| AI evaluation | Custom Python harness |
| Persistence | Local files |
| Paid AI API | Not required initially |
| Kubernetes cluster | Not required |

## 16. Research Conclusion

The selected technology stack provides a practical local-first implementation for the Kubernetes Manifest Review Assistant.

The initial development environment already has Python, Ollama, and Qwen 3 4B available. The remaining dependencies will be limited to those required for YAML parsing and application development.

The main technical risk is model accuracy and consistency. The independent evaluation harness, rather than successful model execution alone, will determine whether the application meets the assignment's acceptance criteria.
