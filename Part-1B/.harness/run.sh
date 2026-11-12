#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

RUN_ID=$(date -u +"%Y%m%dT%H%M%SZ")
RESULTS="artifacts/harness-runs/evaluation-${RUN_ID}.json"

echo "=== Part-1B AI Evaluation Harness ==="

echo "1. Running automated tests"
python -m pytest -v

echo "2. Running AI evaluation with dataset v1.0.6"
mkdir -p artifacts/harness-runs

k8s-review --evaluate \
  --dataset evals/dataset.json \
  --results "$RESULTS"

echo "Evaluation evidence: $RESULTS"
echo "=== Harness completed successfully ==="
