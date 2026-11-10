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

The application uses a local Ollama runtime with Qwen3:4b. No paid external AI API is required.

## Final Evaluation and Acceptance

The implementation and evaluation workflow are complete.

The final V7 evaluation used dataset version 1.0.6 and achieved:

- **Evaluation cases:** 20
- **Aggregate semantic score:** 100%
- **Acceptance threshold:** 80%
- **Overall evaluation status:** PASS

The November 10 harness execution also completed successfully:

- **Automated tests:** 168 passed
- **Evaluation cases processed:** 20
- **Overall harness status:** PASS

Refer to the following evidence:

- `FINAL-ACCEPTANCE.md` — final human acceptance and known limitations.
- `artifacts/full-evaluation-v7/` — V7 evaluation evidence.
- `artifacts/harness-runs/` — individual harness execution results.
- `harness-log.md` — development and harness activity log.

**Note:** The evaluation results demonstrate performance against the defined test dataset. They do not guarantee correct handling of every possible Kubernetes manifest.