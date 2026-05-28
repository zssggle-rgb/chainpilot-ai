from __future__ import annotations


def explanation_status(evidence_ids: list[str] | tuple[str, ...]) -> str:
    return "Ready" if evidence_ids else "NEED_EVIDENCE"
