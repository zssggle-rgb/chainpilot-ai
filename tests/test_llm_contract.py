from __future__ import annotations

import pytest

from chainpilot_ai.ai.contracts import LLMGuardrailError, LLMResult
from chainpilot_ai.ai.guardrails import parse_json_object, validate_evidence_bound_output
from chainpilot_ai.ai.service import build_approval_summary_with_llm, explain_recommendation_with_llm, parse_goal_with_llm


def test_parse_json_object_accepts_fenced_json() -> None:
    payload = parse_json_object('```json\n{"ok": true}\n```')
    assert payload == {"ok": True}


def test_validate_evidence_bound_output_rejects_unknown_evidence_id() -> None:
    payload = _valid_payload()
    payload["evidence_ids"] = ["EVD-NOT-FOUND"]
    with pytest.raises(LLMGuardrailError):
        validate_evidence_bound_output(payload, [{"evidence_id": "EVD-1"}])


def test_validate_evidence_bound_output_rejects_direct_writeback() -> None:
    payload = _valid_payload()
    payload["approval_focus"] = ["无需审批写入 SAP"]
    with pytest.raises(LLMGuardrailError):
        validate_evidence_bound_output(payload, [{"evidence_id": "EVD-1"}])


def test_validate_evidence_bound_output_allows_safe_writeback_boundary() -> None:
    payload = _valid_payload()
    payload["approval_focus"] = ["审批通过后仅生成草稿，不直接写入SAP。"]
    validate_evidence_bound_output(payload, [{"evidence_id": "EVD-1"}])


def test_explain_recommendation_with_llm_validates_and_renders(monkeypatch) -> None:
    def fake_generate_json(*args, **kwargs):
        return LLMResult(
            provider="mock",
            model="mock-model",
            content='{"conclusion":"建议进入审批复核。","reasons":["证据显示该动作有业务依据。"],"risks":["需确认供应风险。"],"non_execution_impact":"不处理会保留当前风险。","approval_focus":["确认执行窗口。"],"evidence_ids":["EVD-1"],"limitations":["仅基于当前快照。"]}',
            raw_summary="{}",
            duration_ms=1,
        )

    monkeypatch.setattr("chainpilot_ai.ai.service.generate_json", fake_generate_json)
    result = explain_recommendation_with_llm(
        recommendation={"recommendation_id": "REC-1", "action_type": "REVIEW_MOQ"},
        algorithm_result={"result_id": "ARES-1", "algorithm_run": "AR-1", "raw": {"result_type": "MASTER_DATA_ISSUE"}},
        evidence=[{"evidence_id": "EVD-1", "summary": "证据"}],
        constraint_check={"verdict": "PASS_WITH_APPROVAL"},
    )
    assert result["status"] == "Ready"
    assert result["model_name"] == "mock-model"
    assert result["evidence_ids_used"] == "EVD-1"
    assert "结论：" in result["generated_text"]


def test_parse_goal_with_llm_validates_constraints(monkeypatch) -> None:
    def fake_generate_json(*args, **kwargs):
        return LLMResult(
            provider="mock",
            model="mock-model",
            content='{"user_goal":"减少 8000 万采购资金占用","cash_release_target":80000000,"protected_product_lines":["空调"],"preferred_actions":["REDUCE_PR_QTY"],"minimum_inventory_days":28,"max_shortage_risk_after":3.5,"freeze_window_days":7,"sap_writeback_mode":"draft_only","source":"llm"}',
            raw_summary="{}",
            duration_ms=1,
        )

    monkeypatch.setattr("chainpilot_ai.ai.service.generate_json", fake_generate_json)
    result = parse_goal_with_llm("减少 8000 万采购资金占用")
    assert result["cash_release_target"] == 80_000_000
    assert result["source"] == "llm:mock-model"
    assert result["sap_writeback_mode"] == "draft_only"


def test_build_approval_summary_with_llm_rejects_auto_write(monkeypatch) -> None:
    def fake_generate_json(*args, **kwargs):
        return LLMResult(
            provider="mock",
            model="mock-model",
            content='{"approval_summary":"审批通过后自动写入 SAP。","risk_summary":"风险低。","approval_focus":["确认窗口"],"limitations":["仅基于当前数据"]}',
            raw_summary="{}",
            duration_ms=1,
        )

    monkeypatch.setattr("chainpilot_ai.ai.service.generate_json", fake_generate_json)
    with pytest.raises(ValueError):
        build_approval_summary_with_llm(
            [{"recommendation_id": "REC-1", "cash_release": 100}],
            {"recommendation_count": 1, "total_cash_release": 100},
        )


def _valid_payload() -> dict[str, object]:
    return {
        "conclusion": "建议进入审批复核。",
        "reasons": ["证据显示该动作有业务依据。"],
        "risks": ["需确认供应风险。"],
        "non_execution_impact": "不处理会保留当前风险。",
        "approval_focus": ["确认执行窗口。"],
        "evidence_ids": ["EVD-1"],
        "limitations": ["仅基于当前快照。"],
    }
