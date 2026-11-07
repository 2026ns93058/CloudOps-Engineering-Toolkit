from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from cloudops_tracker.domain import (
    CheckStatus,
    DecisionType,
    Deployment,
    DeploymentStatus,
    Environment,
    MANDATORY_CHECK_NAMES,
    Priority,
)
from cloudops_tracker.service import DeploymentService
from cloudops_tracker.storage import JsonStore, StorageError


_DEFAULT_STORE = Path("data/deployments.json")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cloudops-tracker",
        description="Manage local deployment requests and readiness evidence.",
    )
    parser.add_argument(
        "--store",
        type=Path,
        default=_DEFAULT_STORE,
        help=f"local JSON state file (default: {_DEFAULT_STORE})",
    )
    commands = parser.add_subparsers(dest="resource", required=True)
    deploy = commands.add_parser("deploy", help="manage deployment requests")
    actions = deploy.add_subparsers(dest="action", required=True)

    create = actions.add_parser("create", help="create a deployment request")
    create.add_argument("--application", required=True)
    create.add_argument("--version", required=True)
    create.add_argument("--image", required=True)
    create.add_argument(
        "--environment",
        required=True,
        choices=[item.value for item in Environment],
    )
    create.add_argument(
        "--priority",
        required=True,
        choices=[item.value for item in Priority],
    )
    create.add_argument("--requester", required=True)

    view = actions.add_parser("view", help="view a deployment request")
    view.add_argument("deployment_id")

    listing = actions.add_parser("list", help="list deployment requests")
    listing.add_argument(
        "--environment",
        choices=[item.value for item in Environment],
    )
    listing.add_argument("--sort", choices=("priority",))

    update = actions.add_parser("update", help="update request metadata")
    update.add_argument("deployment_id")
    update.add_argument("--application")
    update.add_argument("--version")
    update.add_argument("--image")
    update.add_argument(
        "--environment",
        choices=[item.value for item in Environment],
    )
    update.add_argument(
        "--priority",
        choices=[item.value for item in Priority],
    )
    update.add_argument("--requester")
    update.add_argument("--reason", required=True)

    readiness = actions.add_parser("readiness", help="manage readiness checks")
    readiness_actions = readiness.add_subparsers(dest="readiness_action", required=True)
    set_readiness = readiness_actions.add_parser("set", help="record a readiness result")
    set_readiness.add_argument("deployment_id")
    set_readiness.add_argument("--check", required=True, choices=MANDATORY_CHECK_NAMES)
    set_readiness.add_argument(
        "--status",
        required=True,
        choices=[item.value for item in CheckStatus],
    )
    set_readiness.add_argument("--evidence")
    set_readiness.add_argument("--reason")
    show_readiness = readiness_actions.add_parser("show", help="show readiness")
    show_readiness.add_argument("deployment_id")

    approval = actions.add_parser("approval", help="record a final operator decision")
    approval.add_argument("deployment_id")
    approval.add_argument(
        "--decision",
        required=True,
        choices=[item.value for item in DecisionType],
    )
    approval.add_argument("--actor", required=True)
    approval.add_argument("--reason", required=True)

    status = actions.add_parser("status", help="change lifecycle status")
    status.add_argument("deployment_id")
    status.add_argument(
        "--to",
        required=True,
        choices=[item.value for item in DeploymentStatus],
    )
    status.add_argument("--reason", required=True)
    status.add_argument("--failure-details")
    status.add_argument("--rollback-details")

    return parser


def _print_deployment(deployment: Deployment, output: TextIO) -> None:
    print(f"Deployment ID: {deployment.deployment_id}", file=output)
    print(f"Application: {deployment.application_name}", file=output)
    print(f"Version: {deployment.application_version}", file=output)
    print(f"Image: {deployment.container_image}", file=output)
    print(f"Environment: {deployment.environment.value}", file=output)
    print(f"Priority: {deployment.priority.value}", file=output)
    print(f"Requester: {deployment.requester}", file=output)
    print(f"Status: {deployment.status.value}", file=output)
    print(f"Created at: {deployment.created_at.isoformat()}", file=output)
    print(f"Updated at: {deployment.updated_at.isoformat()}", file=output)
    for name in MANDATORY_CHECK_NAMES:
        check = deployment.readiness_checks[name]
        print(
            f"Readiness {name}: {check.status.value}; "
            f"evidence={check.evidence or '-'}; reason={check.reason or '-'}",
            file=output,
        )
    if deployment.approval_decision is not None:
        decision = deployment.approval_decision
        print(
            f"Decision: {decision.decision.value}; actor={decision.actor}; "
            f"decided_at={decision.decided_at.isoformat()}; reason={decision.reason}",
            file=output,
        )
    if deployment.failure_details is not None:
        print(f"Failure details: {deployment.failure_details}", file=output)
    if deployment.rollback_details is not None:
        print(f"Rollback details: {deployment.rollback_details}", file=output)


def _print_readiness(
    service: DeploymentService, deployment_id: str, output: TextIO
) -> None:
    deployment = service.get_deployment(deployment_id)
    readiness_eligibility = service.readiness_eligibility(deployment_id)
    approved_eligibility = service.approved_gate_eligibility(deployment_id)
    for name in MANDATORY_CHECK_NAMES:
        check = deployment.readiness_checks[name]
        print(
            f"{name}: {check.status.value}; "
            f"evidence={check.evidence or '-'}; reason={check.reason or '-'}",
            file=output,
        )
    unmet_readiness = (
        ", ".join(readiness_eligibility.unmet_checks)
        if readiness_eligibility.unmet_checks
        else "none"
    )
    unmet_approved = (
        ", ".join(approved_eligibility.unmet_checks)
        if approved_eligibility.unmet_checks
        else "none"
    )
    print(
        f"APPROVED readiness gate eligible: "
        f"{'yes' if approved_eligibility.eligible else 'no'}",
        file=output,
    )
    print(
        f"DEPLOYING readiness gate eligible: "
        f"{'yes' if readiness_eligibility.eligible else 'no'}",
        file=output,
    )
    print(f"Unmet readiness checks: {unmet_readiness}", file=output)
    print(f"Unmet APPROVED gates: {unmet_approved}", file=output)


def _execute(arguments: argparse.Namespace, service: DeploymentService) -> int:
    if arguments.action == "create":
        deployment = service.create_deployment(
            application_name=arguments.application,
            application_version=arguments.version,
            container_image=arguments.image,
            environment=arguments.environment,
            priority=arguments.priority,
            requester=arguments.requester,
        )
        print(f"Created deployment: {deployment.deployment_id}")
        return 0

    if arguments.action == "view":
        deployment = service.get_deployment(arguments.deployment_id)
        _print_deployment(deployment, sys.stdout)
        events = service.list_audit_events(deployment.deployment_id)
        print("Audit history:", file=sys.stdout)
        for event in events:
            print(
                f"{event.occurred_at.isoformat()} {event.event_type.value} "
                f"actor={event.actor or '-'} reason={event.reason or '-'} "
                f"details={json.dumps(event.details, sort_keys=True, ensure_ascii=False)}",
                file=sys.stdout,
            )
        return 0

    if arguments.action == "list":
        deployments = service.list_deployments(
            environment=arguments.environment,
            sort_by_priority=arguments.sort == "priority",
        )
        if not deployments:
            print("No deployments found.")
            return 0
        for deployment in deployments:
            print(
                f"{deployment.deployment_id} | {deployment.application_name} | "
                f"{deployment.application_version} | {deployment.environment.value} | "
                f"{deployment.priority.value} | {deployment.status.value}"
            )
        return 0

    if arguments.action == "update":
        updates = {
            field: value
            for field, value in {
                "application_name": arguments.application,
                "application_version": arguments.version,
                "container_image": arguments.image,
                "environment": arguments.environment,
                "priority": arguments.priority,
                "requester": arguments.requester,
            }.items()
            if value is not None
        }
        deployment = service.update_metadata(
            arguments.deployment_id,
            updates,
            actor="operator",
            reason=arguments.reason,
        )
        print(f"Deployment {deployment.deployment_id} updated.")
        return 0

    if arguments.action == "readiness":
        if arguments.readiness_action == "set":
            deployment = service.set_readiness(
                arguments.deployment_id,
                check_name=arguments.check,
                status=arguments.status,
                evidence=arguments.evidence,
                reason=arguments.reason,
                actor="operator",
            )
            result = deployment.readiness_checks[arguments.check]
            print(
                f"Readiness {result.check_name} recorded as {result.status.value}."
            )
            return 0
        _print_readiness(service, arguments.deployment_id, sys.stdout)
        return 0

    if arguments.action == "approval":
        deployment = service.record_decision(
            arguments.deployment_id,
            decision=arguments.decision,
            actor=arguments.actor,
            reason=arguments.reason,
        )
        print(
            f"Decision {deployment.approval_decision.decision.value} recorded "
            f"for deployment {deployment.deployment_id}."
        )
        return 0

    if arguments.action == "status":
        deployment = service.transition_status(
            arguments.deployment_id,
            target=arguments.to,
            actor="operator",
            reason=arguments.reason,
            failure_details=arguments.failure_details,
            rollback_details=arguments.rollback_details,
        )
        print(
            f"Deployment {deployment.deployment_id} status changed to "
            f"{deployment.status.value}."
        )
        return 0

    raise ValueError(f"Unsupported command {arguments.action!r}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    try:
        arguments = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    try:
        service = DeploymentService(JsonStore(arguments.store))
        return _execute(arguments, service)
    except (OSError, StorageError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
