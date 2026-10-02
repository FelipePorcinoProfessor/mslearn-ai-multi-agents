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
    if sys.version_info < (3, 11):
        failures.append("Python 3.11 or later is required.")

    for package in ("mcp", "httpx", "aiohttp", "jsonschema", "azure.identity"):
        if importlib.util.find_spec(package) is None:
            failures.append(f"Missing package: {package}")

    for asset in ("drug_interactions.json", "appointment_capacity.json", "tool-catalog.json"):
        try:
            json.loads((ROOT / "assets" / asset).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            failures.append(f"Invalid asset {asset}: {error}")

    for source in (ROOT / "src").glob("*.py"):
        try:
            py_compile.compile(str(source), doraise=True)
        except py_compile.PyCompileError as error:
            failures.append(str(error))

    print(f"Local MCP URL configured: {bool(os.getenv('MCP_SERVER_URL'))}")
    print(f"Remote token scope configured: {bool(os.getenv('MCP_TOKEN_SCOPE'))}")
    if failures:
        print("Preflight failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("Preflight passed. Numbered LAB PLACEHOLDER blocks remain intentionally incomplete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())