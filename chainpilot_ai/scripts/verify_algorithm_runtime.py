from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from chainpilot_ai.algorithms.schemas import ALGORITHM_CODES
from chainpilot_ai.recommendation.result_to_recommendation import convert_algorithm_results
from chainpilot_ai.snapshots.mock_loader import DEFAULT_MOCK_SAP_SNAPSHOT_PATH, load_mock_sap_snapshot
from chainpilot_ai.snapshots.snapshot_service import build_snapshot_run
from chainpilot_ai.snapshots.validators import validate_mock_sap_snapshot
from chainpilot_ai.algorithms.registry import run_mvp_algorithms

ROOT = Path(__file__).resolve().parents[2]
VERIFY_REPORT_PATH = ROOT / "tmp" / "algorithm_runtime_verify_report.json"


def _status(status: str, evidence: str, notes: str = "") -> dict[str, str]:
    return {"status": status, "evidence": evidence, "notes": notes}


def check_mock_snapshot_contract() -> dict[str, str]:
    data = load_mock_sap_snapshot()
    validation = validate_mock_sap_snapshot(data)
    if validation["ok"] and validation["counts"]["pr_lines"] + validation["counts"]["po_lines"] >= 20:
        return _status("Pass", str(DEFAULT_MOCK_SAP_SNAPSHOT_PATH), json.dumps(validation["counts"], ensure_ascii=False))
    return _status("Fail", str(DEFAULT_MOCK_SAP_SNAPSHOT_PATH), json.dumps(validation, ensure_ascii=False))


def check_doctype_contract() -> dict[str, str]:
    base = ROOT / "chainpilot_ai" / "chainpilot_ai" / "doctype"
    required = [
        "sap_snapshot_run/sap_snapshot_run.json",
        "sap_bom_component_snapshot/sap_bom_component_snapshot.json",
        "sap_planned_demand_snapshot/sap_planned_demand_snapshot.json",
        "sap_consumption_history_snapshot/sap_consumption_history_snapshot.json",
        "sap_supplier_performance_snapshot/sap_supplier_performance_snapshot.json",
        "sap_mrp_parameter_snapshot/sap_mrp_parameter_snapshot.json",
        "algorithm_definition/algorithm_definition.json",
        "algorithm_run/algorithm_run.json",
        "algorithm_result/algorithm_result.json",
        "ai_explanation/ai_explanation.json",
    ]
    missing = [relative for relative in required if not (base / relative).exists()]
    if missing:
        return _status("Fail", str(base), json.dumps({"missing": missing}, ensure_ascii=False))
    invalid = []
    for relative in required:
        payload = json.loads((base / relative).read_text(encoding="utf-8"))
        if payload.get("doctype") != "DocType" or payload.get("module") != "ChainPilot AI":
            invalid.append(relative)
    return _status("Pass" if not invalid else "Fail", str(base), json.dumps({"invalid": invalid, "count": len(required)}, ensure_ascii=False))


def check_runtime_counts() -> dict[str, str]:
    data = load_mock_sap_snapshot()
    snapshot_run = build_snapshot_run(data)
    runtime = run_mvp_algorithms(data)
    generated = convert_algorithm_results(runtime)
    cash_summary = next((run["summary"] for run in runtime["runs"] if run["run"]["algorithm_code"] == "CASH_RELEASE_PR_PO_OPT"), {})
    counts = {
        **runtime["counts"],
        "selected_cash_actions": cash_summary.get("selected_actions", 0),
        "blocked_cash_actions": cash_summary.get("blocked_actions", 0),
        "recommendations": len(generated["recommendations"]),
        "evidence": len(generated["evidence"]),
        "checks": len(generated["checks"]),
        "explanations": len(generated["explanations"]),
        "snapshot_id": snapshot_run["snapshot_id"],
    }
    ok = (
        runtime["ok"]
        and runtime["counts"]["algorithm_runs"] == len(ALGORITHM_CODES)
        and runtime["counts"]["shortage_results"] >= 5
        and runtime["counts"]["cash_release_results"] >= 20
        and runtime["counts"]["master_data_results"] >= 15
        and int(counts["selected_cash_actions"]) >= 10
        and int(counts["blocked_cash_actions"]) >= 1
        and counts["recommendations"] >= 20
        and counts["evidence"] == counts["recommendations"]
        and counts["checks"] == counts["recommendations"]
        and counts["explanations"] == counts["recommendations"]
    )
    return _status("Pass" if ok else "Fail", "chainpilot_ai.algorithms.registry.run_mvp_algorithms", json.dumps(counts, ensure_ascii=False))


def check_recommendation_traceability() -> dict[str, str]:
    runtime = run_mvp_algorithms(load_mock_sap_snapshot())
    generated = convert_algorithm_results(runtime)
    bad = [
        row["recommendation_id"]
        for row in generated["recommendations"]
        if not row.get("snapshot_id") or not row.get("algorithm_run") or not row.get("algorithm_result") or int(row.get("evidence_count") or 0) <= 0
    ]
    explanations_without_evidence = [row["explanation_id"] for row in generated["explanations"] if not row.get("evidence_ids_used") or row.get("status") != "Ready"]
    ok = not bad and not explanations_without_evidence
    return _status("Pass" if ok else "Fail", "result_to_recommendation traceability", json.dumps({"bad": bad, "explanations_without_evidence": explanations_without_evidence}, ensure_ascii=False))


CHECKS = {
    "AR-001": check_mock_snapshot_contract,
    "AR-002": check_doctype_contract,
    "AR-003": check_runtime_counts,
    "AR-004": check_recommendation_traceability,
}


def run() -> dict[str, Any]:
    results = {name: check() for name, check in CHECKS.items()}
    counts: dict[str, int] = {}
    for result in results.values():
        counts[result["status"]] = counts.get(result["status"], 0) + 1
    report = {"ok": counts.get("Fail", 0) == 0, "counts": counts, "results": results}
    VERIFY_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    VERIFY_REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
