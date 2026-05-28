from __future__ import annotations


def execution_health(statuses: list[str]) -> dict[str, int]:
    return {status: statuses.count(status) for status in sorted(set(statuses))}
