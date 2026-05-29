from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from chainpilot_ai.ai.contracts import EVIDENCE_EXPLANATION_SCHEMA_VERSION
from chainpilot_ai.ai.guardrails import parse_json_object, validate_evidence_bound_output
from chainpilot_ai.ai.provider import generate_json, health_check

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
        payload = parse_json_object(result.content)
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


@_whitelist
def test_llm_connection() -> dict[str, Any]:
    return health_check()


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
