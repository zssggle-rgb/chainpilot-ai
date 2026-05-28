from __future__ import annotations

import json
from pathlib import Path

from chainpilot_ai.approval.service import build_approval_summary, dry_run_package
from chainpilot_ai.writeback.service import build_supplier_communication, build_writeback_draft

ROOT = Path(__file__).resolve().parents[2]

M4_DOCTYPE_FILES = [
    "approval_package/approval_package.json",
    "approval_task/approval_task.json",
    "sap_writeback_draft/sap_writeback_draft.json",
    "execution_result/execution_result.json",
    "feedback_record/feedback_record.json",
    "learning_signal/learning_signal.json",
    "supplier_communication_draft/supplier_communication_draft.json",
]


def _status(status: str, evidence: str, notes: str = "") -> dict[str, str]:
    return {"status": status, "evidence": evidence, "notes": notes}


def check_m4_doctype_contract() -> dict[str, str]:
    base = ROOT / "chainpilot_ai" / "chainpilot_ai" / "doctype"
    missing = [relative for relative in M4_DOCTYPE_FILES if not (base / relative).exists()]
    if missing:
        return _status("Fail", str(base), json.dumps({"missing": missing}, ensure_ascii=False))
    for relative in M4_DOCTYPE_FILES:
        payload = json.loads((base / relative).read_text(encoding="utf-8"))
        if payload.get("doctype") != "DocType" or not payload.get("fields"):
            return _status("Fail", str(base / relative), "Invalid DocType JSON.")
    return _status("Pass", str(base), f"{len(M4_DOCTYPE_FILES)} M4 DocType JSON files")


def check_m4_approval_summary() -> dict[str, str]:
    package = dry_run_package(5)
    if package["recommendation_count"] == 5 and package["total_cash_release"] > 0 and "approval_summary" in package:
        return _status("Pass", "chainpilot_ai.approval.service.dry_run_package", json.dumps(package, ensure_ascii=False))
    return _status("Fail", "chainpilot_ai.approval.service.dry_run_package", json.dumps(package, ensure_ascii=False))


def check_m4_writeback_guardrail() -> dict[str, str]:
    pending = {
        "approval_status": "Pending",
        "recommendation_id": "REC-X",
        "sap_object_type": "PR",
        "sap_doc_no": "100",
        "sap_item_no": "10",
        "action_type": "REDUCE_PR_QTY",
        "before_qty": 10,
        "after_qty": 7,
    }
    try:
        build_writeback_draft(pending, "APKG-X")
    except ValueError as exc:
        if "Approved" in str(exc):
            approved = {**pending, "approval_status": "Approved"}
            draft = build_writeback_draft(approved, "APKG-X")
            if draft["safety_mode"] == "DRAFT_ONLY" and draft["status"] == "Ready" and draft["conflict_status"] == "Match":
                return _status("Pass", "chainpilot_ai.writeback.service.build_writeback_draft", json.dumps({"draft_status": draft["status"], "safety_mode": draft["safety_mode"]}, ensure_ascii=False))
    return _status("Fail", "chainpilot_ai.writeback.service.build_writeback_draft", "Pending recommendation was not blocked or approved draft invalid.")


def check_m4_supplier_draft() -> dict[str, str]:
    rec = {
        "recommendation_id": "REC-PO",
        "sap_object_type": "PO",
        "sap_doc_no": "4500001",
        "sap_item_no": "10",
        "action_type": "DELAY_UNCONFIRMED_PO",
        "material_code": "MAT-1",
        "supplier": "S0001",
        "before_date": "2026-06-01",
        "after_date": "2026-06-15",
    }
    draft = build_supplier_communication(rec, "APKG-X")
    if draft and draft["status"] == "Draft" and "not sent automatically" in draft["message"]:
        return _status("Pass", "chainpilot_ai.writeback.service.build_supplier_communication", draft["communication_id"])
    return _status("Fail", "chainpilot_ai.writeback.service.build_supplier_communication", json.dumps(draft, ensure_ascii=False))


def check_m4_console_assets() -> dict[str, str]:
    page_js = ROOT / "chainpilot_ai" / "chainpilot_ai" / "page" / "execution_monitor" / "execution_monitor.js"
    workspace = ROOT / "chainpilot_ai" / "fixtures" / "workspace.json"
    text = page_js.read_text(encoding="utf-8") if page_js.exists() else ""
    required = ["Execution Monitor", "create_approval_package_rpc", "approve_package_rpc", "SAP Writeback Draft", "Learning Signal"]
    if all(token in text for token in required) and "execution-monitor" in workspace.read_text(encoding="utf-8"):
        return _status("Pass", f"{page_js}; {workspace}", "")
    return _status("Fail", f"{page_js}; {workspace}", "M4 Execution Monitor route or core actions missing.")


CHECKS = {
    "M4-APPROVAL-001": check_m4_doctype_contract,
    "M4-APPROVAL-002": check_m4_approval_summary,
    "M4-WRITEBACK-001": check_m4_writeback_guardrail,
    "M4-SUPPLIER-001": check_m4_supplier_draft,
    "M4-MONITOR-001": check_m4_console_assets,
}


def run() -> dict[str, object]:
    results = {name: check() for name, check in CHECKS.items()}
    counts: dict[str, int] = {}
    for result in results.values():
        counts[result["status"]] = counts.get(result["status"], 0) + 1
    return {"ok": counts.get("Fail", 0) == 0, "counts": counts, "results": results}


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
