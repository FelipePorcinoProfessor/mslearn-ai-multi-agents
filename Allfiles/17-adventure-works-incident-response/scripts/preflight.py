"""Validate incident assets and non-secret settings without Azure changes."""

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
    schema = json.loads(Path("assets/trace-snapshot.schema.json").read_text(encoding="utf-8"))
    hypotheses = json.loads(Path("assets/hypotheses.json").read_text(encoding="utf-8"))["hypotheses"]
    placeholders = sum(
        path.read_text(encoding="utf-8").count("LAB PLACEHOLDER")
        for path in Path("src").glob("*.py")
    )
    validate({"schema_version":"1.0","operation_id":"SYN","spans":[],"model_deployments":[],"configuration_versions":[],"prompts":{},"prompt_hashes":{},"tool_mocks":{"catalog_lookup":{"mock_id":"SYN","response":{},"success":True,"synthetic":True}},"replay_mode":True}, schema)
    snapshot_fields = set(schema["properties"])
    checks = {
        "python_3_10_or_newer": sys.version_info >= (3, 10),
        "three_kql_queries": len(list(Path("kql").glob("*.kql"))) == 3,
        "hypotheses_present": Path("assets/hypotheses.json").is_file(),
        "hypotheses_match_snapshot": all(
            hypothesis.get("statement")
            and all(predicate["path"].split(".", 1)[0] in snapshot_fields for predicate in hypothesis["predicates"])
            for hypothesis in hypotheses
        ),
        "app_insights_connection": bool(os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")),
        "workspace_id": bool(os.getenv("LOG_ANALYTICS_WORKSPACE_ID")),
        "blob_account_url": bool(os.getenv("BLOB_ACCOUNT_URL")),
        "alert_eventhub_namespace": bool(os.getenv("ALERT_EVENTHUB_NAMESPACE")),
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