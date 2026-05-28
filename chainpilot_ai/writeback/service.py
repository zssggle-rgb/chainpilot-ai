from __future__ import annotations


def create_draft_payload(sap_object_type: str, sap_doc_no: str, sap_item_no: str, changes: dict[str, object]) -> dict[str, object]:
    if not changes:
        raise ValueError("changes are required for a writeback draft.")
    return {
        "sap_object_type": sap_object_type,
        "sap_doc_no": sap_doc_no,
        "sap_item_no": sap_item_no,
        "changes": changes,
        "mode": "DRAFT_ONLY",
    }
