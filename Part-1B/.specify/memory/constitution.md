# Kubernetes Manifest Review Assistant Constitution

**Version:** 1.0.0  
**Project:** Kubernetes Manifest Review Assistant  
**Status:** Active

## Core Principles

### I. Specification-Driven Development
- Requirements, acceptance criteria, and expected behaviours MUST be documented before implementation.
- Implementation MUST remain traceable to the approved specification.
- Changes to requirements MUST be reflected in the specification and related tests.

### II. Evidence-Based Engineering
- Every evaluation MUST produce traceable results and supporting evidence.
- Initial and final evaluation outputs MUST be preserved.
- Failures MUST be recorded honestly, including their causes and corrective actions.
- Evaluation results MUST NOT be altered to manufacture a passing outcome.

### III. Contract and Structural Validation
- AI-generated review results MUST conform to the defined output schema.
- Required fields, data types, and structural invariants MUST be validated.
- Invalid or incomplete outputs MUST NOT be treated as successful reviews.

### IV. Behavioural and Semantic Quality
- Review findings MUST be evaluated against expected Kubernetes manifest issues.
- Evaluation MUST cover normal, boundary, ambiguous, missing-information, malformed, and adversarial inputs.
- Semantic quality MUST be measured using predefined evaluation criteria.
- The evaluation threshold MUST remain fixed during an evaluation cycle.

### V. Safety and Security
- Sensitive information MUST be protected and redacted where applicable.
- AI-generated recommendations MUST NOT be treated as automatically safe or authoritative.
- Unsupported security conclusions and known limitations MUST be documented.
- Validation failures MUST NOT be bypassed to obtain a passing result.

### VI. Harness Engineering and Continuous Improvement
- The evaluation harness MUST execute the defined tests and AI evaluation pipeline.
- The pipeline MUST validate schema, structural invariants, behavioural properties, safety requirements, and semantic quality.
- Failed evaluations MUST retain diagnostic evidence.
- Repairs MUST be followed by reevaluation using the established criteria.

### VII. Human Oversight and Acceptance
- Automated PASS status MUST NOT independently constitute final acceptance.
- A human reviewer MUST examine the evaluation evidence and known limitations.
- Final acceptance or rejection MUST be explicitly documented.
- The human reviewer retains responsibility for the final decision.

## Engineering Standards

- Python code MUST follow the project's configured linting and formatting standards.
- Automated tests MUST cover important application behaviours and validation rules.
- Evaluation datasets and thresholds MUST be versioned and traceable.
- Secrets, credentials, and sensitive raw inputs MUST NOT be committed to the repository.
- Documentation MUST include setup, execution, evaluation, and known limitations.

## Governance

Changes to these principles MUST be documented with a version update. Project requirements and implementation decisions MUST remain consistent with this constitution.

**End of Constitution**