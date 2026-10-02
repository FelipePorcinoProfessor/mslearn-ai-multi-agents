from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REQUIRED_AGENTS = {"scanner", "reviewer", "orchestrator"}


def validate_verified_manifest(
    manifest: dict[str, Any],
    *,
    environment: str,
    app_name: str | None = None,
) -> dict[str, Any]:
    if manifest.get("schema_version") != 2:
        raise ValueError("Verified manifest must use schema_version 2")
    if manifest.get("environment") != environment:
        raise ValueError("Verified manifest environment does not match the target environment")
    if manifest.get("status") != "verified":
        raise ValueError("Persisted manifest must have status: verified")
    if not manifest.get("release_set_id"):
        raise ValueError("Verified manifest is missing release_set_id")
    agents = manifest.get("agents")
    if not isinstance(agents, dict) or set(agents) != REQUIRED_AGENTS:
        raise ValueError("Verified manifest must contain scanner, reviewer, and orchestrator")
    for service in REQUIRED_AGENTS:
        deployment = agents[service].get("hosted_deployment", {})
        for field in ("name", "version", "responses_endpoint", "version_endpoint"):
            if not deployment.get(field):
                raise ValueError(f"Verified manifest is missing {service}.{field}")
    dashboard = manifest.get("dashboard", {})
    if not dashboard.get("app_name") or not dashboard.get("revision"):
        raise ValueError("Verified manifest is missing dashboard app/revision evidence")
    if app_name and dashboard["app_name"] != app_name:
        raise ValueError("Verified dashboard app does not match the target app")
    if dashboard.get("release_channel") != "stable":
        raise ValueError("Verified dashboard release_channel must be stable")
    if not dashboard.get("stable_label_url"):
        raise ValueError("Verified manifest is missing the stable label URL")
    if dashboard.get("target_orchestrator") != agents["orchestrator"]["hosted_deployment"]:
        raise ValueError("Dashboard target does not match the immutable orchestrator deployment")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed validation for persisted release evidence")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--app-name")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    validate_verified_manifest(manifest, environment=args.environment, app_name=args.app_name)
    print(manifest["release_set_id"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
