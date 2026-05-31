from __future__ import annotations

import random
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from statistics import mean, median, pstdev
from typing import Any

from chainpilot_ai.strategy.policy import policy_for_material


def run(snapshot: dict[str, Any], scenario: dict[str, Any] | None = None) -> dict[str, Any]:
    scenario = scenario or {}
    base_date = _snapshot_date(snapshot)
    horizon_days = int(scenario.get("horizon_days") or 14)
    simulations = int(scenario.get("simulations") or 600)
    max_results = int(scenario.get("max_shortage_results") or 120)
    forecast_reserve_ratio = float(scenario.get("forecast_reserve_ratio") or 0.0)
    inventory = {(row["material_code"], row["plant"]): row for row in snapshot.get("inventory", [])}
    demands = _group(snapshot.get("planned_demands", []), "material_code", "plant")
    history = _group(snapshot.get("consumption_history", []), "material_code", "plant")
    performance = _group(snapshot.get("supplier_performance", []), "material_code", "plant")
    po_lines = _group(snapshot.get("po_lines", []), "material_code", "plant")
    bom_by_material = _bom_index(snapshot.get("bom_components", []))
    materials = {(row["material_code"], row["plant"]): row for row in snapshot.get("materials", [])}

    results = []
    forecast_profiles: list[dict[str, Any]] = []
    for key, inv_row in inventory.items():
        material_code, plant = key
        material = materials.get(key, {})
        material_policy = policy_for_material(material, scenario)
        alert_threshold = float(material_policy.get("shortage_alert_threshold") or scenario.get("default_shortage_alert_threshold") or 0.2)
        material_demands = demands.get(key, [])
        if not material_demands:
            continue
        rng = random.Random(_stable_seed(material_code, plant))
        shortage_days: list[int] = []
        shortage_qtys: list[float] = []
        forecast_profile = _forecast_profile(history.get(key, []), material_demands, horizon_days)
        forecast_profiles.append(forecast_profile)
        demand_std = max(_demand_std(history.get(key, []), material_demands), float(forecast_profile.get("daily_uncertainty_qty") or 0))
        residual_daily_demand = max(0.0, float(forecast_profile.get("forecast_daily_qty") or 0) - _planned_daily_demand(material_demands, base_date, horizon_days))
        delay_samples = _delay_samples(performance.get(key, []))

        for _ in range(simulations):
            stock = float(inv_row.get("unrestricted_qty") or inv_row.get("available_stock") or 0)
            first_shortage_day = None
            worst_shortage = 0.0
            for day_offset in range(1, horizon_days + 1):
                current_day = base_date + timedelta(days=day_offset)
                inbound = _inbound_qty(po_lines.get(key, []), current_day, base_date, rng, delay_samples)
                demand = (
                    _demand_qty(material_demands, current_day)
                    + residual_daily_demand * forecast_reserve_ratio
                    + max(0, rng.gauss(0, demand_std * 0.35))
                )
                stock += inbound - demand
                safety_stock = float(inv_row.get("safety_stock") or 0)
                if stock < safety_stock:
                    first_shortage_day = first_shortage_day or day_offset
                    worst_shortage = max(worst_shortage, safety_stock - stock)
            if first_shortage_day:
                shortage_days.append(first_shortage_day)
                shortage_qtys.append(worst_shortage)

        probability = round(len(shortage_days) / simulations, 3)
        if probability < alert_threshold:
            continue
        shortage_day = _percentile(shortage_days, 0.5) if shortage_days else horizon_days
        shortage_qty_p90 = round(_percentile(shortage_qtys, 0.9), 2) if shortage_qtys else 0.0
        target_po = _nearest_po(po_lines.get(key, []), base_date)
        result = {
            "result_type": "SHORTAGE_RISK",
            "material_code": material_code,
            "plant": plant,
            "shortage_probability_14d": probability,
            "shortage_date_p50": str(base_date + timedelta(days=int(shortage_day))),
            "shortage_qty_p90": shortage_qty_p90,
            "affected_production_orders": sorted({row.get("production_order") for row in material_demands if row.get("production_order")}),
            "affected_finished_goods": sorted(set(bom_by_material.get(material_code, [])) | {row.get("finished_good") for row in material_demands if row.get("finished_good")}),
            "suggested_action": "EXPEDITE_PO" if target_po else "CREATE_EMERGENCY_PR",
            "target_po_no": target_po.get("po_no") if target_po else "",
            "target_po_item": target_po.get("po_item") if target_po else "",
            "supplier": target_po.get("supplier") if target_po else "",
            "sap_object_type": "PO" if target_po else "PR",
            "sap_doc_no": target_po.get("po_no") if target_po else f"NEW-PR-{material_code}",
            "sap_item_no": target_po.get("po_item") if target_po else "00010",
            "metric_name": "shortage_probability_14d",
            "metric_value": probability,
            "evidence": {
                "inventory": float(inv_row.get("unrestricted_qty") or 0),
                "safety_stock": float(inv_row.get("safety_stock") or 0),
                "demand_std": round(demand_std, 2),
                "forecast_model": forecast_profile["selected_model"],
                "forecast_model_label": forecast_profile["selected_model_label"],
                "forecast_wape": forecast_profile["wape"],
                "forecast_mae": forecast_profile["mae"],
                "forecast_holdout_points": forecast_profile["holdout_points"],
                "forecast_daily_qty": forecast_profile["forecast_daily_qty"],
                "forecast_confidence": forecast_profile["confidence"],
                "forecast_residual_daily_qty": round(residual_daily_demand, 2),
                "forecast_reserve_ratio": forecast_reserve_ratio,
                "forecast_driver_summary": forecast_profile["driver_summary"],
                "forecast_model_candidates": forecast_profile["candidate_metrics"],
                "simulation_count": simulations,
                "delay_samples": delay_samples,
                "abc_class": material.get("abc_class"),
                "xyz_class": material.get("xyz_class"),
                "service_level": material_policy.get("service_level"),
                "alert_threshold": alert_threshold,
            },
        }
        results.append(result)

    results.sort(key=lambda item: item["shortage_probability_14d"], reverse=True)
    limited_results = results[:max_results]
    return {
        "results": limited_results,
        "summary": {
            "result_count": len(limited_results),
            "high_risk_count": sum(1 for item in results if item["shortage_probability_14d"] >= 0.5),
            "forecast_model_counts": dict(Counter(profile["selected_model_label"] for profile in forecast_profiles)),
            "avg_forecast_wape": round(mean(float(profile["wape"]) for profile in forecast_profiles), 4) if forecast_profiles else 0.0,
            "avg_forecast_confidence": round(mean(float(profile["confidence"]) for profile in forecast_profiles), 4) if forecast_profiles else 0.0,
            "forecast_backtest_materials": len(forecast_profiles),
            "simulation_count": simulations,
            "horizon_days": horizon_days,
            "max_results": max_results,
        },
    }


def _snapshot_date(snapshot: dict[str, Any]) -> date:
    value = snapshot.get("snapshot", {}).get("snapshot_time") or "2026-05-29"
    return datetime.fromisoformat(str(value).replace(" ", "T")).date()


def _stable_seed(*values: str) -> int:
    return sum((index + 1) * ord(ch) for index, value in enumerate(values) for ch in value)


def _group(rows: list[dict[str, Any]], *keys: str) -> dict[tuple[str, ...], list[dict[str, Any]]]:
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(str(row.get(key)) for key in keys)].append(row)
    return grouped


def _bom_index(rows: list[dict[str, Any]]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        index[row["component_material"]].append(row["finished_good"])
    return index


def _demand_std(history_rows: list[dict[str, Any]], demand_rows: list[dict[str, Any]]) -> float:
    values = [float(row.get("actual_consumption_qty") or 0) for row in history_rows]
    if len(values) >= 2:
        return max(1.0, pstdev(values))
    demand_values = [float(row.get("demand_qty") or 0) for row in demand_rows]
    return max(1.0, mean(demand_values) * 0.2 if demand_values else 1.0)


def _forecast_profile(history_rows: list[dict[str, Any]], demand_rows: list[dict[str, Any]], horizon_days: int) -> dict[str, Any]:
    weekly_history = [
        float(row.get("actual_consumption_qty") or 0)
        for row in sorted(history_rows, key=lambda item: str(item.get("posting_date") or ""))
        if float(row.get("actual_consumption_qty") or 0) > 0
    ]
    if len(weekly_history) < 4:
        fallback_qty = mean([float(row.get("demand_qty") or 0) for row in demand_rows] or [0.0])
        weekly_history = [max(1.0, fallback_qty)] * 4

    holdout_points = min(3, max(2, len(weekly_history) // 3))
    train = weekly_history[:-holdout_points] or weekly_history
    holdout = weekly_history[-holdout_points:] or weekly_history[-1:]
    candidate_metrics = []
    for candidate in _forecast_candidates(train, len(holdout)):
        forecasts = candidate["forecast"]
        wape = _wape(holdout, forecasts)
        mae = _mae(holdout, forecasts)
        candidate_metrics.append(
            {
                "model": candidate["model"],
                "label": candidate["label"],
                "wape": round(wape, 4),
                "mae": round(mae, 2),
            }
        )
    best = sorted(candidate_metrics, key=lambda item: (float(item["wape"]), float(item["mae"])))[0]
    future_weeks = max(1, int(round(horizon_days / 7)))
    future_candidate = next(candidate for candidate in _forecast_candidates(weekly_history, future_weeks) if candidate["model"] == best["model"])
    forecast_weekly_qty = mean(future_candidate["forecast"])
    forecast_daily_qty = max(0.0, forecast_weekly_qty / 7.0)
    weekly_std = pstdev(weekly_history) if len(weekly_history) >= 2 else forecast_weekly_qty * 0.15
    planned_daily = sum(float(row.get("demand_qty") or 0) for row in demand_rows) / max(1, horizon_days)
    confidence = max(0.0, min(0.99, 1.0 - float(best["wape"])))
    return {
        "selected_model": best["model"],
        "selected_model_label": best["label"],
        "wape": round(float(best["wape"]), 4),
        "mae": round(float(best["mae"]), 2),
        "holdout_points": len(holdout),
        "forecast_daily_qty": round(forecast_daily_qty, 2),
        "daily_uncertainty_qty": round(max(1.0, weekly_std / 7.0), 2),
        "confidence": round(confidence, 4),
        "candidate_metrics": candidate_metrics,
        "driver_summary": {
            "historical_weekly_avg": round(mean(weekly_history), 2),
            "historical_weekly_std": round(weekly_std, 2),
            "future_planned_daily": round(planned_daily, 2),
            "history_points": len(weekly_history),
        },
    }


def _forecast_candidates(train: list[float], steps: int) -> list[dict[str, Any]]:
    recent = train[-min(4, len(train)) :]
    moving_avg = mean(recent)
    robust_level = median(recent)
    trend_slope = (train[-1] - train[0]) / max(1, len(train) - 1)
    trend = [max(0.0, train[-1] + trend_slope * step) for step in range(1, steps + 1)]
    trend_blend = [max(0.0, moving_avg * 0.65 + value * 0.35) for value in trend]
    return [
        {"model": "MOVING_AVERAGE", "label": "近四周移动平均", "forecast": [max(0.0, moving_avg) for _ in range(steps)]},
        {"model": "TREND_BLEND", "label": "趋势修正组合", "forecast": trend_blend},
        {"model": "ROBUST_MEDIAN", "label": "稳健中位数", "forecast": [max(0.0, robust_level) for _ in range(steps)]},
    ]


def _wape(actual: list[float], forecast: list[float]) -> float:
    return sum(abs(a - f) for a, f in zip(actual, forecast)) / max(1.0, sum(abs(value) for value in actual))


def _mae(actual: list[float], forecast: list[float]) -> float:
    return mean(abs(a - f) for a, f in zip(actual, forecast)) if actual else 0.0


def _planned_daily_demand(rows: list[dict[str, Any]], base_date: date, horizon_days: int) -> float:
    end_date = base_date + timedelta(days=horizon_days)
    total = 0.0
    for row in rows:
        demand_date = datetime.fromisoformat(row["demand_date"]).date()
        if base_date < demand_date <= end_date:
            total += float(row.get("demand_qty") or 0)
    return total / max(1, horizon_days)


def _delay_samples(rows: list[dict[str, Any]]) -> list[int]:
    samples = []
    for row in rows:
        planned = datetime.fromisoformat(row["planned_delivery_date"]).date()
        actual = datetime.fromisoformat(row["actual_gr_date"]).date()
        samples.append(max(0, (actual - planned).days))
    return samples or [0, 2, 4]


def _inbound_qty(po_rows: list[dict[str, Any]], current_day: date, base_date: date, rng: random.Random, delay_samples: list[int]) -> float:
    qty = 0.0
    for row in po_rows:
        planned = datetime.fromisoformat(row["delivery_date"]).date()
        delay = rng.choice(delay_samples)
        arrival = planned + timedelta(days=delay)
        if arrival == current_day and arrival > base_date:
            qty += float(row.get("open_qty") or 0)
    return qty


def _demand_qty(rows: list[dict[str, Any]], current_day: date) -> float:
    return sum(float(row.get("demand_qty") or 0) for row in rows if datetime.fromisoformat(row["demand_date"]).date() == current_day)


def _percentile(values: list[float] | list[int], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(float(value) for value in values)
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * percentile))))
    return ordered[index]


def _nearest_po(rows: list[dict[str, Any]], base_date: date) -> dict[str, Any]:
    future = [row for row in rows if datetime.fromisoformat(row["delivery_date"]).date() >= base_date]
    if not future:
        return {}
    return sorted(future, key=lambda row: row["delivery_date"])[0]
