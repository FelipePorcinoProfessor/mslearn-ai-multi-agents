"""Reconstruct a captured span sequence without live side effects."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


def reconstruct_trace(snapshot: dict[str, Any]) -> dict[str, Any]:
    # LAB PLACEHOLDER 4
    return {
        "operation_id": snapshot["operation_id"],
        "side_effects_enabled": False,
        "prompt_checks": [],
        "steps": [],
        "divergences": [],
        "comparison_metrics": {},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = reconstruct_trace(json.loads(args.snapshot.read_text(encoding="utf-8")))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()