from __future__ import annotations

from typing import Any

from .memory_store import PatientMemoryStore


async def validate_read_your_writes(
    store: PatientMemoryStore,
    memory: dict[str, Any],
) -> dict[str, Any]:
    """Write a memory and point-read it using the returned session token."""
    # LAB PLACEHOLDER 4: Replace this line with the Task 4 sample.
    raise NotImplementedError("Complete validate_read_your_writes in Task 4")