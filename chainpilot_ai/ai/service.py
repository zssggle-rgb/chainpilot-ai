from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any

from chainpilot_ai.ai.contracts import EVIDENCE_EXPLANATION_SCHEMA_VERSION, LLMConfigurationError
from chainpilot_ai.ai.guardrails import parse_json_object, validate_evidence_bound_output
from chainpilot_ai.ai.provider import generate_json, get_llm_config, health_check

try:
    import frappe
except Exception:  # pragma: no cover - local tests run without a Frappe site.
    frappe = None


EVIDENCE_EXPLANATION_SYSTEM_PROMPT = """你是 ChainPilot AI 的供应链建议解释助手。
你只能基于输入中的 algorithm_result、recommendation、constraint_check 和 evidence 生成中文解释。
禁止编造金额、数量、日期、概率、SAP 单号或证据 ID。
禁止建议直接写入 SAP；只能说明进入审批或生成回写草稿。
不要输出英文标题、内部过程说明或动作编码。
必须只输出 JSON 对象，字段为：
conclusion: string
reasons: string[]
risks: string[]
non_execution_impact: string
approval_focus: string[]
evidence_ids: string[]
limitations: string[]
输出示例：
{"conclusion":"建议进入审批复核。","reasons":["证据显示该动作满足当前约束。"],"risks":["需确认供应商交付风险。"],"non_execution_impact":"不处理会保留当前库存或缺料风险。","approval_focus":["确认执行窗口。"],"evidence_ids":["EVD-EXAMPLE"],"limitations":["仅基于当前快照。"]}
"""

INTENT_SCHEMA_VERSION = "intent-to-constraints-v1"
INTENT_TO_CONSTRAINTS_SYSTEM_PROMPT = """你是 ChainPilot AI 的供应链目标理解助手。
你只把用户中文目标转成可校验的约束 JSON，不做优化计算。
金额、库存天数、缺料阈值只能来自用户输入或默认策略；不允许编造 SAP 单号、物料号或供应商。
必须只输出 JSON 对象，字段为：
user_goal: string
cash_release_target: number | null
protected_product_lines: string[]
preferred_actions: string[]
minimum_inventory_days: number
max_shortage_risk_after: number
freeze_window_days: number
sap_writeback_mode: string
source: string
preferred_actions 只能使用 REDUCE_PR_QTY、DELAY_UNCONFIRMED_PO、REVIEW_SAFETY_STOCK、REVIEW_SUPPLIER_LEAD_TIME。
sap_writeback_mode 必须为 draft_only。
"""

APPROVAL_SUMMARY_SCHEMA_VERSION = "approval-summary-v1"
APPROVAL_SUMMARY_SYSTEM_PROMPT = """你是 ChainPilot AI 的采购优化审批摘要助手。
你只能基于输入的 recommendation_summary、risk_summary 和 approval_rules 生成中文审批摘要。
禁止新增金额、数量、概率、SAP 单号或审批结论；审批路由由系统规则决定。
禁止建议直接写入 SAP；只能说明审批通过后生成回写草稿。
必须使用中文业务表达，不要输出英文标题、英文句子或内部过程说明。
必须只输出 JSON 对象，字段为：
approval_summary: string
risk_summary: string
approval_focus: string[]
limitations: string[]
"""

SUPPLIER_COMMUNICATION_SCHEMA_VERSION = "supplier-communication-v1"
SUPPLIER_COMMUNICATION_SYSTEM_PROMPT = """你是 ChainPilot AI 的采购供应商沟通草稿助手。
你只能根据输入的采购订单行、建议动作和审批边界生成中文沟通草稿。
草稿不得表示消息已发送，不得承诺自动修改 SAP，不得新增金额、数量或日期。
必须只输出 JSON 对象，字段为：
subject: string
message: string
review_focus: string[]
limitations: string[]
"""


def _whitelist(fn):
    if frappe:
        return frappe.whitelist()(fn)
    return fn


def _frappe_ready() -> bool:
    try:
        return bool(frappe and getattr(frappe.local, "site", None) and getattr(frappe, "db", None))
    except Exception:
        return False


def explain_recommendation_with_llm(
    recommendation: dict[str, Any],
    algorithm_result: dict[str, Any],
    evidence: list[dict[str, Any]],
    constraint_check: dict[str, Any] | None = None,
) -> dict[str, Any]:
    user_payload = {
        "task_code": "EVIDENCE_EXPLANATION",
        "schema_version": EVIDENCE_EXPLANATION_SCHEMA_VERSION,
        "recommendation": recommendation,
        "algorithm_result": _compact_algorithm_result(algorithm_result),
        "constraint_check": constraint_check or {},
        "evidence": evidence,
    }
    input_hash = _hash_json(user_payload)
    try:
        result = generate_json("EVIDENCE_EXPLANATION", EVIDENCE_EXPLANATION_SYSTEM_PROMPT, user_payload)
        payload = _localize_business_terms(parse_json_object(result.content))
        validate_evidence_bound_output(payload, evidence)
        output_hash = _hash_json(payload)
        _log_llm_call(
            task_code="EVIDENCE_EXPLANATION",
            provider=result.provider,
            model=result.model,
            input_hash=input_hash,
            output_hash=output_hash,
            schema_version=EVIDENCE_EXPLANATION_SCHEMA_VERSION,
            duration_ms=result.duration_ms,
            status="Success",
            error_message="",
        )
        return {
            "status": "Ready",
            "model_name": result.model,
            "prompt_version": EVIDENCE_EXPLANATION_SCHEMA_VERSION,
            "generated_text": _render_explanation(payload),
            "evidence_ids_used": ",".join(payload["evidence_ids"]),
            "llm_payload": payload,
        }
    except Exception as exc:
        _log_llm_call(
            task_code="EVIDENCE_EXPLANATION",
            provider="configured",
            model="configured",
            input_hash=input_hash,
            output_hash="",
            schema_version=EVIDENCE_EXPLANATION_SCHEMA_VERSION,
            duration_ms=0,
            status="Failed",
            error_message=str(exc),
        )
        raise


def parse_goal_with_llm(user_goal: str) -> dict[str, Any]:
    from chainpilot_ai.scenario.service import validate_constraint_schema

    user_payload = {
        "task_code": "INTENT_TO_CONSTRAINTS",
        "schema_version": INTENT_SCHEMA_VERSION,
        "user_goal": user_goal,
        "defaults": {
            "minimum_inventory_days": 28,
            "max_shortage_risk_after": 3.5,
            "freeze_window_days": 7,
            "sap_writeback_mode": "draft_only",
        },
    }
    input_hash = _hash_json(user_payload)
    try:
        result = generate_json("INTENT_TO_CONSTRAINTS", INTENT_TO_CONSTRAINTS_SYSTEM_PROMPT, user_payload, max_tokens=500)
        payload = parse_json_object(result.content)
        payload["user_goal"] = str(payload.get("user_goal") or user_goal)
        payload["source"] = f"llm:{result.model}"
        validated = validate_constraint_schema(payload)
        _log_llm_call(
            task_code="INTENT_TO_CONSTRAINTS",
            provider=result.provider,
            model=result.model,
            input_hash=input_hash,
            output_hash=_hash_json(validated),
            schema_version=INTENT_SCHEMA_VERSION,
            duration_ms=result.duration_ms,
            status="Success",
            error_message="",
        )
        return validated
    except Exception as exc:
        _log_llm_call(
            task_code="INTENT_TO_CONSTRAINTS",
            provider="configured",
            model="configured",
            input_hash=input_hash,
            output_hash="",
            schema_version=INTENT_SCHEMA_VERSION,
            duration_ms=0,
            status="Failed",
            error_message=str(exc),
        )
        raise


def build_approval_summary_with_llm(recommendations: list[dict[str, Any]], rule_summary: dict[str, Any]) -> dict[str, Any]:
    user_payload = {
        "task_code": "APPROVAL_SUMMARY",
        "schema_version": APPROVAL_SUMMARY_SCHEMA_VERSION,
        "recommendation_summary": _compact_recommendations(recommendations),
        "rule_summary": rule_summary,
        "approval_rules": {
            "sap_writeback": "draft_only",
            "approval_decision": "human_only",
            "numbers_must_come_from_input": True,
        },
    }
    input_hash = _hash_json(user_payload)
    try:
        result = generate_json("APPROVAL_SUMMARY", APPROVAL_SUMMARY_SYSTEM_PROMPT, user_payload, max_tokens=700)
        payload = _localize_business_terms(parse_json_object(result.content))
        _validate_text_payload(payload, ["approval_summary", "risk_summary"], ["approval_focus", "limitations"])
        _reject_forbidden_sap_writeback(payload)
        _log_llm_call(
            task_code="APPROVAL_SUMMARY",
            provider=result.provider,
            model=result.model,
            input_hash=input_hash,
            output_hash=_hash_json(payload),
            schema_version=APPROVAL_SUMMARY_SCHEMA_VERSION,
            duration_ms=result.duration_ms,
            status="Success",
            error_message="",
        )
        return {
            "approval_summary": payload["approval_summary"],
            "risk_summary": payload["risk_summary"],
            "approval_focus": payload["approval_focus"],
            "limitations": payload["limitations"],
            "model_name": result.model,
        }
    except Exception as exc:
        _log_llm_call(
            task_code="APPROVAL_SUMMARY",
            provider="configured",
            model="configured",
            input_hash=input_hash,
            output_hash="",
            schema_version=APPROVAL_SUMMARY_SCHEMA_VERSION,
            duration_ms=0,
            status="Failed",
            error_message=str(exc),
        )
        raise


def build_supplier_communication_with_llm(recommendation: dict[str, Any], package_id: str) -> dict[str, Any]:
    user_payload = {
        "task_code": "SUPPLIER_COMMUNICATION",
        "schema_version": SUPPLIER_COMMUNICATION_SCHEMA_VERSION,
        "package_id": package_id,
        "recommendation": _compact_recommendations([recommendation])[0],
        "boundary": {
            "draft_only": True,
            "must_be_reviewed_by_buyer": True,
            "do_not_send_automatically": True,
        },
    }
    input_hash = _hash_json(user_payload)
    try:
        result = generate_json("SUPPLIER_COMMUNICATION", SUPPLIER_COMMUNICATION_SYSTEM_PROMPT, user_payload, max_tokens=700)
        payload = parse_json_object(result.content)
        _validate_text_payload(payload, ["subject", "message"], ["review_focus", "limitations"])
        _reject_forbidden_sap_writeback(payload)
        _log_llm_call(
            task_code="SUPPLIER_COMMUNICATION",
            provider=result.provider,
            model=result.model,
            input_hash=input_hash,
            output_hash=_hash_json(payload),
            schema_version=SUPPLIER_COMMUNICATION_SCHEMA_VERSION,
            duration_ms=result.duration_ms,
            status="Success",
            error_message="",
        )
        return {
            "subject": payload["subject"],
            "message": payload["message"],
            "review_focus": payload["review_focus"],
            "limitations": payload["limitations"],
            "model_name": result.model,
        }
    except Exception as exc:
        _log_llm_call(
            task_code="SUPPLIER_COMMUNICATION",
            provider="configured",
            model="configured",
            input_hash=input_hash,
            output_hash="",
            schema_version=SUPPLIER_COMMUNICATION_SCHEMA_VERSION,
            duration_ms=0,
            status="Failed",
            error_message=str(exc),
        )
        raise


@_whitelist
def generate_recommendation_explanation_rpc(recommendation_id: str) -> dict[str, Any]:
    if not _frappe_ready():
        return {"ok": False, "status": "NO_SITE"}
    recommendation = _get_recommendation_payload(recommendation_id)
    evidence = _get_recommendation_evidence(recommendation_id)
    constraint_check = _get_primary_constraint_check(recommendation_id)
    algorithm_result = _get_algorithm_result_payload(recommendation)
    explanation = explain_recommendation_with_llm(recommendation, algorithm_result, evidence, constraint_check)
    persistence = _persist_ai_explanation(recommendation, explanation)
    return {"ok": True, "explanation": explanation, "persistence": persistence, "llm": get_llm_runtime_summary()}


@_whitelist
def get_recommendation_ai_panel_rpc(recommendation_id: str) -> dict[str, Any]:
    if not _frappe_ready():
        return {"ok": False, "status": "NO_SITE"}
    latest = frappe.get_all(
        "AI Explanation",
        filters={"recommendation": recommendation_id},
        fields=["explanation_id", "prompt_version", "model_name", "status", "generated_text", "evidence_ids_used", "modified"],
        order_by="modified desc",
        limit=1,
    )
    return {"ok": True, "explanation": latest[0] if latest else None, "llm": get_llm_runtime_summary()}


@_whitelist
def test_llm_connection() -> dict[str, Any]:
    return health_check()


def get_llm_runtime_summary() -> dict[str, Any]:
    try:
        config = get_llm_config()
    except LLMConfigurationError as exc:
        return {"configured": False, "provider": "", "model": "", "status": "未配置", "message": str(exc)}
    return {
        "configured": True,
        "provider": config.provider,
        "model": config.model,
        "status": "已配置",
        "message": "真实模型用于目标理解、证据解释、审批摘要和沟通草稿。",
    }


def _compact_algorithm_result(result: dict[str, Any]) -> dict[str, Any]:
    raw = result.get("raw") or {}
    return {
        "result_id": result.get("result_id"),
        "algorithm_run": result.get("algorithm_run"),
        "result_type": raw.get("result_type"),
        "algorithm_code": raw.get("algorithm_code"),
        "algorithm_version": raw.get("algorithm_version"),
        "method": raw.get("algorithm_method_summary"),
        "material_code": raw.get("material_code"),
        "sap_object_type": raw.get("sap_object_type"),
        "sap_doc_no": raw.get("sap_doc_no"),
        "sap_item_no": raw.get("sap_item_no"),
        "metric_name": raw.get("metric_name"),
        "metric_value": raw.get("metric_value"),
        "snapshot_id": raw.get("snapshot_id"),
    }


def _compact_recommendations(recommendations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keys = [
        "recommendation_id",
        "action_type",
        "sap_object_type",
        "sap_doc_no",
        "sap_item_no",
        "material_code",
        "material_name",
        "plant",
        "supplier",
        "before_qty",
        "after_qty",
        "before_date",
        "after_date",
        "cash_release",
        "inventory_days_after",
        "shortage_risk_after",
        "constraint_verdict",
        "approval_status",
    ]
    return [{key: item.get(key) for key in keys} for item in recommendations]


def _localize_business_terms(value: Any, key: str = "") -> Any:
    if key == "evidence_ids":
        return value
    if isinstance(value, dict):
        return {item_key: _localize_business_terms(item_value, item_key) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [_localize_business_terms(item, key) for item in value]
    if not isinstance(value, str):
        return value
    replacements = {
        "REDUCE_PR_QTY": "下调采购申请数量",
        "CANCEL_PR_LINE": "取消采购申请行",
        "DELAY_UNCONFIRMED_PO": "延后未确认采购订单",
        "SPLIT_PO_DELIVERY": "拆分采购订单交付",
        "ADVANCE_RISK_MATERIAL": "提前处理风险物料",
        "EXPEDITE_PO": "跟催采购订单",
        "CREATE_EMERGENCY_PR": "创建紧急采购申请",
        "USE_SUBSTITUTE_MATERIAL": "评估替代物料",
        "REVIEW_SAFETY_STOCK": "复核安全库存",
        "REVIEW_SUPPLIER_LEAD_TIME": "复核供应商交期",
        "REVIEW_MOQ": "复核最小起订量",
        "REVIEW_SUPPLIER_PARAMETER": "复核供应商参数",
        "SHORTAGE_RISK": "缺料风险",
        "CASH_RELEASE_ACTION": "资金占用优化动作",
        "MASTER_DATA_ISSUE": "主数据问题",
        "PASS_WITH_APPROVAL": "通过但需要审批",
        "L1_AUTO_RECOMMEND": "低风险建议",
        "L2_REVIEW": "需要复核",
        "L3_SUPPLIER_CONFIRM": "需要供应商确认",
        "L4_WATCH_ONLY": "仅观察",
        "SAP_MOCK": "模拟快照",
        "SNAP": "快照",
        "MOCK": "模拟",
        "DRAFT_ONLY": "仅生成草稿",
        "draft_only": "仅生成草稿",
        "PR": "采购申请",
        "PO": "采购订单",
    }
    localized = value
    for source, target in replacements.items():
        localized = localized.replace(source, target)
    localized = re.sub(r"\b[A-Z]{2,}(?:_[A-Z0-9]+)+\b", "业务编码", localized)
    localized = re.sub(r"\b[A-Z]{8,}\b", "业务编码", localized)
    return localized


def _render_explanation(payload: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"结论：{payload['conclusion']}",
            "依据：" + "；".join(payload["reasons"]),
            "风险：" + "；".join(payload["risks"]),
            f"不处理影响：{payload['non_execution_impact']}",
            "审批关注：" + "；".join(payload["approval_focus"]),
            "局限：" + "；".join(payload["limitations"]),
        ]
    )


def _validate_text_payload(payload: dict[str, Any], text_keys: list[str], list_keys: list[str]) -> None:
    for key in text_keys:
        if not isinstance(payload.get(key), str) or not payload[key].strip():
            raise ValueError(f"LLM 输出字段 {key} 必须是非空文本")
    for key in list_keys:
        if not isinstance(payload.get(key), list) or not payload[key]:
            raise ValueError(f"LLM 输出字段 {key} 必须是非空数组")
        if not all(isinstance(item, str) and item.strip() for item in payload[key]):
            raise ValueError(f"LLM 输出字段 {key} 必须全部是非空文本")


def _reject_forbidden_sap_writeback(payload: dict[str, Any]) -> None:
    text = json.dumps(payload, ensure_ascii=False)
    safe = text
    for term in (
        "不直接写入 SAP",
        "不直接写入SAP",
        "不会直接写入 SAP",
        "不会直接写入SAP",
        "不能直接写入 SAP",
        "不能直接写入SAP",
        "不可直接写入 SAP",
        "不可直接写入SAP",
        "禁止直接写入 SAP",
        "禁止直接写入SAP",
        "严禁直接写入 SAP",
        "严禁直接写入SAP",
        "不直接回写",
        "不会直接回写",
        "不能直接回写",
        "不可直接回写",
        "禁止直接回写",
        "严禁直接回写",
    ):
        safe = safe.replace(term, "")
    forbidden = ("直接写入 SAP", "直接写入SAP", "自动写入 SAP", "自动写入SAP", "无需审批写入", "直接回写", "已自动发送", "已发送给供应商")
    if any(term in safe for term in forbidden):
        raise ValueError("LLM 输出包含越权执行表述")


def _get_recommendation_payload(recommendation_id: str) -> dict[str, Any]:
    doc = frappe.get_doc("Recommendation", recommendation_id)
    payload = doc.as_dict()
    payload["recommendation_id"] = payload.get("recommendation_id") or doc.name
    return dict(payload)


def _get_recommendation_evidence(recommendation_id: str) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in frappe.get_all(
            "Recommendation Evidence",
            filters={"recommendation_id": recommendation_id},
            fields=["evidence_id", "source_type", "source_id", "metric_name", "metric_value", "threshold_value", "verdict", "summary"],
            order_by="modified asc",
            limit=20,
        )
    ]


def _get_primary_constraint_check(recommendation_id: str) -> dict[str, Any]:
    rows = frappe.get_all(
        "Constraint Check Result",
        filters={"recommendation_id": recommendation_id},
        fields=["check_id", "rule_code", "verdict", "message", "evidence_id"],
        order_by="modified asc",
        limit=1,
    )
    return dict(rows[0]) if rows else {}


def _get_algorithm_result_payload(recommendation: dict[str, Any]) -> dict[str, Any]:
    result_id = recommendation.get("algorithm_result")
    if result_id and frappe.db.exists("Algorithm Result", result_id):
        doc = frappe.get_doc("Algorithm Result", result_id)
        raw = {}
        if doc.raw_json:
            try:
                raw = json.loads(doc.raw_json)
            except json.JSONDecodeError:
                raw = {}
        return {
            "result_id": doc.result_id,
            "algorithm_run": doc.algorithm_run,
            "raw": raw,
        }
    return {
        "result_id": result_id or recommendation.get("result_id") or recommendation.get("recommendation_id"),
        "algorithm_run": recommendation.get("algorithm_run"),
        "raw": {
            "result_type": "RECOMMENDATION",
            "material_code": recommendation.get("material_code"),
            "sap_object_type": recommendation.get("sap_object_type"),
            "sap_doc_no": recommendation.get("sap_doc_no"),
            "sap_item_no": recommendation.get("sap_item_no"),
            "metric_name": "cash_release",
            "metric_value": recommendation.get("cash_release"),
            "snapshot_id": recommendation.get("snapshot_id"),
        },
    }


def _persist_ai_explanation(recommendation: dict[str, Any], explanation: dict[str, Any]) -> dict[str, Any]:
    algorithm_run = recommendation.get("algorithm_run")
    recommendation_id = recommendation.get("recommendation_id") or recommendation.get("name")
    if not algorithm_run:
        return {"saved": False, "reason": "recommendation_without_algorithm_run"}
    explanation_id = f"EXP-LLM-{str(recommendation_id)[-22:]}"
    payload = {
        "explanation_id": explanation_id,
        "recommendation": recommendation_id,
        "algorithm_run": algorithm_run,
        "prompt_version": explanation["prompt_version"],
        "model_name": explanation["model_name"],
        "status": explanation["status"],
        "generated_text": explanation["generated_text"],
        "evidence_ids_used": explanation["evidence_ids_used"],
    }
    existing = frappe.db.exists("AI Explanation", explanation_id)
    if existing:
        doc = frappe.get_doc("AI Explanation", existing)
        doc.update(payload)
        doc.save(ignore_permissions=True)
    else:
        frappe.get_doc({"doctype": "AI Explanation", **payload}).insert(ignore_permissions=True)
    if frappe.db.exists("Recommendation", recommendation_id):
        rec = frappe.get_doc("Recommendation", recommendation_id)
        rec.explanation_status = explanation["status"]
        rec.save(ignore_permissions=True)
    frappe.db.commit()
    return {"saved": True, "explanation_id": explanation_id}


def _log_llm_call(
    task_code: str,
    provider: str,
    model: str,
    input_hash: str,
    output_hash: str,
    schema_version: str,
    duration_ms: int,
    status: str,
    error_message: str,
) -> None:
    if not _frappe_ready() or not frappe.db.exists("DocType", "LLM Call Log"):
        return
    call_id = "LLM-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    doc = frappe.get_doc(
        {
            "doctype": "LLM Call Log",
            "call_id": call_id,
            "task_code": task_code,
            "provider": provider,
            "model": model,
            "input_hash": input_hash,
            "output_hash": output_hash,
            "schema_version": schema_version,
            "duration_ms": duration_ms,
            "status": status,
            "error_message": error_message[:1000],
        }
    )
    doc.insert(ignore_permissions=True)
    frappe.db.commit()


def _hash_json(payload: dict[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()
