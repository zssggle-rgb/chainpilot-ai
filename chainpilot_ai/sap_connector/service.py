from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SAPEndpointConfig:
    endpoint_name: str
    entity_set: str
    target_doctype: str
    key_fields: tuple[str, ...]


def test_connection(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a safe Phase 0 placeholder connection result."""
    if not config:
        return {"ok": False, "status": "NOT_CONFIGURED", "message": "SAP connection is not configured."}
    return {"ok": False, "status": "DRY_RUN", "message": "Phase 0 does not contact SAP."}


def get_entity_set(endpoint_name: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    """Phase 0 placeholder for the future pyodata read path."""
    return []


def sync_endpoint(endpoint_name: str) -> dict[str, Any]:
    """Phase 0 placeholder that keeps SAP sync explicit and non-writing."""
    return {"endpoint_name": endpoint_name, "status": "NOT_RUN", "synced": 0}


def upsert_snapshot(target_doctype: str, row: dict[str, Any], key_fields: list[str]) -> str:
    """Build the deterministic key that a Frappe upsert will use in M2."""
    missing = [field for field in key_fields if field not in row]
    if missing:
        raise ValueError(f"Missing key fields for snapshot upsert: {', '.join(missing)}")
    return "::".join(str(row[field]) for field in key_fields)
