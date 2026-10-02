from __future__ import annotations

from typing import Any


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def select_context(memories: list[dict[str, Any]], token_budget: int) -> dict[str, Any]:
    """Select important and recent memories without exceeding a token budget."""
    # LAB PLACEHOLDER 5: Replace this line with the Task 5 sample.
    raise NotImplementedError("Complete select_context in Task 5")