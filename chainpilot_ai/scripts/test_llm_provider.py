from __future__ import annotations

import json
import re
from typing import Any

from chainpilot_ai.ai.service import explain_recommendation_with_llm, test_llm_connection
from chainpilot_ai.algorithms.registry import run_mvp_algorithms
from chainpilot_ai.recommendation.result_to_recommendation import convert_algorithm_results
from chainpilot_ai.snapshots.mock_loader import load_mock_sap_snapshot


def run() -> dict[str, Any]:
    try:
        connection = test_llm_connection()
    except Exception as exc:
        return {
            "ok": False,
            "stage": "connection",
            "status": "Failed",
            "error": _redact_error(str(exc)),
            "hint": "请确认火山 Ark Coding Plan 订阅有效，且当前 key 有权访问配置的 Coding Plan endpoint。",
        }
    sample = _build_sample()
    try:
        explanation = explain_recommendation_with_llm(
            recommendation=sample["recommendation"],
            algorithm_result=sample["algorithm_result"],
            evidence=sample["evidence"],
            constraint_check=sample["constraint_check"],
        )
    except Exception as exc:
        return {
            "ok": False,
            "stage": "explanation",
            "status": "Failed",
            "connection": {
                "ok": connection["ok"],
                "provider": connection["provider"],
                "model": connection["model"],
                "duration_ms": connection["duration_ms"],
            },
            "error": _redact_error(str(exc)),
        }
    return {
        "ok": True,
        "connection": {
            "ok": connection["ok"],
            "provider": connection["provider"],
            "model": connection["model"],
            "duration_ms": connection["duration_ms"],
        },
        "explanation": {
            "status": explanation["status"],
            "model_name": explanation["model_name"],
            "prompt_version": explanation["prompt_version"],
            "evidence_ids_used": explanation["evidence_ids_used"],
            "generated_text": explanation["generated_text"],
        },
    }


def _build_sample() -> dict[str, Any]:
    runtime = run_mvp_algorithms(load_mock_sap_snapshot())
    generated = convert_algorithm_results(runtime)
    recommendation = next(row for row in generated["recommendations"] if row["cash_release"] > 0)
    recommendation_id = recommendation["recommendation_id"]
    algorithm_result = next(row for row in runtime["results"] if row["result_id"] == recommendation["algorithm_result"])
    evidence = [row for row in generated["evidence"] if row["recommendation_id"] == recommendation_id]
    constraint_check = next(row for row in generated["checks"] if row["recommendation_id"] == recommendation_id)
    return {
        "recommendation": recommendation,
        "algorithm_result": algorithm_result,
        "evidence": evidence,
        "constraint_check": constraint_check,
    }


def _redact_error(message: str) -> str:
    redacted = re.sub(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b", "[REDACTED]", message)
    redacted = re.sub(r"Bearer\s+[^\\s,，。]+", "Bearer [REDACTED]", redacted)
    return redacted[:600]


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2, default=str))
