from __future__ import annotations

from typing import Any

REQUIRED_SECTIONS: dict[str, set[str]] = {
    "materials": {"material_code", "material_name", "plant", "material_group", "product_line", "abc_class", "xyz_class", "unit_price", "is_protected"},
    "inventory": {"material_code", "plant", "unrestricted_qty", "quality_qty", "blocked_qty", "safety_stock", "snapshot_date"},
    "pr_lines": {"pr_no", "pr_item", "material_code", "plant", "supplier", "open_qty", "delivery_date", "unit_price", "status", "purchasing_group"},
    "po_lines": {"po_no", "po_item", "material_code", "plant", "supplier", "open_qty", "delivery_date", "confirmed_flag", "unit_price", "status"},
    "bom_components": {"finished_good", "component_material", "plant", "usage_qty", "valid_from", "alternative_group"},
    "planned_demands": {"demand_id", "material_code", "plant", "demand_date", "demand_qty", "source_type", "production_order", "finished_good"},
    "consumption_history": {"material_code", "plant", "posting_date", "actual_consumption_qty"},
    "supplier_performance": {"supplier", "material_code", "plant", "po_create_date", "planned_delivery_date", "actual_gr_date", "delivered_qty", "ordered_qty", "quality_issue_flag"},
    "mrp_parameters": {"material_code", "plant", "planned_delivery_time", "safety_stock", "moq", "mpq", "lot_size_rule", "mrp_controller"},
}


def validate_mock_sap_snapshot(data: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    counts: dict[str, int] = {}
    if not isinstance(data.get("snapshot"), dict) or not data["snapshot"].get("snapshot_id"):
        errors.append("snapshot.snapshot_id is required.")
    for section, required in REQUIRED_SECTIONS.items():
        rows = data.get(section)
        if not isinstance(rows, list):
            errors.append(f"{section} must be a list.")
            counts[section] = 0
            continue
        counts[section] = len(rows)
        for index, row in enumerate(rows, start=1):
            missing = sorted(field for field in required if row.get(field) in (None, ""))
            if missing:
                errors.append(f"{section}[{index}] missing fields: {', '.join(missing)}")
    return {"ok": not errors, "errors": errors, "counts": counts}


def snapshot_counts(data: dict[str, Any]) -> dict[str, int]:
    return {section: len(data.get(section, [])) for section in REQUIRED_SECTIONS}
