from __future__ import annotations

from typing import Any


def deployment_order(agents: dict[str, Any]) -> list[str]:
    """Return a stable topological order with dependencies before consumers."""
    indegree = {name: 0 for name in agents}
    dependents = {name: [] for name in agents}

    for consumer, metadata in agents.items():
        for dependency in metadata.get("depends_on", {}):
            if dependency not in agents:
                raise ValueError(f"Unknown dependency {dependency} for {consumer}")
            indegree[consumer] += 1
            dependents[dependency].append(consumer)

    ready = sorted(name for name, count in indegree.items() if count == 0)
    order: list[str] = []
    while ready:
        current = ready.pop(0)
        order.append(current)
        for consumer in sorted(dependents[current]):
            indegree[consumer] -= 1
            if indegree[consumer] == 0:
                ready.append(consumer)
                ready.sort()

    if len(order) != len(agents):
        raise ValueError("Agent dependency graph contains a cycle")
    return order


def rollback_closure(agents: dict[str, Any], failed_agent: str) -> list[str]:
    """Return the failed agent plus all transitive dependents in reverse order."""
    if failed_agent not in agents:
        raise ValueError(f"Unknown failed agent: {failed_agent}")

    dependents = {name: [] for name in agents}
    for consumer, metadata in agents.items():
        for dependency in metadata.get("depends_on", {}):
            if dependency not in agents:
                raise ValueError(f"Unknown dependency {dependency} for {consumer}")
            dependents[dependency].append(consumer)

    affected = {failed_agent}
    pending = [failed_agent]
    while pending:
        dependency = pending.pop()
        for consumer in sorted(dependents[dependency]):
            if consumer not in affected:
                affected.add(consumer)
                pending.append(consumer)

    return [name for name in reversed(deployment_order(agents)) if name in affected]