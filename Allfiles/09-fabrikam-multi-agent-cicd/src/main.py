from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import yaml

from .contracts import find_breaking_changes
from .deployment_graph import deployment_order, rollback_closure
from .quality_gate import evaluate_quality_gate
from .versioning import parse_version, satisfies


def _load(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(text) if path.suffix in {".yml", ".yaml"} else json.loads(text)


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Fabrikam release controls")
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate")
    validate.add_argument("--manifest", type=Path, required=True)
    validate.add_argument("--baseline", type=Path, required=True)
    validate.add_argument("--candidate", type=Path, required=True)
    validate.add_argument("--quality", type=Path, required=True)
    validate.add_argument("--output", type=Path, required=True)
    quality = commands.add_parser("quality")
    quality.add_argument("--quality", type=Path, required=True)
    quality.add_argument("--output", type=Path, required=True)
    rollback = commands.add_parser("rollback-set")
    rollback.add_argument("--manifest", type=Path, required=True)
    rollback.add_argument("--failed-agent", required=True)
    rollback.add_argument("--output", type=Path, required=True)
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "quality":
        result = evaluate_quality_gate(_load(args.quality))
    elif args.command == "rollback-set":
        release_set = _load(args.manifest)
        graph = {
            name: {
                "version": metadata["logical_version"],
                "depends_on": metadata.get("depends_on", {}),
            }
            for name, metadata in release_set["agents"].items()
        }
        result = {
            "release_set_id": release_set.get("release_set_id"),
            "failed_agent": args.failed_agent,
            "agents": rollback_closure(graph, args.failed_agent),
        }
    else:
        manifest = _load(args.manifest)
        agents = {
            name: {
                "version": metadata["logical_version"],
                "depends_on": metadata.get("depends_on", {}),
            }
            for name, metadata in manifest["agents"].items()
        }
        version_findings = []
        for name, metadata in agents.items():
            try:
                parse_version(metadata["version"])
            except ValueError as error:
                version_findings.append({"agent": name, "error": str(error)})
        for consumer, metadata in agents.items():
            for dependency, requirement in metadata.get("depends_on", {}).items():
                if dependency not in agents:
                    version_findings.append({"consumer": consumer, "dependency": dependency, "error": "unknown dependency"})
                elif not satisfies(agents[dependency]["version"], requirement):
                    version_findings.append({"consumer": consumer, "dependency": dependency, "requirement": requirement})
        breaking = find_breaking_changes(_load(args.baseline), _load(args.candidate))
        quality_decision = evaluate_quality_gate(_load(args.quality))
        result = {
            "commit": os.getenv("GITHUB_SHA", "local-validation"),
            "release_set_id": manifest.get("release_set_id"),
            "versions": {name: value["version"] for name, value in agents.items()},
            "deployment_order": deployment_order(agents),
            "version_findings": version_findings,
            "contract_findings": breaking,
            "quality_gate": quality_decision,
            "compatible": not version_findings and not breaking and quality_decision["action"] == "promote",
        }
    _write(args.output, result)
    print(json.dumps(result, indent=2))
    if args.command == "validate" and not result["compatible"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()