from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Bind deterministic smoke results to a release set")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    release_set = json.loads(args.manifest.read_text(encoding="utf-8"))
    samples = [json.loads(line) for line in args.dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    results = [json.loads(line) for line in args.results.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(samples) != len(results):
        raise ValueError(f"Expected {len(samples)} smoke results, received {len(results)}")
    failures = [
        result["id"] for result in results
        if result.get("status") != "passed" or not str(result.get("response", "")).strip()
    ]
    evidence = {
        "release_set_id": release_set["release_set_id"],
        "source_commit": release_set["source"]["commit"],
        "orchestrator": release_set["agents"]["orchestrator"]["hosted_deployment"],
        "dataset": release_set["evaluation"],
        "sample_count": len(samples),
        "failures": failures,
        "status": "passed" if not failures else "failed",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    if failures:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
