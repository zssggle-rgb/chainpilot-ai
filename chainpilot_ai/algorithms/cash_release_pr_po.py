from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from itertools import product
from math import inf
from typing import Any

try:  # pragma: no cover - optional in the bench runtime.
    from scipy.optimize import Bounds, LinearConstraint, milp
except Exception:  # pragma: no cover
    Bounds = LinearConstraint = milp = None


def run(snapshot: dict[str, Any], scenario: dict[str, Any] | None = None) -> dict[str, Any]:
    scenario = scenario or {}
    base_date = _snapshot_date(snapshot)
    freeze_window_days = int(scenario.get("freeze_window_days") or 7)
    minimum_inventory_days = float(scenario.get("minimum_inventory_days") or 28)
    optimization_horizon_days = int(scenario.get("optimization_horizon_days") or 45)
    approval_cash_threshold = float(scenario.get("approval_cash_threshold") or 5_000_000)

    materials = {(row["material_code"], row["plant"]): row for row in snapshot.get("materials", [])}
    inventory = {(row["material_code"], row["plant"]): row for row in snapshot.get("inventory", [])}
    mrp = {(row["material_code"], row["plant"]): row for row in snapshot.get("mrp_parameters", [])}
    demand = _demand_by_material(snapshot.get("planned_demands", []), base_date, optimization_horizon_days)
    baseline_inbound = _baseline_inbound(snapshot.get("pr_lines", []), snapshot.get("po_lines", []), base_date, optimization_horizon_days)
    headroom = _material_headroom(inventory, mrp, demand, baseline_inbound, minimum_inventory_days, optimization_horizon_days)

    candidates: list[dict[str, Any]] = []
    for row in snapshot.get("pr_lines", []):
        candidates.append(
            _pr_candidate(
                row,
                materials,
                inventory,
                mrp,
                demand,
                headroom,
                base_date,
                freeze_window_days,
                minimum_inventory_days,
                approval_cash_threshold,
                optimization_horizon_days,
            )
        )
    for row in snapshot.get("po_lines", []):
        candidates.append(
            _po_candidate(
                row,
                materials,
                inventory,
                mrp,
                demand,
                headroom,
                base_date,
                freeze_window_days,
                minimum_inventory_days,
                optimization_horizon_days,
            )
        )

    selected, solver_summary = _select_actions(candidates, scenario)
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
            **solver_summary,
        },
    }


def _snapshot_date(snapshot: dict[str, Any]):
    value = snapshot.get("snapshot", {}).get("snapshot_time") or "2026-05-29"
    return datetime.fromisoformat(str(value).replace(" ", "T")).date()


def _demand_by_material(rows: list[dict[str, Any]], base_date, horizon_days: int) -> dict[tuple[str, str], float]:
    demand: dict[tuple[str, str], float] = defaultdict(float)
    for row in rows:
        demand_date = datetime.fromisoformat(row["demand_date"]).date()
        if 0 <= (demand_date - base_date).days <= horizon_days:
            demand[(row["material_code"], row["plant"])] += float(row.get("demand_qty") or 0)
    return demand


def _baseline_inbound(pr_rows: list[dict[str, Any]], po_rows: list[dict[str, Any]], base_date, horizon_days: int) -> dict[tuple[str, str], float]:
    inbound: dict[tuple[str, str], float] = defaultdict(float)
    for row in pr_rows:
        delivery_date = datetime.fromisoformat(row["delivery_date"]).date()
        if 0 <= (delivery_date - base_date).days <= horizon_days:
            inbound[(row["material_code"], row["plant"])] += float(row.get("open_qty") or 0) * 0.65
    for row in po_rows:
        delivery_date = datetime.fromisoformat(row["delivery_date"]).date()
        if 0 <= (delivery_date - base_date).days <= horizon_days:
            inbound[(row["material_code"], row["plant"])] += float(row.get("open_qty") or 0)
    return inbound


def _material_headroom(
    inventory: dict[tuple[str, str], dict[str, Any]],
    mrp: dict[tuple[str, str], dict[str, Any]],
    demand: dict[tuple[str, str], float],
    inbound: dict[tuple[str, str], float],
    minimum_inventory_days: float,
    horizon_days: int,
) -> dict[tuple[str, str], float]:
    headroom: dict[tuple[str, str], float] = {}
    for key, inv in inventory.items():
        params = mrp.get(key, {})
        demand_qty = demand.get(key, 0.0)
        daily_demand = demand_qty / max(1.0, float(horizon_days))
        service_stock = max(float(params.get("safety_stock") or inv.get("safety_stock") or 0), daily_demand * minimum_inventory_days)
        available = float(inv.get("unrestricted_qty") or inv.get("available_stock") or 0)
        projected = available + inbound.get(key, 0.0) - demand_qty
        headroom[key] = max(0.0, projected - service_stock)
    return headroom


def _pr_candidate(
    row: dict[str, Any],
    materials: dict[tuple[str, str], dict[str, Any]],
    inventory: dict[tuple[str, str], dict[str, Any]],
    mrp: dict[tuple[str, str], dict[str, Any]],
    demand: dict[tuple[str, str], float],
    headroom: dict[tuple[str, str], float],
    base_date,
    freeze_window_days: int,
    minimum_inventory_days: float,
    approval_cash_threshold: float,
    optimization_horizon_days: int,
) -> dict[str, Any]:
    key = (row["material_code"], row["plant"])
    material = materials.get(key, {})
    inv = inventory.get(key, {})
    params = mrp.get(key, {})
    open_qty = float(row.get("open_qty") or 0)
    unit_price = float(row.get("unit_price") or material.get("unit_price") or 0)
    delivery_date = datetime.fromisoformat(row["delivery_date"]).date()
    days_to_delivery = (delivery_date - base_date).days
    available = float(inv.get("unrestricted_qty") or inv.get("available_stock") or 0)
    safety_stock = float(params.get("safety_stock") or inv.get("safety_stock") or 0)
    demand_qty = demand.get(key, 0.0)
    material_headroom = max(0.0, headroom.get(key, 0.0))
    mpq = max(1.0, float(params.get("mpq") or 1))
    moq = float(params.get("moq") or 0)
    action_type = "CANCEL_PR_LINE" if material_headroom >= open_qty else "REDUCE_PR_QTY"
    reducible = open_qty if action_type == "CANCEL_PR_LINE" else _round_to_mpq(min(open_qty * 0.45, material_headroom), mpq)
    after_qty = max(0.0, open_qty - reducible)
    blocked_reason = ""
    if material.get("is_protected"):
        blocked_reason = "保护物料，不允许自动下调采购申请。"
    elif days_to_delivery <= freeze_window_days:
        blocked_reason = "交期落在冻结期内，不能作为资金优化动作。"
    elif material.get("critical_flag") and material_headroom < reducible:
        blocked_reason = "关键物料服务水平余量不足。"
    elif reducible <= 0:
        blocked_reason = "扣除需求、安全库存和服务水平后没有可优化余量。"
    elif after_qty and after_qty < moq:
        blocked_reason = "调整后数量低于最小采购量。"
    elif reducible % mpq:
        blocked_reason = "调整数量不满足最小包装量。"
    verdict = "BLOCKED" if blocked_reason else "PASS"
    risk_before = _risk_from_headroom(material_headroom, 0.0, demand_qty, safety_stock)
    risk_after = _risk_from_headroom(material_headroom, reducible, demand_qty, safety_stock)
    cash_impact = round(max(0.0, open_qty - after_qty) * unit_price, 2)
    recommendation_level = "L1_AUTO_RECOMMEND" if risk_after <= 0.03 and cash_impact < approval_cash_threshold else "L2_REVIEW"
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
        "cash_impact": cash_impact,
        "risk_before": risk_before,
        "risk_after": risk_after,
        "constraint_verdict": verdict,
        "blocked_reason": blocked_reason,
        "recommendation_level": recommendation_level,
        "inventory_days_after": round(((available + after_qty) / max(1.0, demand_qty / 45.0)), 1),
        "minimum_inventory_days": minimum_inventory_days,
        "capacity_consumed": reducible if days_to_delivery <= optimization_horizon_days else 0.0,
        "material_headroom": round(material_headroom, 2),
        "metric_name": "cash_impact",
        "metric_value": cash_impact,
        "evidence": {
            "available_qty": available,
            "demand_horizon": demand_qty,
            "safety_stock": safety_stock,
            "moq": moq,
            "mpq": mpq,
            "headroom_qty": round(material_headroom, 2),
            "freeze_window_days": freeze_window_days,
        },
    }


def _po_candidate(
    row: dict[str, Any],
    materials: dict[tuple[str, str], dict[str, Any]],
    inventory: dict[tuple[str, str], dict[str, Any]],
    mrp: dict[tuple[str, str], dict[str, Any]],
    demand: dict[tuple[str, str], float],
    headroom: dict[tuple[str, str], float],
    base_date,
    freeze_window_days: int,
    minimum_inventory_days: float,
    optimization_horizon_days: int,
) -> dict[str, Any]:
    key = (row["material_code"], row["plant"])
    material = materials.get(key, {})
    inv = inventory.get(key, {})
    params = mrp.get(key, {})
    open_qty = float(row.get("open_qty") or 0)
    unit_price = float(row.get("unit_price") or material.get("unit_price") or 0)
    delivery_date = datetime.fromisoformat(row["delivery_date"]).date()
    days_to_delivery = (delivery_date - base_date).days
    available = float(inv.get("unrestricted_qty") or inv.get("available_stock") or 0)
    safety_stock = float(params.get("safety_stock") or inv.get("safety_stock") or 0)
    demand_qty = demand.get(key, 0.0)
    material_headroom = max(0.0, headroom.get(key, 0.0))
    blocked_reason = ""
    if material.get("is_protected"):
        blocked_reason = "保护物料，不允许自动延期采购订单。"
    elif days_to_delivery <= freeze_window_days:
        blocked_reason = "订单交期在冻结期内，不允许延期。"
    elif material_headroom <= 0:
        blocked_reason = "延期后服务水平余量不足。"
    delay_days = 14 if not blocked_reason else 0
    capacity_consumed = open_qty if days_to_delivery <= optimization_horizon_days else 0.0
    risk_before = _risk_from_headroom(material_headroom, 0.0, demand_qty, safety_stock)
    risk_after = _risk_from_headroom(material_headroom, capacity_consumed if delay_days else 0.0, demand_qty, safety_stock)
    recommendation_level = "L3_SUPPLIER_CONFIRM" if row.get("confirmed_flag") and not blocked_reason else "L2_REVIEW" if not blocked_reason else "L4_WATCH_ONLY"
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
        "risk_before": risk_before,
        "risk_after": risk_after,
        "constraint_verdict": "BLOCKED" if blocked_reason else "PASS_WITH_APPROVAL",
        "blocked_reason": blocked_reason,
        "recommendation_level": recommendation_level,
        "inventory_days_after": round((available / max(1.0, demand_qty / 45.0)), 1),
        "minimum_inventory_days": minimum_inventory_days,
        "capacity_consumed": capacity_consumed,
        "material_headroom": round(material_headroom, 2),
        "metric_name": "cash_impact",
        "metric_value": round(open_qty * unit_price * 0.25, 2) if not blocked_reason else 0.0,
        "evidence": {
            "available_qty": available,
            "demand_horizon": demand_qty,
            "safety_stock": safety_stock,
            "confirmed_flag": bool(row.get("confirmed_flag")),
            "headroom_qty": round(material_headroom, 2),
            "freeze_window_days": freeze_window_days,
        },
    }


def _round_to_mpq(value: float, mpq: float) -> float:
    return max(0.0, int(value // mpq) * mpq)


def _risk_from_headroom(headroom: float, consumed: float, demand: float, safety_stock: float) -> float:
    residual = headroom - consumed
    if residual >= 0:
        return 0.015
    return round(min(0.99, 0.05 + abs(residual) / max(1.0, demand + safety_stock)), 3)


def _select_actions(candidates: list[dict[str, Any]], scenario: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    allowed = [row for row in candidates if row["constraint_verdict"] != "BLOCKED" and float(row.get("cash_impact") or 0) > 0]
    risk_penalty = float(scenario.get("risk_penalty") or 1_000_000)
    supplier_penalty_value = float(scenario.get("supplier_confirmation_penalty") or 120_000)
    max_selected = int(scenario.get("max_selected_actions") or 20)
    max_review_actions = int(scenario.get("max_review_actions") or max(8, max_selected))
    max_supplier_confirmations = int(scenario.get("max_supplier_confirmations") or 6)
    approval_cash_capacity = float(scenario.get("approval_cash_capacity") or 250_000_000)
    for row in allowed:
        risk_cost = float(row.get("risk_after") or 0) * risk_penalty
        supplier_penalty = supplier_penalty_value if row.get("recommendation_level") == "L3_SUPPLIER_CONFIRM" else 0
        row["objective_score"] = round(float(row.get("cash_impact") or 0) - risk_cost - supplier_penalty, 2)
    if not allowed:
        return [], {"solver_name": "无候选", "solver_status": "INFEASIBLE", "objective_value": 0, "constraint_count": 0}

    constraints = _solver_constraints(allowed, max_selected, max_review_actions, max_supplier_confirmations, approval_cash_capacity)
    selected_indexes, solver_name, solver_status, objective_value = _solve_binary_program(allowed, constraints)
    for index, row in enumerate(allowed):
        row["solver_selected"] = index in selected_indexes
    return [allowed[index] for index in selected_indexes], {
        "solver_name": solver_name,
        "solver_status": solver_status,
        "objective_value": round(objective_value, 2),
        "constraint_count": len(constraints),
        "candidate_action_count_after_constraints": len(allowed),
        "max_selected_actions": max_selected,
        "max_review_actions": max_review_actions,
        "max_supplier_confirmations": max_supplier_confirmations,
        "approval_cash_capacity": approval_cash_capacity,
    }


def _solver_constraints(
    allowed: list[dict[str, Any]],
    max_selected: int,
    max_review_actions: int,
    max_supplier_confirmations: int,
    approval_cash_capacity: float,
) -> list[dict[str, Any]]:
    constraints: list[dict[str, Any]] = [
        {"name": "最多选择动作数", "coefficients": [1.0 for _ in allowed], "upper_bound": float(max_selected)},
        {
            "name": "最多人工复核动作数",
            "coefficients": [1.0 if row.get("recommendation_level") in {"L2_REVIEW", "L3_SUPPLIER_CONFIRM"} else 0.0 for row in allowed],
            "upper_bound": float(max_review_actions),
        },
        {
            "name": "最多供应商确认动作数",
            "coefficients": [1.0 if row.get("recommendation_level") == "L3_SUPPLIER_CONFIRM" else 0.0 for row in allowed],
            "upper_bound": float(max_supplier_confirmations),
        },
        {
            "name": "审批金额容量",
            "coefficients": [float(row.get("cash_impact") or 0) for row in allowed],
            "upper_bound": approval_cash_capacity,
        },
    ]
    material_groups: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0.0 for _ in allowed])
    material_headroom: dict[tuple[str, str], float] = {}
    for index, row in enumerate(allowed):
        key = (str(row.get("material_code")), str(row.get("plant")))
        material_groups[key][index] = float(row.get("capacity_consumed") or 0)
        material_headroom[key] = max(material_headroom.get(key, 0.0), float(row.get("material_headroom") or 0))
    for key, coefficients in material_groups.items():
        constraints.append({"name": f"{key[0]} 服务水平余量", "coefficients": coefficients, "upper_bound": material_headroom.get(key, 0.0)})
    return constraints


def _solve_binary_program(allowed: list[dict[str, Any]], constraints: list[dict[str, Any]]) -> tuple[set[int], str, str, float]:
    scores = [max(0.0, float(row.get("objective_score") or 0)) for row in allowed]
    if milp and Bounds and LinearConstraint:
        try:
            c = [-score for score in scores]
            a_matrix = [constraint["coefficients"] for constraint in constraints]
            upper_bounds = [constraint["upper_bound"] for constraint in constraints]
            linear = LinearConstraint(a_matrix, [-inf for _ in constraints], upper_bounds)
            result = milp(c=c, integrality=[1 for _ in allowed], bounds=Bounds(0, 1), constraints=linear, options={"time_limit": 5})
            if result.success and result.x is not None:
                indexes = {index for index, value in enumerate(result.x) if value >= 0.5 and scores[index] > 0}
                status = "OPTIMAL" if getattr(result, "mip_gap", 0) in (None, 0) else "FEASIBLE"
                return indexes, "HiGHS MILP", status, sum(scores[index] for index in indexes)
        except Exception:
            pass
    return _exact_binary_fallback(scores, constraints)


def _exact_binary_fallback(scores: list[float], constraints: list[dict[str, Any]]) -> tuple[set[int], str, str, float]:
    best_indexes: set[int] = set()
    best_value = 0.0
    candidate_count = len(scores)
    order = sorted(range(candidate_count), key=lambda index: scores[index], reverse=True)[:28] if candidate_count > 28 else list(range(candidate_count))
    for bits in product((0, 1), repeat=len(order)):
        value = sum(scores[index] for index, enabled in zip(order, bits) if enabled)
        if value <= best_value:
            continue
        if _constraints_pass(order, bits, constraints):
            best_value = value
            best_indexes = {index for index, enabled in zip(order, bits) if enabled}
    return best_indexes, "精确整数枚举", "OPTIMAL" if candidate_count <= 28 else "TRUNCATED_OPTIMAL", best_value


def _constraints_pass(order: list[int], bits: tuple[int, ...], constraints: list[dict[str, Any]]) -> bool:
    for constraint in constraints:
        coefficients = constraint["coefficients"]
        used = sum(coefficients[index] for index, enabled in zip(order, bits) if enabled)
        if used > float(constraint["upper_bound"]) + 1e-9:
            return False
    return True
