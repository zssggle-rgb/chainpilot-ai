from __future__ import annotations

from dataclasses import dataclass
from typing import Any

MOCK_ENDPOINTS: dict[str, list[dict[str, Any]]] = {
    "purchase_requisition_items": [
        {
            "sap_object_type": "PR",
            "sap_doc_no": "1000123456",
            "sap_item_no": "00010",
            "material_code": "MAT-000001",
            "plant": "CN01",
            "open_qty": 12000,
            "requested_date": "2026-06-15",
            "supplier": "S000982",
        },
        {
            "sap_object_type": "PR",
            "sap_doc_no": "1000123459",
            "sap_item_no": "00030",
            "material_code": "MAT-000006",
            "plant": "CN01",
            "open_qty": 22000,
            "requested_date": "2026-06-28",
            "supplier": "S000551",
        },
    ],
    "purchase_order_items": [
        {
            "sap_object_type": "PO",
            "sap_doc_no": "4500098765",
            "sap_item_no": "00010",
            "material_code": "MAT-000003",
            "plant": "CN01",
            "confirmed": False,
            "delivery_date": "2026-06-12",
            "supplier": "S000219",
        }
    ],
    "inventory_snapshots": [
        {
            "material_code": "MAT-000001",
            "plant": "CN01",
            "inventory_days": 48,
            "safety_threshold_days": 28,
            "source_snapshot": "SAP_INVENTORY_CN01_MAT-000001",
        },
        {
            "material_code": "MAT-000006",
            "plant": "CN01",
            "inventory_days": 50,
            "safety_threshold_days": 28,
            "source_snapshot": "SAP_INVENTORY_CN01_MAT-000006",
        },
    ],
}


@dataclass(frozen=True)
class SAPEndpointConfig:
    endpoint_name: str
    entity_set: str
    target_doctype: str
    key_fields: tuple[str, ...]


def test_connection(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return an explicit read-only SAP connection status.

    The MVP can run in mock mode before a customer SAP OData destination is configured.
    """
    if not config:
        return {"ok": False, "status": "NOT_CONFIGURED", "message": "SAP connection is not configured."}
    if config.get("mode") == "mock":
        return {"ok": True, "status": "MOCK_READY", "message": "Using ChainPilot mock SAP read adapter."}
    return {"ok": False, "status": "DRY_RUN", "message": "Phase 0 does not contact SAP."}


def get_entity_set(endpoint_name: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Read a named SAP entity set.

    Until M2 receives real SAP credentials, `params={"mode": "mock"}` returns deterministic mock rows
    that match the imported demo recommendations. Production SAP writes are intentionally unsupported.
    """
    params = params or {}
    if params.get("mode") != "mock":
        return []
    rows = MOCK_ENDPOINTS.get(endpoint_name, [])
    filters = {key: value for key, value in params.items() if key != "mode"}
    if not filters:
        return [row.copy() for row in rows]
    return [row.copy() for row in rows if all(row.get(key) == value for key, value in filters.items())]


def sync_endpoint(endpoint_name: str) -> dict[str, Any]:
    """Phase 0 placeholder that keeps SAP sync explicit and non-writing."""
    return {"endpoint_name": endpoint_name, "status": "NOT_RUN", "synced": 0}


def upsert_snapshot(target_doctype: str, row: dict[str, Any], key_fields: list[str]) -> str:
    """Build the deterministic key that a Frappe upsert will use in M2."""
    missing = [field for field in key_fields if field not in row]
    if missing:
        raise ValueError(f"Missing key fields for snapshot upsert: {', '.join(missing)}")
    return "::".join(str(row[field]) for field in key_fields)
