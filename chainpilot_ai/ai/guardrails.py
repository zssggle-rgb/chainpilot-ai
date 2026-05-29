from __future__ import annotations

import json
import re
from typing import Any

from chainpilot_ai.ai.contracts import LLMGuardrailError, validate_evidence_explanation_schema


BLOCKED_WRITEBACK_TERMS = ("直接写入 SAP", "自动写入 SAP", "无需审批写入", "direct_write", "直接回写")


def parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, flags=re.S)
        if not match:
            raise LLMGuardrailError("LLM 没有返回 JSON 对象")
        payload = json.loads(match.group(0))
    if not isinstance(payload, dict):
        raise LLMGuardrailError("LLM 输出必须是 JSON 对象")
    return payload


def validate_evidence_bound_output(payload: dict[str, Any], evidence: list[dict[str, Any]]) -> None:
    validate_evidence_explanation_schema(payload)
    allowed_ids = {item["evidence_id"] for item in evidence if item.get("evidence_id")}
    used_ids = set(payload.get("evidence_ids") or [])
    if not used_ids:
        raise LLMGuardrailError("LLM 输出没有引用证据 ID")
    unknown = sorted(used_ids - allowed_ids)
    if unknown:
        raise LLMGuardrailError(f"LLM 引用了不存在的证据 ID：{', '.join(unknown)}")
    text = json.dumps(payload, ensure_ascii=False)
    if any(term in text for term in BLOCKED_WRITEBACK_TERMS):
        raise LLMGuardrailError("LLM 输出包含越权回写表述")
    if re.search(r"\b[A-Z_]{8,}\b", text):
        raise LLMGuardrailError("LLM 输出包含面向用户不友好的内部编码")
