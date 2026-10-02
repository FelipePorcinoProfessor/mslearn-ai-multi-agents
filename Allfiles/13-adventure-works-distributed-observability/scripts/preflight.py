"""Side-effect-free local readiness checks for Lab 13."""

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
    source = (ROOT / "src/telemetry.py").read_text(encoding="utf-8")
    checks = {
        "python_3_10_or_newer": sys.version_info >= (3, 10),
        "opentelemetry_sdk": package_available("opentelemetry.sdk"),
        "azure_monitor_distro": package_available("azure.monitor.opentelemetry"),
        "synthetic_scenario": (ROOT / "assets/trace-scenario.json").is_file(),
        "telemetry_policy": (ROOT / "config/telemetry-policy.yaml").is_file(),
        "alert_query": (ROOT / "kql/anomaly-alert.kql").is_file(),
        "starter_syntax": bool(compile(source, ROOT / "src/telemetry.py", "exec")),
        "placeholder_1_present": source.count("LAB PLACEHOLDER 1") == 1,
        "azure_monitor_configured": bool(os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")),
        "alert_email_configured": bool(os.getenv("ALERT_EMAIL")),
    }
    for name, passed in checks.items():
        print(f"{'PASS' if passed else 'INFO'} {name}")
    required = (
        "python_3_10_or_newer", "synthetic_scenario", "telemetry_policy",
        "alert_query", "starter_syntax", "placeholder_1_present",
    )
    local_ready = all(checks[name] for name in required)
    print("READY (local)" if local_ready else "NOT READY")
    return 0 if local_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())