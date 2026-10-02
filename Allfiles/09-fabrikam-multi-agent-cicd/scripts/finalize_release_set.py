from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Record dashboard revision evidence in a release set")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--app-name", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--release-channel", choices=("stable", "candidate"), required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--routing-evidence", type=Path, required=True)
    parser.add_argument("--status", choices=("deployed", "candidate", "verified", "rolled-back"), required=True)
    args = parser.parse_args()

    release_set = json.loads(args.manifest.read_text(encoding="utf-8"))
    routing = json.loads(args.routing_evidence.read_text(encoding="utf-8"))["routing"]
    labels = routing["labels"]
    expected_label = args.release_channel
    if labels.get(expected_label) != args.revision:
        raise ValueError(
            f"Dashboard revision is not mapped to authoritative {expected_label} label"
        )
    release_set["status"] = args.status
    release_set["dashboard"].update(
        {
            "app_name": args.app_name,
            "revision": args.revision,
            "release_channel": args.release_channel,
            "url": args.url,
            "stable_label_url": routing["label_urls"].get("stable"),
            "candidate_label_url": routing["label_urls"].get("candidate"),
            "label_mapping": labels,
            "traffic": routing["traffic"],
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(release_set, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
