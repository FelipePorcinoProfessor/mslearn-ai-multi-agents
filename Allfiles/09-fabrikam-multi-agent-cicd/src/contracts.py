from __future__ import annotations

from typing import Any


def find_breaking_changes(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> list[dict[str, str]]:
    """Find backward-incompatible changes to agent tool contracts."""
    findings: list[dict[str, str]] = []

    for agent_name in sorted(baseline):
        if agent_name not in candidate:
            findings.append({"path": agent_name, "change": "agent removed"})
            continue

        baseline_tools = baseline[agent_name]
        candidate_tools = candidate[agent_name]
        for tool_name in sorted(baseline_tools):
            path = f"{agent_name}.{tool_name}"
            if tool_name not in candidate_tools:
                findings.append({"path": path, "change": "tool removed"})
                continue

            baseline_tool = baseline_tools[tool_name]
            candidate_tool = candidate_tools[tool_name]
            baseline_inputs = set(baseline_tool.get("input", {}).get("required", []))
            candidate_inputs = set(candidate_tool.get("input", {}).get("required", []))
            for field_name in sorted(candidate_inputs - baseline_inputs):
                findings.append(
                    {"path": f"{path}.input.{field_name}", "change": "required input added"}
                )

            baseline_outputs = set(baseline_tool.get("output", {}).get("required", []))
            candidate_outputs = set(candidate_tool.get("output", {}).get("required", []))
            for field_name in sorted(baseline_outputs - candidate_outputs):
                findings.append(
                    {"path": f"{path}.output.{field_name}", "change": "required output removed"}
                )

            for direction in ("input", "output"):
                baseline_types = baseline_tool.get(direction, {}).get("types", {})
                candidate_types = candidate_tool.get(direction, {}).get("types", {})
                for field_name in sorted(baseline_types.keys() & candidate_types.keys()):
                    if baseline_types[field_name] != candidate_types[field_name]:
                        findings.append(
                            {
                                "path": f"{path}.{direction}.{field_name}",
                                "change": (
                                    f"type changed from {baseline_types[field_name]} "
                                    f"to {candidate_types[field_name]}"
                                ),
                            }
                        )

    return findings