from __future__ import annotations

import random
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from statistics import mean, pstdev
from typing import Any

from chainpilot_ai.strategy.policy import policy_for_material


def run(snapshot: dict[str, Any], scenario: dict[str, Any] | None = None) -> dict[str, Any]:
    scenario = scenario or {}
    base_date = _snapshot_date(snapshot)
    horizon_days = int(scenario.get("horizon_days") or 14)
    simulations = int(scenario.get("simulations") or 600)
    max_results = int(scenario.get("max_shortage_results") or 120)
    inventory = {(row["material_code"], row["plant"]): row for row in snapshot.get("inventory", [])}
    demands = _group(snapshot.get("planned_demands", []), "material_code", "plant")
    history = _group(snapshot.get("consumption_history", []), "material_code", "plant")
    performance = _group(snapshot.get("supplier_performance", []), "material_code", "plant")
    po_lines = _group(snapshot.get("po_lines", []), "material_code", "plant")
    bom_by_material = _bom_index(snapshot.get("bom_components", []))
    materials = {(row["material_code"], row["plant"]): row for row in snapshot.get("materials", [])}

    results = []
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
        demand_std = _demand_std(history.get(key, []), material_demands)
        delay_samples = _delay_samples(performance.get(key, []))

        for _ in range(simulations):
            stock = float(inv_row.get("unrestricted_qty") or inv_row.get("available_stock") or 0)
            first_shortage_day = None
            worst_shortage = 0.0
            for day_offset in range(1, horizon_days + 1):
                current_day = base_date + timedelta(days=day_offset)
                inbound = _inbound_qty(po_lines.get(key, []), current_day, base_date, rng, delay_samples)
                demand = _demand_qty(material_demands, current_day) + max(0, rng.gauss(0, demand_std * 0.35))
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
