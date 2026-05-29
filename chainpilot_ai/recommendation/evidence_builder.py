from __future__ import annotations

from typing import Any


def build_evidence(result: dict[str, Any], recommendation_id: str, index: int) -> dict[str, Any]:
    raw = result.get("raw") or {}
    result_type = raw.get("result_type") or result.get("result_type")
    evidence_id = f"EVD-{recommendation_id[-22:]}-{index:02d}"
    if result_type == "SHORTAGE_RISK":
        return {
            "evidence_id": evidence_id,
            "recommendation_id": recommendation_id,
            "source_type": "Simulation",
            "source_id": result["result_id"],
            "metric_name": "shortage_probability_14d",
            "metric_value": str(raw.get("shortage_probability_14d")),
            "threshold_value": "0.20",
            "verdict": "WARN",
            "summary": f"14 天缺料概率 {raw.get('shortage_probability_14d')}，P90 缺口 {raw.get('shortage_qty_p90')}。",
        }
    if result_type == "CASH_RELEASE_ACTION":
        return {
            "evidence_id": evidence_id,
            "recommendation_id": recommendation_id,
            "source_type": "Simulation",
            "source_id": result["result_id"],
            "metric_name": "cash_impact",
            "metric_value": str(raw.get("cash_impact")),
            "threshold_value": "0",
            "verdict": "PASS",
            "summary": f"动作满足现金释放约束，预计减少资金占用 {raw.get('cash_impact')}。",
        }
    return {
        "evidence_id": evidence_id,
        "recommendation_id": recommendation_id,
        "source_type": "Simulation",
        "source_id": result["result_id"],
        "metric_name": str(raw.get("metric_name") or "master_data_gap"),
        "metric_value": str(raw.get("metric_value")),
        "threshold_value": "review",
        "verdict": "WARN",
        "summary": f"主数据异常 {raw.get('metric_name')}，样本数 {raw.get('sample_count')}，置信度 {raw.get('confidence_score')}。",
    }
