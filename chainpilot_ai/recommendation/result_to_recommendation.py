from __future__ import annotations

from typing import Any

from chainpilot_ai.agent.explanation_service import generate_algorithm_explanation
from chainpilot_ai.recommendation.constraint_checker import check_algorithm_result
from chainpilot_ai.recommendation.evidence_builder import build_evidence


def convert_algorithm_results(
    algorithm_runtime: dict[str, Any],
    scenario_id: str | None = None,
) -> dict[str, list[dict[str, Any]]]:
    recommendations: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    explanations: list[dict[str, Any]] = []
    snapshot_id = algorithm_runtime.get("snapshot_id")

    for index, result in enumerate(algorithm_runtime.get("results", []), start=1):
        raw = result.get("raw") or {}
        if raw.get("result_type") == "CASH_RELEASE_ACTION" and raw.get("constraint_verdict") == "BLOCKED":
            continue
        recommendation_id = f"REC-{result['result_id'][-22:]}"
        rec = _recommendation_from_result(result, recommendation_id, snapshot_id, scenario_id)
        evidence = build_evidence(result, recommendation_id, 1)
        check = {"check_id": f"CHK-{recommendation_id[-22:]}", "recommendation_id": recommendation_id, "evidence_id": evidence["evidence_id"], **check_algorithm_result(result)}
        explanation = {
            "explanation_id": f"EXP-{recommendation_id[-22:]}",
            "recommendation": recommendation_id,
            "algorithm_run": rec["algorithm_run"],
            "prompt_version": "algorithm-runtime-v1",
            "model_name": "Evidence Template",
            **generate_algorithm_explanation(rec, result, [evidence], check),
        }
        rec["evidence_count"] = 1
        rec["constraint_verdict"] = check["verdict"]
        rec["explanation_status"] = explanation["status"]
        recommendations.append(rec)
        evidence_rows.append(evidence)
        checks.append(check)
        explanations.append(explanation)

    return {
        "recommendations": recommendations,
        "evidence": evidence_rows,
        "checks": checks,
        "explanations": explanations,
    }


def _recommendation_from_result(result: dict[str, Any], recommendation_id: str, snapshot_id: str | None, scenario_id: str | None) -> dict[str, Any]:
    raw = result.get("raw") or {}
    result_type = raw.get("result_type")
    common = {
        "recommendation_id": recommendation_id,
        "result_id": "",
        "snapshot_id": snapshot_id,
        "algorithm_run": result["algorithm_run"],
        "algorithm_result": result["result_id"],
        "scenario_id": scenario_id,
        "sap_object_type": raw.get("sap_object_type") or result.get("sap_object_type") or "MRP_PARAM",
        "sap_doc_no": raw.get("sap_doc_no") or result.get("sap_doc_no") or raw.get("material_code"),
        "sap_item_no": raw.get("sap_item_no") or result.get("sap_item_no") or raw.get("plant"),
        "material_code": raw.get("material_code"),
        "material_name": "",
        "plant": raw.get("plant"),
        "supplier": raw.get("supplier") or "",
        "purchasing_group": "",
        "product_line": "",
        "confidence_score": raw.get("confidence_score") or 0.78,
        "approval_status": "Pending",
        "writeback_status": "Not Created",
        "blocked_reason": raw.get("blocked_reason") or "",
        "execution_owner": "",
        "actual_realized_amount": 0,
    }
    if result_type == "SHORTAGE_RISK":
        return {
            **common,
            "action_type": raw.get("suggested_action") or "EXPEDITE_PO",
            "before_qty": 0,
            "after_qty": raw.get("shortage_qty_p90") or 0,
            "before_date": "",
            "after_date": raw.get("shortage_date_p50"),
            "cash_release": 0,
            "saving_type": "Purchase Deferral",
            "inventory_days_before": 0,
            "inventory_days_after": 0,
            "shortage_risk_before": 0,
            "shortage_risk_after": round(float(raw.get("shortage_probability_14d") or 0) * 100, 2),
            "recommendation_level": "L3_SUPPLIER_CONFIRM",
        }
    if result_type == "CASH_RELEASE_ACTION":
        return {
            **common,
            "action_type": raw.get("action_type"),
            "before_qty": raw.get("before_qty"),
            "after_qty": raw.get("after_qty"),
            "before_date": raw.get("before_date"),
            "after_date": raw.get("after_date"),
            "cash_release": raw.get("cash_impact") or 0,
            "saving_type": "Cash Release" if raw.get("action_type") == "REDUCE_PR_QTY" else "Purchase Deferral",
            "inventory_days_before": 0,
            "inventory_days_after": raw.get("inventory_days_after") or 0,
            "shortage_risk_before": round(float(raw.get("risk_before") or 0) * 100, 2),
            "shortage_risk_after": round(float(raw.get("risk_after") or 0) * 100, 2),
            "recommendation_level": raw.get("recommendation_level") or "L2_REVIEW",
        }
    return {
        **common,
        "action_type": raw.get("action_type") or "REVIEW_SUPPLIER_PARAMETER",
        "before_qty": raw.get("before_value"),
        "after_qty": raw.get("after_value"),
        "before_date": "",
        "after_date": "",
        "cash_release": raw.get("impact_amount") or 0,
        "saving_type": "Book Saving",
        "inventory_days_before": 0,
        "inventory_days_after": 0,
        "shortage_risk_before": 0,
        "shortage_risk_after": 0,
        "recommendation_level": raw.get("recommendation_level") or "L2_REVIEW",
    }
