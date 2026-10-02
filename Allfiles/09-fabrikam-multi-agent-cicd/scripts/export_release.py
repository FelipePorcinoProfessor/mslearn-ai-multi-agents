from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import yaml

MODEL_POLICY = {"name": "gpt-5.4-mini", "version": "2026-03-17"}


def load_definitions(agent_directory: Path) -> list[dict[str, Any]]:
    definitions = [yaml.safe_load(path.read_text(encoding="utf-8")) for path in sorted(agent_directory.glob("*.yml"))]
    if not definitions:
        raise ValueError(f"No agent definitions found in {agent_directory}")
    names = [definition.get("name") for definition in definitions]
    if any(not name for name in names) or len(names) != len(set(names)):
        raise ValueError("Agent definitions must have unique nonempty names")
    return definitions


def canonical_digest(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def build_release_set(
    definitions: list[dict[str, Any]],
    *,
    source_commit: str,
    environment: str,
    status: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    contracts = {definition["name"]: definition.get("tools", {}) for definition in definitions}
    agents: dict[str, Any] = {}
    for definition in definitions:
        if definition.get("model") != MODEL_POLICY:
            raise ValueError(f"{definition['name']} must use model policy {MODEL_POLICY}")
        agents[definition["name"]] = {
            "logical_version": definition["version"],
            "depends_on": definition.get("depends_on", {}),
            "contract_digest": canonical_digest(contracts[definition["name"]]),
            "hosted_manifest": definition["hosted"],
            "hosted_deployment": {
                "name": None,
                "version": None,
                "responses_endpoint": None,
                "version_endpoint": None,
            },
        }

    evaluation = definitions[0]["evaluation"]
    if any(definition.get("evaluation") != evaluation for definition in definitions):
        raise ValueError("All agents in a release set must use the same evaluation identity")

    reviewed_identity = {
        "source_commit": source_commit,
        "contract_digest": canonical_digest(contracts),
        "logical_versions": {
            definition["name"]: definition["version"] for definition in definitions
        },
        "model": MODEL_POLICY,
    }
    reviewed_release_id = hashlib.sha256(
        json.dumps(reviewed_identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    release_set = {
        "schema_version": 2,
        "reviewed_release_id": f"reviewed-{reviewed_release_id}",
        "release_set_id": None,
        "source": {"commit": source_commit},
        "model": MODEL_POLICY,
        "contract_digest": reviewed_identity["contract_digest"],
        "dependencies": {
            definition["name"]: definition.get("depends_on", {}) for definition in definitions
        },
        "evaluation": evaluation,
        "environment": environment,
        "status": status,
        "agents": agents,
        "dashboard": {
            "app_name": None,
            "revision": None,
            "release_channel": None,
            "url": None,
            "stable_label_url": None,
            "candidate_label_url": None,
            "target_orchestrator": {
                "name": None,
                "version": None,
                "responses_endpoint": None,
                "version_endpoint": None,
            },
        },
    }
    return release_set, contracts


def main() -> None:
    parser = argparse.ArgumentParser(description="Export source-derived release-set metadata")
    parser.add_argument("--agents", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--contracts", type=Path, required=True)
    parser.add_argument("--source-commit", default=os.getenv("GITHUB_SHA", "local-validation"))
    parser.add_argument("--environment", default="pr-validation")
    parser.add_argument("--status", default="validated")
    args = parser.parse_args()

    release_set, contracts = build_release_set(
        load_definitions(args.agents),
        source_commit=args.source_commit,
        environment=args.environment,
        status=args.status,
    )
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.contracts.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps(release_set, indent=2) + "\n", encoding="utf-8")
    args.contracts.write_text(json.dumps(contracts, indent=2) + "\n", encoding="utf-8")
    print(f"Exported release metadata for {len(release_set['agents'])} hosted agents.")


if __name__ == "__main__":
    main()
