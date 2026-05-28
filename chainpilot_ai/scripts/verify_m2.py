from __future__ import annotations

import json
from pathlib import Path

from chainpilot_ai.sap_connector.service import (
    DEFAULT_ENDPOINTS,
    get_entity_set,
    run_mock_sync,
    sync_endpoint,
    test_connection,
    upsert_snapshot,
)

ROOT = Path(__file__).resolve().parents[2]

M2_DOCTYPE_FILES = [
    "sap_connection/sap_connection.json",
    "sap_endpoint/sap_endpoint.json",
    "sap_field_mapping/sap_field_mapping.json",
    "sap_sync_job/sap_sync_job.json",
    "sap_api_log/sap_api_log.json",
    "sap_material_snapshot/sap_material_snapshot.json",
    "sap_inventory_snapshot/sap_inventory_snapshot.json",
    "sap_pr_line/sap_pr_line.json",
    "sap_po_line/sap_po_line.json",
]


def _status(status: str, evidence: str, notes: str = "") -> dict[str, str]:
    return {"status": status, "evidence": evidence, "notes": notes}


def check_m2_doctype_contract() -> dict[str, str]:
    base = ROOT / "chainpilot_ai" / "chainpilot_ai" / "doctype"
    missing = []
    invalid = []
    for relative in M2_DOCTYPE_FILES:
        path = base / relative
        if not path.exists():
            missing.append(relative)
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("doctype") != "DocType" or not data.get("fields"):
            invalid.append(relative)
    if missing or invalid:
        return _status("Fail", str(base), json.dumps({"missing": missing, "invalid": invalid}, ensure_ascii=False))
    return _status("Pass", str(base), f"{len(M2_DOCTYPE_FILES)} M2 DocType JSON files")


def check_m2_adapter_contract() -> dict[str, str]:
    connection = test_connection({"mode": "mock"})
    materials = get_entity_set("material_master", {"mode": "mock", "plant": "CN01"})
    dry_run = sync_endpoint("purchase_requisition_items", {"mode": "mock", "dry_run": True})
    all_sync = run_mock_sync("all")
    if connection["ok"] and materials and dry_run["rows_upserted"] == 2 and all_sync["rows_upserted"] >= 7:
        return _status(
            "Pass",
            "chainpilot_ai.sap_connector.service",
            json.dumps(
                {
                    "endpoints": list(DEFAULT_ENDPOINTS),
                    "dry_run_pr_rows": dry_run["rows_upserted"],
                    "all_rows": all_sync["rows_upserted"],
                },
                ensure_ascii=False,
            ),
        )
    return _status("Fail", "chainpilot_ai.sap_connector.service", json.dumps({"connection": connection, "materials": materials, "dry_run": dry_run, "all_sync": all_sync}, ensure_ascii=False))


def check_m2_console_assets() -> dict[str, str]:
    page_js = ROOT / "chainpilot_ai" / "chainpilot_ai" / "page" / "sap_integration_console" / "sap_integration_console.js"
    workspace = ROOT / "chainpilot_ai" / "fixtures" / "workspace.json"
    page_text = page_js.read_text(encoding="utf-8") if page_js.exists() else ""
    workspace_text = workspace.read_text(encoding="utf-8")
    required = ["SAP 连接", "run_mock_sync", "快照覆盖", "接口配置"]
    if all(token in page_text for token in required) and "sap-integration-console" in workspace_text:
        return _status("Pass", f"{page_js}; {workspace}", "")
    return _status("Fail", f"{page_js}; {workspace}", "M2 console route or core copy missing.")


def check_m2_snapshot_key_contract() -> dict[str, str]:
    key = upsert_snapshot("SAP PR Line", {"purchase_requisition": "1000123456", "purchase_requisition_item": "00010"}, ["purchase_requisition", "purchase_requisition_item"])
    try:
        upsert_snapshot("SAP PR Line", {"purchase_requisition": "1000123456"}, ["purchase_requisition", "purchase_requisition_item"])
    except ValueError as exc:
        if key == "1000123456::00010" and "purchase_requisition_item" in str(exc):
            return _status("Pass", "snapshot upsert key", key)
    return _status("Fail", "snapshot upsert key", key)


CHECKS = {
    "M2-SAP-001": check_m2_doctype_contract,
    "M2-SAP-002": check_m2_adapter_contract,
    "M2-SAP-003": check_m2_console_assets,
    "M2-SAP-004": check_m2_snapshot_key_contract,
}


def run() -> dict[str, object]:
    results = {name: check() for name, check in CHECKS.items()}
    counts: dict[str, int] = {}
    for result in results.values():
        counts[result["status"]] = counts.get(result["status"], 0) + 1
    return {"ok": counts.get("Fail", 0) == 0, "counts": counts, "results": results}


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
