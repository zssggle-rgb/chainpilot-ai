from __future__ import annotations

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


def execution_health(statuses: list[str]) -> dict[str, int]:
    return {status: statuses.count(status) for status in sorted(set(statuses))}


@_whitelist
def get_execution_dashboard() -> dict[str, object]:
    if not _frappe_ready():
        return {
            "ok": True,
            "counts": {
                "Approval Package": 0,
                "SAP Writeback Draft": 0,
                "Execution Result": 0,
                "Feedback Record": 0,
                "Learning Signal": 0,
            },
            "packages": [],
            "tasks": [],
            "drafts": [],
            "communications": [],
            "executions": [],
            "feedback": [],
            "signals": [],
        }
    packages = frappe.get_all(
        "Approval Package",
        fields=["package_id", "status", "recommendation_count", "total_cash_release", "risk_summary", "approval_summary", "submitted_at", "approved_by", "approved_at", "rejected_reason"],
        order_by="modified desc",
        limit=8,
    )
    tasks = frappe.get_all(
        "Approval Task",
        fields=["task_id", "package_id", "approval_role", "approver", "status", "decision_comment", "decided_at"],
        order_by="modified desc",
        limit=12,
    )
    drafts = frappe.get_all(
        "SAP Writeback Draft",
        fields=["draft_id", "package_id", "recommendation_id", "status", "safety_mode", "sap_object_type", "sap_doc_no", "sap_item_no", "conflict_status", "target_api", "approved_by", "approved_at"],
        order_by="modified desc",
        limit=12,
    )
    communications = frappe.get_all(
        "Supplier Communication Draft",
        fields=["communication_id", "package_id", "recommendation_id", "supplier", "sap_doc_no", "status", "subject", "message", "created_at"],
        order_by="modified desc",
        limit=8,
    )
    executions = frappe.get_all(
        "Execution Result",
        fields=["execution_id", "draft_id", "recommendation_id", "status", "expected_cash_release", "realized_cash_release", "unrealized_reason", "monitored_at"],
        order_by="modified desc",
        limit=12,
    )
    feedback = frappe.get_all(
        "Feedback Record",
        fields=["feedback_id", "package_id", "recommendation_id", "feedback_type", "reason", "comment", "created_at"],
        order_by="modified desc",
        limit=8,
    )
    signals = frappe.get_all(
        "Learning Signal",
        fields=["signal_id", "feedback_id", "target_type", "target", "reason", "suggested_weight_delta", "status"],
        order_by="modified desc",
        limit=8,
    )
    return {
        "ok": True,
        "counts": {
            "Approval Package": frappe.db.count("Approval Package"),
            "Approval Task": frappe.db.count("Approval Task"),
            "SAP Writeback Draft": frappe.db.count("SAP Writeback Draft"),
            "Supplier Communication Draft": frappe.db.count("Supplier Communication Draft"),
            "Execution Result": frappe.db.count("Execution Result"),
            "Feedback Record": frappe.db.count("Feedback Record"),
            "Learning Signal": frappe.db.count("Learning Signal"),
        },
        "packages": packages,
        "tasks": tasks,
        "drafts": drafts,
        "communications": communications,
        "executions": executions,
        "feedback": feedback,
        "signals": signals,
        "health": execution_health([item.status for item in executions]),
    }
