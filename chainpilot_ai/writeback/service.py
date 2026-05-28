from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

try:
    import frappe
except Exception:  # pragma: no cover - local smoke tests can run without a Frappe site.
    frappe = None


def _whitelist(fn):
    if frappe:
        return frappe.whitelist()(fn)
    return fn


def _frappe_ready() -> bool:
    try:
        return bool(frappe and getattr(frappe.local, "site", None) and getattr(frappe, "db", None))
    except Exception:
        return False


def _now() -> str:
    if _frappe_ready():
        return str(frappe.utils.now_datetime())
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _unique_id(prefix: str) -> str:
    return f"{prefix}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"


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


def _json_dumps(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, default=str)


def build_writeback_draft(recommendation: dict[str, Any], package_id: str, approved_by: str = "ChainPilot Mock Approver") -> dict[str, Any]:
    if recommendation.get("approval_status") != "Approved":
        raise ValueError("Only Approved Recommendation can generate SAP Writeback Draft.")
    old_value, new_value = _value_pair(recommendation)
    current_value = dict(old_value)
    conflict_status = "Match" if current_value == old_value else "Conflict"
    draft_id = _unique_id("WBD")
    payload = create_draft_payload(
        recommendation["sap_object_type"],
        recommendation["sap_doc_no"],
        recommendation["sap_item_no"],
        new_value,
    )
    return {
        "draft_id": draft_id,
        "package_id": package_id,
        "recommendation_id": recommendation["recommendation_id"],
        "status": "Ready" if conflict_status == "Match" else "Conflict",
        "safety_mode": "DRAFT_ONLY",
        "sap_object_type": recommendation["sap_object_type"],
        "sap_doc_no": recommendation["sap_doc_no"],
        "sap_item_no": recommendation["sap_item_no"],
        "target_api": _target_api(recommendation["sap_object_type"]),
        "old_value_json": _json_dumps(old_value),
        "new_value_json": _json_dumps(new_value),
        "current_value_json": _json_dumps(current_value),
        "conflict_status": conflict_status,
        "payload_json": _json_dumps(payload),
        "rollback_payload_json": _json_dumps(create_draft_payload(recommendation["sap_object_type"], recommendation["sap_doc_no"], recommendation["sap_item_no"], old_value)),
        "approved_by": approved_by,
        "approved_at": _now(),
    }


def create_execution_result(draft: dict[str, Any], recommendation: dict[str, Any]) -> dict[str, Any]:
    return {
        "execution_id": draft["draft_id"].replace("WBD", "EXE"),
        "draft_id": draft["draft_id"],
        "recommendation_id": recommendation["recommendation_id"],
        "status": "Draft Ready",
        "expected_cash_release": recommendation.get("cash_release") or 0,
        "realized_cash_release": 0,
        "unrealized_reason": "Awaiting approved manual SAP execution. Production SAP auto-write is disabled.",
        "monitored_at": _now(),
    }


def build_supplier_communication(recommendation: dict[str, Any], package_id: str) -> dict[str, Any] | None:
    if recommendation.get("sap_object_type") != "PO" and recommendation.get("action_type") != "DELAY_UNCONFIRMED_PO":
        return None
    return {
        "communication_id": _unique_id("SUP"),
        "package_id": package_id,
        "recommendation_id": recommendation["recommendation_id"],
        "supplier": recommendation.get("supplier"),
        "sap_doc_no": recommendation.get("sap_doc_no"),
        "status": "Draft",
        "subject": f"PO {recommendation.get('sap_doc_no')} delivery date coordination",
        "message": (
            f"Please confirm whether PO {recommendation.get('sap_doc_no')}/{recommendation.get('sap_item_no')} "
            f"for material {recommendation.get('material_code')} can move from {recommendation.get('before_date')} "
            f"to {recommendation.get('after_date')}. This is a draft communication and is not sent automatically."
        ),
        "created_at": _now(),
    }


@_whitelist
def create_writeback_drafts_for_package(package_id: str) -> dict[str, Any]:
    if not _frappe_ready():
        return {"ok": False, "status": "NO_SITE", "drafts": []}
    package = frappe.get_doc("Approval Package", package_id)
    if package.status != "Approved":
        raise ValueError("Approval Package must be Approved before generating Writeback Drafts.")
    recommendation_ids = json.loads(package.recommendation_ids)
    drafts = []
    communications = []
    executions = []
    for recommendation_id in recommendation_ids:
        rec = frappe.get_doc("Recommendation", recommendation_id)
        if rec.approval_status != "Approved":
            continue
        draft = build_writeback_draft(rec.as_dict(), package.name, package.approved_by or "ChainPilot Mock Approver")
        _insert_doc("SAP Writeback Draft", "draft_id", draft)
        execution = create_execution_result(draft, rec.as_dict())
        _insert_doc("Execution Result", "execution_id", execution)
        communication = build_supplier_communication(rec.as_dict(), package.name)
        if communication:
            _insert_doc("Supplier Communication Draft", "communication_id", communication)
            communications.append(communication)
        rec.writeback_status = "Draft"
        rec.save(ignore_permissions=True)
        drafts.append(draft)
        executions.append(execution)
    frappe.db.commit()
    return {"ok": True, "drafts": drafts, "communications": communications, "executions": executions}


def _value_pair(recommendation: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    action_type = recommendation.get("action_type")
    if action_type in {"REDUCE_PR_QTY", "REVIEW_SAFETY_STOCK"}:
        return (
            {"quantity": recommendation.get("before_qty")},
            {"quantity": recommendation.get("after_qty")},
        )
    if action_type in {"DELAY_UNCONFIRMED_PO", "ADVANCE_RISK_MATERIAL"}:
        return (
            {"delivery_date": recommendation.get("before_date")},
            {"delivery_date": recommendation.get("after_date")},
        )
    return (
        {"before_qty": recommendation.get("before_qty"), "before_date": recommendation.get("before_date")},
        {"after_qty": recommendation.get("after_qty"), "after_date": recommendation.get("after_date")},
    )


def _target_api(sap_object_type: str) -> str:
    if sap_object_type == "PR":
        return "/sap/opu/odata/sap/API_PURCHASEREQ_PROCESS_SRV/A_PurchaseRequisitionItem"
    if sap_object_type == "PO":
        return "/sap/opu/odata/sap/API_PURCHASEORDER_PROCESS_SRV/A_PurchaseOrderItem"
    return "/sap/opu/odata/sap/API_MATERIAL_SRV/A_ProductPlant"


def _insert_doc(doctype: str, key_field: str, payload: dict[str, Any]) -> str:
    existing = frappe.db.exists(doctype, payload[key_field])
    if existing:
        doc = frappe.get_doc(doctype, existing)
        doc.update(payload)
        doc.save(ignore_permissions=True)
        return doc.name
    doc = frappe.get_doc({"doctype": doctype, **payload})
    doc.insert(ignore_permissions=True)
    return doc.name
