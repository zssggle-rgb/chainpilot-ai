from __future__ import annotations

import json
from datetime import datetime, timezone
from time import perf_counter
from typing import Any, Callable

from chainpilot_ai.algorithms.cash_release_pr_po import run as run_cash_release
from chainpilot_ai.algorithms.master_data_diagnosis import run as run_master_data
from chainpilot_ai.algorithms.schemas import (
    ALGORITHM_CODES,
    CASH_RELEASE_PR_PO_OPT,
    MASTER_DATA_DIAGNOSIS_STAT,
    SHORTAGE_RISK_14D_PROB,
    definition_by_code,
)
from chainpilot_ai.algorithms.shortage_risk_14d import run as run_shortage

AlgorithmRunner = Callable[[dict[str, Any], dict[str, Any] | None], dict[str, Any]]

RUNNERS: dict[str, AlgorithmRunner] = {
    SHORTAGE_RISK_14D_PROB: run_shortage,
    CASH_RELEASE_PR_PO_OPT: run_cash_release,
    MASTER_DATA_DIAGNOSIS_STAT: run_master_data,
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _unique_id(prefix: str, code: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    return f"{prefix}-{code}-{stamp}"


def run_algorithm(
    algorithm_code: str,
    snapshot: dict[str, Any],
    scenario: dict[str, Any] | None = None,
    snapshot_id: str | None = None,
) -> dict[str, Any]:
    if algorithm_code not in RUNNERS:
        raise ValueError(f"Unknown algorithm_code: {algorithm_code}")

    definitions = definition_by_code()
    definition = definitions[algorithm_code]
    algorithm_run_id = _unique_id("AR", algorithm_code)
    started_at = _now()
    started_perf = perf_counter()
    try:
        payload = RUNNERS[algorithm_code](snapshot, scenario)
        raw_results = payload["results"]
        results = []
        for index, row in enumerate(raw_results, start=1):
            raw = {
                **row,
                "algorithm_code": algorithm_code,
                "algorithm_version": definition["version"],
                "algorithm_method_summary": definition["assumptions"],
                "snapshot_id": snapshot_id or snapshot.get("snapshot", {}).get("snapshot_id"),
            }
            result_id = f"ARES-{algorithm_run_id[-18:]}-{index:03d}"
            results.append(
                {
                    "result_id": result_id,
                    "algorithm_run": algorithm_run_id,
                    "result_type": row["result_type"],
                    "material_code": row.get("material_code"),
                    "plant": row.get("plant"),
                    "supplier": row.get("supplier"),
                    "sap_object_type": row.get("sap_object_type"),
                    "sap_doc_no": row.get("sap_doc_no") or row.get("target_po_no"),
                    "sap_item_no": row.get("sap_item_no") or row.get("target_po_item"),
                    "metric_name": row.get("metric_name") or row["result_type"],
                    "metric_value": str(row.get("metric_value") or row.get("cash_impact") or row.get("shortage_probability_14d") or row.get("impact_amount") or ""),
                    "raw_json": json.dumps(raw, ensure_ascii=False, sort_keys=True),
                    "raw": raw,
                }
            )
        finished_at = _now()
        return {
            "ok": True,
            "run": {
                "algorithm_run_id": algorithm_run_id,
                "algorithm_code": algorithm_code,
                "snapshot_id": snapshot_id or snapshot.get("snapshot", {}).get("snapshot_id"),
                "scenario_id": (scenario or {}).get("scenario_id"),
                "algorithm_version": definition["version"],
                "status": "Success",
                "started_at": started_at,
                "finished_at": finished_at,
                "duration_ms": int((perf_counter() - started_perf) * 1000),
                "input_payload_json": json.dumps({"snapshot_id": snapshot_id, "scenario": scenario or {}}, ensure_ascii=False, sort_keys=True),
                "summary_result_json": json.dumps(payload["summary"], ensure_ascii=False, sort_keys=True),
                "error_message": "",
            },
            "results": results,
            "summary": payload["summary"],
        }
    except Exception as exc:
        return {
            "ok": False,
            "run": {
                "algorithm_run_id": algorithm_run_id,
                "algorithm_code": algorithm_code,
                "snapshot_id": snapshot_id or snapshot.get("snapshot", {}).get("snapshot_id"),
                "scenario_id": (scenario or {}).get("scenario_id"),
                "algorithm_version": definition["version"],
                "status": "Failed",
                "started_at": started_at,
                "finished_at": _now(),
                "duration_ms": int((perf_counter() - started_perf) * 1000),
                "input_payload_json": json.dumps({"snapshot_id": snapshot_id, "scenario": scenario or {}}, ensure_ascii=False, sort_keys=True),
                "summary_result_json": "{}",
                "error_message": str(exc),
            },
            "results": [],
            "summary": {},
        }


def run_mvp_algorithms(snapshot: dict[str, Any], scenario: dict[str, Any] | None = None) -> dict[str, Any]:
    snapshot_id = snapshot.get("snapshot", {}).get("snapshot_id")
    runs = [run_algorithm(code, snapshot, scenario=scenario, snapshot_id=snapshot_id) for code in ALGORITHM_CODES]
    results = [result for run in runs for result in run["results"]]
    return {
        "ok": all(run["ok"] for run in runs),
        "snapshot_id": snapshot_id,
        "runs": runs,
        "results": results,
        "counts": {
            "algorithm_runs": len(runs),
            "algorithm_results": len(results),
            "shortage_results": sum(1 for result in results if result["result_type"] == "SHORTAGE_RISK"),
            "cash_release_results": sum(1 for result in results if result["result_type"] == "CASH_RELEASE_ACTION"),
            "master_data_results": sum(1 for result in results if result["result_type"] == "MASTER_DATA_ISSUE"),
        },
    }
