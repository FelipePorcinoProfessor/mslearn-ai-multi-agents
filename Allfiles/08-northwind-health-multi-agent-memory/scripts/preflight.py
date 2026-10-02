from __future__ import annotations

import importlib.util
import json
import os
import py_compile
import sys
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def main() -> int:
    failures: list[str] = []
    if sys.version_info < (3, 13):
        failures.append("Python 3.13 or later is required.")
    for package in ("agent_framework", "agent_framework_foundry_hosting", "azure.cosmos", "azure.identity", "openai", "pydantic", "dotenv"):
        if importlib.util.find_spec(package) is None:
            failures.append(f"Missing package: {package}")
    try:
        memories = json.loads((ROOT / "assets" / "memories.json").read_text(encoding="utf-8"))
        required = {"id", "patientId", "content", "importance", "memoryType", "critical", "timestamp", "ttl", "schemaVersion"}
        if any(required - set(memory) for memory in memories):
            failures.append("Synthetic memories are missing required fields.")
        if any(not str(memory["patientId"]).startswith("synthetic-") for memory in memories):
            failures.append("Only synthetic patient IDs are allowed.")
    except (OSError, json.JSONDecodeError) as error:
        failures.append(f"Invalid memory asset: {error}")
    for source in [ROOT / "agent.py", *(ROOT / "src").glob("*.py")]:
        try:
            py_compile.compile(str(source), doraise=True)
        except py_compile.PyCompileError as error:
            failures.append(str(error))
    for variable in ("FOUNDRY_PROJECT_ENDPOINT", "AZURE_COSMOS_ENDPOINT", "AZURE_OPENAI_ENDPOINT"):
        print(f"{variable} configured: {bool(os.getenv(variable))}")
    if failures:
        print("Preflight failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Preflight passed. Live service values may remain unset until provisioning.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())