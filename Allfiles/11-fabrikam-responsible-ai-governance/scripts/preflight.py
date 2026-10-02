"""Side-effect-free readiness checks for the Foundry governance lab."""

import importlib.util
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
    source = (ROOT / "src/governance.py").read_text(encoding="utf-8")
    main_source = (ROOT / "src/main.py").read_text(encoding="utf-8")
    checks = {
        "python_3_10_or_newer": sys.version_info >= (3, 10),
        "azure_ai_projects_package": package_available("azure.ai.projects"),
        "azure_monitor_distro_package": package_available("azure.monitor.opentelemetry"),
        "opentelemetry_sdk_package": package_available("opentelemetry.sdk"),
        "pyyaml_package": package_available("yaml"),
        "policy_present": (ROOT / "policy/governance-policy.yaml").is_file(),
        "synthetic_scenario": (ROOT / "assets/governance-scenario.json").is_file(),
        "starter_syntax": all(
            compile(text, path, "exec")
            for text, path in (
                (source, ROOT / "src/governance.py"),
                (main_source, ROOT / "src/main.py"),
            )
        ),
        "placeholder_1_present": source.count("LAB PLACEHOLDER 1") == 1,
        "foundry_project_configured": bool(os.getenv("FOUNDRY_PROJECT_ENDPOINT")),
        "model_configured": bool(os.getenv("FOUNDRY_MODEL_NAME")),
        "application_insights_configured": bool(os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")),
    }
    for name, passed in checks.items():
        print(f"{'PASS' if passed else 'INFO'} {name}")
    required = (
        "python_3_10_or_newer",
        "azure_ai_projects_package",
        "azure_monitor_distro_package",
        "opentelemetry_sdk_package",
        "pyyaml_package",
        "policy_present",
        "synthetic_scenario",
        "starter_syntax",
        "placeholder_1_present",
    )
    local_ready = all(checks[name] for name in required)
    azure_checks = (
        "foundry_project_configured",
        "model_configured",
        "application_insights_configured",
    )
    azure_ready = all(checks[name] for name in azure_checks)
    if not local_ready:
        print("NOT READY")
    elif azure_ready:
        print("READY (Azure configured)")
    else:
        print("READY (local)")
    return 0 if local_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())