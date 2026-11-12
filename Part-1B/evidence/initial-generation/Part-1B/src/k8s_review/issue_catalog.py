"""Controlled catalogue of stable Kubernetes review issue identifiers."""

ISSUE_CATALOG = {
    "K8S-SEC-001": {
        "category": "Security",
        "description": "Container runs as root or does not enforce non-root execution.",
    },
    "K8S-SEC-002": {
        "category": "Security",
        "description": "Privileged container execution is enabled.",
    },
    "K8S-SEC-003": {
        "category": "Security",
        "description": "Privilege escalation is not disabled.",
    },
    "K8S-SEC-004": {
        "category": "Security",
        "description": "Container capabilities are not restricted.",
    },
    "K8S-SEC-005": {
        "category": "Security",
        "description": "Sensitive configuration is exposed through insecure manifest settings.",
    },
    "K8S-REL-001": {
        "category": "Reliability",
        "description": "Container readiness probe is missing.",
    },
    "K8S-REL-002": {
        "category": "Reliability",
        "description": "Container liveness probe is missing.",
    },
    "K8S-REL-003": {
        "category": "Reliability",
        "description": "Deployment replica count is not configured explicitly.",
    },
    "K8S-REL-004": {
        "category": "Reliability",
        "description": "Persistent workload storage configuration is incomplete.",
    },
    "K8S-REL-005": {
        "category": "Reliability",
        "description": "CronJob concurrency or scheduling configuration is unsafe or incomplete.",
    },
    "K8S-CFG-001": {
        "category": "Configuration",
        "description": "Container image uses a mutable latest tag.",
    },
    "K8S-CFG-002": {
        "category": "Configuration",
        "description": "Service target port does not match the intended container port.",
    },
    "K8S-CFG-003": {
        "category": "Configuration",
        "description": "Selector and pod labels are inconsistent.",
    },
    "K8S-CFG-004": {
        "category": "Configuration",
        "description": "Required configuration reference is missing or inconsistent.",
    },
    "K8S-RES-001": {
        "category": "Resource Management",
        "description": "Container resource requests are missing.",
    },
    "K8S-RES-002": {
        "category": "Resource Management",
        "description": "Container resource limits are missing.",
    },
    "K8S-RES-003": {
        "category": "Resource Management",
        "description": "Configured resource requests or limits are inconsistent.",
    },
}

def is_known_issue(issue_id: str) -> bool:
    """Return True when an identifier belongs to the controlled catalogue."""
    return issue_id in ISSUE_CATALOG


def get_issue_category(issue_id: str) -> str | None:
    """Return the controlled category for a known issue identifier."""
    issue = ISSUE_CATALOG.get(issue_id)
    return issue["category"] if issue else None
