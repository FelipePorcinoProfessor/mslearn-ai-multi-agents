"""Side-effect-free readiness checks for the Foundry zero-trust lab."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]


def package_available(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except ModuleNotFoundError:
        return False


def valid_json(path: Path) -> bool:
    try:
        json.loads(path.read_text(encoding="utf-8"))
        return True
    except (OSError, json.JSONDecodeError):
        return False


def main() -> int:
    load_dotenv(ROOT / ".env")
    policy_path = ROOT / "assets/security-policy.json"
    requests_path = ROOT / "assets/security-requests.json"
    security_source = (ROOT / "src/security.py").read_text(encoding="utf-8")
    checks = {
        "python_3_10_or_newer": sys.version_info >= (3, 10),
        "azure_ai_projects_package": package_available("azure.ai.projects"),
        "azure_cosmos_package": package_available("azure.cosmos"),
        "policy_json": valid_json(policy_path),
        "request_json": valid_json(requests_path),
        "source_syntax": all(
            compile(path.read_text(encoding="utf-8"), path, "exec")
            for path in (ROOT / "src/main.py", ROOT / "src/security.py")
        ),
        "placeholder_1_present": security_source.count("LAB PLACEHOLDER 1") == 1,
        "foundry_project_configured": bool(os.getenv("FOUNDRY_PROJECT_ENDPOINT")),
        "model_configured": bool(os.getenv("FOUNDRY_MODEL_NAME")),
        "cosmos_configured": bool(os.getenv("COSMOS_ENDPOINT")),
    }
    for name, passed in checks.items():
        print(f"{'PASS' if passed else 'INFO'} {name}")
    required = (
        "python_3_10_or_newer",
        "azure_ai_projects_package",
        "azure_cosmos_package",
        "policy_json",
        "request_json",
        "source_syntax",
        "placeholder_1_present",
    )
    ready = all(checks[name] for name in required)
    print("READY (local)" if ready else "NOT READY")
    return 0 if ready else 1


if __name__ == "__main__":
    raise SystemExit(main())