from __future__ import annotations

import copy
from typing import Any


SEGMENT_ORDER = ["AX", "AY", "AZ", "BX", "BY", "BZ", "CX", "CY", "CZ"]

BASE_SEGMENT_POLICY: dict[str, dict[str, float]] = {
    "AX": {"service_level": 0.99, "shortage_alert_threshold": 0.12},
    "AY": {"service_level": 0.98, "shortage_alert_threshold": 0.15},
    "AZ": {"service_level": 0.97, "shortage_alert_threshold": 0.18},
    "BX": {"service_level": 0.96, "shortage_alert_threshold": 0.20},
    "BY": {"service_level": 0.95, "shortage_alert_threshold": 0.23},
    "BZ": {"service_level": 0.93, "shortage_alert_threshold": 0.28},
    "CX": {"service_level": 0.92, "shortage_alert_threshold": 0.30},
    "CY": {"service_level": 0.90, "shortage_alert_threshold": 0.36},
    "CZ": {"service_level": 0.88, "shortage_alert_threshold": 0.42},
}


def strategy_presets() -> list[dict[str, Any]]:
    conservative = _preset(
        "STRAT-CONSERVATIVE-MOCK",
        "保守策略",
        "Conservative",
        threshold_delta=-0.04,
        service_delta=0.01,
        freeze_window_days=10,
        minimum_inventory_days=35,
        approval_cash_threshold=2_000_000,
        max_selected_actions=12,
        risk_penalty=1_600_000,
        supplier_confirmation_penalty=200_000,
        description="优先降低缺料漏报和供应扰动，资金改善更谨慎。",
    )
    balanced = _preset(
        "STRAT-BALANCED-MOCK",
        "均衡策略",
        "Recommended",
        threshold_delta=0,
        service_delta=0,
        freeze_window_days=7,
        minimum_inventory_days=28,
        approval_cash_threshold=5_000_000,
        max_selected_actions=20,
        risk_penalty=1_000_000,
        supplier_confirmation_penalty=120_000,
        description="在缺料风险和资金改善之间保持均衡，适合作为默认试点策略。",
    )
    aggressive = _preset(
        "STRAT-AGGRESSIVE-MOCK",
        "进取策略",
        "Aggressive",
        threshold_delta=0.05,
        service_delta=-0.015,
        freeze_window_days=5,
        minimum_inventory_days=21,
        approval_cash_threshold=8_000_000,
        max_selected_actions=28,
        risk_penalty=650_000,
        supplier_confirmation_penalty=80_000,
        description="提高资金改善目标，允许更高人工复核压力。",
    )
    return [conservative, balanced, aggressive]


def strategy_by_id(strategy_id: str | None) -> dict[str, Any]:
    presets = strategy_presets()
    if not strategy_id:
        return presets[1]
    for strategy in presets:
        if strategy["strategy_id"] == strategy_id:
            return strategy
    raise ValueError(f"Unknown strategy_id: {strategy_id}")


def scenario_from_strategy(strategy: dict[str, Any]) -> dict[str, Any]:
    params = strategy["parameter_json"]
    return {
        "scenario_id": f"SCN-{strategy['strategy_id']}",
        "strategy_id": strategy["strategy_id"],
        "strategy_name": strategy["strategy_name"],
        "strategy_type": strategy["strategy_type"],
        "horizon_days": params["horizon_days"],
        "simulations": params["simulations"],
        "freeze_window_days": params["freeze_window_days"],
        "minimum_inventory_days": params["minimum_inventory_days"],
        "approval_cash_threshold": params["approval_cash_threshold"],
        "max_selected_actions": params["max_selected_actions"],
        "risk_penalty": params["risk_penalty"],
        "supplier_confirmation_penalty": params["supplier_confirmation_penalty"],
        "shortage_thresholds": params["segment_policy"],
        "default_shortage_alert_threshold": 0.24,
        "sap_writeback_mode": "draft_only",
    }


def segment_code(material: dict[str, Any]) -> str:
    abc = str(material.get("abc_class") or "B").upper()[:1]
    xyz = str(material.get("xyz_class") or "Y").upper()[:1]
    code = f"{abc}{xyz}"
    return code if code in BASE_SEGMENT_POLICY else "BY"


def policy_for_material(material: dict[str, Any], scenario: dict[str, Any] | None = None) -> dict[str, float]:
    scenario = scenario or {}
    code = segment_code(material)
    configured = scenario.get("shortage_thresholds") or {}
    if code in configured:
        return configured[code]
    return BASE_SEGMENT_POLICY[code]


def _preset(
    strategy_id: str,
    name: str,
    strategy_type: str,
    threshold_delta: float,
    service_delta: float,
    freeze_window_days: int,
    minimum_inventory_days: int,
    approval_cash_threshold: int,
    max_selected_actions: int,
    risk_penalty: int,
    supplier_confirmation_penalty: int,
    description: str,
) -> dict[str, Any]:
    segment_policy = copy.deepcopy(BASE_SEGMENT_POLICY)
    for policy in segment_policy.values():
        policy["shortage_alert_threshold"] = round(min(0.65, max(0.05, policy["shortage_alert_threshold"] + threshold_delta)), 3)
        policy["service_level"] = round(min(0.995, max(0.82, policy["service_level"] + service_delta)), 3)
    return {
        "strategy_id": strategy_id,
        "strategy_name": name,
        "strategy_type": strategy_type,
        "status": "Draft" if strategy_type != "Recommended" else "Recommended",
        "version": "mock-v1",
        "description": description,
        "parameter_json": {
            "segment_policy": segment_policy,
            "horizon_days": 14,
            "simulations": 180,
            "freeze_window_days": freeze_window_days,
            "minimum_inventory_days": minimum_inventory_days,
            "approval_cash_threshold": approval_cash_threshold,
            "max_selected_actions": max_selected_actions,
            "risk_penalty": risk_penalty,
            "supplier_confirmation_penalty": supplier_confirmation_penalty,
            "mock_history_days": 120,
            "sample_interval_days": 14,
        },
    }
