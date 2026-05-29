from __future__ import annotations

import json
from typing import Any

from chainpilot_ai.algorithms.registry import run_mvp_algorithms
from chainpilot_ai.recommendation.result_to_recommendation import convert_algorithm_results
from chainpilot_ai.scripts.run_mvp_algorithms import run as run_mvp_algorithms_script
from chainpilot_ai.snapshots.mock_loader import load_mock_sap_snapshot

try:
    import frappe
except Exception:  # pragma: no cover - local tests run without a Frappe site.
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


@_whitelist
def run_algorithm_runtime_rpc() -> dict[str, Any]:
    return run_mvp_algorithms_script(dry_run=False)


@_whitelist
def get_algorithm_runtime_dashboard() -> dict[str, Any]:
    if _frappe_ready():
        dashboard = _dashboard_from_frappe()
        if dashboard["counts"]["Algorithm Run"]:
            return dashboard
    return _dashboard_from_dry_run()


def _dashboard_from_dry_run() -> dict[str, Any]:
    runtime = run_mvp_algorithms(load_mock_sap_snapshot())
    generated = convert_algorithm_results(runtime)
    all_results = [item for item in runtime["results"]]
    raw_results = [_raw(item) for item in all_results]
    return {
        "ok": True,
        "mode": "dry_run",
        "snapshot_id": runtime["snapshot_id"],
        "counts": {
            "Algorithm Run": runtime["counts"]["algorithm_runs"],
            "Algorithm Result": runtime["counts"]["algorithm_results"],
            "Recommendation": len(generated["recommendations"]),
        },
        "runs": [item["run"] for item in runtime["runs"]],
        "shortage": sorted([item for item in raw_results if item.get("result_type") == "SHORTAGE_RISK"], key=lambda row: row.get("shortage_probability_14d") or 0, reverse=True)[:10],
        "cash": sorted([item for item in raw_results if item.get("result_type") == "CASH_RELEASE_ACTION" and item.get("selected")], key=lambda row: row.get("cash_impact") or 0, reverse=True)[:10],
        "blocked_cash": [item for item in raw_results if item.get("result_type") == "CASH_RELEASE_ACTION" and item.get("constraint_verdict") == "BLOCKED"][:10],
        "master_data": sorted([item for item in raw_results if item.get("result_type") == "MASTER_DATA_ISSUE"], key=lambda row: row.get("impact_amount") or 0, reverse=True)[:10],
        "recommendations": generated["recommendations"][:20],
    }


def _dashboard_from_frappe() -> dict[str, Any]:
    runs = frappe.get_all(
        "Algorithm Run",
        fields=["algorithm_run_id", "algorithm_code", "snapshot_id", "status", "started_at", "finished_at", "duration_ms", "summary_result_json"],
        order_by="started_at desc",
        limit=12,
    )
    results = frappe.get_all(
        "Algorithm Result",
        fields=["result_id", "algorithm_run", "result_type", "material_code", "plant", "supplier", "sap_object_type", "sap_doc_no", "sap_item_no", "metric_name", "metric_value", "raw_json"],
        order_by="modified desc",
        limit=200,
    )
    raw_results = [_raw(dict(item)) for item in results]
    recommendations = frappe.get_all(
        "Recommendation",
        fields=["recommendation_id", "snapshot_id", "algorithm_run", "algorithm_result", "action_type", "sap_object_type", "sap_doc_no", "sap_item_no", "material_code", "plant", "supplier", "cash_release", "shortage_risk_after", "recommendation_level", "constraint_verdict", "approval_status", "evidence_count"],
        order_by="modified desc",
        limit=20,
    )
    return {
        "ok": True,
        "mode": "frappe",
        "snapshot_id": runs[0].snapshot_id if runs else "",
        "counts": {
            "Algorithm Run": frappe.db.count("Algorithm Run"),
            "Algorithm Result": frappe.db.count("Algorithm Result"),
            "Recommendation": frappe.db.count("Recommendation", {"algorithm_run": ["is", "set"]}),
        },
        "runs": [dict(item) for item in runs],
        "shortage": sorted([item for item in raw_results if item.get("result_type") == "SHORTAGE_RISK"], key=lambda row: row.get("shortage_probability_14d") or 0, reverse=True)[:10],
        "cash": sorted([item for item in raw_results if item.get("result_type") == "CASH_RELEASE_ACTION" and item.get("selected")], key=lambda row: row.get("cash_impact") or 0, reverse=True)[:10],
        "blocked_cash": [item for item in raw_results if item.get("result_type") == "CASH_RELEASE_ACTION" and item.get("constraint_verdict") == "BLOCKED"][:10],
        "master_data": sorted([item for item in raw_results if item.get("result_type") == "MASTER_DATA_ISSUE"], key=lambda row: row.get("impact_amount") or 0, reverse=True)[:10],
        "recommendations": [dict(item) for item in recommendations],
    }


def _raw(row: dict[str, Any]) -> dict[str, Any]:
    raw_json = row.get("raw_json")
    if isinstance(row.get("raw"), dict):
        raw = dict(row["raw"])
    elif raw_json:
        try:
            raw = json.loads(str(raw_json))
        except json.JSONDecodeError:
            raw = {}
    else:
        raw = {}
    return {**row, **raw}
