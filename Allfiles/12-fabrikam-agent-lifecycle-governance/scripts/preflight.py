"""Side-effect-free local readiness checks for Lab 12."""

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


def main() -> int:
    load_dotenv(ROOT / ".env")
    lifecycle_source = (ROOT / "src/lifecycle.py").read_text(encoding="utf-8")
    usage_source = (ROOT / "src/usage.py").read_text(encoding="utf-8")
    checks = {
        "python_3_10_or_newer": sys.version_info >= (3, 10),
        "projects_sdk": package_available("azure.ai.projects"),
        "cosmos_sdk": package_available("azure.cosmos"),
        "packaging_sdk": package_available("packaging"),
        "manifest_present": (ROOT / "registry/fabrikam-review-topology-v2.4.0.yaml").is_file(),
        "technical_file_present": (ROOT / "evidence/FAB-AI-240-technical-file.json").is_file(),
        "starter_syntax": all((
            bool(compile(lifecycle_source, ROOT / "src/lifecycle.py", "exec")),
            bool(compile(usage_source, ROOT / "src/usage.py", "exec")),
        )),
        "placeholder_1_present": lifecycle_source.count("LAB PLACEHOLDER 1") == 1,
        "placeholder_2_present": usage_source.count("LAB PLACEHOLDER 2") == 1,
        "project_configured": bool(os.getenv("FOUNDRY_PROJECT_ENDPOINT")),
        "cosmos_configured": bool(os.getenv("COSMOS_ENDPOINT")),
    }
    for name, passed in checks.items():
        print(f"{'PASS' if passed else 'INFO'} {name}")
    required = (
        "python_3_10_or_newer", "projects_sdk", "cosmos_sdk", "packaging_sdk",
        "manifest_present", "technical_file_present", "starter_syntax",
        "placeholder_1_present", "placeholder_2_present",
    )
    local_ready = all(checks[name] for name in required)
    print("READY (local)" if local_ready else "NOT READY")
    return 0 if local_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())