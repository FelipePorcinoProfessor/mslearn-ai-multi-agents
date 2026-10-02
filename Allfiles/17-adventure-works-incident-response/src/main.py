"""Query Application Insights and persist sanitized replay snapshots."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient, LogsQueryStatus
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv


def query_rows(client: LogsQueryClient, workspace_id: str, query: str) -> list[dict[str, Any]]:
    response = client.query_workspace(workspace_id, query, timespan=timedelta(hours=24))
    if response.status == LogsQueryStatus.PARTIAL:
        raise RuntimeError(f"Partial KQL result: {response.partial_error}")
    rows = []
    for table in response.tables:
        columns = [
            column if isinstance(column, str) else column.name
            for column in table.columns
        ]
        rows.extend(dict(zip(columns, row, strict=True)) for row in table.rows)
    return rows


def sanitize_rows(rows: list[dict[str, Any]], operation_id: str) -> dict[str, Any]:
    """Transform query rows into the replay snapshot contract without sensitive content."""
    # LAB PLACEHOLDER 1
    spans: list[dict[str, Any]] = []
    deployments: dict[str, dict[str, Any]] = {}
    configurations: dict[str, dict[str, Any]] = {}
    prompts: dict[str, str] = {}
    prompt_hashes: dict[str, str] = {}
    tool_mocks: dict[str, dict[str, Any]] = {}
    return {
        "schema_version": "1.0",
        "operation_id": operation_id,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "spans": spans,
        "model_deployments": list(deployments.values()),
        "configuration_versions": list(configurations.values()),
        "prompts": prompts,
        "prompt_hashes": prompt_hashes,
        "tool_mocks": tool_mocks,
        "replay_mode": True,
    }


def upload_snapshot(snapshot: dict[str, Any], account_url: str, container: str, credential: Any) -> str:
    service = BlobServiceClient(account_url=account_url, credential=credential)
    name = f"{snapshot['operation_id']}.snapshot.json"
    service.get_blob_client(container=container, blob=name).upload_blob(
        json.dumps(snapshot, indent=2, default=str), overwrite=True
    )
    return name


def main() -> None:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    candidates = commands.add_parser("candidates")
    candidates.add_argument("--query", type=Path, required=True)
    capture = commands.add_parser("capture")
    capture.add_argument("--operation-id", required=True)
    capture.add_argument("--query", type=Path, required=True)
    args = parser.parse_args()

    credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
    client = LogsQueryClient(credential)
    query = args.query.read_text(encoding="utf-8")
    if args.command == "candidates":
        print(json.dumps(query_rows(client, os.environ["LOG_ANALYTICS_WORKSPACE_ID"], query), indent=2, default=str))
        return

    safe_operation_id = args.operation_id.replace("'", "''")
    rows = query_rows(
        client,
        os.environ["LOG_ANALYTICS_WORKSPACE_ID"],
        query.replace("__OPERATION_ID__", safe_operation_id),
    )
    snapshot = sanitize_rows(rows, args.operation_id)
    report_path = Path("reports") / f"{args.operation_id}.snapshot.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(snapshot, indent=2, default=str), encoding="utf-8")
    blob_name = upload_snapshot(
        snapshot,
        os.environ["BLOB_ACCOUNT_URL"],
        os.getenv("SNAPSHOT_CONTAINER", "trace-snapshots"),
        credential,
    )
    print(json.dumps({"local_snapshot": str(report_path), "blob": blob_name}, indent=2))


if __name__ == "__main__":
    main()