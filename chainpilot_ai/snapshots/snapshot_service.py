from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from chainpilot_ai.snapshots.validators import snapshot_counts, validate_mock_sap_snapshot

try:
    import frappe
except Exception:  # pragma: no cover - local tests run without a Frappe site.
    frappe = None


def _frappe_ready() -> bool:
    try:
        return bool(frappe and getattr(frappe.local, "site", None) and getattr(frappe, "db", None))
    except Exception:
        return False


def _now() -> str:
    if _frappe_ready():
        return str(frappe.utils.now_datetime())
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def build_snapshot_run(data: dict[str, Any]) -> dict[str, Any]:
    validation = validate_mock_sap_snapshot(data)
    if not validation["ok"]:
        raise ValueError("; ".join(validation["errors"]))
    snapshot = data["snapshot"]
    counts = snapshot_counts(data)
    return {
        "snapshot_id": snapshot["snapshot_id"],
        "source_type": snapshot.get("source_type") or "Mock",
        "source_system": snapshot.get("source_system") or "SAP_MOCK",
        "plant_scope": snapshot.get("plant_scope") or "",
        "material_scope": snapshot.get("material_scope") or "",
        "snapshot_time": snapshot.get("snapshot_time") or _now(),
        "status": "Verified",
        "record_count_materials": counts["materials"],
        "record_count_inventory": counts["inventory"],
        "record_count_pr_lines": counts["pr_lines"],
        "record_count_po_lines": counts["po_lines"],
        "record_count_bom_components": counts["bom_components"],
        "record_count_planned_demands": counts["planned_demands"],
        "record_count_consumption_history": counts["consumption_history"],
        "record_count_supplier_performance": counts["supplier_performance"],
        "record_count_mrp_parameters": counts["mrp_parameters"],
        "raw_summary_json": json.dumps(counts, ensure_ascii=False, sort_keys=True),
    }


def import_mock_snapshot(data: dict[str, Any], dry_run: bool = False) -> dict[str, Any]:
    run_doc = build_snapshot_run(data)
    detail_docs = build_snapshot_detail_docs(data, run_doc["snapshot_id"])
    if _frappe_ready() and not dry_run:
        _insert_doc("SAP Snapshot Run", "snapshot_id", run_doc)
        for doctype, rows in detail_docs.items():
            key_field = _key_field_for_doctype(doctype)
            for row in rows:
                _insert_doc(doctype, key_field, row)
        frappe.db.commit()
    return {
        "ok": True,
        "snapshot": run_doc,
        "details": detail_docs,
        "counts": {"SAP Snapshot Run": 1, **{doctype: len(rows) for doctype, rows in detail_docs.items()}},
    }


def build_snapshot_detail_docs(data: dict[str, Any], snapshot_id: str) -> dict[str, list[dict[str, Any]]]:
    now = _now()
    return {
        "SAP Material Snapshot": [
            {
                "snapshot_id": _line_id(snapshot_id, "MAT", row["material_code"], row["plant"]),
                "snapshot_run": snapshot_id,
                "source_system": data["snapshot"].get("source_system") or "SAP_MOCK",
                "last_synced_at": now,
                **row,
            }
            for row in data["materials"]
        ],
        "SAP Inventory Snapshot": [
            {
                "snapshot_id": _line_id(snapshot_id, "INV", row["material_code"], row["plant"], row.get("storage_location", "1000")),
                "snapshot_run": snapshot_id,
                "available_stock": row["unrestricted_qty"],
                "safety_threshold_days": 28,
                "source_snapshot": snapshot_id,
                "last_synced_at": now,
                **row,
            }
            for row in data["inventory"]
        ],
        "SAP PR Line": [
            {
                "snapshot_id": _line_id(snapshot_id, "PR", row["pr_no"], row["pr_item"]),
                "snapshot_run": snapshot_id,
                "purchase_requisition": row["pr_no"],
                "purchase_requisition_item": row["pr_item"],
                "requested_quantity": row["open_qty"],
                "last_synced_at": now,
                **row,
            }
            for row in data["pr_lines"]
        ],
        "SAP PO Line": [
            {
                "snapshot_id": _line_id(snapshot_id, "PO", row["po_no"], row["po_item"]),
                "snapshot_run": snapshot_id,
                "purchase_order": row["po_no"],
                "purchase_order_item": row["po_item"],
                "order_quantity": row["open_qty"],
                "confirmation_status": "Confirmed" if row.get("confirmed_flag") else "Unconfirmed",
                "last_synced_at": now,
                **row,
            }
            for row in data["po_lines"]
        ],
        "SAP BOM Component Snapshot": [
            {"snapshot_line_id": _line_id(snapshot_id, "BOM", row["finished_good"], row["component_material"]), "snapshot_run": snapshot_id, "last_synced_at": now, **row}
            for row in data["bom_components"]
        ],
        "SAP Planned Demand Snapshot": [
            {"snapshot_run": snapshot_id, "last_synced_at": now, **row}
            for row in data["planned_demands"]
        ],
        "SAP Consumption History Snapshot": [
            {"history_id": _line_id(snapshot_id, "CONS", row["material_code"], row["posting_date"]), "snapshot_run": snapshot_id, "last_synced_at": now, **row}
            for row in data["consumption_history"]
        ],
        "SAP Supplier Performance Snapshot": [
            {
                "performance_id": _line_id(snapshot_id, "SUP", row["supplier"], row["material_code"], row["actual_gr_date"]),
                "snapshot_run": snapshot_id,
                "last_synced_at": now,
                **row,
            }
            for row in data["supplier_performance"]
        ],
        "SAP MRP Parameter Snapshot": [
            {"parameter_id": _line_id(snapshot_id, "MRP", row["material_code"], row["plant"]), "snapshot_run": snapshot_id, "last_synced_at": now, **row}
            for row in data["mrp_parameters"]
        ],
    }


def _line_id(*parts: object) -> str:
    return "-".join(str(part).replace("/", "-").replace(" ", "-") for part in parts if part not in (None, ""))


def _key_field_for_doctype(doctype: str) -> str:
    return {
        "SAP Snapshot Run": "snapshot_id",
        "SAP Material Snapshot": "snapshot_id",
        "SAP Inventory Snapshot": "snapshot_id",
        "SAP PR Line": "snapshot_id",
        "SAP PO Line": "snapshot_id",
        "SAP BOM Component Snapshot": "snapshot_line_id",
        "SAP Planned Demand Snapshot": "demand_id",
        "SAP Consumption History Snapshot": "history_id",
        "SAP Supplier Performance Snapshot": "performance_id",
        "SAP MRP Parameter Snapshot": "parameter_id",
    }[doctype]


def _insert_doc(doctype: str, key_field: str, payload: dict[str, Any]) -> str:
    existing = frappe.db.exists(doctype, payload[key_field])
    if existing:
        doc = frappe.get_doc(doctype, existing)
        doc.update(payload)
        doc.save(ignore_permissions=True)
        return doc.name
    doc = frappe.get_doc({"doctype": doctype, **payload})
    doc.insert(ignore_permissions=True)
    return doc.name
