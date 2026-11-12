"""Application orchestration for Kubernetes manifest reviews."""

from pathlib import Path
from typing import Any, Callable

import yaml

from k8s_review.finding_validation import validate_findings
from k8s_review.issue_catalog import ISSUE_CATALOG
from k8s_review.manifest import load_manifest_documents
from k8s_review.metadata import build_model_metadata
from k8s_review.ollama_client import (
    OllamaConfig,
    generate_review,
)
from k8s_review.redaction import redact_secret_data
from k8s_review.report_writer import write_review_report
from k8s_review.response_parser import parse_model_response
from k8s_review.schema_validation import validate_review_response
from k8s_review.static_review import (
    _workload_pod_spec,
    review_static_configuration,
)
from k8s_review.validation import (
    SUPPORTED_KINDS,
    validate_manifest_document,
)


class ReviewApplicationError(RuntimeError):
    """Raised when a manifest review cannot be completed."""


def review_manifest(
    manifest_path: Path,
    output_path: Path,
    config: OllamaConfig | None = None,
    model_call: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Review a Kubernetes manifest and optionally write its JSON report."""
    manifest_path = Path(manifest_path)
    output_path = Path(output_path)

    documents = load_manifest_documents(manifest_path)
    documents = [document for document in documents if document is not None]

    if not documents:
        raise ReviewApplicationError("Manifest contains no YAML resources.")

    for index, document in enumerate(documents):
        errors = validate_manifest_document(document)
        if errors:
            details = "; ".join(errors)
            raise ReviewApplicationError(
                f"Invalid manifest document {index}: {details}"
            )

    supported_documents = [
        document
        for document in documents
        if document["kind"] in SUPPORTED_KINDS
    ]

    unsupported_documents = [
        document
        for document in documents
        if document["kind"] not in SUPPORTED_KINDS
    ]

    sanitized_documents = [
        redact_secret_data(document)
        for document in supported_documents
    ]

    resources_reviewed = [
        {
            "api_version": document["apiVersion"],
            "kind": document["kind"],
            "name": document["metadata"]["name"],
            "namespace": document["metadata"].get("namespace"),
            "document_index": documents.index(document),
            "supported": True,
        }
        for document in supported_documents
    ]

    unsupported_resources = [
        {
            "api_version": document["apiVersion"],
            "kind": document["kind"],
            "name": document["metadata"]["name"],
            "namespace": document["metadata"].get("namespace"),
            "document_index": documents.index(document),
            "supported": False,
        }
        for document in unsupported_documents
    ]

    findings = review_static_configuration(supported_documents)
    review_summary = "No supported resources were available for AI review."
    model_metadata = {
        "provider": "Ollama",
        "model": config.model if config else OllamaConfig().model,
        "prompt_version": "1.0.3",
        "temperature": config.temperature if config else OllamaConfig().temperature,
        "duration_ms": 0,
    }

    if supported_documents:
        project_root = Path(__file__).resolve().parents[2]
        prompt_path = project_root / "prompts" / "k8s-review-v1.0.3.md"
        prompt = prompt_path.read_text(encoding="utf-8")
        import json
        prompt += (
            "\n\n## Controlled Issue Catalogue\n"
            "Select issue_id only from this catalogue. "
            "Use null only when no catalogue entry applies. "
            "Do not invent identifiers.\n"
            + json.dumps(ISSUE_CATALOG, indent=2)
        )

        sanitized_yaml = yaml.safe_dump_all(
            sanitized_documents,
            sort_keys=False,
        )

        active_config = config or OllamaConfig()
        execute_model = model_call or generate_review

        result = execute_model(
            active_config,
            prompt,
            sanitized_yaml,
        )

        parsed_response = parse_model_response(result.content)

        schema_errors = validate_review_response(parsed_response)
        if schema_errors:
            raise ReviewApplicationError(
                "Invalid model response schema: " + "; ".join(schema_errors)
            )

        ai_findings = parsed_response["findings"]

        # Keep deterministic findings and add only distinct AI findings.
        seen_issues = {
            (finding["issue_id"], finding["resource_kind"], finding["resource_name"])
            for finding in findings
            if finding.get("issue_id") is not None
        }

        # Deterministic resource checks are authoritative for supported workloads.
        resource_checked = set()

        for document in supported_documents:
            workload = _workload_pod_spec(document)
            if workload is None:
                continue

            _, pod_spec = workload
            containers = pod_spec.get("containers", [])

            if isinstance(containers, list) and any(
                isinstance(container, dict) for container in containers
            ):
                resource_checked.add((
                    document["kind"],
                    document["metadata"]["name"],
                ))

        for finding in ai_findings:
            issue_id = finding.get("issue_id")
            key = (
                issue_id,
                finding["resource_kind"],
                finding["resource_name"],
            )

            if (
                issue_id in {"K8S-RES-001", "K8S-RES-002", "K8S-RES-003"}
                and (finding["resource_kind"], finding["resource_name"])
                in resource_checked
            ):
                continue

            if issue_id is not None and key in seen_issues:
                continue

            findings.append(finding)
            if issue_id is not None:
                seen_issues.add(key)


        # Ensure every finding has a unique identifier within this report.
        for index, finding in enumerate(findings, start=1):
            finding["finding_id"] = f"F-{index:03d}"
        finding_errors = validate_findings(findings, sanitized_documents)
        if finding_errors:
            raise ReviewApplicationError(
                "Invalid combined findings: " + "; ".join(finding_errors)
            )

        review_summary = parsed_response["review_summary"]
        model_metadata = build_model_metadata(result)

    report = {
        "review_summary": review_summary,
        "resources_reviewed": resources_reviewed,
        "unsupported_resources": unsupported_resources,
        "findings": findings,
        "model_metadata": model_metadata,
    }

    write_review_report(report, output_path)

    return report
