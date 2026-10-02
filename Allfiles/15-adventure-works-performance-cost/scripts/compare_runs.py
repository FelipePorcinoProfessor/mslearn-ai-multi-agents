"""Compare measured control and optimized summaries."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    runs = [json.loads(Path(name).read_text(encoding="utf-8")) for name in sys.argv[1:]]
    control = runs[0]
    comparison = []
    for run in runs[1:]:
        comparison.append(
            {
                "policy": run["policy"],
                "cost_delta_usd": round(run["total_cost_usd"] - control["total_cost_usd"], 6),
                "input_token_delta": run["total_input_tokens"] - control["total_input_tokens"],
                "quality_delta": round(run["quality_mean"] - control["quality_mean"], 2),
                "p95_latency_delta_ms": run["latency_p95_ms"] - control["latency_p95_ms"],
                "cache_hit_rate": run["cache_hit_rate"],
                "exact_result_cache_hit_rate": run["exact_result_cache_hit_rate"],
                "prompt_cache_hit_rate": run["prompt_cache_hit_rate"],
            }
        )
    print(json.dumps(comparison, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())