from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from src.responses_client import _agent_urls, version_endpoint


def _required(values: dict[str, str], key: str) -> str:
    value = values.get(key, "").strip()
    if not value:
        raise ValueError(f"Missing required azd environment output: {key}")
    return value


def bind_deployments(release_set: dict[str, Any], values: dict[str, str]) -> dict[str, Any]:
    for service in ("scanner", "reviewer", "orchestrator"):
        prefix = f"AGENT_{service.upper()}"
        name = _required(values, f"{prefix}_NAME")
        version = _required(values, f"{prefix}_VERSION")
        responses_endpoint = _required(values, f"{prefix}_RESPONSES_ENDPOINT")
        _agent_urls(responses_endpoint, name)
        release_set["agents"][service]["hosted_deployment"] = {
            "name": name,
            "version": version,
            "responses_endpoint": responses_endpoint,
            "version_endpoint": version_endpoint(responses_endpoint, name, version),
        }
    identity = {
        "environment": release_set["environment"],
        "commit": release_set["source"]["commit"],
        "contracts": release_set["contract_digest"],
        "versions": {
            name: metadata["hosted_deployment"]["version"]
            for name, metadata in release_set["agents"].items()
        },
    }
    digest = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]
    release_set["release_set_id"] = f"{release_set['environment']}-{digest}"
    release_set["status"] = "deployed"
    release_set["dashboard"]["target_orchestrator"] = release_set["agents"]["orchestrator"]["hosted_deployment"]
    return release_set


def main() -> None:
    parser = argparse.ArgumentParser(description="Bind immutable Foundry outputs to a release set")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--azd-values", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    release_set = json.loads(args.manifest.read_text(encoding="utf-8"))
    values = json.loads(args.azd_values.read_text(encoding="utf-8"))
    bound = bind_deployments(release_set, values)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(bound, indent=2) + "\n", encoding="utf-8")
    print(bound["release_set_id"])


if __name__ == "__main__":
    main()
