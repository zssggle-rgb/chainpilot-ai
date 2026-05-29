from __future__ import annotations

import copy
import random
from datetime import date, datetime, timedelta
from typing import Any

from chainpilot_ai.snapshots.mock_loader import load_mock_sap_snapshot


DATE_FIELDS = {
    "snapshot_time",
    "delivery_date",
    "demand_date",
    "planned_delivery_date",
    "actual_gr_date",
    "po_create_date",
    "posting_date",
    "consumption_date",
}


def generate_mock_history(history_days: int = 120, sample_interval_days: int = 14) -> list[dict[str, Any]]:
    base = load_mock_sap_snapshot()
    base_date = _snapshot_date(base)
    points = max(4, min(18, history_days // max(1, sample_interval_days)))
    start = base_date - timedelta(days=history_days)
    snapshots = []
    for index in range(points):
        snapshot_date = start + timedelta(days=index * sample_interval_days)
        snapshots.append(_shift_snapshot(base, snapshot_date, index))
    return snapshots


def _shift_snapshot(base: dict[str, Any], snapshot_date: date, index: int) -> dict[str, Any]:
    shifted = copy.deepcopy(base)
    base_date = _snapshot_date(base)
    delta_days = (snapshot_date - base_date).days
    snapshot_id = f"SNAP-MOCK-HIST-{snapshot_date.strftime('%Y%m%d')}"
    shifted["snapshot"]["snapshot_id"] = snapshot_id
    shifted["snapshot"]["snapshot_time"] = snapshot_date.isoformat()
    shifted["snapshot"]["source_system"] = "SAP_MOCK_HISTORY"
    _shift_dates(shifted, delta_days)
    _perturb_quantities(shifted, index)
    shifted["_actual_outcomes"] = _actual_outcomes(shifted, snapshot_date)
    return shifted


def _shift_dates(value: Any, delta_days: int) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            if key in DATE_FIELDS and isinstance(item, str):
                value[key] = _shift_date_value(item, delta_days)
            else:
                _shift_dates(item, delta_days)
    elif isinstance(value, list):
        for item in value:
            _shift_dates(item, delta_days)


def _shift_date_value(value: str, delta_days: int) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace(" ", "T"))
    except ValueError:
        return value
    shifted = parsed + timedelta(days=delta_days)
    return shifted.date().isoformat() if "T" not in value and " " not in value else shifted.strftime("%Y-%m-%d %H:%M:%S")


def _perturb_quantities(snapshot: dict[str, Any], index: int) -> None:
    rng = random.Random(4100 + index)
    material_stress = {f"MAT-{number:06d}": 0.68 + 0.08 * ((index + number) % 3) for number in range(1, 6)}
    material_surplus = {f"MAT-{number:06d}": 1.25 + 0.1 * ((index + number) % 2) for number in range(6, 11)}
    for row in snapshot.get("inventory", []):
        material = row["material_code"]
        factor = material_stress.get(material) or material_surplus.get(material) or 1.0
        row["unrestricted_qty"] = round(float(row.get("unrestricted_qty") or 0) * factor * rng.uniform(0.92, 1.08), 2)
        row["available_stock"] = row["unrestricted_qty"]
    for row in snapshot.get("planned_demands", []):
        material = row["material_code"]
        factor = 1.18 if material in material_stress else 0.92 if material in material_surplus else 1.0
        row["demand_qty"] = round(float(row.get("demand_qty") or 0) * factor * rng.uniform(0.88, 1.12), 2)
    for row in snapshot.get("supplier_performance", []):
        if row.get("material_code") in material_stress and index % 3 == 1:
            actual = datetime.fromisoformat(row["actual_gr_date"]).date() + timedelta(days=3)
            row["actual_gr_date"] = actual.isoformat()


def _actual_outcomes(snapshot: dict[str, Any], snapshot_date: date) -> dict[str, Any]:
    shortages = []
    inventory = {(row["material_code"], row["plant"]): row for row in snapshot.get("inventory", [])}
    mrp = {(row["material_code"], row["plant"]): row for row in snapshot.get("mrp_parameters", [])}
    for key, inv in inventory.items():
        material, plant = key
        demand_14 = sum(
            float(row.get("demand_qty") or 0)
            for row in snapshot.get("planned_demands", [])
            if row["material_code"] == material and row["plant"] == plant and 0 <= (_date(row["demand_date"]) - snapshot_date).days <= 14
        )
        inbound_14 = sum(
            float(row.get("open_qty") or 0)
            for row in snapshot.get("po_lines", [])
            if row["material_code"] == material and row["plant"] == plant and 0 <= (_date(row["delivery_date"]) - snapshot_date).days <= 14
        )
        safety = float(mrp.get(key, {}).get("safety_stock") or inv.get("safety_stock") or 0)
        projected = float(inv.get("unrestricted_qty") or 0) + inbound_14 - demand_14
        if projected < safety:
            shortages.append(
                {
                    "material_code": material,
                    "plant": plant,
                    "shortage_qty": round(safety - projected, 2),
                    "actual_date": (snapshot_date + timedelta(days=14)).isoformat(),
                }
            )
    return {
        "shortages": shortages,
        "shortage_materials": sorted({row["material_code"] for row in shortages}),
        "evaluation_date": (snapshot_date + timedelta(days=14)).isoformat(),
    }


def _snapshot_date(snapshot: dict[str, Any]) -> date:
    return _date(snapshot.get("snapshot", {}).get("snapshot_time") or "2026-05-29")


def _date(value: str) -> date:
    return datetime.fromisoformat(str(value).replace(" ", "T")).date()
