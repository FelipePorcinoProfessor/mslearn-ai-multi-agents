"""Check pricing, deployments, and local files without Azure side effects."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    config = json.loads(Path("assets/optimization-config.json").read_text(encoding="utf-8"))
    main_source = Path("src/main.py").read_text(encoding="utf-8")
    cache_source = Path("src/cache.py").read_text(encoding="utf-8")
    prices_set = all(
        tier["prices_usd"]["input_per_million"] > 0
        and tier["prices_usd"]["output_per_million"] > 0
        for tier in config["tiers"].values()
    )
    placeholders = main_source.count("LAB PLACEHOLDER") + cache_source.count("LAB PLACEHOLDER")
    checks = {
        "python_3_10_or_newer": sys.version_info >= (3, 10),
        "synthetic_requests_present": Path("assets/requests.jsonl").is_file(),
        "project_endpoint": bool(os.getenv("FOUNDRY_PROJECT_ENDPOINT")),
        "redis_host": bool(os.getenv("REDIS_HOST")),
            "redis_port": bool(os.getenv("REDIS_PORT")),
        "principal_id": bool(os.getenv("AZURE_PRINCIPAL_ID")),
        "three_deployments": all(os.getenv(f"TIER{tier}_DEPLOYMENT") for tier in (1, 2, 3)),
        "current_prices_entered": prices_set,
        "exact_result_invalidation": "--invalidate-exact" in main_source and "def delete_exact(" in cache_source,
        "multilevel_cache_metrics": all(
            metric in main_source
            for metric in ("cache_hit_rate", "exact_result_cache_hit_rate", "prompt_cache_hit_rate")
        ),
        "learner_code_complete": placeholders == 0,
    }
    for name, passed in checks.items():
        print(f"{name}: {'ready' if passed else 'not ready'}")
    required = checks if args.require_complete else {
        name: passed for name, passed in checks.items() if name != "learner_code_complete"
    }
    return 0 if all(required.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())