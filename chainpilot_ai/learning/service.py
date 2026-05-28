from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta, timezone
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


def _today() -> date:
    if _frappe_ready():
        return frappe.utils.getdate(frappe.utils.today())
    return datetime.now(timezone.utc).date()


def build_learning_signal(target: str, reason: str) -> dict[str, str]:
    if not target or not reason:
        raise ValueError("target and reason are required.")
    return {"target": target, "reason": reason}


def build_rule_adjustment(signal: dict[str, Any], current_weight: float = 1.0) -> dict[str, Any]:
    target = signal.get("target")
    if not target:
        raise ValueError("Learning signal target is required.")
    delta = float(signal.get("suggested_weight_delta") or -0.1)
    suggested = max(0.1, round(float(current_weight) + delta, 2))
    return {
        "adjustment_id": f"RWA-{signal.get('signal_id') or target}".replace(" ", "-"),
        "signal_id": signal.get("signal_id"),
        "target_type": signal.get("target_type") or "Action Type",
        "target": target,
        "current_weight": float(current_weight),
        "suggested_weight": suggested,
        "confidence": _confidence_from_delta(delta),
        "rationale": signal.get("reason") or "Generated from feedback signal.",
        "status": "Draft",
        "generated_at": _now(),
    }


def calculate_learning_metrics(
    packages: list[dict[str, Any]],
    feedback: list[dict[str, Any]],
    executions: list[dict[str, Any]],
    communications: list[dict[str, Any]],
    shortage_events: list[dict[str, Any]],
) -> dict[str, Any]:
    total_packages = len(packages)
    approved = sum(1 for item in packages if item.get("status") == "Approved")
    rejected = sum(1 for item in packages if item.get("status") == "Rejected")
    supplier_feedback = [item for item in feedback if item.get("feedback_type") == "Supplier Feedback" or item.get("supplier_response")]
    accepted_supplier = sum(1 for item in supplier_feedback if "accept" in str(item.get("supplier_response") or "").lower())
    supplier_denominator = len(supplier_feedback) or len(communications)
    expected_cash = sum(float(item.get("expected_cash_release") or 0) for item in executions)
    realized_cash = sum(float(item.get("realized_cash_release") or 0) for item in executions)
    rejection_reasons = Counter(
        (item.get("reason") or item.get("comment") or "Unspecified")
        for item in feedback
        if item.get("feedback_type") == "Rejected"
    )
    return {
        "adoption_rate": _percent(approved, total_packages),
        "rejection_rate": _percent(rejected, total_packages),
        "supplier_acceptance_rate": _percent(accepted_supplier, supplier_denominator),
        "realization_rate": _percent(realized_cash, expected_cash),
        "approved_package_count": approved,
        "rejected_package_count": rejected,
        "supplier_feedback_count": len(supplier_feedback),
        "total_expected_cash": round(expected_cash, 2),
        "total_realized_cash": round(realized_cash, 2),
        "shortage_event_count": len(shortage_events),
        "top_rejection_reason": rejection_reasons.most_common(1)[0][0] if rejection_reasons else "No rejection yet",
        "rejection_reasons": [{"reason": reason, "count": count} for reason, count in rejection_reasons.most_common(8)],
    }


@_whitelist
def seed_learning_mock_data() -> dict[str, Any]:
    if not _frappe_ready():
        return _mock_dashboard()

    _seed_execution_outcomes()
    _seed_supplier_feedback()
    _seed_shortage_events()
    _seed_rule_adjustments()
    dashboard = get_learning_dashboard()
    snapshot = _snapshot_from_metrics(dashboard["metrics"])
    _insert_doc("Learning Metric Snapshot", "snapshot_id", snapshot)
    frappe.db.commit()
    dashboard = get_learning_dashboard()
    dashboard["snapshot"] = snapshot
    return dashboard


@_whitelist
def get_learning_dashboard() -> dict[str, Any]:
    if not _frappe_ready():
        return _mock_dashboard()

    packages = _get_rows(
        "Approval Package",
        ["package_id", "status", "recommendation_count", "total_cash_release", "risk_summary", "approval_summary", "submitted_at", "approved_at", "rejected_reason"],
        "modified desc",
        30,
    )
    feedback = _get_rows(
        "Feedback Record",
        ["feedback_id", "package_id", "recommendation_id", "feedback_type", "reason", "comment", "supplier_response", "created_at"],
        "created_at desc",
        50,
    )
    executions = _get_rows(
        "Execution Result",
        ["execution_id", "draft_id", "recommendation_id", "status", "expected_cash_release", "realized_cash_release", "unrealized_reason", "monitored_at"],
        "modified desc",
        50,
    )
    communications = _get_rows(
        "Supplier Communication Draft",
        ["communication_id", "package_id", "recommendation_id", "supplier", "sap_doc_no", "status", "subject", "message", "created_at"],
        "modified desc",
        50,
    )
    signals = _get_rows(
        "Learning Signal",
        ["signal_id", "feedback_id", "target_type", "target", "reason", "suggested_weight_delta", "status"],
        "modified desc",
        30,
    )
    shortage_events = _get_rows(
        "Shortage Event",
        ["event_id", "recommendation_id", "material_code", "plant", "severity", "event_date", "lost_revenue_estimate", "root_cause", "linked_action", "status"],
        "event_date desc",
        20,
    )
    adjustments = _get_rows(
        "Rule Weight Adjustment",
        ["adjustment_id", "signal_id", "target_type", "target", "current_weight", "suggested_weight", "confidence", "rationale", "status", "generated_at"],
        "modified desc",
        30,
    )
    snapshots = _get_rows(
        "Learning Metric Snapshot",
        ["snapshot_id", "period_start", "period_end", "adoption_rate", "supplier_acceptance_rate", "realization_rate", "shortage_event_count", "top_rejection_reason", "summary", "generated_at"],
        "generated_at desc",
        8,
    )
    metrics = calculate_learning_metrics(packages, feedback, executions, communications, shortage_events)
    return {
        "ok": True,
        "counts": {
            "Learning Metric Snapshot": len(snapshots),
            "Shortage Event": len(shortage_events),
            "Rule Weight Adjustment": len(adjustments),
            "Feedback Record": len(feedback),
            "Learning Signal": len(signals),
        },
        "metrics": metrics,
        "packages": packages[:12],
        "feedback": feedback[:20],
        "executions": executions[:20],
        "communications": communications[:20],
        "signals": signals[:20],
        "shortage_events": shortage_events,
        "adjustments": adjustments,
        "snapshots": snapshots,
        "insights": _build_insights(metrics, adjustments, shortage_events),
    }


def _seed_execution_outcomes() -> None:
    rows = frappe.get_all(
        "Execution Result",
        fields=["name", "execution_id", "expected_cash_release", "realized_cash_release", "status"],
        order_by="creation asc",
        limit=8,
    )
    ratios = [0.92, 0.85, 0.76, 1.0, 0.68, 0, 0.88, 0.81]
    for index, row in enumerate(rows):
        doc = frappe.get_doc("Execution Result", row.name)
        expected = float(doc.expected_cash_release or 0)
        ratio = ratios[index % len(ratios)]
        doc.realized_cash_release = round(expected * ratio, 2)
        doc.status = "Executed" if ratio else "Failed"
        doc.unrealized_reason = "Closed by M5 mock learning snapshot." if ratio else "Supplier confirmation expired before manual SAP execution."
        doc.monitored_at = _now()
        doc.save(ignore_permissions=True)


def _seed_supplier_feedback() -> None:
    rows = frappe.get_all(
        "Supplier Communication Draft",
        fields=["name", "communication_id", "package_id", "recommendation_id", "supplier"],
        order_by="creation asc",
        limit=6,
    )
    responses = ["Accepted", "Accepted with later ship date", "Countered", "Accepted", "Rejected", "Accepted"]
    for index, row in enumerate(rows):
        doc = frappe.get_doc("Supplier Communication Draft", row.name)
        response = responses[index % len(responses)]
        doc.status = "Sent" if "Accepted" in response else "Reviewed"
        doc.save(ignore_permissions=True)
        feedback_id = f"FDBK-SUP-{row.communication_id[-18:]}"
        _insert_doc(
            "Feedback Record",
            "feedback_id",
            {
                "feedback_id": feedback_id,
                "package_id": row.package_id,
                "recommendation_id": row.recommendation_id,
                "feedback_type": "Supplier Feedback",
                "reason": "Supplier Response",
                "comment": f"Supplier {row.supplier or '-'} response captured by M5 mock loop.",
                "supplier_response": response,
                "created_at": _now(),
            },
        )


def _seed_shortage_events() -> None:
    rows = frappe.get_all(
        "Recommendation",
        filters={"approval_status": ["in", ["Rejected", "Approved"]]},
        fields=["name", "recommendation_id", "material_code", "plant", "action_type"],
        order_by="modified desc",
        limit=4,
    )
    event_day = _today() - timedelta(days=1)
    for index, row in enumerate(rows[:3]):
        severity = ["Medium", "High", "Medium"][index]
        _insert_doc(
            "Shortage Event",
            "event_id",
            {
                "event_id": f"SHE-{row.recommendation_id}",
                "recommendation_id": row.recommendation_id,
                "material_code": row.material_code,
                "plant": row.plant,
                "severity": severity,
                "event_date": event_day,
                "lost_revenue_estimate": [180000, 420000, 95000][index],
                "root_cause": f"{row.action_type} needs stronger confirmation before recommendation ranking.",
                "linked_action": row.action_type,
                "status": "Contained" if index != 1 else "Open",
            },
        )


def _seed_rule_adjustments() -> None:
    signals = frappe.get_all(
        "Learning Signal",
        fields=["name", "signal_id", "target_type", "target", "reason", "suggested_weight_delta"],
        order_by="modified desc",
        limit=12,
    )
    for signal in signals:
        _insert_doc("Rule Weight Adjustment", "adjustment_id", build_rule_adjustment(dict(signal), 1.0))


def _snapshot_from_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    today = _today()
    return {
        "snapshot_id": f"LMS-{today.strftime('%Y%m%d')}",
        "period_start": today - timedelta(days=30),
        "period_end": today,
        "adoption_rate": metrics["adoption_rate"],
        "rejection_rate": metrics["rejection_rate"],
        "supplier_acceptance_rate": metrics["supplier_acceptance_rate"],
        "realization_rate": metrics["realization_rate"],
        "total_expected_cash": metrics["total_expected_cash"],
        "total_realized_cash": metrics["total_realized_cash"],
        "shortage_event_count": metrics["shortage_event_count"],
        "top_rejection_reason": metrics["top_rejection_reason"],
        "summary": (
            f"Adoption {metrics['adoption_rate']:.1f}%, supplier acceptance {metrics['supplier_acceptance_rate']:.1f}%, "
            f"realization {metrics['realization_rate']:.1f}%."
        ),
        "generated_at": _now(),
    }


def _build_insights(metrics: dict[str, Any], adjustments: list[dict[str, Any]], shortage_events: list[dict[str, Any]]) -> list[dict[str, str]]:
    insights = [
        {
            "title": "Realization discipline",
            "body": f"Realized {metrics['realization_rate']:.1f}% of expected cash; keep manual SAP execution and Finance reconciliation visible.",
            "tone": "green" if metrics["realization_rate"] >= 75 else "amber",
        },
        {
            "title": "Supplier confirmation",
            "body": f"Supplier acceptance is {metrics['supplier_acceptance_rate']:.1f}%; rank PO delay actions lower when confirmation is missing.",
            "tone": "green" if metrics["supplier_acceptance_rate"] >= 60 else "amber",
        },
    ]
    if shortage_events:
        insights.append(
            {
                "title": "Shortage guardrail",
                "body": f"{len(shortage_events)} shortage events should feed safety stock and supplier lead-time weights before the next recommendation run.",
                "tone": "red",
            }
        )
    if adjustments:
        insights.append(
            {
                "title": "Rule adjustment queue",
                "body": f"{len(adjustments)} draft adjustments are waiting for business review before applying to ranking.",
                "tone": "blue",
            }
        )
    return insights


def _get_rows(doctype: str, fields: list[str], order_by: str, limit: int) -> list[dict[str, Any]]:
    try:
        return [dict(row) for row in frappe.get_all(doctype, fields=fields, order_by=order_by, limit=limit)]
    except Exception:
        return []


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


def _percent(numerator: float, denominator: float) -> float:
    if not denominator:
        return 0.0
    return round(float(numerator) / float(denominator) * 100, 1)


def _confidence_from_delta(delta: float) -> float:
    return min(95.0, max(55.0, round(70.0 + abs(delta) * 100, 1)))


def _mock_dashboard() -> dict[str, Any]:
    packages = [
        {"package_id": "APKG-MOCK-APPROVED", "status": "Approved", "total_cash_release": 6350000},
        {"package_id": "APKG-MOCK-REJECTED", "status": "Rejected", "total_cash_release": 1450000},
    ]
    feedback = [
        {"feedback_id": "FDBK-001", "feedback_type": "Rejected", "reason": "Supplier confirmation missing"},
        {"feedback_id": "FDBK-002", "feedback_type": "Supplier Feedback", "supplier_response": "Accepted"},
    ]
    executions = [
        {"execution_id": "EXE-001", "status": "Executed", "expected_cash_release": 920000, "realized_cash_release": 820000},
        {"execution_id": "EXE-002", "status": "Failed", "expected_cash_release": 410000, "realized_cash_release": 0},
    ]
    communications = [{"communication_id": "SUP-001", "status": "Sent", "supplier": "S000219"}]
    shortage_events = [{"event_id": "SHE-001", "severity": "High", "material_code": "MAT-000003", "status": "Open"}]
    metrics = calculate_learning_metrics(packages, feedback, executions, communications, shortage_events)
    signals = [{"signal_id": "LSIG-001", "target_type": "Action Type", "target": "DELAY_UNCONFIRMED_PO", "suggested_weight_delta": -0.1, "status": "New"}]
    adjustments = [build_rule_adjustment(signals[0], 1.0)]
    return {
        "ok": True,
        "counts": {"Learning Metric Snapshot": 1, "Shortage Event": 1, "Rule Weight Adjustment": 1, "Feedback Record": 2, "Learning Signal": 1},
        "metrics": metrics,
        "packages": packages,
        "feedback": feedback,
        "executions": executions,
        "communications": communications,
        "signals": signals,
        "shortage_events": shortage_events,
        "adjustments": adjustments,
        "snapshots": [_snapshot_from_metrics(metrics)],
        "insights": _build_insights(metrics, adjustments, shortage_events),
    }
