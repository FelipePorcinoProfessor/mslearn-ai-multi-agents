"""Run live multi-agent evaluation and apply deterministic quality gates."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from azure.ai.evaluation import evaluate
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from .evaluators import create_evaluators


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def calibration_agreement(rows: list[dict[str, Any]]) -> float:
    """Return exact agreement between rounded judge scores and human labels."""
    # LAB PLACEHOLDER 2
    return 0.0


def apply_regression_gate(
    metrics: dict[str, float], agreement: float, config: dict[str, Any]
) -> dict[str, Any]:
    """Compare measured metrics with absolute, delta, and calibration gates."""
    # LAB PLACEHOLDER 3
    return {
        "passed": False,
        "failed_gates": ["implementation_incomplete"],
        "comparisons": [],
        "calibration_agreement": agreement,
    }


def run(data_path: Path, output_path: Path) -> dict[str, Any]:
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    endpoint = os.environ["FOUNDRY_ACCOUNT_ENDPOINT"]
    deployment = os.environ["FOUNDRY_MODEL_NAME"]
    api_version = os.getenv("FOUNDRY_API_VERSION", "2024-10-21")
    config = load_json(Path("assets/evaluation-config.json"))
    credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
    model_config = {
        "azure_endpoint": endpoint,
        "azure_deployment": deployment,
        "api_version": api_version,
        "project_endpoint": os.environ["FOUNDRY_PROJECT_ENDPOINT"],
    }
    evaluators = create_evaluators(model_config, credential)

    # LAB PLACEHOLDER 4
    evaluation = None
    if evaluation is None:
        raise NotImplementedError("Complete the batch evaluation task before running the lab.")
    rows = list(evaluation["rows"])
    metrics = {name: float(value) for name, value in evaluation["metrics"].items()}
    agreement = calibration_agreement(rows)
    report = {
        "dataset": str(data_path),
        "deployment": deployment,
        "evaluators": sorted(evaluators),
        "metrics": metrics,
        "gate": apply_regression_gate(metrics, agreement, config),
        "row_count": len(rows),
    }
    # LAB PLACEHOLDER 5
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("assets/evaluation-data.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("reports/evaluation-result.json"))
    args = parser.parse_args()
    print(json.dumps(run(args.data, args.output), indent=2))


if __name__ == "__main__":
    main()