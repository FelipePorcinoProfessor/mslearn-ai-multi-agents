from __future__ import annotations

from typing import Any


def evaluate_quality_gate(metrics: dict[str, Any]) -> dict[str, Any]:
    """Return a machine-readable promote, hold, or rollback decision."""
    baseline = metrics["baseline"]
    candidate = metrics["candidate"]
    tolerances = metrics["tolerances"]
    rollback_reasons: list[str] = []
    hold_reasons: list[str] = []

    if candidate["quality"] < baseline["quality"] - tolerances["quality_drop"]:
        rollback_reasons.append("quality_drop")
    if candidate["schema_violation_rate"] > tolerances["schema_violation_max"]:
        rollback_reasons.append("schema_violation_rate")
    if candidate["error_rate"] > baseline["error_rate"] * tolerances["error_rate_multiplier"]:
        hold_reasons.append("error_rate")
    if candidate["p95_latency_ms"] > baseline["p95_latency_ms"] * tolerances["latency_multiplier"]:
        hold_reasons.append("p95_latency_ms")

    if rollback_reasons:
        action = "rollback"
    elif hold_reasons:
        action = "hold"
    else:
        action = "promote"

    return {"action": action, "reasons": rollback_reasons + hold_reasons}