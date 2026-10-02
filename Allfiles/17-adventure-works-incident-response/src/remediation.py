"""Consume Azure Monitor alerts and persist side-effect-safe remediation evidence."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock, Timer
from typing import Any

from azure.eventhub import EventHubConsumerClient
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv


def build_evidence(alert: dict[str, Any]) -> dict[str, Any]:
    essentials = alert.get("data", {}).get("essentials", {})
    alert_id = essentials.get("alertId") or essentials.get("alertRule") or "unknown-alert"
    return {
        "schema_version": "1.0",
        "alert_id": alert_id,
        "alert_rule": essentials.get("alertRule"),
        "severity": essentials.get("severity"),
        "monitor_condition": essentials.get("monitorCondition"),
        "received_at": datetime.now(timezone.utc).isoformat(),
        "remediation": "isolate synthetic pricing failures and require operator-approved rollback",
        "status": "evidence_recorded",
        "side_effects_enabled": False,
    }


def persist_evidence(evidence: dict[str, Any], service: BlobServiceClient, container: str) -> str:
    safe_alert_id = str(evidence["alert_id"]).replace("/", "_").replace(":", "_")
    blob_name = f"remediation/{safe_alert_id}.json"
    service.get_blob_client(container=container, blob=blob_name).upload_blob(
        json.dumps(evidence, indent=2), overwrite=True
    )
    return blob_name


def receive_bounded(
    client: EventHubConsumerClient,
    process_event: Any,
    max_wait_seconds: int,
    max_events: int,
) -> int:
    processed = 0
    processed_lock = Lock()

    def on_batch(partition_context: Any, events: list[Any]) -> None:
        nonlocal processed
        with processed_lock:
            for event in events[: max_events - processed]:
                process_event(event)
                processed += 1
                partition_context.update_checkpoint(event)
            if events:
                client.close()

    stop_timer = Timer(max_wait_seconds, client.close)
    stop_timer.daemon = True
    stop_timer.start()
    try:
        partition_ids = client.get_eventhub_properties()["partition_ids"]
        client.receive_batch(
            on_event_batch=on_batch,
            starting_position={
                partition_id: "-1" for partition_id in partition_ids
            },
            starting_position_inclusive=True,
            max_batch_size=max_events,
            max_wait_time=min(5, max_wait_seconds),
        )
    finally:
        stop_timer.cancel()
    return processed


def main() -> None:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-wait-seconds", type=int, default=30)
    parser.add_argument("--max-events", type=int, default=10)
    args = parser.parse_args()
    credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
    blob_service = BlobServiceClient(account_url=os.environ["BLOB_ACCOUNT_URL"], credential=credential)
    persisted: list[str] = []

    def process_event(event: Any) -> None:
        evidence = build_evidence(event.body_as_json(encoding="UTF-8"))
        persisted.append(
            persist_evidence(evidence, blob_service, os.getenv("REPORT_CONTAINER", "incident-reports"))
        )

    client = EventHubConsumerClient(
        fully_qualified_namespace=os.environ["ALERT_EVENTHUB_NAMESPACE"],
        eventhub_name=os.getenv("ALERT_EVENTHUB_NAME", "incident-alerts"),
        consumer_group="$Default",
        credential=credential,
    )
    with client:
        processed = receive_bounded(
            client,
            process_event,
            max_wait_seconds=args.max_wait_seconds,
            max_events=args.max_events,
        )
    print(json.dumps({"processed": processed, "evidence_blobs": persisted}, indent=2))


if __name__ == "__main__":
    main()