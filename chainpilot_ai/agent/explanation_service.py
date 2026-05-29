from __future__ import annotations

import json
from typing import Any


def generate_algorithm_explanation(
    recommendation: dict[str, Any],
    algorithm_result: dict[str, Any],
    evidence: list[dict[str, Any]],
    constraint_check: dict[str, Any] | None = None,
) -> dict[str, Any]:
    evidence_ids = [item["evidence_id"] for item in evidence if item.get("evidence_id")]
    if not evidence_ids:
        return {
            "status": "NEED_EVIDENCE",
            "generated_text": "证据不足，不能生成正式解释。",
            "evidence_ids_used": "",
        }
    raw = algorithm_result.get("raw") or _loads(algorithm_result.get("raw_json"))
    algorithm_code = raw.get("algorithm_code") or ""
    algorithm_version = raw.get("algorithm_version") or ""
    method = raw.get("algorithm_method_summary") or "专业轻量算法运行结果。"
    verdict = (constraint_check or {}).get("verdict") or recommendation.get("constraint_verdict") or "PASS"
    lines = [
        f"算法来源：{algorithm_code} {algorithm_version}。",
        f"数据快照：{recommendation.get('snapshot_id') or raw.get('snapshot_id')}；算法运行：{recommendation.get('algorithm_run') or algorithm_result.get('algorithm_run')}。",
        f"建议动作：{_sentence(_action_text(recommendation))}",
        f"核心证据：{'; '.join(item.get('summary', '') for item in evidence if item.get('summary'))}",
        f"约束校验：{verdict}。{(constraint_check or {}).get('message') or recommendation.get('blocked_reason') or '未发现阻断条件。'}",
        f"审批建议：{_sentence(_approval_text(recommendation))}",
        f"不执行影响：{_non_execution_text(recommendation, raw)}",
        f"算法假设与局限：{method}",
    ]
    return {
        "status": "Ready",
        "generated_text": "\n".join(lines),
        "evidence_ids_used": ",".join(evidence_ids),
    }


def _loads(value: object) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        return json.loads(str(value))
    except json.JSONDecodeError:
        return {}


def _action_text(recommendation: dict[str, Any]) -> str:
    action = recommendation.get("action_type")
    material = recommendation.get("material_code")
    doc = f"{recommendation.get('sap_object_type')} {recommendation.get('sap_doc_no')}/{recommendation.get('sap_item_no')}"
    if action == "REDUCE_PR_QTY":
        return f"下调 {doc}，物料 {material}，数量从 {recommendation.get('before_qty')} 调整为 {recommendation.get('after_qty')}"
    if action == "DELAY_UNCONFIRMED_PO":
        return f"延期 {doc}，物料 {material}，交期从 {recommendation.get('before_date')} 调整为 {recommendation.get('after_date')}"
    if action in {"EXPEDITE_PO", "ADVANCE_RISK_MATERIAL", "CREATE_EMERGENCY_PR"}:
        return f"处理缺料风险物料 {material}，{_action_label(action)}"
    return f"复核物料 {material} 的 SAP 参数，{_action_label(action)}"


def _approval_text(recommendation: dict[str, Any]) -> str:
    level = recommendation.get("recommendation_level")
    if level == "L1_AUTO_RECOMMEND":
        return "低风险动作，可进入常规审批包"
    if level == "L3_SUPPLIER_CONFIRM":
        return "需要采购员先与供应商确认，再进入审批"
    if level == "L4_WATCH_ONLY":
        return "仅观察，不建议进入审批"
    return "需要计划经理复核后进入审批"


def _non_execution_text(recommendation: dict[str, Any], raw: dict[str, Any]) -> str:
    if raw.get("result_type") == "SHORTAGE_RISK":
        return f"未来 14 天缺料概率 {raw.get('shortage_probability_14d')}，若不处理，可能影响 {', '.join(raw.get('affected_production_orders') or [])}。"
    if raw.get("result_type") == "CASH_RELEASE_ACTION":
        return f"若不执行，预计资金占用减少额 {recommendation.get('cash_release')} 无法释放。"
    if raw.get("result_type") == "MASTER_DATA_ISSUE":
        return "若不复核，MRP 可能继续按异常参数生成采购计划。"
    return "若不处理，相关业务风险会继续保留。"


def _action_label(action: object) -> str:
    labels = {
        "EXPEDITE_PO": "跟催采购订单",
        "ADVANCE_RISK_MATERIAL": "提前处理高风险物料",
        "CREATE_EMERGENCY_PR": "创建紧急采购申请",
        "CANCEL_PR_LINE": "取消采购申请行",
        "SPLIT_PO_DELIVERY": "拆分采购订单交付",
        "USE_SUBSTITUTE_MATERIAL": "评估替代物料",
        "REVIEW_MOQ": "复核最小起订量",
        "REVIEW_SUPPLIER_PARAMETER": "复核供应商参数",
    }
    return labels.get(str(action), "复核采购参数")


def _sentence(text: str) -> str:
    return text.rstrip("。；;,. ") + "。"
