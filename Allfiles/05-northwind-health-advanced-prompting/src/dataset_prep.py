"""Prepare reviewed synthetic examples; this module never starts training."""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path


def prepare(records:list[dict])->list[dict]:
    """Learner task: retain only reviewed, deidentified, consented examples."""
    # LAB PLACEHOLDER 6: Replace this line with the Task 7 sample.
    raise NotImplementedError("Complete dataset preparation in Task 7")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_manifest(source: Path, output: Path, manifest: Path, records: list[dict], prepared: list[dict]) -> None:
    document = {
        "manifest_version": "1.0",
        "source": {"path": source.as_posix(), "sha256": sha256(source), "record_count": len(records)},
        "output": {"path": output.as_posix(), "sha256": sha256(output), "record_count": len(prepared)},
        "provenance": sorted({str(row["provenance"]) for row in prepared}),
        "filters": ["reviewed=true", "deidentified=true", "consent=synthetic", "schema-valid"],
        "reviewer_ids": sorted({str(row["reviewer_id"]) for row in prepared}),
    }
    manifest.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


def main()->None:
    p=argparse.ArgumentParser();p.add_argument("--input",type=Path,required=True);p.add_argument("--output",type=Path,required=True);p.add_argument("--manifest",type=Path);a=p.parse_args();rows=[json.loads(x) for x in a.input.read_text(encoding="utf-8").splitlines() if x.strip()];prepared=prepare(rows);a.output.write_text("\n".join(json.dumps(x) for x in prepared)+"\n",encoding="utf-8");write_manifest(a.input,a.output,a.manifest or a.output.with_suffix(".manifest.json"),rows,prepared)
if __name__=="__main__":main()