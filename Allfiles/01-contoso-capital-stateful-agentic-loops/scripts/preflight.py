"""Side-effect-free local readiness checks for Lab 01."""

from __future__ import annotations

import ast
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    checks = {
        "python_3_11": sys.version_info >= (3, 11),
        "synthetic_input": (ROOT / "assets/research-request.json").is_file(),
        "input_shape": bool(json.loads((ROOT / "assets/research-request.json").read_text(encoding="utf-8")).get("research_request")),
        "starter_syntax": bool(ast.parse((ROOT / "src/main.py").read_text(encoding="utf-8"))),
        "endpoint_configured": bool(os.getenv("FOUNDRY_PROJECT_ENDPOINT")),
        "model_configured": bool(os.getenv("FOUNDRY_MODEL_NAME")),
    }
    for name, passed in checks.items():
        print(f"{'PASS' if passed else 'INFO'} {name}")
    local_ready = all(checks[name] for name in ("python_3_11", "synthetic_input", "input_shape", "starter_syntax"))
    print("READY (local)" if local_ready else "NOT READY")
    return 0 if local_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())