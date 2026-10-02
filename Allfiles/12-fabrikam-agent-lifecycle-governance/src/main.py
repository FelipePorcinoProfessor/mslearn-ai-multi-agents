"""Command-line interface for governed prompt-agent topology operations."""

import argparse
import json
from pathlib import Path

import yaml

from dotenv import load_dotenv

from .lifecycle import (
    create_client,
    list_inventory,
    load_manifest,
    promote_topology,
    reconcile_orphaned_versions,
    retire_version,
)
from .usage import create_usage_container, enforce_and_meter_usage


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("inventory", "promote", "reconcile", "retire", "meter"))
    parser.add_argument("--manifest", default="registry/fabrikam-review-topology-v2.4.0.yaml")
    parser.add_argument("--agent-name", default="scanner")
    parser.add_argument("--agent-version")
    parser.add_argument("--policy", default="policy/promotion-policy.yaml")
    parser.add_argument("--retirement-request", default="assets/retirement-request.json")
    parser.add_argument("--usage-request", default="assets/usage-request.json")
    parser.add_argument(
        "--orphan-version",
        action="append",
        default=[],
        metavar="AGENT:VERSION",
    )
    parser.add_argument("--confirm-delete-orphans", action="store_true")
    parser.add_argument("--confirm-delete-version", action="store_true")
    args = parser.parse_args()
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    policy = yaml.safe_load(Path(args.policy).read_text(encoding="utf-8"))

    if args.operation == "meter":
        request = json.loads(Path(args.usage_request).read_text(encoding="utf-8"))
        print(json.dumps(enforce_and_meter_usage(create_usage_container(), request, policy), indent=2))
        return

    client = create_client()

    if args.operation == "inventory":
        print(json.dumps(list_inventory(client), indent=2))
    elif args.operation == "promote":
        manifest = load_manifest(args.manifest)
        print(json.dumps(promote_topology(client, manifest), indent=2))
    elif args.operation == "reconcile":
        targets: list[tuple[str, str]] = []
        for value in args.orphan_version:
            if ":" not in value:
                parser.error("--orphan-version must use AGENT:VERSION")
            agent_name, agent_version = value.split(":", 1)
            targets.append((agent_name, agent_version))
        if not targets:
            parser.error("reconcile requires at least one --orphan-version")
        result = reconcile_orphaned_versions(
            client,
            targets,
            args.confirm_delete_orphans,
        )
        print(json.dumps(result, indent=2))
    else:
        if not args.agent_version:
            parser.error("retire requires --agent-version")
        retirement_request = json.loads(Path(args.retirement_request).read_text(encoding="utf-8"))
        result = retire_version(
            client,
            args.agent_name,
            args.agent_version,
            retirement_request,
            policy,
            args.confirm_delete_version,
        )
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()