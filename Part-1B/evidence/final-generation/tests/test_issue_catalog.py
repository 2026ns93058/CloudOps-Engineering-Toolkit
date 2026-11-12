"""Tests for the controlled Kubernetes issue catalogue."""

from k8s_review.issue_catalog import (
    ISSUE_CATALOG,
    get_issue_category,
    is_known_issue,
)


def test_catalog_contains_at_least_15_issue_identifiers():
    assert len(ISSUE_CATALOG) >= 15


def test_all_issue_identifiers_are_unique():
    identifiers = list(ISSUE_CATALOG.keys())

    assert len(identifiers) == len(set(identifiers))


def test_all_categories_are_allowed():
    allowed = {
        "Security",
        "Reliability",
        "Configuration",
        "Resource Management",
    }

    assert all(
        issue["category"] in allowed
        for issue in ISSUE_CATALOG.values()
    )


def test_known_issue_identifier_is_recognised():
    assert is_known_issue("K8S-SEC-001") is True


def test_unknown_issue_identifier_is_rejected():
    assert is_known_issue("K8S-UNKNOWN-999") is False


def test_issue_category_is_returned():
    assert get_issue_category("K8S-RES-001") == "Resource Management"


def test_unknown_issue_has_no_category():
    assert get_issue_category("K8S-UNKNOWN-999") is None
