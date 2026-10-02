from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / "assets" / "workflows"
EXPECTED_WORKFLOWS = {
    "canary-quality-gate.yml",
    "deploy-environment.yml",
    "rollback-agents.yml",
    "validate-agents.yml",
}


def _require(text: str, markers: tuple[str, ...], path: str, failures: list[str]) -> None:
    for marker in markers:
        if marker not in text:
            failures.append(f"{path}: missing required marker {marker}")


def main() -> int:
    failures: list[str] = []
    paths = sorted(WORKFLOWS.glob("*.yml"))
    if {path.name for path in paths} != EXPECTED_WORKFLOWS:
        failures.append("Expected exactly the four supplied workflow templates.")
    for path in paths:
        text = path.read_text(encoding="utf-8")
        try:
            document = yaml.safe_load(text)
        except yaml.YAMLError as error:
            failures.append(f"{path.name}: invalid YAML: {error}")
            continue
        if not document.get("jobs"):
            failures.append(f"{path.name}: missing jobs")
        if "azure/login@" in text and "id-token: write" not in text:
            failures.append(f"{path.name}: Azure login requires OIDC id-token permission")
        if "AZURE_CREDENTIALS" in text:
            failures.append(f"{path.name}: long-lived credential secret is forbidden")
        for action in re.findall(r"uses:\s+([^\s]+)", text):
            if not action.startswith("./") and not re.fullmatch(r"[^@]+@v\d+", action):
                failures.append(f"{path.name}: action is not pinned to a major version: {action}")
        for line in text.splitlines():
            if (
                re.search(r"\bazd\s+(?:env|deploy|ai|provision)\b", line)
                and "AZURE_DEV_USER_AGENT=microsoft_foundry_skill" not in line
            ):
                failures.append(f"{path.name}: every azd command must set AZURE_DEV_USER_AGENT inline: {line.strip()}")
        if path.name != "validate-agents.yml" and "environment:" not in text:
            failures.append(f"{path.name}: missing GitHub environment binding")

    validate_text = (WORKFLOWS / "validate-agents.yml").read_text(encoding="utf-8")
    _require(
        validate_text,
        (
            "pull_request:",
            "scripts/export_release.py",
            "python -m unittest discover",
            "assets/evaluation/smoke-v1.jsonl",
            "actions/upload-artifact@v4",
        ),
        "validate-agents.yml",
        failures,
    )
    if "azure/login@" in validate_text:
        failures.append("validate-agents.yml: PR validation must remain credential-free")

    deploy_text = (WORKFLOWS / "deploy-environment.yml").read_text(encoding="utf-8")
    _require(
        deploy_text,
        (
            "needs: validate",
            "azd deploy scanner --no-prompt",
            "azd ai agent show scanner --output json",
            'azd ai agent invoke scanner --version "$scanner_version"',
            "azd deploy reviewer --no-prompt",
            "azd ai agent show reviewer --output json",
            "azd deploy orchestrator --no-prompt",
            "scripts/capture_release_set.py",
            "AGENT_ORCHESTRATOR_RESPONSES_ENDPOINT",
            "azd deploy dashboard --no-prompt",
            "--strategy canary",
            "scripts/release_manifest.py",
            "Persist proven first-release baseline",
            "bootstrap-revisions.json",
            '"scripts/**"',
            '"tests/**"',
            '"assets/workflows/**"',
        ),
        "deploy-environment.yml",
        failures,
    )
    scanner_position = deploy_text.find("azd deploy scanner --no-prompt")
    reviewer_position = deploy_text.find("azd deploy reviewer --no-prompt")
    orchestrator_position = deploy_text.find("azd deploy orchestrator --no-prompt")
    if not (0 <= scanner_position < reviewer_position < orchestrator_position):
        failures.append("deploy-environment.yml: agents must deploy serially in dependency order")

    canary_text = (WORKFLOWS / "canary-quality-gate.yml").read_text(encoding="utf-8")
    _require(
        canary_text,
        (
            "quality-regression-detected",
            "--strategy blue-green",
            "--stable-revision",
            "verified-${{ inputs.environment }}",
            "release-set.json",
            "scripts/release_manifest.py",
            "--routing-evidence artifacts/promotion-traffic.json",
        ),
        "canary-quality-gate.yml",
        failures,
    )

    rollback_text = (WORKFLOWS / "rollback-agents.yml").read_text(encoding="utf-8")
    _require(
        rollback_text,
        (
            "verified-${{ github.event.client_payload.environment }}",
            "scripts.restore_verified_release",
            "rollback-set",
            "--version \"$orchestrator_version\"",
            "/metadata",
            "actions/github-script@v7",
            "scripts/release_manifest.py",
            "--environment \"${{ github.event.client_payload.environment }}\"",
        ),
        "rollback-agents.yml",
        failures,
    )
    if "revisions[-2]" in rollback_text or "second-newest" in rollback_text:
        failures.append("rollback-agents.yml: rollback must not infer safety from revision age")

    expected_concurrency = {
        "deploy-environment.yml": "group: lab09-release-${{ github.event_name == 'push' && 'development' || inputs.environment }}",
        "canary-quality-gate.yml": "group: lab09-release-${{ inputs.environment }}",
        "rollback-agents.yml": "group: lab09-release-${{ github.event.client_payload.environment }}",
    }
    for workflow, marker in expected_concurrency.items():
        text = (WORKFLOWS / workflow).read_text(encoding="utf-8")
        _require(text, (marker, "cancel-in-progress: false"), workflow, failures)
    combined = deploy_text + canary_text + rollback_text
    if " || true" in combined:
        failures.append("State-changing workflows must not ignore manifest or routing failures")
    if "${fqdn/./--" in combined:
        failures.append("Label URLs must use Azure readback and the triple-hyphen hostname")
    if "RELEASE_CHANNEL" in combined:
        failures.append("Dashboard channel must be derived from authoritative request routing")

    if failures:
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Validated hosted-agent CI/CD, dashboard progressive delivery, and persisted rollback evidence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
