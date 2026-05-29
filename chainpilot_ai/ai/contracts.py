from __future__ import annotations

from dataclasses import dataclass
from typing import Any


EVIDENCE_EXPLANATION_SCHEMA_VERSION = "evidence-explanation-v1"

EVIDENCE_EXPLANATION_REQUIRED_KEYS = {
    "conclusion",
    "reasons",
    "risks",
    "non_execution_impact",
    "approval_focus",
    "evidence_ids",
    "limitations",
}


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    base_url: str
    api_key: str
    model: str
    timeout_seconds: int = 60


@dataclass(frozen=True)
class LLMResult:
    provider: str
    model: str
    content: str
    raw_summary: str
    duration_ms: int
    input_tokens: int = 0
    output_tokens: int = 0


class LLMConfigurationError(RuntimeError):
    pass


class LLMProviderError(RuntimeError):
    pass


class LLMGuardrailError(ValueError):
    pass


def validate_evidence_explanation_schema(payload: dict[str, Any]) -> None:
    missing = sorted(EVIDENCE_EXPLANATION_REQUIRED_KEYS - set(payload))
    if missing:
        raise LLMGuardrailError(f"LLM 输出缺少字段：{', '.join(missing)}")
    for key in ["conclusion", "non_execution_impact"]:
        if not isinstance(payload.get(key), str) or not payload[key].strip():
            raise LLMGuardrailError(f"LLM 输出字段 {key} 必须是非空文本")
    for key in ["reasons", "risks", "approval_focus", "evidence_ids", "limitations"]:
        if not isinstance(payload.get(key), list) or not payload[key]:
            raise LLMGuardrailError(f"LLM 输出字段 {key} 必须是非空数组")
    if not all(isinstance(item, str) and item.strip() for item in payload["evidence_ids"]):
        raise LLMGuardrailError("LLM 输出 evidence_ids 必须全部是非空文本")
