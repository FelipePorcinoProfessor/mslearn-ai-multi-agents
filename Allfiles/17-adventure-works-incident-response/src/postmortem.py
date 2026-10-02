"""Create an evidence-linked blameless postmortem draft."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv


def summarize_evidence(analysis: list[dict[str, Any]], replay: dict[str, Any]) -> tuple[str, str]:
    # LAB PLACEHOLDER 5
    return (
        "Root cause is not yet established because evidence synthesis is incomplete.",
        "No causal observation has enough supporting evidence.",
    )


def upload_report(content: str, operation_id: str, credential: Any) -> str:
    service = BlobServiceClient(account_url=os.environ["BLOB_ACCOUNT_URL"], credential=credential)
    blob_name = f"{operation_id}.postmortem.md"
    service.get_blob_client(
        container=os.getenv("REPORT_CONTAINER", "incident-reports"), blob=blob_name
    ).upload_blob(content, overwrite=True)
    return blob_name


def main() -> None:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--analysis", type=Path, required=True)
    parser.add_argument("--replay", type=Path, required=True)
    args = parser.parse_args()
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    analysis = json.loads(args.analysis.read_text(encoding="utf-8"))
    replay = json.loads(args.replay.read_text(encoding="utf-8"))
    root_cause, evidence_summary = summarize_evidence(analysis, replay)
    template = Path("assets/postmortem-template.md").read_text(encoding="utf-8")
    rendered = (
        template.replace("{{operation_id}}", snapshot["operation_id"])
        .replace("{{root_cause}}", root_cause)
        .replace("{{replay_metrics}}", json.dumps(replay["comparison_metrics"], sort_keys=True))
        .replace("{{evidence_summary}}", evidence_summary)
    )
    output = Path("reports") / f"{snapshot['operation_id']}.postmortem.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
    blob_name = upload_report(rendered, snapshot["operation_id"], credential)
    print(json.dumps({"local_report": str(output), "blob": blob_name}, indent=2))


if __name__ == "__main__":
    main()