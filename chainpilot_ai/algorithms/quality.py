from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from chainpilot_ai.algorithms.registry import run_mvp_algorithms
from chainpilot_ai.snapshots.mock_loader import load_mock_sap_snapshot
from chainpilot_ai.snapshots.validators import snapshot_counts
from chainpilot_ai.strategy.backtest import run_strategy_backtest
from chainpilot_ai.strategy.policy import strategy_presets

ROOT = Path(__file__).resolve().parents[2]
QUALITY_REPORT_PATH = ROOT / "tmp" / "algorithm_quality_report.json"


def evaluate_algorithm_quality(
    history_days: int = 120,
    sample_interval_days: int = 14,
    write_report: bool = False,
) -> dict[str, Any]:
    snapshot = load_mock_sap_snapshot()
    runtime = run_mvp_algorithms(snapshot)
    backtests = [
        run_strategy_backtest(strategy, history_days=history_days, sample_interval_days=sample_interval_days)
        for strategy in strategy_presets()
    ]
    ranked = sorted(backtests, key=lambda row: row["score"], reverse=True)
    best = ranked[0] if ranked else {}
    shortage_summary = _run_summary(runtime, "SHORTAGE_RISK_14D_PROB")
    cash_summary = _run_summary(runtime, "CASH_RELEASE_PR_PO_OPT")
    report = {
        "ok": True,
        "basis": {
            "mock_snapshot_id": snapshot.get("snapshot", {}).get("snapshot_id"),
            "source_system": snapshot.get("snapshot", {}).get("source_system"),
            "history_days": history_days,
            "sample_interval_days": sample_interval_days,
            "record_counts": snapshot_counts(snapshot),
        },
        "forecast_quality": {
            "avg_wape": shortage_summary.get("avg_forecast_wape", 0),
            "avg_confidence": shortage_summary.get("avg_forecast_confidence", 0),
            "backtest_materials": shortage_summary.get("forecast_backtest_materials", 0),
            "model_counts": shortage_summary.get("forecast_model_counts", {}),
            "shortage_result_count": shortage_summary.get("result_count", 0),
        },
        "optimizer_quality": {
            "solver_name": cash_summary.get("solver_name"),
            "solver_status": cash_summary.get("solver_status"),
            "mip_gap": cash_summary.get("mip_gap"),
            "decision_variable_count": cash_summary.get("decision_variable_count", 0),
            "constraint_count": cash_summary.get("constraint_count", 0),
            "selected_actions": cash_summary.get("selected_actions", 0),
            "blocked_actions": cash_summary.get("blocked_actions", 0),
            "cash_release_total": cash_summary.get("cash_release_total", 0),
            "objective_components": cash_summary.get("objective_components", {}),
            "tight_constraints": [
                row for row in cash_summary.get("constraint_utilization", []) if row.get("status") == "紧约束"
            ],
        },
        "strategy_backtests": backtests,
        "recommended_strategy_id": best.get("strategy_id", ""),
        "recommended_strategy_name": best.get("strategy_name", ""),
        "quality_gates": _quality_gates(best, shortage_summary, cash_summary),
    }
    report["ok"] = all(row["pass"] for row in report["quality_gates"])
    if write_report:
        QUALITY_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        QUALITY_REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return report


def _run_summary(runtime: dict[str, Any], algorithm_code: str) -> dict[str, Any]:
    return next((run["summary"] for run in runtime["runs"] if run["run"]["algorithm_code"] == algorithm_code), {})


def _quality_gates(
    best_backtest: dict[str, Any],
    shortage_summary: dict[str, Any],
    cash_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    mip_gap = cash_summary.get("mip_gap")
    recall = _number(best_backtest.get("recall_rate"))
    precision = _number(best_backtest.get("precision_rate"))
    false_intervention = _number(best_backtest.get("false_intervention_rate"), default=1.0)
    forecast_wape = _number(shortage_summary.get("avg_forecast_wape"), default=1.0)
    hard_constraint_violations = int(best_backtest.get("hard_constraint_violations") or 0)
    cash_realization = _number(best_backtest.get("cash_realization_rate"))
    selected_actions = int(cash_summary.get("selected_actions") or 0)
    cash_release_total = _number(cash_summary.get("cash_release_total"))
    return [
        {
            "gate": "缺料召回率",
            "threshold": ">= 0.90",
            "actual": recall,
            "pass": recall >= 0.90,
        },
        {
            "gate": "缺料预测准确率",
            "threshold": ">= 0.90",
            "actual": precision,
            "pass": precision >= 0.90,
        },
        {
            "gate": "误干预率",
            "threshold": "<= 0.05",
            "actual": false_intervention,
            "pass": false_intervention <= 0.05,
        },
        {
            "gate": "预测模型 WAPE",
            "threshold": "<= 0.12",
            "actual": forecast_wape,
            "pass": forecast_wape <= 0.12,
        },
        {
            "gate": "硬约束违规",
            "threshold": "= 0",
            "actual": hard_constraint_violations,
            "pass": hard_constraint_violations == 0,
        },
        {
            "gate": "优化器求解状态",
            "threshold": "OPTIMAL / FEASIBLE",
            "actual": cash_summary.get("solver_status"),
            "pass": cash_summary.get("solver_status") in {"OPTIMAL", "FEASIBLE"},
        },
        {
            "gate": "MIP Gap",
            "threshold": "<= 0.001",
            "actual": mip_gap,
            "pass": mip_gap is not None and float(mip_gap) <= 0.001,
        },
        {
            "gate": "资金动作包规模",
            "threshold": ">= 15 条且金额 > 0",
            "actual": {
                "selected_actions": selected_actions,
                "cash_release_total": cash_release_total,
            },
            "pass": selected_actions >= 15 and cash_release_total > 0,
        },
        {
            "gate": "资金兑现率",
            "threshold": ">= 0.80",
            "actual": cash_realization,
            "pass": cash_realization >= 0.80,
        },
    ]


def _number(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default
