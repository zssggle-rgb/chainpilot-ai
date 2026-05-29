from __future__ import annotations

from datetime import date, timedelta
from typing import Any


BASE_DATE = date(2026, 5, 29)
PLANT = "CN01"


def build_realistic_mock_sap_snapshot() -> dict[str, Any]:
    """Build a deterministic SAP-like validation set for production algorithms."""
    materials = _materials()
    inventory = _inventory()
    mrp_parameters = _mrp_parameters()
    planned_demands = _planned_demands()
    pr_lines = _pr_lines()
    po_lines = _po_lines()
    supplier_performance = _supplier_performance()
    consumption_history = _consumption_history()
    return {
        "snapshot": {
            "snapshot_id": "SNAP-MOCK-REALISTIC-20260529",
            "source_type": "Mock",
            "source_system": "SAP_MOCK_REALISTIC",
            "plant_scope": PLANT,
            "material_scope": "SUPPLY_CHAIN_CONSTRAINT_VALIDATION",
            "snapshot_time": f"{BASE_DATE.isoformat()} 08:00:00",
        },
        "materials": materials,
        "inventory": inventory,
        "pr_lines": pr_lines,
        "po_lines": po_lines,
        "bom_components": _bom_components(materials),
        "planned_demands": planned_demands,
        "consumption_history": consumption_history,
        "supplier_performance": supplier_performance,
        "mrp_parameters": mrp_parameters,
        "mock_expectations": _expectations(),
    }


def _materials() -> list[dict[str, Any]]:
    rows = [
        ("MAT-100001", "变频压缩机控制板", "ELEC", "空调", "A", "Y", 920, 0, "P01", 1),
        ("MAT-100002", "冷凝风机组件", "MECH", "空调", "A", "Z", 680, 0, "P01", 1),
        ("MAT-100003", "长交期功率芯片", "ELEC", "空调", "A", "Z", 1550, 1, "P02", 1),
        ("MAT-100004", "铜管组件", "METAL", "空调", "B", "Y", 126, 0, "P02", 0),
        ("MAT-100005", "注塑外壳", "PLASTIC", "空调", "B", "X", 46, 0, "P03", 0),
        ("MAT-100006", "通用固定支架", "MECH", "空调", "C", "X", 18, 0, "P03", 0),
        ("MAT-100007", "包装纸箱", "PACK", "空调", "C", "Y", 8, 0, "P04", 0),
        ("MAT-100008", "遥控器组件", "ELEC", "空调", "B", "Z", 72, 0, "P04", 0),
        ("MAT-100009", "显示面板", "DISPLAY", "商显", "A", "Y", 1180, 0, "P05", 1),
        ("MAT-100010", "背光模组", "DISPLAY", "商显", "A", "Z", 960, 0, "P05", 1),
        ("MAT-100011", "电源线束", "ELEC", "商显", "B", "Y", 52, 0, "P06", 0),
        ("MAT-100012", "泡棉缓冲件", "PACK", "商显", "C", "X", 5, 0, "P06", 0),
        ("MAT-100013", "压缩机减振垫", "RUBBER", "空调", "B", "X", 22, 0, "P03", 0),
        ("MAT-100014", "电机轴承", "MECH", "空调", "A", "Y", 210, 0, "P01", 1),
        ("MAT-100015", "控制器散热片", "METAL", "空调", "B", "Y", 38, 0, "P02", 0),
        ("MAT-100016", "说明书套装", "PACK", "通用", "C", "X", 2.4, 0, "P04", 0),
        ("MAT-100017", "WiFi 通信模块", "ELEC", "商显", "A", "Z", 145, 0, "P05", 1),
        ("MAT-100018", "标准螺钉包", "MECH", "通用", "C", "X", 3.6, 0, "P06", 0),
    ]
    return [
        {
            "material_code": code,
            "material_name": name,
            "plant": PLANT,
            "material_group": group,
            "product_line": line,
            "abc_class": abc,
            "xyz_class": xyz,
            "unit_price": price,
            "is_protected": protected,
            "purchasing_group": buyer,
            "critical_flag": critical,
        }
        for code, name, group, line, abc, xyz, price, protected, buyer, critical in rows
    ]


def _inventory() -> list[dict[str, Any]]:
    levels = {
        "MAT-100001": (760, 0, 0, 900),
        "MAT-100002": (620, 0, 0, 850),
        "MAT-100003": (410, 0, 0, 520),
        "MAT-100004": (14500, 120, 0, 3800),
        "MAT-100005": (42000, 0, 0, 9000),
        "MAT-100006": (98000, 0, 800, 16000),
        "MAT-100007": (155000, 0, 1200, 28000),
        "MAT-100008": (5400, 0, 0, 2600),
        "MAT-100009": (520, 0, 0, 720),
        "MAT-100010": (430, 0, 0, 680),
        "MAT-100011": (18500, 0, 0, 6200),
        "MAT-100012": (210000, 0, 0, 42000),
        "MAT-100013": (66000, 0, 0, 11000),
        "MAT-100014": (1250, 0, 0, 1150),
        "MAT-100015": (32000, 0, 0, 7200),
        "MAT-100016": (260000, 0, 0, 50000),
        "MAT-100017": (960, 0, 0, 1200),
        "MAT-100018": (310000, 0, 0, 58000),
    }
    return [
        {
            "material_code": material,
            "plant": PLANT,
            "storage_location": "1000",
            "unrestricted_qty": unrestricted,
            "quality_qty": quality,
            "blocked_qty": blocked,
            "safety_stock": safety,
            "snapshot_date": BASE_DATE.isoformat(),
        }
        for material, (unrestricted, quality, blocked, safety) in levels.items()
    ]


def _mrp_parameters() -> list[dict[str, Any]]:
    params = {
        "MAT-100001": (14, 900, 200, 100, "EX", "M01"),
        "MAT-100002": (12, 850, 200, 100, "EX", "M01"),
        "MAT-100003": (42, 520, 100, 50, "EX", "M02"),
        "MAT-100004": (8, 3800, 2000, 500, "HB", "M02"),
        "MAT-100005": (7, 9000, 5000, 1000, "HB", "M03"),
        "MAT-100006": (5, 16000, 10000, 2000, "HB", "M03"),
        "MAT-100007": (4, 28000, 20000, 5000, "HB", "M04"),
        "MAT-100008": (10, 2600, 1000, 200, "EX", "M04"),
        "MAT-100009": (28, 720, 100, 50, "EX", "M05"),
        "MAT-100010": (24, 680, 100, 50, "EX", "M05"),
        "MAT-100011": (9, 6200, 2000, 500, "EX", "M06"),
        "MAT-100012": (5, 42000, 20000, 5000, "HB", "M06"),
        "MAT-100013": (7, 11000, 5000, 1000, "HB", "M03"),
        "MAT-100014": (15, 1150, 300, 100, "EX", "M01"),
        "MAT-100015": (8, 7200, 3000, 500, "HB", "M02"),
        "MAT-100016": (3, 50000, 30000, 5000, "HB", "M04"),
        "MAT-100017": (30, 1200, 300, 100, "EX", "M05"),
        "MAT-100018": (4, 58000, 30000, 10000, "HB", "M06"),
    }
    return [
        {
            "material_code": material,
            "plant": PLANT,
            "planned_delivery_time": lead_time,
            "safety_stock": safety,
            "moq": moq,
            "mpq": mpq,
            "lot_size_rule": lot_size,
            "mrp_controller": controller,
        }
        for material, (lead_time, safety, moq, mpq, lot_size, controller) in params.items()
    ]


def _planned_demands() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    demand_plan = {
        "MAT-100001": [(5, 780), (12, 520), (25, 380)],
        "MAT-100002": [(4, 820), (10, 460), (21, 360)],
        "MAT-100003": [(9, 420), (18, 260)],
        "MAT-100004": [(9, 5400), (17, 4200), (31, 3800)],
        "MAT-100005": [(10, 9000), (24, 7800), (39, 6400)],
        "MAT-100006": [(8, 13000), (24, 11000), (41, 9000)],
        "MAT-100007": [(6, 26000), (22, 21000), (38, 19000)],
        "MAT-100008": [(7, 2400), (17, 1900), (34, 1600)],
        "MAT-100009": [(6, 520), (14, 330), (28, 260)],
        "MAT-100010": [(5, 460), (13, 380), (32, 280)],
        "MAT-100011": [(11, 5200), (26, 4300)],
        "MAT-100012": [(8, 34000), (23, 30000), (37, 26000)],
        "MAT-100013": [(12, 9000), (30, 7200)],
        "MAT-100014": [(6, 760), (15, 480), (34, 360)],
        "MAT-100015": [(10, 5400), (24, 4800), (42, 3600)],
        "MAT-100016": [(9, 46000), (20, 42000), (35, 38000)],
        "MAT-100017": [(8, 860), (16, 620), (31, 420)],
        "MAT-100018": [(7, 52000), (19, 45000), (36, 39000)],
    }
    seq = 1
    for material, entries in demand_plan.items():
        for offset, qty in entries:
            rows.append(
                {
                    "demand_id": f"DEM-{seq:04d}",
                    "material_code": material,
                    "plant": PLANT,
                    "demand_date": _day(offset),
                    "demand_qty": qty,
                    "source_type": "MO" if seq % 3 else "SO",
                    "production_order": f"MO-{20000 + seq}",
                    "finished_good": _finished_good(material),
                }
            )
            seq += 1
    return rows


def _pr_lines() -> list[dict[str, Any]]:
    specs = [
        ("1000200101", "MAT-100004", "S200401", 6000, 18, 126),
        ("1000200102", "MAT-100004", "S200401", 5000, 33, 126),
        ("1000200103", "MAT-100005", "S200501", 18000, 20, 46),
        ("1000200104", "MAT-100005", "S200501", 14000, 29, 46),
        ("1000200105", "MAT-100006", "S200601", 36000, 17, 18),
        ("1000200106", "MAT-100006", "S200602", 26000, 27, 18),
        ("1000200107", "MAT-100007", "S200701", 62000, 16, 8),
        ("1000200108", "MAT-100007", "S200701", 48000, 31, 8),
        ("1000200109", "MAT-100011", "S201101", 12000, 21, 52),
        ("1000200110", "MAT-100011", "S201101", 8000, 38, 52),
        ("1000200111", "MAT-100012", "S201201", 90000, 19, 5),
        ("1000200112", "MAT-100012", "S201201", 70000, 36, 5),
        ("1000200113", "MAT-100013", "S201301", 22000, 23, 22),
        ("1000200114", "MAT-100013", "S201301", 16000, 40, 22),
        ("1000200115", "MAT-100015", "S201501", 16000, 20, 38),
        ("1000200116", "MAT-100015", "S201502", 13000, 35, 38),
        ("1000200117", "MAT-100016", "S201601", 120000, 15, 2.4),
        ("1000200118", "MAT-100016", "S201601", 95000, 30, 2.4),
        ("1000200119", "MAT-100018", "S201801", 140000, 18, 3.6),
        ("1000200120", "MAT-100018", "S201801", 120000, 32, 3.6),
        ("1000200121", "MAT-100001", "S200101", 700, 9, 920),
        ("1000200122", "MAT-100002", "S200201", 900, 8, 680),
        ("1000200123", "MAT-100003", "S200301", 300, 45, 1550),
        ("1000200124", "MAT-100009", "S200901", 420, 24, 1180),
        ("1000200125", "MAT-100010", "S201001", 360, 22, 960),
        ("1000200126", "MAT-100014", "S201401", 700, 6, 210),
        ("1000200127", "MAT-100017", "S201701", 800, 29, 145),
        ("1000200128", "MAT-100008", "S200801", 2600, 5, 72),
        ("1000200129", "MAT-100005", "S200501", 9000, 6, 46),
        ("1000200130", "MAT-100006", "S200602", 18000, 4, 18),
        ("1000200131", "MAT-100004", "S200403", 1400, 26, 126),
        ("1000200132", "MAT-100015", "S201502", 1800, 28, 38),
    ]
    buyer_by_material = {row["material_code"]: row["purchasing_group"] for row in _materials()}
    return [
        {
            "pr_no": pr_no,
            "pr_item": "00010",
            "material_code": material,
            "plant": PLANT,
            "supplier": supplier,
            "open_qty": qty,
            "delivery_date": _day(offset),
            "unit_price": unit_price,
            "status": "Open",
            "purchasing_group": buyer_by_material.get(material, "P01"),
        }
        for pr_no, material, supplier, qty, offset, unit_price in specs
    ]


def _po_lines() -> list[dict[str, Any]]:
    specs = [
        ("4500100101", "MAT-100001", "S200101", 1300, 8, False, 920),
        ("4500100102", "MAT-100002", "S200201", 1200, 7, False, 680),
        ("4500100103", "MAT-100003", "S200301", 520, 17, True, 1550),
        ("4500100104", "MAT-100004", "S200401", 4200, 11, False, 126),
        ("4500100105", "MAT-100004", "S200402", 3600, 24, True, 126),
        ("4500100106", "MAT-100005", "S200501", 16000, 12, False, 46),
        ("4500100107", "MAT-100005", "S200501", 12000, 26, True, 46),
        ("4500100108", "MAT-100006", "S200601", 22000, 10, False, 18),
        ("4500100109", "MAT-100006", "S200602", 18000, 25, True, 18),
        ("4500100110", "MAT-100007", "S200701", 42000, 9, False, 8),
        ("4500100111", "MAT-100007", "S200701", 36000, 23, True, 8),
        ("4500100112", "MAT-100008", "S200801", 3100, 13, False, 72),
        ("4500100113", "MAT-100009", "S200901", 620, 9, False, 1180),
        ("4500100114", "MAT-100010", "S201001", 580, 11, False, 960),
        ("4500100115", "MAT-100011", "S201101", 7200, 18, False, 52),
        ("4500100116", "MAT-100012", "S201201", 78000, 13, False, 5),
        ("4500100117", "MAT-100013", "S201301", 18000, 16, False, 22),
        ("4500100118", "MAT-100014", "S201401", 900, 5, False, 210),
        ("4500100119", "MAT-100015", "S201501", 12000, 14, False, 38),
        ("4500100120", "MAT-100016", "S201601", 105000, 12, False, 2.4),
        ("4500100121", "MAT-100017", "S201701", 760, 19, False, 145),
        ("4500100122", "MAT-100018", "S201801", 130000, 15, False, 3.6),
        ("4500100123", "MAT-100005", "S200501", 9000, 3, False, 46),
        ("4500100124", "MAT-100006", "S200601", 12000, 2, False, 18),
        ("4500100125", "MAT-100012", "S201201", 50000, 4, True, 5),
        ("4500100126", "MAT-100018", "S201801", 70000, 6, True, 3.6),
        ("4500100127", "MAT-100004", "S200402", 1200, 6, True, 126),
        ("4500100128", "MAT-100015", "S201501", 2500, 7, False, 38),
    ]
    return [
        {
            "po_no": po_no,
            "po_item": "00010",
            "material_code": material,
            "plant": PLANT,
            "supplier": supplier,
            "open_qty": qty,
            "delivery_date": _day(offset),
            "confirmed_flag": confirmed,
            "unit_price": unit_price,
            "status": "Open",
        }
        for po_no, material, supplier, qty, offset, confirmed, unit_price in specs
    ]


def _bom_components(materials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for index, material in enumerate(materials, start=1):
        rows.append(
            {
                "finished_good": _finished_good(material["material_code"]),
                "component_material": material["material_code"],
                "plant": PLANT,
                "usage_qty": 1 if material["abc_class"] != "C" else 2,
                "valid_from": "2026-01-01",
                "alternative_group": "MAIN" if index % 5 else "ALT-A",
            }
        )
    return rows


def _supplier_performance() -> list[dict[str, Any]]:
    rows = []
    suppliers = {
        "MAT-100001": "S200101",
        "MAT-100002": "S200201",
        "MAT-100003": "S200301",
        "MAT-100004": "S200401",
        "MAT-100005": "S200501",
        "MAT-100006": "S200601",
        "MAT-100007": "S200701",
        "MAT-100008": "S200801",
        "MAT-100009": "S200901",
        "MAT-100010": "S201001",
        "MAT-100011": "S201101",
        "MAT-100012": "S201201",
        "MAT-100013": "S201301",
        "MAT-100014": "S201401",
        "MAT-100015": "S201501",
        "MAT-100016": "S201601",
        "MAT-100017": "S201701",
        "MAT-100018": "S201801",
    }
    for index, material in enumerate(suppliers, start=1):
        for sample in range(6):
            planned = BASE_DATE - timedelta(days=72 - sample * 9 - index % 4)
            delay = [0, 1, 2, 4, 7, 10][(sample + index) % 6]
            if material in {"MAT-100001", "MAT-100002", "MAT-100009", "MAT-100010", "MAT-100017"}:
                delay += 2
            rows.append(
                {
                    "supplier": suppliers[material],
                    "material_code": material,
                    "plant": PLANT,
                    "po_create_date": (planned - timedelta(days=20)).isoformat(),
                    "planned_delivery_date": planned.isoformat(),
                    "actual_gr_date": (planned + timedelta(days=delay)).isoformat(),
                    "delivered_qty": 1000 + index * 75 + sample * 40,
                    "ordered_qty": 1000 + index * 75 + sample * 40,
                    "quality_issue_flag": bool(material in {"MAT-100003", "MAT-100010"} and sample == 4),
                }
            )
    return rows


def _consumption_history() -> list[dict[str, Any]]:
    rows = []
    demand_by_material = {
        row["material_code"]: sum(item["demand_qty"] for item in _planned_demands() if item["material_code"] == row["material_code"])
        for row in _materials()
    }
    for index, material in enumerate(demand_by_material, start=1):
        weekly_base = max(20, demand_by_material[material] / 7)
        for week in range(8):
            variation = 1 + ((week % 3) - 1) * 0.08 + (0.04 if index % 4 == 0 else 0)
            rows.append(
                {
                    "material_code": material,
                    "plant": PLANT,
                    "posting_date": (BASE_DATE - timedelta(days=7 * (8 - week))).isoformat(),
                    "actual_consumption_qty": round(weekly_base * variation, 2),
                }
            )
    return rows


def _expectations() -> dict[str, Any]:
    return {
        "purpose": "用于验证生产级现金优化和缺料预测，而不是页面演示假数据。",
        "constraint_cases": [
            {"case": "冻结期", "examples": ["MAT-100005", "MAT-100006", "MAT-100008", "MAT-100014"]},
            {"case": "MOQ/MPQ", "examples": ["MAT-100004", "MAT-100015"]},
            {"case": "保护物料", "examples": ["MAT-100003"]},
            {"case": "供应商确认", "examples": ["4500100103", "4500100105", "4500100111"]},
            {"case": "同物料多单联动", "examples": ["MAT-100004", "MAT-100005", "MAT-100006", "MAT-100018"]},
            {"case": "审批容量", "examples": ["高金额 PR/PO 组合需要被求解器筛选"]},
        ],
        "expected_shortage_materials": ["MAT-100001", "MAT-100002", "MAT-100009", "MAT-100010", "MAT-100017"],
        "expected_cash_materials": ["MAT-100005", "MAT-100006", "MAT-100007", "MAT-100012", "MAT-100013", "MAT-100016", "MAT-100018"],
        "expected_blocked_reasons": ["冻结期", "保护物料", "供应商已确认", "服务水平余量不足", "MOQ/MPQ"],
    }


def _finished_good(material: str) -> str:
    number = int(material.split("-")[-1])
    if number <= 8:
        return "AC-PRO-900"
    if number <= 12:
        return "DS-PLUS-75"
    return "GEN-ASSY-01"


def _day(offset: int) -> str:
    return (BASE_DATE + timedelta(days=offset)).isoformat()
