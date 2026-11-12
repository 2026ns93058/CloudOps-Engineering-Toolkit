# Kubernetes Manifest Review Assistant

**Part 1B — AI-Augmented SDLC Assignment**

A local AI-assisted Python CLI application for reviewing Kubernetes YAML manifests using Ollama and Qwen3:4b.

## Requirements

- Python 3.13+
- Ollama
- Qwen3:4b model

## Setup

Create and activate the virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install project dependencies:

```bash
python -m pip install -e ".[dev]"
```

Make sure Ollama is running and the Qwen3:4b model is available locally.

## CLI Usage

Display help:

```bash
k8s-review --help
```

Display version:

```bash
k8s-review --version
```

Review a Kubernetes manifest:

```bash
k8s-review deployment.yaml
```

Specify a JSON output path:

```bash
k8s-review deployment.yaml --output review.json
```

## Testing and Harness Execution

Run automated tests:

```bash
pytest -v
```

Run the complete Part-1B evaluation harness:

```bash
./.harness/run.sh
```

The harness runs automated tests and evaluates the application against `evals/dataset.json`, the default dataset. The tracked `evals/dataset.json` is byte-for-byte identical to `evals/dataset-v1.0.6.json` (version 1.0.6, 20 cases). Evaluation results are saved under `artifacts/harness-runs/`.

## AI Runtime

### Ollama Installation and Model Setup

1. Install Ollama for macOS from the official website: https://ollama.com/download
2. Open the Ollama application and ensure the local runtime is running.
3. Pull the required model:

   ```bash
   ollama pull qwen3:4b
   ```

4. Verify that the model is available:

   ```bash
   ollama list
   ```

5. If needed, start the Ollama service from Terminal:

   ```bash
   ollama serve
   ```

6. Activate the project's Python virtual environment, install the project dependencies, and run the CLI or evaluation harness as described above.

The application uses the local Ollama runtime. Model availability and successful inference depend on the local machine having sufficient resources.

The application uses a local Ollama runtime with Qwen3:4b. No paid external AI API is required.

## Final Evaluation and Acceptance

The final V7 evaluation used dataset version 1.0.6 and achieved:

- **Application-level cases processed:** 20
- **Application-level outcomes passed:** 20/20
- **Semantic cases evaluated:** 17
- **Aggregate semantic score:** 100% across the 17 applicable cases
- **Excluded cases:** K8S-EVAL-013 and K8S-EVAL-014 (input rejected), and K8S-EVAL-015 (unsupported resource recorded)
- **Acceptance threshold:** 80%
- **Overall evaluation status:** PASS

The November 10 V7 acceptance run and the later November 12 full harness verification are separate records. The latest November 12 run used the default `evals/dataset.json` (verified byte-for-byte identical to `evals/dataset-v1.0.6.json`) and completed with:

- **Automated code-validation tests:** 169 passed
- **Evaluation cases processed:** 20
- **Aggregate semantic score:** 100% across the 17 applicable cases
- **Overall harness status:** PASS
- **Evidence:** `artifacts/harness-runs/evaluation-20261112T144214Z.json`

The 169 automated tests are separate from the 20 evaluation cases. The semantic score applies only to the 17 applicable cases; the other three were rejected or handled as unsupported.

Refer to the following evidence:

- `FINAL-ACCEPTANCE.md` — final human acceptance and known limitations.
- `artifacts/full-evaluation-v7/` — V7 evaluation evidence.
- `artifacts/harness-runs/` — individual harness execution results, including the latest November 12 verification.
- `evals/dataset.json` — default harness dataset; it is byte-for-byte identical to `evals/dataset-v1.0.6.json`.
- `harness-log.md` — development and harness activity log.

## Output Contract and Evaluation Methodology

The CLI emits a JSON review report with four top-level fields:

- `review_summary`: overall review summary.
- `resources_reviewed`: supported resources actually reviewed.
- `unsupported_resources`: resources not reviewed.
- `findings`: structured findings with finding/issue IDs, severity, category, resource identity, title, explanation, manifest-grounded evidence, and remediation.

The application validates model responses against the output schema before accepting them. The evaluation harness independently checks:

1. **Schema:** valid JSON, required fields, and enumerated values.
2. **Structural and safety invariants:** resource identity, manifest-grounded evidence, and safety requirements.
3. **Semantic quality:** expected issue matching, false positives/negatives, severity, evidence, and remediation.
4. **Acceptance:** aggregate semantic score of at least 80%, with schema and safety gates passing.

V7 processed 20 cases and all 20 application-level outcomes passed. Seventeen applicable cases received semantic scores, with an aggregate score of 100%. The other three were rejected or handled as unsupported and were not included in semantic scoring.

**Note:** These results demonstrate performance against the defined evaluation dataset. They do not guarantee correct handling of every possible Kubernetes manifest.

The default evaluation input is `evals/dataset.json`. It is kept identical to the versioned final dataset `evals/dataset-v1.0.6.json`; the harness script explicitly selects `evals/dataset.json`.
