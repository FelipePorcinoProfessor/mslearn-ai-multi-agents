from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from .memory_store import PatientMemoryStore


async def prune_memories(
    store: PatientMemoryStore,
    patient_id: str,
    memories: list[dict[str, Any]],
    dry_run: bool,
) -> dict[str, Any]:
    """Apply importance and age policy while preserving critical memories."""
    # LAB PLACEHOLDER 6: Replace this line with the Task 6 sample.
    raise NotImplementedError("Complete prune_memories in Task 6")