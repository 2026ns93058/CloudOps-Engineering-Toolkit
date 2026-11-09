# Kubernetes Manifest Review Assistant

Part 1B — AI-Augmented SDLC Assignment.

A local AI-assisted Python CLI application for reviewing Kubernetes YAML manifests.

## Requirements

- Python 3.13+
- Ollama
- Qwen 3 4B model

## Setup

Create and activate the virtual environment:

    python3 -m venv .venv
    source .venv/bin/activate

Install dependencies:

    python -m pip install -e ".[dev]"

## CLI Usage

Display help:

    k8s-review --help

Display version:

    k8s-review --version

Review a manifest (functionality under development):

    k8s-review deployment.yaml

Specify a JSON output path:

    k8s-review deployment.yaml --output review.json

## Development Checks

    pytest -v
    ruff check .
    bandit -r src

## AI Runtime

The planned AI runtime is local Ollama with Qwen 3 4B. No paid external AI API is required initially.

## Current Development Status

Project setup and initial CLI argument tests are complete. Manifest parsing, AI review, structured findings, and evaluation functionality are under development.
