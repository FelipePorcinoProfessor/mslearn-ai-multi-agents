"""Check local readiness without creating or modifying Azure resources."""

from __future__ import annotations

import argparse
import importlib.util
import os
import sys
from pathlib import Path

from dotenv import load_dotenv


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    placeholders = sum(
        path.read_text(encoding="utf-8").count("LAB PLACEHOLDER")
        for path in Path("src").glob("*.py")
    )
    checks = {
        "python_3_10_or_newer": sys.version_info >= (3, 10),
        "dataset_present": Path("assets/evaluation-data.jsonl").is_file(),
        "configuration_present": Path("assets/evaluation-config.json").is_file(),
        "evaluation_sdk_installed": importlib.util.find_spec("azure.ai.evaluation") is not None,
        "endpoint_configured": bool(os.getenv("FOUNDRY_ACCOUNT_ENDPOINT")),
        "deployment_configured": bool(os.getenv("FOUNDRY_MODEL_NAME")),
        "learner_code_complete": placeholders == 0,
    }
    for name, passed in checks.items():
        print(f"{name}: {'ready' if passed else 'not ready'}")
    required = [
        "python_3_10_or_newer",
        "dataset_present",
        "configuration_present",
        "evaluation_sdk_installed",
    ]
    if args.require_complete:
        required.append("learner_code_complete")
    return 0 if all(checks[name] for name in required) else 1


if __name__ == "__main__":
    raise SystemExit(main())