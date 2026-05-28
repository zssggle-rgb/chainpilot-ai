from __future__ import annotations


def build_learning_signal(target: str, reason: str) -> dict[str, str]:
    if not target or not reason:
        raise ValueError("target and reason are required.")
    return {"target": target, "reason": reason}
