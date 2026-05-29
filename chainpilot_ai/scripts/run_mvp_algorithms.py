from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from chainpilot_ai.algorithms.registry import run_mvp_algorithms as run_algorithms
from chainpilot_ai.recommendation.result_to_recommendation import convert_algorithm_results
from chainpilot_ai.scripts.seed_algorithm_definitions import run as seed_algorithm_definitions
from chainpilot_ai.snapshots.mock_loader import load_mock_sap_snapshot
from chainpilot_ai.snapshots.snapshot_service import import_mock_snapshot

try:
    import frappe
except Exception:  # pragma: no cover - local tests run without a Frappe site.
    frappe = None

ROOT = Path(__file__).resolve().parents[2]
LOCAL_RUNTIME_SUMMARY_PATH = ROOT / "tmp" / "algorithm_runtime_summary.json"


def _frappe_ready() -> bool:
    try:
        return bool(frappe and getattr(frappe.local, "site", None) and getattr(frappe, "db", None))
    except Exception:
        return False


def run(dry_run: bool = False) -> dict[str, Any]:
    snapshot = load_mock_sap_snapshot()
    snapshot_import = import_mock_snapshot(snapshot, dry_run=dry_run)
    seed_algorithm_definitions(dry_run=dry_run)
    runtime = run_algorithms(snapshot)
    generated = convert_algorithm_results(runtime)
    if _frappe_ready() and not dry_run:
        _persist_runtime(runtime, generated)
        frappe.db.commit()
    result = {
        "ok": runtime["ok"],
        "snapshot": snapshot_import["snapshot"],
        "runtime_counts": runtime["counts"],
        "recommendation_counts": {key: len(value) for key, value in generated.items()},
        "runs": [item["run"] for item in runtime["runs"]],
        "generated": generated,
    }
    LOCAL_RUNTIME_SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_RUNTIME_SUMMARY_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return result


def _persist_runtime(runtime: dict[str, Any], generated: dict[str, list[dict[str, Any]]]) -> None:
    for run_result in runtime["runs"]:
        _insert_doc("Algorithm Run", "algorithm_run_id", run_result["run"])
        for result in run_result["results"]:
            payload = {key: value for key, value in result.items() if key != "raw"}
            _insert_doc("Algorithm Result", "result_id", payload)
    for row in generated["recommendations"]:
        _insert_doc("Recommendation", "recommendation_id", row)
    for row in generated["evidence"]:
        _insert_doc("Recommendation Evidence", "evidence_id", row)
    for row in generated["checks"]:
        _insert_doc("Constraint Check Result", "check_id", row)
    for row in generated["explanations"]:
        _insert_doc("AI Explanation", "explanation_id", row)


def _insert_doc(doctype: str, key_field: str, payload: dict[str, Any]) -> str:
    clean_payload = {key: value for key, value in payload.items() if value is not None}
    existing = frappe.db.exists(doctype, clean_payload[key_field])
    if existing:
        doc = frappe.get_doc(doctype, existing)
        doc.update(clean_payload)
        doc.save(ignore_permissions=True)
        return doc.name
    doc = frappe.get_doc({"doctype": doctype, **clean_payload})
    doc.insert(ignore_permissions=True)
    return doc.name


if __name__ == "__main__":
    print(json.dumps(run(dry_run=True), ensure_ascii=False, indent=2, default=str))
