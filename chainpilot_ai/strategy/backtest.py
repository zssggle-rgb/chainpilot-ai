from __future__ import annotations

import json
from statistics import mean
from typing import Any

from chainpilot_ai.algorithms.registry import run_mvp_algorithms
from chainpilot_ai.strategy.mock_history import generate_mock_history
from chainpilot_ai.strategy.policy import scenario_from_strategy, strategy_presets


def run_strategy_backtest(
    strategy: dict[str, Any],
    history_days: int | None = None,
    sample_interval_days: int | None = None,
) -> dict[str, Any]:
    params = strategy["parameter_json"]
    history_days = int(history_days or params.get("mock_history_days") or 120)
    sample_interval_days = int(sample_interval_days or params.get("sample_interval_days") or 14)
    scenario = scenario_from_strategy(strategy)
    snapshots = generate_mock_history(history_days, sample_interval_days)

    true_positive = false_positive = false_negative = 0
    recommended_cash = realized_cash = 0.0
    hard_constraint_violations = 0
    master_data_issues = 0
    daily_scores: list[float] = []
    detail_rows: list[dict[str, Any]] = []

    for snapshot in snapshots:
        runtime = run_mvp_algorithms(snapshot, scenario=scenario)
        actual_shortages = set(snapshot.get("_actual_outcomes", {}).get("shortage_materials") or [])
        predicted_shortages = _predicted_shortage_materials(runtime)
        true_positive += len(predicted_shortages & actual_shortages)
        false_positive += len(predicted_shortages - actual_shortages)
        false_negative += len(actual_shortages - predicted_shortages)

        cash_rows = _selected_cash_rows(runtime)
        recommended_cash += sum(float(row.get("cash_impact") or 0) for row in cash_rows)
        realized_cash += sum(_realized_cash(row, strategy) for row in cash_rows)
        hard_constraint_violations += sum(1 for row in cash_rows if row.get("constraint_verdict") == "BLOCKED" or float(row.get("risk_after") or 0) > 0.12)
        master_data_issues += sum(1 for row in runtime["results"] if row["result_type"] == "MASTER_DATA_ISSUE")
        daily_scores.append(_daily_score(predicted_shortages, actual_shortages, cash_rows))
        detail_rows.extend(_detail_rows(snapshot, runtime, actual_shortages)[:6])

    recall = _ratio(true_positive, true_positive + false_negative)
    precision = _ratio(true_positive, true_positive + false_positive)
    false_intervention_rate = _ratio(false_positive, true_positive + false_positive)
    cash_realization_rate = _ratio(realized_cash, recommended_cash)
    score = _overall_score(recall, precision, cash_realization_rate, false_intervention_rate, hard_constraint_violations)
    return {
        "backtest_id": f"BT-{strategy['strategy_id']}-{history_days}D",
        "strategy_id": strategy["strategy_id"],
        "strategy_name": strategy["strategy_name"],
        "strategy_type": strategy["strategy_type"],
        "status": "Pass" if hard_constraint_violations == 0 else "Needs Review",
        "history_days": history_days,
        "sample_count": len(snapshots),
        "recall_rate": round(recall, 4),
        "precision_rate": round(precision, 4),
        "cash_release_total": round(recommended_cash, 2),
        "realized_cash_total": round(realized_cash, 2),
        "cash_realization_rate": round(cash_realization_rate, 4),
        "false_intervention_rate": round(false_intervention_rate, 4),
        "hard_constraint_violations": hard_constraint_violations,
        "master_data_issue_count": master_data_issues,
        "score": round(score, 2),
        "daily_score_avg": round(mean(daily_scores), 2) if daily_scores else 0,
        "detail_rows": detail_rows[:30],
        "summary_json": json.dumps(
            {
                "true_positive": true_positive,
                "false_positive": false_positive,
                "false_negative": false_negative,
                "scenario": scenario,
            },
            ensure_ascii=False,
            sort_keys=True,
        ),
    }


def tune_strategy_presets(history_days: int = 120) -> dict[str, Any]:
    strategies = strategy_presets()
    backtests = [run_strategy_backtest(strategy, history_days=history_days) for strategy in strategies]
    ranked = sorted(backtests, key=lambda row: row["score"], reverse=True)
    return {
        "ok": True,
        "history_days": history_days,
        "strategies": strategies,
        "backtests": backtests,
        "recommended_strategy_id": ranked[0]["strategy_id"] if ranked else "",
        "recommended_strategy_name": ranked[0]["strategy_name"] if ranked else "",
        "requires_human_approval": True,
        "decision_note": "系统只推荐策略版本，必须由业务负责人确认后启用。",
    }


def _predicted_shortage_materials(runtime: dict[str, Any]) -> set[str]:
    return {
        row["material_code"]
        for row in runtime["results"]
        if row["result_type"] == "SHORTAGE_RISK" and float((row.get("raw") or {}).get("shortage_probability_14d") or 0) > 0
    }


def _selected_cash_rows(runtime: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for row in runtime["results"]:
        raw = row.get("raw") or {}
        if raw.get("result_type") == "CASH_RELEASE_ACTION" and raw.get("selected") and raw.get("constraint_verdict") != "BLOCKED":
            rows.append(raw)
    return rows


def _realized_cash(row: dict[str, Any], strategy: dict[str, Any]) -> float:
    base = float(row.get("cash_impact") or 0)
    strategy_type = strategy.get("strategy_type")
    if strategy_type == "Conservative":
        rate = 0.86
    elif strategy_type == "Aggressive":
        rate = 0.70
    else:
        rate = 0.80
    if row.get("recommendation_level") == "L3_SUPPLIER_CONFIRM":
        rate -= 0.08
    return max(0.0, base * rate)


def _daily_score(predicted: set[str], actual: set[str], cash_rows: list[dict[str, Any]]) -> float:
    recall = _ratio(len(predicted & actual), len(actual))
    precision = _ratio(len(predicted & actual), len(predicted))
    cash_score = min(1.0, sum(float(row.get("cash_impact") or 0) for row in cash_rows) / 12_000_000)
    return round((recall * 45 + precision * 25 + cash_score * 30), 2)


def _overall_score(recall: float, precision: float, realization: float, false_intervention: float, violations: int) -> float:
    return max(0.0, recall * 38 + precision * 22 + realization * 28 - false_intervention * 12 - violations * 10)


def _detail_rows(snapshot: dict[str, Any], runtime: dict[str, Any], actual_shortages: set[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    snapshot_id = snapshot.get("snapshot", {}).get("snapshot_id")
    for result in runtime["results"]:
        raw = result.get("raw") or {}
        if raw.get("result_type") == "SHORTAGE_RISK":
            rows.append(
                {
                    "result_type": "SHORTAGE_RISK",
                    "snapshot_id": snapshot_id,
                    "material_code": raw.get("material_code"),
                    "metric_name": "缺料预测",
                    "metric_value": raw.get("shortage_probability_14d"),
                    "expected_value": "实际缺料" if raw.get("material_code") in actual_shortages else "未缺料",
                    "verdict": "命中" if raw.get("material_code") in actual_shortages else "误报",
                }
            )
        elif raw.get("result_type") == "CASH_RELEASE_ACTION" and raw.get("selected"):
            rows.append(
                {
                    "result_type": "CASH_RELEASE_ACTION",
                    "snapshot_id": snapshot_id,
                    "material_code": raw.get("material_code"),
                    "metric_name": "资金改善",
                    "metric_value": raw.get("cash_impact"),
                    "expected_value": raw.get("constraint_verdict"),
                    "verdict": "可执行" if raw.get("constraint_verdict") != "BLOCKED" else "阻断",
                }
            )
    return rows


def _ratio(numerator: float, denominator: float) -> float:
    return float(numerator) / float(denominator) if denominator else 0.0
