from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime
from statistics import mean, pstdev
from typing import Any


def run(snapshot: dict[str, Any], scenario: dict[str, Any] | None = None) -> dict[str, Any]:
    materials = {(row["material_code"], row["plant"]): row for row in snapshot.get("materials", [])}
    mrp_rows = snapshot.get("mrp_parameters", [])
    performance = _group(snapshot.get("supplier_performance", []), "material_code", "plant")
    history = _group(snapshot.get("consumption_history", []), "material_code", "plant")
    results = []

    for params in mrp_rows:
        key = (params["material_code"], params["plant"])
        material = materials.get(key, {})
        lead_times = _lead_times(performance.get(key, []))
        demand_values = [float(row.get("actual_consumption_qty") or 0) for row in history.get(key, [])]
        planned_delivery_time = float(params.get("planned_delivery_time") or 0)
        current_safety_stock = float(params.get("safety_stock") or 0)
        current_moq = float(params.get("moq") or 0)
        current_mpq = float(params.get("mpq") or 0)

        if lead_times:
            p80 = _percentile(lead_times, 0.8)
            if p80 > planned_delivery_time * 1.3 or p80 - planned_delivery_time > 5:
                results.append(
                    _issue(
                        "REVIEW_SUPPLIER_LEAD_TIME",
                        "lead_time_p80_gap",
                        p80 - planned_delivery_time,
                        params,
                        material,
                        planned_delivery_time,
                        p80,
                        len(lead_times),
                        min(0.95, 0.55 + len(lead_times) * 0.08),
                        abs(p80 - planned_delivery_time) * float(material.get("unit_price") or 0) * 120,
                        {"lead_time_p50": _percentile(lead_times, 0.5), "lead_time_p80": p80, "lead_time_p95": _percentile(lead_times, 0.95)},
                    )
                )

        if demand_values:
            suggested_safety_stock = _suggest_safety_stock(demand_values, lead_times or [planned_delivery_time])
            if current_safety_stock and abs(suggested_safety_stock - current_safety_stock) / current_safety_stock >= 0.3:
                results.append(
                    _issue(
                        "REVIEW_SAFETY_STOCK",
                        "safety_stock_gap",
                        suggested_safety_stock - current_safety_stock,
                        params,
                        material,
                        current_safety_stock,
                        suggested_safety_stock,
                        len(demand_values),
                        min(0.92, 0.5 + len(demand_values) * 0.1),
                        abs(suggested_safety_stock - current_safety_stock) * float(material.get("unit_price") or 0),
                        {"avg_demand": mean(demand_values), "demand_std": pstdev(demand_values) if len(demand_values) >= 2 else 0},
                    )
                )
            avg_demand = mean(demand_values)
            if current_moq > avg_demand * 2 or current_mpq > avg_demand:
                results.append(
                    _issue(
                        "REVIEW_MOQ",
                        "moq_mpq_gap",
                        max(current_moq - avg_demand * 1.2, current_mpq - avg_demand),
                        params,
                        material,
                        current_moq,
                        max(avg_demand * 1.2, current_mpq),
                        len(demand_values),
                        min(0.88, 0.5 + len(demand_values) * 0.08),
                        max(0, current_moq - avg_demand * 1.2) * float(material.get("unit_price") or 0),
                        {"avg_consumption": avg_demand, "current_moq": current_moq, "current_mpq": current_mpq},
                    )
                )

    results.sort(key=lambda item: float(item.get("impact_amount") or 0), reverse=True)
    return {
        "results": results,
        "summary": {
            "result_count": len(results),
            "lead_time_issue_count": sum(1 for item in results if item["action_type"] == "REVIEW_SUPPLIER_LEAD_TIME"),
            "safety_stock_issue_count": sum(1 for item in results if item["action_type"] == "REVIEW_SAFETY_STOCK"),
            "moq_issue_count": sum(1 for item in results if item["action_type"] == "REVIEW_MOQ"),
        },
    }


def _group(rows: list[dict[str, Any]], *keys: str) -> dict[tuple[str, ...], list[dict[str, Any]]]:
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(str(row.get(key)) for key in keys)].append(row)
    return grouped


def _lead_times(rows: list[dict[str, Any]]) -> list[int]:
    values = []
    for row in rows:
        start = datetime.fromisoformat(row["po_create_date"]).date()
        end = datetime.fromisoformat(row["actual_gr_date"]).date()
        values.append(max(1, (end - start).days))
    return values


def _percentile(values: list[float] | list[int], percentile: float) -> float:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return 0.0
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * percentile))))
    return round(ordered[index], 2)


def _suggest_safety_stock(demand_values: list[float], lead_times: list[float]) -> float:
    avg_demand = mean(demand_values)
    demand_std = pstdev(demand_values) if len(demand_values) >= 2 else max(1.0, avg_demand * 0.2)
    lead_avg = mean(lead_times)
    lead_std = pstdev(lead_times) if len(lead_times) >= 2 else max(1.0, lead_avg * 0.2)
    service_z = 1.65
    return round(service_z * math.sqrt(lead_avg * demand_std**2 + avg_demand**2 * lead_std**2), 2)


def _issue(
    action_type: str,
    metric_name: str,
    metric_value: float,
    params: dict[str, Any],
    material: dict[str, Any],
    before_value: float,
    after_value: float,
    sample_count: int,
    confidence_score: float,
    impact_amount: float,
    evidence: dict[str, Any],
) -> dict[str, Any]:
    return {
        "result_type": "MASTER_DATA_ISSUE",
        "action_type": action_type,
        "sap_object_type": "MRP_PARAM",
        "sap_doc_no": params["material_code"],
        "sap_item_no": params["plant"],
        "material_code": params["material_code"],
        "plant": params["plant"],
        "supplier": "",
        "before_value": round(before_value, 2),
        "after_value": round(after_value, 2),
        "metric_name": metric_name,
        "metric_value": round(metric_value, 2),
        "sample_count": sample_count,
        "confidence_score": round(confidence_score, 2),
        "impact_amount": round(impact_amount, 2),
        "recommendation_level": "L2_REVIEW",
        "constraint_verdict": "PASS_WITH_APPROVAL",
        "evidence": {
            **evidence,
            "abc_class": material.get("abc_class"),
            "xyz_class": material.get("xyz_class"),
            "unit_price": material.get("unit_price"),
        },
    }
