from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from chainpilot_ai.strategy.backtest import run_strategy_backtest, tune_strategy_presets
from chainpilot_ai.strategy.policy import SEGMENT_ORDER, strategy_by_id, strategy_presets

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
def get_strategy_optimization_dashboard(history_days: int = 120) -> dict[str, Any]:
    history_days = int(history_days or 120)
    tuned = tune_strategy_presets(history_days=history_days)
    return {
        **tuned,
        "segment_order": SEGMENT_ORDER,
        "page_mode": "mock_history_backtest",
        "sap_writeback_mode": "draft_only",
        "latest_persisted": _latest_persisted_backtests(),
    }


@_whitelist
def run_backtest_rpc(strategy_id: str | None = None, history_days: int = 120) -> dict[str, Any]:
    strategy = strategy_by_id(strategy_id)
    result = run_strategy_backtest(strategy, history_days=int(history_days or 120))
    if _frappe_ready():
        _persist_strategy(strategy)
        _persist_backtest(result)
        frappe.db.commit()
    return {"ok": True, "strategy": strategy, "backtest": result, "persisted": _frappe_ready()}


@_whitelist
def get_strategy_presets() -> dict[str, Any]:
    return {"ok": True, "strategies": strategy_presets(), "segment_order": SEGMENT_ORDER}


def _persist_strategy(strategy: dict[str, Any]) -> None:
    if not frappe.db.exists("DocType", "Decision Strategy"):
        return
    payload = {
        "doctype": "Decision Strategy",
        "strategy_id": strategy["strategy_id"],
        "strategy_name": strategy["strategy_name"],
        "strategy_type": strategy["strategy_type"],
        "status": strategy["status"],
        "version": strategy["version"],
        "description": strategy["description"],
        "parameter_json": json.dumps(strategy["parameter_json"], ensure_ascii=False, sort_keys=True),
    }
    _upsert("Decision Strategy", "strategy_id", payload)


def _persist_backtest(backtest: dict[str, Any]) -> None:
    if not frappe.db.exists("DocType", "Backtest Run"):
        return
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    run_payload = {
        "doctype": "Backtest Run",
        "backtest_id": backtest["backtest_id"],
        "strategy_id": backtest["strategy_id"],
        "strategy_name": backtest["strategy_name"],
        "status": backtest["status"],
        "history_days": backtest["history_days"],
        "sample_count": backtest["sample_count"],
        "started_at": now,
        "finished_at": now,
        "recall_rate": backtest["recall_rate"],
        "precision_rate": backtest["precision_rate"],
        "cash_release_total": backtest["cash_release_total"],
        "realized_cash_total": backtest["realized_cash_total"],
        "false_intervention_rate": backtest["false_intervention_rate"],
        "hard_constraint_violations": backtest["hard_constraint_violations"],
        "score": backtest["score"],
        "summary_json": backtest["summary_json"],
    }
    _upsert("Backtest Run", "backtest_id", run_payload)
    if not frappe.db.exists("DocType", "Backtest Result"):
        return
    for index, row in enumerate(backtest["detail_rows"][:30], start=1):
        result_payload = {
            "doctype": "Backtest Result",
            "result_id": f"{backtest['backtest_id']}-{index:03d}",
            "backtest_run": backtest["backtest_id"],
            "result_type": row["result_type"],
            "material_code": row.get("material_code"),
            "metric_name": row.get("metric_name"),
            "metric_value": str(row.get("metric_value")),
            "expected_value": str(row.get("expected_value")),
            "verdict": row.get("verdict"),
            "detail_json": json.dumps(row, ensure_ascii=False, sort_keys=True),
        }
        _upsert("Backtest Result", "result_id", result_payload)


def _latest_persisted_backtests() -> list[dict[str, Any]]:
    if not _frappe_ready() or not frappe.db.exists("DocType", "Backtest Run"):
        return []
    return frappe.get_all(
        "Backtest Run",
        fields=["backtest_id", "strategy_id", "strategy_name", "status", "history_days", "recall_rate", "precision_rate", "cash_release_total", "realized_cash_total", "false_intervention_rate", "hard_constraint_violations", "score", "modified"],
        order_by="modified desc",
        limit=6,
    )


def _upsert(doctype: str, key_field: str, payload: dict[str, Any]) -> str:
    existing = frappe.db.exists(doctype, payload[key_field])
    if existing:
        doc = frappe.get_doc(doctype, existing)
        doc.update(payload)
        doc.save(ignore_permissions=True)
        return doc.name
    doc = frappe.get_doc(payload)
    doc.insert(ignore_permissions=True)
    return doc.name
