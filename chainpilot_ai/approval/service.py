from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from chainpilot_ai.writeback.service import create_writeback_drafts_for_package

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


def summarize_package(recommendation_count: int, total_cash_release: float) -> dict[str, object]:
    if recommendation_count < 0:
        raise ValueError("recommendation_count cannot be negative.")
    return {
        "recommendation_count": recommendation_count,
        "total_cash_release": round(float(total_cash_release), 2),
    }


def build_approval_summary(recommendations: list[dict[str, Any]]) -> dict[str, Any]:
    if not recommendations:
        raise ValueError("recommendations are required.")
    total = sum(float(item.get("cash_release") or 0) for item in recommendations)
    po_count = sum(1 for item in recommendations if item.get("sap_object_type") == "PO")
    pr_count = sum(1 for item in recommendations if item.get("sap_object_type") == "PR")
    risk_count = sum(1 for item in recommendations if float(item.get("shortage_risk_after") or 0) >= 2.5)
    summary = summarize_package(len(recommendations), total)
    summary.update(
        {
            "risk_count": risk_count,
            "risk_summary": f"{risk_count} high-attention actions; {po_count} PO coordination items; {pr_count} PR quantity changes.",
            "approval_summary": (
                f"Package covers {len(recommendations)} SAP line actions with expected cash release {total:,.0f}. "
                f"Review focus: safety stock, supplier confirmation, and draft-only SAP writeback payloads."
            ),
        }
    )
    return summary


def dry_run_package(limit: int = 5) -> dict[str, Any]:
    from chainpilot_ai.scripts.import_demo_data import DEFAULT_DEMO_PATH, load_demo_data

    recommendations = load_demo_data(DEFAULT_DEMO_PATH)["recommendations"][:limit]
    summary = build_approval_summary(recommendations)
    return {
        "package_id": _unique_id("APKG"),
        "status": "Submitted",
        "recommendation_ids": [item["recommendation_id"] for item in recommendations],
        **summary,
    }


@_whitelist
def create_approval_package_rpc(limit: int = 5) -> dict[str, Any]:
    if not _frappe_ready():
        return {"ok": False, "status": "NO_SITE", "package": dry_run_package(limit)}
    recommendations = _eligible_recommendations(int(limit))
    if not recommendations:
        raise ValueError("No eligible Recommendation found. Need Pending/Ready recommendations with evidence and no BLOCKED constraint.")
    summary = build_approval_summary(recommendations)
    package_id = _unique_id("APKG")
    scenario_result = recommendations[0].get("result_id")
    package = {
        "doctype": "Approval Package",
        "package_id": package_id,
        "status": "Submitted",
        "scenario_result": scenario_result,
        "recommendation_ids": json.dumps([item["recommendation_id"] for item in recommendations], ensure_ascii=False),
        "recommendation_count": summary["recommendation_count"],
        "total_cash_release": summary["total_cash_release"],
        "risk_summary": summary["risk_summary"],
        "approval_summary": summary["approval_summary"],
        "requester": getattr(frappe.session, "user", "Administrator"),
        "submitted_at": _now(),
    }
    _insert_doc("Approval Package", "package_id", package)
    tasks = _build_approval_tasks(package_id, summary["total_cash_release"], summary["risk_count"])
    for task in tasks:
        _insert_doc("Approval Task", "task_id", task)
    frappe.db.commit()
    return {"ok": True, "package": package, "tasks": tasks}


@_whitelist
def approve_package_rpc(package_id: str | None = None, approver: str = "ChainPilot Mock Approver", comment: str = "Approved in M4 mock workflow.") -> dict[str, Any]:
    if not _frappe_ready():
        return {"ok": False, "status": "NO_SITE"}
    package = _latest_package(package_id)
    if not package:
        raise ValueError("No Approval Package found.")
    now = _now()
    for task in frappe.get_all("Approval Task", filters={"package_id": package.name}, fields=["name"]):
        doc = frappe.get_doc("Approval Task", task.name)
        doc.status = "Approved"
        doc.approver = approver
        doc.decision_comment = comment
        doc.decided_at = now
        doc.save(ignore_permissions=True)
    recommendation_ids = json.loads(package.recommendation_ids)
    for recommendation_id in recommendation_ids:
        rec = frappe.get_doc("Recommendation", recommendation_id)
        rec.approval_status = "Approved"
        rec.save(ignore_permissions=True)
    package.status = "Approved"
    package.approved_by = approver
    package.approved_at = now
    package.save(ignore_permissions=True)
    frappe.db.commit()
    writeback = create_writeback_drafts_for_package(package.name)
    return {"ok": True, "package_id": package.name, "writeback": writeback}


@_whitelist
def reject_package_rpc(package_id: str | None = None, reason: str = "Business owner rejected the package in mock workflow.") -> dict[str, Any]:
    if not _frappe_ready():
        return {"ok": False, "status": "NO_SITE"}
    package = _latest_package(package_id)
    if not package:
        raise ValueError("No Approval Package found.")
    now = _now()
    package.status = "Rejected"
    package.rejected_reason = reason
    package.save(ignore_permissions=True)
    feedback = []
    signals = []
    for recommendation_id in json.loads(package.recommendation_ids):
        rec = frappe.get_doc("Recommendation", recommendation_id)
        rec.approval_status = "Rejected"
        rec.save(ignore_permissions=True)
        feedback_doc = {
            "doctype": "Feedback Record",
            "feedback_id": _unique_id("FDBK"),
            "package_id": package.name,
            "recommendation_id": recommendation_id,
            "feedback_type": "Rejected",
            "reason": "Approval Rejected",
            "comment": reason,
            "created_at": now,
        }
        _insert_doc("Feedback Record", "feedback_id", feedback_doc)
        signal_doc = {
            "doctype": "Learning Signal",
            "signal_id": _unique_id("LSIG"),
            "feedback_id": feedback_doc["feedback_id"],
            "target_type": "Action Type",
            "target": rec.action_type,
            "reason": reason,
            "suggested_weight_delta": -0.1,
            "status": "New",
        }
        _insert_doc("Learning Signal", "signal_id", signal_doc)
        feedback.append(feedback_doc)
        signals.append(signal_doc)
    frappe.db.commit()
    return {"ok": True, "package_id": package.name, "feedback": feedback, "signals": signals}


def _eligible_recommendations(limit: int) -> list[dict[str, Any]]:
    rows = frappe.get_all(
        "Recommendation",
        filters={"approval_status": "Pending", "explanation_status": "Ready"},
        fields=[
            "name",
            "recommendation_id",
            "result_id",
            "action_type",
            "sap_object_type",
            "sap_doc_no",
            "sap_item_no",
            "material_code",
            "supplier",
            "before_qty",
            "after_qty",
            "before_date",
            "after_date",
            "cash_release",
            "shortage_risk_after",
        ],
        order_by="cash_release desc",
        limit=limit * 4,
    )
    eligible = []
    for row in rows:
        evidence_count = frappe.db.count("Recommendation Evidence", {"recommendation_id": row.recommendation_id})
        blocked_count = frappe.db.count("Constraint Check Result", {"recommendation_id": row.recommendation_id, "verdict": "BLOCKED"})
        if evidence_count and not blocked_count:
            eligible.append(dict(row))
        if len(eligible) >= limit:
            break
    return eligible


def _build_approval_tasks(package_id: str, total_cash_release: float, risk_count: int) -> list[dict[str, Any]]:
    roles = ["ChainPilot Planning Manager", "ChainPilot Procurement Manager"]
    if total_cash_release >= 5_000_000:
        roles.append("ChainPilot Finance BP")
    if total_cash_release >= 20_000_000 or risk_count:
        roles.append("ChainPilot Supply Chain Director")
    return [
        {
            "doctype": "Approval Task",
            "task_id": _unique_id("ATSK"),
            "package_id": package_id,
            "approval_role": role,
            "status": "Pending",
        }
        for role in roles
    ]


def _latest_package(package_id: str | None):
    if package_id:
        return frappe.get_doc("Approval Package", package_id)
    rows = frappe.get_all("Approval Package", filters={"status": ["in", ["Submitted", "Draft"]]}, fields=["name"], order_by="submitted_at desc", limit=1)
    if rows:
        return frappe.get_doc("Approval Package", rows[0].name)
    rows = frappe.get_all("Approval Package", fields=["name"], order_by="modified desc", limit=1)
    return frappe.get_doc("Approval Package", rows[0].name) if rows else None


def _insert_doc(doctype: str, key_field: str, payload: dict[str, Any]) -> str:
    clean_payload = {key: value for key, value in payload.items() if key != "doctype"}
    existing = frappe.db.exists(doctype, clean_payload[key_field])
    if existing:
        doc = frappe.get_doc(doctype, existing)
        doc.update(clean_payload)
        doc.save(ignore_permissions=True)
        return doc.name
    doc = frappe.get_doc({"doctype": doctype, **clean_payload})
    doc.insert(ignore_permissions=True)
    return doc.name
