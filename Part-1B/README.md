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

The harness runs automated tests and evaluates the application against the versioned evaluation dataset. Evaluation results are saved under `artifacts/harness-runs/`.

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

The separate November 10 harness execution also completed successfully:

- **Automated code-validation tests:** 168 passed
- **Evaluation cases processed:** 20
- **Overall harness status:** PASS

The 168 automated tests are separate from the 20 evaluation cases. The 100% semantic score applies only to the 17 applicable cases.

Refer to the following evidence:

- `FINAL-ACCEPTANCE.md` — final human acceptance and known limitations.
- `artifacts/full-evaluation-v7/` — V7 evaluation evidence.
- `artifacts/harness-runs/` — individual harness execution results.
- `harness-log.md` — development and harness activity log.

**Note:** These results demonstrate performance against the defined evaluation dataset. They do not guarantee correct handling of every possible Kubernetes manifest.