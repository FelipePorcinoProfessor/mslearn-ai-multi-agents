"""Validate local approval assets and non-secret configuration."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from jsonschema import validate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    request = json.loads(Path("assets/refund-request.json").read_text(encoding="utf-8"))
    schema = json.loads(Path("assets/workflow-state.schema.json").read_text(encoding="utf-8"))
    placeholders = sum(
        path.read_text(encoding="utf-8").count("LAB PLACEHOLDER")
        for path in Path("src").glob("*.py")
    )
    checks = {
        "python_3_10_or_newer": sys.version_info >= (3, 10),
        "synthetic_request": request["request_id"].startswith("SYN-"),
        "state_schema_valid_json": schema["type"] == "object",
        "cosmos_endpoint": bool(os.getenv("COSMOS_ENDPOINT")),
        "service_bus_namespace": bool(os.getenv("SERVICE_BUS_NAMESPACE")),
        "learner_code_complete": placeholders == 0,
    }
    validate({"id":"x","workflow_id":"x","state":"WAITING_FOR_REVIEW","policy_version":"v1","trace_id":"SYN","version":1,"updated_at":"2026-01-01T00:00:00Z"}, schema)
    for name, passed in checks.items():
        print(f"{name}: {'ready' if passed else 'not ready'}")
    required = checks if args.require_complete else {
        name: passed for name, passed in checks.items() if name != "learner_code_complete"
    }
    return 0 if all(required.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())