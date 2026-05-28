from __future__ import annotations


def snapshot_key(*parts: object) -> str:
    if not parts:
        raise ValueError("At least one key part is required.")
    return "::".join(str(part) for part in parts)
