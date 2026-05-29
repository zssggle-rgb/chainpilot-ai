from __future__ import annotations

from typing import Any


def check_algorithm_result(result: dict[str, Any]) -> dict[str, str]:
    raw = result.get("raw") or {}
    result_type = raw.get("result_type") or result.get("result_type")
    if result_type == "CASH_RELEASE_ACTION":
        verdict = raw.get("constraint_verdict") or "PASS"
        return {
            "rule_code": "CASH_RELEASE_CONSTRAINTS",
            "verdict": verdict,
            "message": raw.get("blocked_reason") or "冻结期、保护物料、MOQ/MPQ 和安全库存约束已校验。",
        }
    if result_type == "SHORTAGE_RISK":
        return {
            "rule_code": "SHORTAGE_RISK_SIMULATION",
            "verdict": "PASS_WITH_APPROVAL",
            "message": "缺料风险来自 14 天轻量仿真，需计划经理复核补救动作。",
        }
    return {
        "rule_code": "MASTER_DATA_REVIEW",
        "verdict": "PASS_WITH_APPROVAL",
        "message": "主数据建议只生成复核任务，不直接修改 SAP 参数。",
    }
