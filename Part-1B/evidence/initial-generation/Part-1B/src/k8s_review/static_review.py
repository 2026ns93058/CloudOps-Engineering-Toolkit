"""Deterministic static checks for Kubernetes manifest configuration."""

import re
from decimal import Decimal, InvalidOperation
from typing import Any


def _workload_pod_spec(
    document: dict[str, Any],
) -> tuple[str, dict[str, Any]] | None:
    """Return the pod spec and its manifest path for supported workloads."""

    kind = document.get("kind")
    spec = document.get("spec", {})

    if not isinstance(spec, dict):
        return None

    if kind in {"Deployment", "StatefulSet", "DaemonSet", "Job"}:
        pod_spec = spec.get("template", {}).get("spec")
        path = "spec.template.spec"
    elif kind == "CronJob":
        pod_spec = (
            spec.get("jobTemplate", {})
            .get("spec", {})
            .get("template", {})
            .get("spec")
        )
        path = "spec.jobTemplate.spec.template.spec"
    else:
        return None

    if isinstance(pod_spec, dict):
        return path, pod_spec

    return None


def _finding(
    document: dict[str, Any],
    issue_id: str,
    severity: str,
    title: str,
    explanation: str,
    field_path: str,
    observed_value: Any,
    observation: str,
    remediation: str,
) -> dict[str, Any]:
    """Build a finding using the application's standard finding schema."""

    if issue_id.startswith("K8S-SEC"):
        category = "Security"
    elif issue_id.startswith("K8S-CFG"):
        category = "Configuration"
    elif issue_id.startswith("K8S-REL"):
        category = "Reliability"
    else:
        category = "Resource Management"

    return {
        "finding_id": f"STATIC-{issue_id}",
        "issue_id": issue_id,
        "severity": severity,
        "category": category,
        "resource_kind": document["kind"],
        "resource_name": document["metadata"]["name"],
        "title": title,
        "explanation": explanation,
        "evidence": {
            "field_path": field_path,
            "observed_value": observed_value,
            "observation": observation,
        },
        "remediation": remediation,
    }

def _parse_resource_quantity(value: Any, resource: str) -> Decimal | None:
    """Parse common Kubernetes CPU and memory quantities safely."""
    if not isinstance(value, (str, int, float)) or isinstance(value, bool):
        return None

    match = re.fullmatch(r"([0-9]+(?:\.[0-9]+)?)([a-zA-Z]*)", str(value).strip())
    if not match:
        return None

    try:
        number = Decimal(match.group(1))
    except InvalidOperation:
        return None

    suffix = match.group(2)

    if resource == "cpu":
        factors = {
            "": Decimal(1),
            "m": Decimal("0.001"),
            "u": Decimal("0.000001"),
            "n": Decimal("0.000000001"),
        }
    else:
        factors = {
            "": Decimal(1),
            "K": Decimal(1000),
            "M": Decimal(1000) ** 2,
            "G": Decimal(1000) ** 3,
            "T": Decimal(1000) ** 4,
            "P": Decimal(1000) ** 5,
            "E": Decimal(1000) ** 6,
            "Ki": Decimal(1024),
            "Mi": Decimal(1024) ** 2,
            "Gi": Decimal(1024) ** 3,
            "Ti": Decimal(1024) ** 4,
            "Pi": Decimal(1024) ** 5,
            "Ei": Decimal(1024) ** 6,
        }

    factor = factors.get(suffix)
    return number * factor if factor is not None else None



def _review_container_resources(
    document: dict[str, Any],
    container: dict[str, Any],
    container_path: str,
    containers: list[Any],
) -> list[dict[str, Any]]:
    """Check missing resource requests/limits and comparable quantities."""
    findings: list[dict[str, Any]] = []
    resources = container.get("resources")

    if not isinstance(resources, dict):
        findings.append(_finding(
            document,
            "K8S-RES-001",
            "Medium",
            "Container resource requests are missing",
            "The container does not configure resource requests.",
            f"{container_path}.resources.requests",
            None,
            "Resource requests are not configured.",
            "Configure appropriate CPU and memory requests for the container.",
        ))
        return findings

    for field, issue_id, title in (
        ("requests", "K8S-RES-001", "Container resource requests are missing"),
        ("limits", "K8S-RES-002", "Container resource limits are missing"),
    ):
        configured = resources.get(field)

        if not isinstance(configured, dict) or not configured:
            findings.append(_finding(
                document,
                issue_id,
                "Medium",
                title,
                f"The container does not configure resource {field}.",
                f"{container_path}.resources.{field}",
                str(configured) if field in resources else None,
                f"Resource {field} are not configured.",
                f"Configure appropriate CPU and memory {field} for the container.",
            ))

    requests = resources.get("requests")
    limits = resources.get("limits")

    if isinstance(requests, dict) and isinstance(limits, dict):
        for resource in ("cpu", "memory"):
            if resource not in requests or resource not in limits:
                continue

            request_value = _parse_resource_quantity(requests[resource], resource)
            limit_value = _parse_resource_quantity(limits[resource], resource)

            if (
                request_value is not None
                and limit_value is not None
                and request_value > limit_value
            ):
                findings.append(_finding(
                    document,
                    "K8S-RES-003",
                    "Medium",
                    f"Container {resource} request exceeds its limit",
                    f"The configured {resource} request is greater than its limit.",
                    f"{container_path.rsplit('.containers[', 1)[0]}.containers",
                    str(containers),
                    f"Request {requests[resource]} exceeds limit {limits[resource]}.",
                    f"Set the {resource} request to a value no greater than its limit.",
                ))

    return findings



def review_static_configuration(
    documents: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Detect objective security and selector configuration problems."""

    findings: list[dict[str, Any]] = []

    for document in documents:
        kind = document.get("kind")
        spec = document.get("spec", {})

        if not isinstance(spec, dict):
            continue

        # Deployment selector must match the Pod template labels.
        if kind == "Deployment":
            selector = spec.get("selector", {})
            selector_labels = (
                selector.get("matchLabels", {})
                if isinstance(selector, dict)
                else {}
            )
            template = spec.get("template", {})
            template_metadata = (
                template.get("metadata", {})
                if isinstance(template, dict)
                else {}
            )
            template_labels = (
                template_metadata.get("labels", {})
                if isinstance(template_metadata, dict)
                else {}
            )

            if (
                isinstance(selector_labels, dict)
                and isinstance(template_labels, dict)
                and selector_labels
                and any(
                    template_labels.get(key) != value
                    for key, value in selector_labels.items()
                )
            ):
                findings.append(_finding(
                    document,
                    "K8S-CFG-003",
                    "High",
                    "Deployment selector does not match Pod template labels",
                    "One or more labels required by the Deployment selector "
                    "are absent or have different values in the Pod template.",
                    "spec.selector.matchLabels",
                    str(selector_labels),
                    "Deployment selector labels do not match Pod template labels.",
                    "Update the Pod template labels so they satisfy all "
                    "Deployment selector matchLabels.",
                ))

        workload = _workload_pod_spec(document)
        if workload is None:
            continue

        pod_path, pod_spec = workload
        containers = pod_spec.get("containers", [])

        if not isinstance(containers, list):
            continue

        for index, container in enumerate(containers):
            if not isinstance(container, dict):
                continue

            container_path = f"{pod_path}.containers[{index}]"
            findings.extend(
                _review_container_resources(
                    document, container, container_path, containers
                )
            )
            security = container.get("securityContext")
            container_security = security if isinstance(security, dict) else {}
            pod_security = pod_spec.get("securityContext", {})
            pod_security = pod_security if isinstance(pod_security, dict) else {}

            # Enforce non-root execution at either container or pod level.
            if (
                container_security.get("runAsNonRoot") is not True
                and pod_security.get("runAsNonRoot") is not True
            ):
                if "runAsNonRoot" in container_security:
                    evidence_path = f"{container_path}.securityContext.runAsNonRoot"
                    observed = str(container_security["runAsNonRoot"]).lower()
                elif "runAsNonRoot" in pod_security:
                    evidence_path = f"{pod_path}.securityContext.runAsNonRoot"
                    observed = str(pod_security["runAsNonRoot"]).lower()
                else:
                    evidence_path = f"{container_path}.securityContext.runAsNonRoot"
                    observed = None

                findings.append(_finding(
                    document,
                    "K8S-SEC-001",
                    "Medium",
                    "Non-root execution is not explicitly enforced",
                    "Neither the container-level nor pod-level security context "
                    "explicitly enforces non-root execution.",
                    evidence_path,
                    observed,
                    "Non-root execution is not explicitly enforced by the manifest.",
                    "Configure runAsNonRoot: true at the container or pod level.",
                ))


            # An empty or absent securityContext alone is ambiguous.
            # Check privilege escalation only when security settings exist.
            if isinstance(security, dict) and security:
                allow_escalation = security.get("allowPrivilegeEscalation")

                if allow_escalation is not False:
                    findings.append(_finding(
                        document,
                        "K8S-SEC-003",
                        "Medium",
                        "Privilege escalation is not disabled",
                        "The configured container security context does not "
                        "explicitly disable privilege escalation.",
                        f"{container_path}.securityContext.allowPrivilegeEscalation",
                        allow_escalation,
                        (
                            "allowPrivilegeEscalation is not configured."
                            if "allowPrivilegeEscalation" not in security
                            else f"allowPrivilegeEscalation is {allow_escalation}."
                        ),
                        "Set allowPrivilegeEscalation: false in the "
                        "container security context.",
                    ))

    return findings
