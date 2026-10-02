"""Select, export, and evaluate human corrections for active learning."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def project_example(item: dict[str, Any]) -> dict[str, Any]:
    review = item["human_review"]
    return {
        "workflow_id": item["workflow_id"],
        "trace_id": item["trace_id"],
        "policy_version": item["policy_version"],
        "risk": item["risk"],
        "request": item["request"],
        "human_decision": review["decision"],
        "rationale_category": review["category"],
        "reviewer_comment": review["comment"],
        "reviewed_at": review["reviewed_at"],
    }


def evaluate(examples: list[dict[str, Any]]) -> dict[str, Any]:
    decisions = Counter(example["human_decision"] for example in examples)
    categories = Counter(example["rationale_category"] for example in examples)
    total = len(examples)
    return {
        "example_count": total,
        "decision_counts": dict(decisions),
        "rationale_category_counts": dict(categories),
        "rejection_rate": round(decisions["REJECTED"] / total, 4) if total else 0.0,
        "override_rate": round(decisions["OVERRIDDEN"] / total, 4) if total else 0.0,
        "trace_coverage": len({example["trace_id"] for example in examples}),
    }


def main() -> None:
    from .main import create_workflow

    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("reports/active-learning.jsonl"))
    parser.add_argument("--evaluation", type=Path, default=Path("reports/active-learning-evaluation.json"))
    parser.add_argument("--max-items", type=int, default=100)
    args = parser.parse_args()
    items = create_workflow().select_active_learning_examples(args.max_items)
    examples = [project_example(item) for item in items]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(item) + "\n" for item in examples), encoding="utf-8")
    args.evaluation.write_text(json.dumps(evaluate(examples), indent=2), encoding="utf-8")
    print(json.dumps({"dataset": str(args.output), "evaluation": str(args.evaluation), **evaluate(examples)}, indent=2))


if __name__ == "__main__":
    main()