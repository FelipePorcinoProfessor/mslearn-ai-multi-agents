"""Run a synthetic three-agent flow with real OpenTelemetry instrumentation."""

import argparse
import json
from pathlib import Path

import yaml
from dotenv import load_dotenv

from .telemetry import run_chain


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="assets/trace-scenario.json")
    parser.add_argument("--policy", default="config/telemetry-policy.yaml")
    parser.add_argument("--output", default="evidence/trace-evidence.json")
    args = parser.parse_args()
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    scenario = json.loads(Path(args.scenario).read_text(encoding="utf-8"))
    policy = yaml.safe_load(Path(args.policy).read_text(encoding="utf-8"))
    result = run_chain(scenario, policy)
    destination = Path(args.output)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("correlation_complete", "trace_id", "span_count", "anomalies", "error_rate", "error_rate_anomaly")}, indent=2))


if __name__ == "__main__":
    main()