from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any


def run(snapshot: dict[str, Any], scenario: dict[str, Any] | None = None) -> dict[str, Any]:
    scenario = scenario or {}
    freeze_window_days = int(scenario.get("freeze_window_days") or 7)
    minimum_inventory_days = float(scenario.get("minimum_inventory_days") or 28)
    materials = {(row["material_code"], row["plant"]): row for row in snapshot.get("materials", [])}
    inventory = {(row["material_code"], row["plant"]): row for row in snapshot.get("inventory", [])}
    mrp = {(row["material_code"], row["plant"]): row for row in snapshot.get("mrp_parameters", [])}
    demand_45d = _demand_by_material(snapshot.get("planned_demands", []))
    base_date = _snapshot_date(snapshot)

    candidates: list[dict[str, Any]] = []
    for row in snapshot.get("pr_lines", []):
        candidates.append(_pr_candidate(row, materials, inventory, mrp, demand_45d, base_date, freeze_window_days, minimum_inventory_days))
    for row in snapshot.get("po_lines", []):
        candidates.append(_po_candidate(row, materials, inventory, mrp, demand_45d, base_date, freeze_window_days, minimum_inventory_days))

    selected = _select_actions(candidates)
    for row in selected:
        row["selected"] = True
    for row in candidates:
        row.setdefault("selected", False)

    results = sorted(candidates, key=lambda item: (item["constraint_verdict"] == "BLOCKED", -float(item.get("cash_impact") or 0)))
    return {
        "results": results,
        "summary": {
            "candidate_action_count": len(candidates),
            "selected_actions": sum(1 for item in results if item.get("selected") and item["constraint_verdict"] != "BLOCKED"),
            "blocked_actions": sum(1 for item in results if item["constraint_verdict"] == "BLOCKED"),
            "cash_release_total": round(sum(float(item.get("cash_impact") or 0) for item in results if item.get("selected") and item["constraint_verdict"] != "BLOCKED"), 2),
            "supplier_confirmation_count": sum(1 for item in results if item.get("recommendation_level") == "L3_SUPPLIER_CONFIRM" and item.get("selected")),
            "low_risk_action_count": sum(1 for item in results if item.get("recommendation_level") == "L1_AUTO_RECOMMEND" and item.get("selected")),
        },
    }


def _snapshot_date(snapshot: dict[str, Any]):
    value = snapshot.get("snapshot", {}).get("snapshot_time") or "2026-05-29"
    return datetime.fromisoformat(str(value).replace(" ", "T")).date()


def _demand_by_material(rows: list[dict[str, Any]]) -> dict[tuple[str, str], float]:
    demand: dict[tuple[str, str], float] = defaultdict(float)
    for row in rows:
        demand[(row["material_code"], row["plant"])] += float(row.get("demand_qty") or 0)
    return demand


def _pr_candidate(
    row: dict[str, Any],
    materials: dict[tuple[str, str], dict[str, Any]],
    inventory: dict[tuple[str, str], dict[str, Any]],
    mrp: dict[tuple[str, str], dict[str, Any]],
    demand_45d: dict[tuple[str, str], float],
    base_date,
    freeze_window_days: int,
    minimum_inventory_days: float,
) -> dict[str, Any]:
    key = (row["material_code"], row["plant"])
    material = materials.get(key, {})
    inv = inventory.get(key, {})
    params = mrp.get(key, {})
    open_qty = float(row.get("open_qty") or 0)
    unit_price = float(row.get("unit_price") or material.get("unit_price") or 0)
    delivery_date = datetime.fromisoformat(row["delivery_date"]).date()
    days_to_delivery = (delivery_date - base_date).days
    available = float(inv.get("unrestricted_qty") or 0)
    safety_stock = float(params.get("safety_stock") or inv.get("safety_stock") or 0)
    demand = demand_45d.get(key, 0.0)
    surplus = max(0.0, available + open_qty - demand - safety_stock)
    mpq = max(1.0, float(params.get("mpq") or 1))
    moq = float(params.get("moq") or 0)
    action_type = "CANCEL_PR_LINE" if surplus >= open_qty else "REDUCE_PR_QTY"
    reducible = open_qty if action_type == "CANCEL_PR_LINE" else _round_to_mpq(min(open_qty * 0.45, surplus), mpq)
    after_qty = max(0.0, open_qty - reducible)
    blocked_reason = ""
    if material.get("is_protected"):
        blocked_reason = "保护物料，不允许自动下调采购申请。"
    elif days_to_delivery <= freeze_window_days:
        blocked_reason = "交期落在冻结期内，不能作为现金释放动作。"
    elif reducible <= 0:
        blocked_reason = "扣除需求和安全库存后没有可释放余量。"
    elif after_qty and after_qty < moq:
        blocked_reason = "调整后数量低于 MOQ。"
    verdict = "BLOCKED" if blocked_reason else "PASS"
    risk_after = _risk_after(available, after_qty, demand, safety_stock)
    return {
        "result_type": "CASH_RELEASE_ACTION",
        "action_type": action_type,
        "sap_object_type": "PR",
        "sap_doc_no": row["pr_no"],
        "sap_item_no": row["pr_item"],
        "material_code": row["material_code"],
        "plant": row["plant"],
        "supplier": row.get("supplier"),
        "before_qty": open_qty,
        "after_qty": after_qty,
        "before_date": row["delivery_date"],
        "after_date": row["delivery_date"],
        "cash_impact": round(max(0.0, open_qty - after_qty) * unit_price, 2),
        "risk_before": _risk_after(available, open_qty, demand, safety_stock),
        "risk_after": risk_after,
        "constraint_verdict": verdict,
        "blocked_reason": blocked_reason,
        "recommendation_level": "L1_AUTO_RECOMMEND" if risk_after <= 0.03 else "L2_REVIEW",
        "inventory_days_after": round(((available + after_qty) / max(1.0, demand / 45.0)), 1),
        "minimum_inventory_days": minimum_inventory_days,
        "metric_name": "cash_impact",
        "metric_value": round(max(0.0, open_qty - after_qty) * unit_price, 2),
        "evidence": {
            "available_qty": available,
            "demand_45d": demand,
            "safety_stock": safety_stock,
            "moq": moq,
            "mpq": mpq,
            "surplus_qty": surplus,
        },
    }


def _po_candidate(
    row: dict[str, Any],
    materials: dict[tuple[str, str], dict[str, Any]],
    inventory: dict[tuple[str, str], dict[str, Any]],
    mrp: dict[tuple[str, str], dict[str, Any]],
    demand_45d: dict[tuple[str, str], float],
    base_date,
    freeze_window_days: int,
    minimum_inventory_days: float,
) -> dict[str, Any]:
    key = (row["material_code"], row["plant"])
    material = materials.get(key, {})
    inv = inventory.get(key, {})
    params = mrp.get(key, {})
    open_qty = float(row.get("open_qty") or 0)
    unit_price = float(row.get("unit_price") or material.get("unit_price") or 0)
    delivery_date = datetime.fromisoformat(row["delivery_date"]).date()
    days_to_delivery = (delivery_date - base_date).days
    available = float(inv.get("unrestricted_qty") or 0)
    safety_stock = float(params.get("safety_stock") or inv.get("safety_stock") or 0)
    demand = demand_45d.get(key, 0.0)
    blocked_reason = ""
    if material.get("is_protected"):
        blocked_reason = "保护物料，不允许自动延期采购订单。"
    elif row.get("confirmed_flag"):
        blocked_reason = "供应商已确认订单，需人工供应商确认。"
    elif days_to_delivery <= freeze_window_days:
        blocked_reason = "订单交期在冻结期内，不允许延期。"
    elif available - demand < safety_stock:
        blocked_reason = "延期后安全库存不足。"
    after_date = str(delivery_date.replace(day=min(28, delivery_date.day)) if False else delivery_date)
    delay_days = 14 if not blocked_reason else 0
    risk_after = _risk_after(available, open_qty, demand + (open_qty if delay_days else 0), safety_stock)
    return {
        "result_type": "CASH_RELEASE_ACTION",
        "action_type": "DELAY_UNCONFIRMED_PO",
        "sap_object_type": "PO",
        "sap_doc_no": row["po_no"],
        "sap_item_no": row["po_item"],
        "material_code": row["material_code"],
        "plant": row["plant"],
        "supplier": row.get("supplier"),
        "before_qty": open_qty,
        "after_qty": open_qty,
        "before_date": row["delivery_date"],
        "after_date": str(delivery_date.fromordinal(delivery_date.toordinal() + delay_days)),
        "cash_impact": round(open_qty * unit_price * 0.25, 2) if not blocked_reason else 0.0,
        "risk_before": _risk_after(available, open_qty, demand, safety_stock),
        "risk_after": risk_after,
        "constraint_verdict": "BLOCKED" if blocked_reason else "PASS_WITH_APPROVAL",
        "blocked_reason": blocked_reason,
        "recommendation_level": "L3_SUPPLIER_CONFIRM" if not blocked_reason else "L4_WATCH_ONLY",
        "inventory_days_after": round((available / max(1.0, demand / 45.0)), 1),
        "minimum_inventory_days": minimum_inventory_days,
        "metric_name": "cash_impact",
        "metric_value": round(open_qty * unit_price * 0.25, 2) if not blocked_reason else 0.0,
        "evidence": {
            "available_qty": available,
            "demand_45d": demand,
            "safety_stock": safety_stock,
            "confirmed_flag": bool(row.get("confirmed_flag")),
            "freeze_window_days": freeze_window_days,
        },
    }


def _round_to_mpq(value: float, mpq: float) -> float:
    return max(0.0, int(value // mpq) * mpq)


def _risk_after(available: float, inbound_qty: float, demand: float, safety_stock: float) -> float:
    cover = available + inbound_qty - demand
    if cover >= safety_stock:
        return 0.015
    shortage = safety_stock - cover
    return round(min(0.99, 0.05 + shortage / max(1.0, demand + safety_stock)), 3)


def _select_actions(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    allowed = [row for row in candidates if row["constraint_verdict"] != "BLOCKED" and float(row.get("cash_impact") or 0) > 0]
    for row in allowed:
        risk_penalty = float(row.get("risk_after") or 0) * 1_000_000
        supplier_penalty = 120_000 if row.get("recommendation_level") == "L3_SUPPLIER_CONFIRM" else 0
        row["objective_score"] = round(float(row.get("cash_impact") or 0) - risk_penalty - supplier_penalty, 2)
    return sorted(allowed, key=lambda item: item["objective_score"], reverse=True)[:20]
