"""Tests for deterministic Kubernetes manifest checks."""

from k8s_review.static_review import review_static_configuration


def deployment(pod_spec, spec_extra=None):
    def add_safe_security_context(pod):
        for container in pod.get("containers", []):
            if "resources" not in container:
                container["resources"] = {
                    "requests": {"cpu": "100m", "memory": "128Mi"},
                    "limits": {"cpu": "500m", "memory": "512Mi"},
                }
            if "securityContext" not in container:
                container["securityContext"] = {
                    "runAsNonRoot": True,
                    "allowPrivilegeEscalation": False,
                }

    add_safe_security_context(pod_spec)
    spec = {"template": {"spec": pod_spec}}
    if spec_extra:
        spec.update(spec_extra)
        template = spec_extra.get("template", {})
        if isinstance(template, dict):
            nested_pod = template.get("spec", {})
            if isinstance(nested_pod, dict):
                add_safe_security_context(nested_pod)

    return {
        "apiVersion": "apps/v1",
        "kind": "Deployment",
        "metadata": {"name": "sample-app"},
        "spec": spec,
    }


def test_missing_optional_configuration_does_not_create_findings():
    manifest = deployment({
        "containers": [{"name": "app", "image": "nginx:1.27"}]
    })

    assert review_static_configuration([manifest]) == []


def test_empty_security_context_reports_missing_non_root_enforcement():
    manifest = deployment({
        "containers": [{
            "name": "app",
            "image": "nginx:1.27",
            "securityContext": {},
        }]
    })

    findings = review_static_configuration([manifest])
    assert [f["issue_id"] for f in findings] == ["K8S-SEC-001"]


def test_run_as_non_root_absence_is_not_a_static_finding():
    manifest = deployment({
        "containers": [{
            "name": "app",
            "image": "nginx:1.27",
            "securityContext": {"runAsNonRoot": True},
        }]
    })

    assert "K8S-SEC-001" not in {
        f["issue_id"] for f in review_static_configuration([manifest])
    }


def test_detects_privilege_escalation_not_disabled():
    manifest = deployment({
        "containers": [{
            "name": "app",
            "image": "nginx:1.27",
            "securityContext": {"runAsNonRoot": True},
        }]
    })

    findings = review_static_configuration([manifest])

    assert len(findings) == 1
    finding = findings[0]
    assert finding["issue_id"] == "K8S-SEC-003"
    assert finding["severity"] == "Medium"
    assert finding["evidence"]["field_path"] == (
        "spec.template.spec.containers[0].securityContext."
        "allowPrivilegeEscalation"
    )
    assert finding["evidence"]["observed_value"] is None


def test_explicit_true_privilege_escalation_is_reported():
    manifest = deployment({
        "containers": [{
            "name": "app",
            "image": "nginx:1.27",
            "securityContext": {
                "runAsNonRoot": True,
                "allowPrivilegeEscalation": True,
            },
        }]
    })

    findings = review_static_configuration([manifest])

    assert [f["issue_id"] for f in findings] == ["K8S-SEC-003"]
    assert findings[0]["evidence"]["observed_value"] is True


def test_disabled_privilege_escalation_is_not_reported():
    manifest = deployment({
        "containers": [{
            "name": "app",
            "image": "nginx:1.27",
            "securityContext": {
                "runAsNonRoot": True,
                "allowPrivilegeEscalation": False,
            },
        }]
    })

    assert review_static_configuration([manifest]) == []


def test_detects_deployment_selector_label_mismatch():
    manifest = deployment(
        {
            "containers": [{"name": "app", "image": "nginx:1.27"}],
        },
        {
            "selector": {"matchLabels": {"app": "expected"}},
            "template": {
                "metadata": {"labels": {"app": "actual"}},
                "spec": {
                    "containers": [
                        {"name": "app", "image": "nginx:1.27"}
                    ]
                },
            },
        },
    )

    findings = review_static_configuration([manifest])

    assert len(findings) == 1
    finding = findings[0]
    assert finding["issue_id"] == "K8S-CFG-003"
    assert finding["severity"] == "High"
    assert finding["evidence"]["field_path"] == "spec.selector.matchLabels"


def test_matching_deployment_selector_does_not_create_finding():
    manifest = deployment(
        {"containers": [{"name": "app", "image": "nginx:1.27"}]},
        {
            "selector": {"matchLabels": {"app": "sample"}},
            "template": {
                "metadata": {"labels": {"app": "sample", "tier": "web"}},
                "spec": {
                    "containers": [
                        {"name": "app", "image": "nginx:1.27"}
                    ]
                },
            },
        },
    )

    assert review_static_configuration([manifest]) == []


def test_service_selector_is_not_compared_with_unrelated_deployment():
    service = {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {"name": "frontend-service"},
        "spec": {"selector": {"app": "frontend"}},
    }
    app = deployment(
        {"containers": [{"name": "app", "image": "nginx:1.27"}]},
        {
            "selector": {"matchLabels": {"app": "backend"}},
            "template": {
                "metadata": {"labels": {"app": "backend"}},
                "spec": {
                    "containers": [
                        {"name": "app", "image": "nginx:1.27"}
                    ]
                },
            },
        },
    )

    assert review_static_configuration([service, app]) == []


def test_unsupported_resource_kind_is_ignored():
    manifest = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {"name": "app-config"},
        "data": {"MODE": "production"},
    }

    assert review_static_configuration([manifest]) == []
