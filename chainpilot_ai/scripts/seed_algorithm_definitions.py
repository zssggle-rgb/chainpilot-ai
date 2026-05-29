from __future__ import annotations

import json
from typing import Any

from chainpilot_ai.algorithms.schemas import algorithm_definitions

try:
    import frappe
except Exception:  # pragma: no cover - local tests run without a Frappe site.
    frappe = None


def _frappe_ready() -> bool:
    try:
        return bool(frappe and getattr(frappe.local, "site", None) and getattr(frappe, "db", None))
    except Exception:
        return False


def run(dry_run: bool = False) -> dict[str, Any]:
    definitions = algorithm_definitions()
    if _frappe_ready() and not dry_run:
        for definition in definitions:
            payload = dict(definition)
            payload["input_schema_json"] = json.dumps(payload["input_schema_json"], ensure_ascii=False, sort_keys=True)
            payload["output_schema_json"] = json.dumps(payload["output_schema_json"], ensure_ascii=False, sort_keys=True)
            _insert_doc("Algorithm Definition", "algorithm_code", payload)
        frappe.db.commit()
    return {"ok": True, "definitions": definitions, "count": len(definitions)}


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


if __name__ == "__main__":
    print(json.dumps(run(dry_run=True), ensure_ascii=False, indent=2, default=str))
