from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DEMO_PATH = ROOT / "demo_data" / "phase0_demo.json"
LOCAL_IMPORT_SUMMARY_PATH = ROOT / "tmp" / "phase0_demo_import_summary.json"

REQUIRED_FIELDS: dict[str, set[str]] = {
    "optimization_sessions": {
        "session_id",
        "source_system",
        "source_report",
        "baseline_amount",
        "material_count",
        "sample_count",
        "best_solution_count",
        "run_date",
        "status",
    },
    "scenario_results": {
        "result_id",
        "session_id",
        "strategy_name",
        "strategy_type",
        "purchase_amount",
        "cash_release",
        "cash_release_rate",
        "risk_level",
        "recommendation_count",
    },
    "recommendations": {
        "recommendation_id",
        "result_id",
        "action_type",
        "sap_object_type",
        "sap_doc_no",
        "sap_item_no",
        "material_code",
        "plant",
        "cash_release",
        "saving_type",
        "approval_status",
        "writeback_status",
        "explanation_status",
    },
    "evidence": {
        "evidence_id",
        "recommendation_id",
        "source_type",
        "source_id",
        "metric_name",
        "metric_value",
        "verdict",
        "summary",
    },
    "constraint_checks": {
        "check_id",
        "recommendation_id",
        "rule_code",
        "verdict",
        "message",
    },
}

DOCTYPE_MAP = {
    "optimization_sessions": "Optimization Session",
    "scenario_results": "Scenario Result",
    "recommendations": "Recommendation",
    "evidence": "Recommendation Evidence",
    "constraint_checks": "Constraint Check Result",
}


def load_demo_data(path: str | Path | None = None) -> dict[str, Any]:
    demo_path = Path(path) if path else DEFAULT_DEMO_PATH
    with demo_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_demo_data(data: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    counts: dict[str, int] = {}

    for section, required_fields in REQUIRED_FIELDS.items():
        rows = data.get(section)
        if not isinstance(rows, list):
            errors.append(f"{section} must be a list.")
            counts[section] = 0
            continue
        counts[section] = len(rows)
        for index, row in enumerate(rows, start=1):
            missing = sorted(field for field in required_fields if row.get(field) in (None, ""))
            if missing:
                errors.append(f"{section}[{index}] missing required fields: {', '.join(missing)}")

    session_ids = {row["session_id"] for row in data.get("optimization_sessions", []) if row.get("session_id")}
    result_ids = {row["result_id"] for row in data.get("scenario_results", []) if row.get("result_id")}
    recommendation_ids = {row["recommendation_id"] for row in data.get("recommendations", []) if row.get("recommendation_id")}
    evidence_by_recommendation: dict[str, list[str]] = {}

    for result in data.get("scenario_results", []):
        if result.get("session_id") not in session_ids:
            errors.append(f"Scenario Result {result.get('result_id')} references missing session_id {result.get('session_id')}.")

    for recommendation in data.get("recommendations", []):
        if recommendation.get("result_id") not in result_ids:
            errors.append(
                f"Recommendation {recommendation.get('recommendation_id')} references missing result_id {recommendation.get('result_id')}."
            )

    for evidence in data.get("evidence", []):
        recommendation_id = evidence.get("recommendation_id")
        if recommendation_id not in recommendation_ids:
            errors.append(f"Evidence {evidence.get('evidence_id')} references missing recommendation_id {recommendation_id}.")
        evidence_by_recommendation.setdefault(recommendation_id, []).append(evidence.get("evidence_id", ""))

    evidence_ids = {row["evidence_id"] for row in data.get("evidence", []) if row.get("evidence_id")}
    for check in data.get("constraint_checks", []):
        recommendation_id = check.get("recommendation_id")
        if recommendation_id not in recommendation_ids:
            errors.append(f"Constraint Check {check.get('check_id')} references missing recommendation_id {recommendation_id}.")
        if check.get("evidence_id") and check.get("evidence_id") not in evidence_ids:
            errors.append(f"Constraint Check {check.get('check_id')} references missing evidence_id {check.get('evidence_id')}.")

    for recommendation in data.get("recommendations", []):
        recommendation_id = recommendation.get("recommendation_id")
        if recommendation.get("explanation_status") == "Ready" and not evidence_by_recommendation.get(recommendation_id):
            errors.append(f"Recommendation {recommendation_id} is Ready but has no Evidence.")

    return {"ok": not errors, "counts": counts, "errors": errors}


def _insert_with_frappe(data: dict[str, Any]) -> dict[str, Any]:
    import frappe  # type: ignore

    inserted = 0
    updated = 0
    for section, doctype in DOCTYPE_MAP.items():
        for row in data.get(section, []):
            name_field = {
                "optimization_sessions": "session_id",
                "scenario_results": "result_id",
                "recommendations": "recommendation_id",
                "evidence": "evidence_id",
                "constraint_checks": "check_id",
            }[section]
            doc_name = row[name_field]
            if frappe.db.exists(doctype, doc_name):
                doc = frappe.get_doc(doctype, doc_name)
                doc.update(row)
                doc.save(ignore_permissions=True)
                updated += 1
            else:
                doc = frappe.get_doc({"doctype": doctype, **row})
                doc.insert(ignore_permissions=True)
                inserted += 1
    frappe.db.commit()
    return {"mode": "frappe", "inserted": inserted, "updated": updated}


def _write_local_summary(data: dict[str, Any], validation: dict[str, Any]) -> dict[str, Any]:
    LOCAL_IMPORT_SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    summary = {
        "mode": "local_contract_validation",
        "ok": validation["ok"],
        "counts": validation["counts"],
        "errors": validation["errors"],
        "demo_path": str(DEFAULT_DEMO_PATH),
    }
    with LOCAL_IMPORT_SUMMARY_PATH.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    return summary


def run(demo_path: str | None = None) -> dict[str, Any]:
    data = load_demo_data(demo_path)
    validation = validate_demo_data(data)
    if not validation["ok"]:
        return _write_local_summary(data, validation)

    try:
        import frappe  # noqa: F401
    except ModuleNotFoundError:
        return _write_local_summary(data, validation)

    try:
        result = _insert_with_frappe(data)
    except Exception as exc:  # Frappe may be importable outside a site context.
        summary = _write_local_summary(data, validation)
        summary["frappe_import_error"] = str(exc)
        return summary

    result["ok"] = True
    result["counts"] = validation["counts"]
    return result


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
