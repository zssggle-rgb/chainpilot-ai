from __future__ import annotations

import re


ALLOWED_CONSTRAINT_FIELDS = {
    "user_goal",
    "cash_release_target",
    "protected_product_lines",
    "preferred_actions",
    "minimum_inventory_days",
    "max_shortage_risk_after",
    "freeze_window_days",
    "sap_writeback_mode",
    "source",
}

DEFAULT_CONSTRAINTS = {
    "cash_release_target": None,
    "protected_product_lines": [],
    "preferred_actions": [],
    "minimum_inventory_days": 28,
    "max_shortage_risk_after": 3.5,
    "freeze_window_days": 7,
    "sap_writeback_mode": "draft_only",
    "source": "m3_mock_parser",
}


def build_default_constraint(user_goal: str) -> dict[str, object]:
    return parse_user_goal(user_goal)


def parse_user_goal(user_goal: str) -> dict[str, object]:
    if not user_goal.strip():
        raise ValueError("user_goal is required.")
    goal = user_goal.strip()
    parsed = {
        **DEFAULT_CONSTRAINTS,
        "user_goal": user_goal,
    }
    parsed["cash_release_target"] = _extract_cash_target(goal)
    parsed["protected_product_lines"] = _extract_protected_lines(goal)
    parsed["preferred_actions"] = _extract_preferred_actions(goal)
    return validate_constraint_schema(parsed)


def validate_constraint_schema(constraint: dict[str, object]) -> dict[str, object]:
    unknown = sorted(set(constraint) - ALLOWED_CONSTRAINT_FIELDS)
    if unknown:
        raise ValueError(f"Unsupported constraint fields: {', '.join(unknown)}")
    normalized = {**DEFAULT_CONSTRAINTS, **constraint}
    if not str(normalized.get("user_goal", "")).strip():
        raise ValueError("user_goal is required.")
    if normalized["cash_release_target"] is not None and float(normalized["cash_release_target"]) < 0:
        raise ValueError("cash_release_target cannot be negative.")
    if float(normalized["minimum_inventory_days"]) < 0:
        raise ValueError("minimum_inventory_days cannot be negative.")
    if float(normalized["max_shortage_risk_after"]) < 0:
        raise ValueError("max_shortage_risk_after cannot be negative.")
    if str(normalized["sap_writeback_mode"]) != "draft_only":
        raise ValueError("sap_writeback_mode must remain draft_only before M4.")
    normalized["protected_product_lines"] = list(normalized.get("protected_product_lines") or [])
    normalized["preferred_actions"] = list(normalized.get("preferred_actions") or [])
    return normalized


def _extract_cash_target(goal: str) -> float | None:
    match = re.search(r"释放\s*([0-9]+(?:\.[0-9]+)?)\s*(亿|万|m|million)?", goal, flags=re.IGNORECASE)
    if not match:
        return None
    amount = float(match.group(1))
    unit = (match.group(2) or "").lower()
    if unit == "亿":
        return amount * 100_000_000
    if unit == "万":
        return amount * 10_000
    if unit in {"m", "million"}:
        return amount * 1_000_000
    return amount


def _extract_protected_lines(goal: str) -> list[str]:
    protected = []
    for token in ("空调", "冰箱", "洗衣机", "关键物料"):
        if f"不影响{token}" in goal or f"保护{token}" in goal:
            protected.append(token)
    return protected


def _extract_preferred_actions(goal: str) -> list[str]:
    actions = []
    if "PR" in goal.upper() or "采购申请" in goal:
        actions.append("REDUCE_PR_QTY")
    if "PO" in goal.upper() or "采购订单" in goal:
        actions.append("DELAY_UNCONFIRMED_PO")
    if "安全库存" in goal:
        actions.append("REVIEW_SAFETY_STOCK")
    return actions
