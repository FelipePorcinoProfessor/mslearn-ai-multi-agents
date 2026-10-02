from __future__ import annotations

import importlib.util
import py_compile
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
MODEL = {"name": "gpt-5.4-mini", "version": "2026-03-17"}
AGENTS = ("scanner", "reviewer", "orchestrator")


def _validate_agent_service(name: str, service: dict, failures: list[str]) -> None:
    expected_entry = f"src/{name}_agent.py"
    if service.get("host") != "azure.ai.agent" or service.get("kind") != "hosted":
        failures.append(f"azure.yaml: {name} must be a hosted azure.ai.agent service.")
    code = service.get("codeConfiguration", {})
    if code.get("runtime") != "python_3_13" or code.get("entryPoint") != expected_entry:
        failures.append(f"azure.yaml: {name} must use Python 3.13 entry point {expected_entry}.")
    if service.get("protocols") != [{"protocol": "responses", "version": "2.0.0"}]:
        failures.append(f"azure.yaml: {name} must declare Responses protocol 2.0.0.")
    if "docker" in service or "resourceName" in service:
        failures.append(f"azure.yaml: {name} must use Foundry code deployment, not Container Apps.")


def main() -> int:
    failures: list[str] = []
    if sys.version_info < (3, 11):
        failures.append("Python 3.11 or later is required for local validation.")
    for package in (
        "yaml",
        "packaging",
        "jsonschema",
        "fastapi",
        "uvicorn",
        "dotenv",
        "azure.identity",
        "httpx",
        "agent_framework",
        "agent_framework_foundry_hosting",
    ):
        if importlib.util.find_spec(package) is None:
            failures.append(f"Missing package: {package}")

    try:
        definitions = [
            yaml.safe_load(path.read_text(encoding="utf-8"))
            for path in sorted((ROOT / "agents").glob("*.yml"))
        ]
        if {definition.get("name") for definition in definitions} != set(AGENTS):
            failures.append("Expected scanner, reviewer, and orchestrator definitions.")
        for definition in definitions:
            if definition.get("model") != MODEL:
                failures.append(f"{definition.get('name')}: model policy must be {MODEL}.")
            hosted = definition.get("hosted", {})
            if hosted.get("kind") != "hosted" or hosted.get("protocol_version") != "2.0.0":
                failures.append(f"{definition.get('name')}: invalid hosted-agent v2 manifest.")
            if not definition.get("instructions") or not definition.get("tools"):
                failures.append(f"{definition.get('name')}: instructions and tool contracts are required.")
    except (OSError, yaml.YAMLError) as error:
        failures.append(f"Invalid agent definition: {error}")

    try:
        azd_config = yaml.safe_load((ROOT / "azure.yaml").read_text(encoding="utf-8"))
        services = azd_config.get("services", {})
        for service_name in AGENTS:
            _validate_agent_service(service_name, services.get(service_name, {}), failures)
        if services.get("dashboard", {}).get("host") != "containerapp":
            failures.append("azure.yaml: dashboard must be the only Container Apps service.")
        container_apps = [name for name, service in services.items() if service.get("host") == "containerapp"]
        if container_apps != ["dashboard"]:
            failures.append(f"azure.yaml: expected only dashboard on Container Apps, found {container_apps}.")
        deployment = services.get("ai-project", {}).get("deployments", [{}])[0].get("model", {})
        if deployment.get("name") != MODEL["name"] or deployment.get("version") != MODEL["version"]:
            failures.append("azure.yaml: exact model name/version policy is required.")
    except (OSError, yaml.YAMLError) as error:
        failures.append(f"Invalid azure.yaml: {error}")

    active_source = "\n".join(
        path.read_text(encoding="utf-8")
        for folder in ("src", "dashboard")
        for path in (ROOT / folder).glob("*.py")
    )
    for obsolete in ("AIProjectClient", "azure.ai.agents", "AGENT_NAME=orchestrator"):
        if obsolete in active_source:
            failures.append(f"Obsolete v1 or pseudo-agent pattern remains active: {obsolete}")
    for marker in ("version_indicator", "agent_session_id", "x-ms-agent-version"):
        if marker not in active_source:
            failures.append(f"Version-bound hosted-agent invocation marker is missing: {marker}")
    if "RELEASE_CHANNEL" in active_source or "RELEASE_CHANNEL" in (ROOT / "azure.yaml").read_text(encoding="utf-8"):
        failures.append("Dashboard release channel must derive from authoritative request routing.")

    bicep = (ROOT / "infra" / "delivery-resources.bicep").read_text(encoding="utf-8")
    if bicep.count("Microsoft.App/containerApps@") != 1 or "resource dashboard " not in bicep:
        failures.append("Bicep must define exactly one Container App for the dashboard.")
    for marker in ("Microsoft.CognitiveServices/accounts@", "accounts/projects@", "NoAutoUpgrade"):
        if marker not in bicep:
            failures.append(f"delivery-resources.bicep: missing Foundry marker {marker}.")

    source_files = (
        list((ROOT / "src").glob("*.py"))
        + list((ROOT / "dashboard").glob("*.py"))
        + list((ROOT / "scripts").glob("*.py"))
        + list((ROOT / "tests").glob("*.py"))
    )
    for source in source_files:
        try:
            py_compile.compile(str(source), doraise=True)
        except py_compile.PyCompileError as error:
            failures.append(str(error))

    if failures:
        print("Preflight failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Preflight passed. Three Foundry hosted agents v2 and one release dashboard are ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
