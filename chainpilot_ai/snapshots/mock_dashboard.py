from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any

try:
    import frappe
except Exception:  # pragma: no cover
    frappe = None

from chainpilot_ai.algorithms.registry import run_mvp_algorithms
from chainpilot_ai.snapshots.mock_loader import load_mock_sap_snapshot
from chainpilot_ai.snapshots.validators import snapshot_counts, validate_mock_sap_snapshot
from chainpilot_ai.strategy.backtest import tune_strategy_presets


def _whitelist(fn):
    if frappe:
        return frappe.whitelist()(fn)
    return fn


@_whitelist
def get_mock_data_dashboard(history_days: int = 90) -> dict[str, Any]:
    return _build_mock_data_dashboard(int(history_days or 90))


@lru_cache(maxsize=8)
def _build_mock_data_dashboard(history_days: int) -> dict[str, Any]:
    snapshot = load_mock_sap_snapshot()
    validation = validate_mock_sap_snapshot(snapshot)
    runtime = run_mvp_algorithms(snapshot)
    tuned = tune_strategy_presets(history_days)
    cash_rows = [row["raw"] for row in runtime["results"] if row["result_type"] == "CASH_RELEASE_ACTION"]
    shortage_rows = [row["raw"] for row in runtime["results"] if row["result_type"] == "SHORTAGE_RISK"]
    selected_cash = [row for row in cash_rows if row.get("selected")]
    cash_summary = next((run["summary"] for run in runtime["runs"] if run["run"]["algorithm_code"] == "CASH_RELEASE_PR_PO_OPT"), {})
    counts = snapshot_counts(snapshot)
    return {
        "ok": True,
        "snapshot": snapshot.get("snapshot") or {},
        "counts": counts,
        "validation": validation,
        "expectations": snapshot.get("mock_expectations") or {},
        "ai_capability_model": _ai_capability_model(),
        "business_summary": _business_summary(snapshot, counts),
        "source_mapping": _source_mapping(counts),
        "relationship_checks": _relationship_checks(snapshot),
        "planning_workbench": _planning_workbench(snapshot, cash_rows, shortage_rows, cash_summary),
        "material_profiles": _material_profiles(snapshot, cash_rows, shortage_rows),
        "algorithm_counts": runtime["counts"],
        "cash_summary": cash_summary,
        "shortage_rows": shortage_rows[:16],
        "selected_cash_rows": selected_cash[:16],
        "blocked_reasons": _blocked_reason_rows(cash_rows),
        "constraint_cases": _constraint_cases(snapshot, cash_rows),
        "sample_tables": _sample_tables(snapshot),
        "backtests": tuned["backtests"],
        "recommended_strategy_id": tuned["recommended_strategy_id"],
        "recommended_strategy_name": tuned["recommended_strategy_name"],
    }


def _ai_capability_model() -> list[dict[str, str]]:
    return [
        {
            "code": "PREDICTIVE_MODEL",
            "label": "预测模型",
            "business_role": "预测缺料概率、P90 缺口、供应延迟和需求波动。",
            "current_implementation": "当前模拟阶段使用概率仿真和统计特征；接入两年 SAP 历史后训练需求、交期和供应延迟模型。",
            "ui_surface": "缺料例外工作表、行项目详情、驱动因素。",
        },
        {
            "code": "OPTIMIZER",
            "label": "优化器",
            "business_role": "在服务水平、冻结期、保护物料、最小采购量和审批容量下选择采购动作包。",
            "current_implementation": "当前使用 HiGHS MILP 整数规划求解，运行环境不支持时使用同一约束模型的精确整数枚举。",
            "ui_surface": "采购动作工作表、优化运行、场景对比。",
        },
        {
            "code": "EXPLAINABILITY",
            "label": "驱动因素",
            "business_role": "把预测和优化结果拆成库存、安全库存、需求波动、供应商延迟、约束状态和证据链。",
            "current_implementation": "当前由算法证据字段和约束校验结果生成；LLM 只能基于证据生成摘要，不能新增事实。",
            "ui_surface": "行项目详情、证据链、约束校验。",
        },
        {
            "code": "COPLANNER",
            "label": "协同助手",
            "business_role": "围绕当前行、当前场景和当前算法运行回答计划员问题，生成审批摘要和供应商沟通草稿。",
            "current_implementation": "当前接入可配置 LLM，输出受证据边界和只读/草稿回写边界约束。",
            "ui_surface": "行项目详情侧栏、审批包、供应商确认草稿。",
        },
    ]


def _business_summary(snapshot: dict[str, Any], counts: dict[str, int]) -> list[dict[str, str]]:
    materials = snapshot.get("materials", [])
    pr_rows = snapshot.get("pr_lines", [])
    po_rows = snapshot.get("po_lines", [])
    bom_rows = snapshot.get("bom_components", [])
    demand_rows = snapshot.get("planned_demands", [])
    supplier_rows = snapshot.get("supplier_performance", [])
    plants = sorted({row.get("plant") for row in materials if row.get("plant")})
    product_lines = sorted({row.get("product_line") for row in materials if row.get("product_line")})
    suppliers = sorted({row.get("supplier") for row in pr_rows + po_rows if row.get("supplier")})
    finished_goods = sorted({row.get("finished_good") for row in bom_rows if row.get("finished_good")})
    pr_amount = sum(float(row.get("open_qty") or 0) * float(row.get("unit_price") or 0) for row in pr_rows)
    po_amount = sum(float(row.get("open_qty") or 0) * float(row.get("unit_price") or 0) for row in po_rows)
    demand_qty = sum(float(row.get("demand_qty") or 0) for row in demand_rows)
    confirmed_po = sum(1 for row in po_rows if row.get("confirmed_flag"))
    protected_materials = sum(1 for row in materials if row.get("is_protected"))
    avg_delay = _average_supplier_delay(supplier_rows)
    return [
        {"label": "业务范围", "value": f"{len(plants)} 个工厂 / {len(product_lines)} 条产品线", "detail": "、".join(plants + product_lines)},
        {"label": "主数据规模", "value": f"{counts.get('materials', 0)} 个物料 / {len(finished_goods)} 个成品", "detail": f"保护物料 {protected_materials} 个，物料清单组件 {counts.get('bom_components', 0)} 条"},
        {"label": "采购未清", "value": _money(pr_amount + po_amount), "detail": f"采购申请 {counts.get('pr_lines', 0)} 行，采购订单 {counts.get('po_lines', 0)} 行，已确认订单 {confirmed_po} 行"},
        {"label": "需求与履约", "value": f"{_qty(demand_qty)} 需求量", "detail": f"历史消耗 {counts.get('consumption_history', 0)} 条，供应商履约 {counts.get('supplier_performance', 0)} 条，平均延迟 {avg_delay} 天"},
    ]


def _planning_workbench(snapshot: dict[str, Any], cash_rows: list[dict[str, Any]], shortage_rows: list[dict[str, Any]], cash_summary: dict[str, Any]) -> dict[str, Any]:
    materials = snapshot.get("materials", [])
    plants = sorted({row.get("plant") for row in materials if row.get("plant")})
    product_lines = sorted({row.get("product_line") for row in materials if row.get("product_line")})
    blocked_count = sum(1 for row in cash_rows if row.get("constraint_verdict") == "BLOCKED")
    selected_count = sum(1 for row in cash_rows if row.get("selected"))
    delayed_supplier_rows = sum(1 for row in snapshot.get("supplier_performance", []) if _delay_days(row) >= 7)
    quality_issue_rows = sum(1 for row in snapshot.get("supplier_performance", []) if row.get("quality_issue_flag"))
    return {
        "scenario": {
            "name": "基准模拟账套",
            "horizon": "未来 45 天",
            "plants": "、".join(plants),
            "product_lines": "、".join(product_lines),
            "planning_level": "物料 / 工厂 / 供应商",
        },
        "exception_pillars": [
            {"label": "缺料风险", "value": len(shortage_rows), "detail": "未来 14 天高风险物料"},
            {"label": "可处理建议", "value": selected_count, "detail": "进入资金占用处理清单"},
            {"label": "约束阻断", "value": blocked_count, "detail": "冻结期、保护物料、数量约束"},
            {"label": "供应异常", "value": delayed_supplier_rows + quality_issue_rows, "detail": "延迟交付或质量异常记录"},
        ],
        "weekly_supply_plan": _weekly_supply_plan(snapshot),
        "inventory_policy_rows": _inventory_policy_rows(snapshot),
        "solver": {
            "name": cash_summary.get("solver_name") or "-",
            "status": cash_summary.get("solver_status") or "-",
            "selected_actions": selected_count,
            "cash_release_total": cash_summary.get("cash_release_total") or 0,
        },
    }


def _weekly_supply_plan(snapshot: dict[str, Any], weeks: int = 6) -> list[dict[str, Any]]:
    base_date = _snapshot_date(snapshot)
    rows = []
    for index in range(weeks):
        start = base_date + timedelta(days=index * 7)
        end = start + timedelta(days=6)
        demand_qty = _sum_between(snapshot.get("planned_demands", []), "demand_date", "demand_qty", start, end)
        firm_supply_qty = _sum_between(snapshot.get("po_lines", []), "delivery_date", "open_qty", start, end)
        planned_supply_qty = _sum_between(snapshot.get("pr_lines", []), "delivery_date", "open_qty", start, end)
        net_gap_qty = demand_qty - firm_supply_qty - planned_supply_qty
        rows.append(
            {
                "label": f"第 {index + 1} 周",
                "date_range": f"{start.strftime('%m-%d')} 至 {end.strftime('%m-%d')}",
                "demand_qty": round(demand_qty, 2),
                "firm_supply_qty": round(firm_supply_qty, 2),
                "planned_supply_qty": round(planned_supply_qty, 2),
                "net_gap_qty": round(net_gap_qty, 2),
                "status": "供应缺口" if net_gap_qty > 0 else "供应覆盖",
            }
        )
    return rows


def _sum_between(rows: list[dict[str, Any]], date_field: str, qty_field: str, start, end) -> float:
    total = 0.0
    for row in rows:
        value = row.get(date_field)
        if not value:
            continue
        date_value = datetime.fromisoformat(str(value)).date()
        if start <= date_value <= end:
            total += float(row.get(qty_field) or 0)
    return total


def _inventory_policy_rows(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    materials = {(row["material_code"], row["plant"]): row for row in snapshot.get("materials", [])}
    inventory = {(row["material_code"], row["plant"]): row for row in snapshot.get("inventory", [])}
    demand = _demand_45d(snapshot)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for key, material in materials.items():
        inv = inventory.get(key, {})
        demand_qty = float(demand.get(key, 0) or 0)
        available = float(inv.get("unrestricted_qty") or 0)
        safety = float(inv.get("safety_stock") or 0)
        daily_demand = demand_qty / 45 if demand_qty else 0
        coverage_days = available / daily_demand if daily_demand else 999
        grouped[_segment_label(material)].append(
            {
                "coverage_days": min(999, coverage_days),
                "low": available < safety or coverage_days < 21,
                "high": demand_qty > 0 and coverage_days > 90,
            }
        )
    rows = []
    for segment, items in sorted(grouped.items()):
        if not items:
            continue
        avg_coverage = sum(item["coverage_days"] for item in items) / len(items)
        low_count = sum(1 for item in items if item["low"])
        high_count = sum(1 for item in items if item["high"])
        if low_count:
            policy = "提高目标库存"
        elif high_count > len(items) * 0.4:
            policy = "降低目标库存"
        else:
            policy = "维持策略"
        rows.append(
            {
                "segment": segment,
                "materials": len(items),
                "avg_coverage_days": round(avg_coverage, 1),
                "low_coverage": low_count,
                "high_coverage": high_count,
                "policy": policy,
            }
        )
    return rows


def _source_mapping(counts: dict[str, int]) -> list[dict[str, Any]]:
    return [
        {"domain": "物料主数据", "rows": counts.get("materials", 0), "real_source": "物料主数据、工厂视图", "business_use": "产品线、物料分层、单价、采购组、保护物料"},
        {"domain": "库存", "rows": counts.get("inventory", 0), "real_source": "库存余额、质检库存、冻结库存", "business_use": "判断可用库存、安全库存和库存覆盖天数"},
        {"domain": "采购申请", "rows": counts.get("pr_lines", 0), "real_source": "采购申请行项目", "business_use": "识别可取消或可下调的未清采购申请"},
        {"domain": "采购订单", "rows": counts.get("po_lines", 0), "real_source": "采购订单行项目、交货计划、确认信息", "business_use": "识别可延期、需供应商确认或冻结期内不可动的订单"},
        {"domain": "需求", "rows": counts.get("planned_demands", 0), "real_source": "计划需求、生产订单、销售订单或预测", "business_use": "计算未来需求和缺料风险"},
        {"domain": "供应商履约", "rows": counts.get("supplier_performance", 0), "real_source": "历史收货、交期确认、质量异常", "business_use": "估计供应延迟和交付稳定性"},
        {"domain": "计划参数", "rows": counts.get("mrp_parameters", 0), "real_source": "计划参数、最小采购量、最小包装量、计划交货期", "business_use": "校验最小采购量、最小包装量、安全库存和交期主数据"},
    ]


def _relationship_checks(snapshot: dict[str, Any]) -> list[dict[str, str]]:
    materials = {(row["material_code"], row["plant"]) for row in snapshot.get("materials", [])}
    inventory = {(row["material_code"], row["plant"]) for row in snapshot.get("inventory", [])}
    mrp = {(row["material_code"], row["plant"]) for row in snapshot.get("mrp_parameters", [])}
    bom_components = {(row["component_material"], row["plant"]) for row in snapshot.get("bom_components", [])}
    purchase_refs = [(row["material_code"], row["plant"]) for row in snapshot.get("pr_lines", []) + snapshot.get("po_lines", [])]
    demand_refs = [(row["material_code"], row["plant"]) for row in snapshot.get("planned_demands", [])]
    history_refs = [(row["material_code"], row["plant"]) for row in snapshot.get("consumption_history", [])]
    supplier_refs = [(row["material_code"], row["plant"]) for row in snapshot.get("supplier_performance", [])]
    return [
        _check_row("采购单据关联物料", len(purchase_refs), _missing_count(purchase_refs, materials), "采购申请和采购订单必须能回到物料主数据"),
        _check_row("库存关联物料", len(inventory), _missing_count(inventory, materials), "每个物料都有库存快照"),
        _check_row("需求关联物料", len(demand_refs), _missing_count(demand_refs, materials), "每条计划需求都能回到物料和工厂"),
        _check_row("物料清单关联物料", len(bom_components), _missing_count(bom_components, materials), "组件物料必须在物料主数据中存在"),
        _check_row("计划参数关联物料", len(mrp), _missing_count(mrp, materials), "每个物料都有安全库存、最小采购量、最小包装量和交期参数"),
        _check_row("历史数据关联物料", len(history_refs) + len(supplier_refs), _missing_count(history_refs + supplier_refs, materials), "消耗历史和供应商履约都能追溯到物料"),
    ]


def _check_row(label: str, total: int, missing: int, detail: str) -> dict[str, str]:
    return {"label": label, "value": f"{total - missing}/{total}", "detail": detail, "status": "通过" if missing == 0 else f"缺失 {missing} 条"}


def _missing_count(refs: Any, valid: set[tuple[str, str]]) -> int:
    return sum(1 for ref in refs if ref not in valid)


def _material_profiles(snapshot: dict[str, Any], cash_rows: list[dict[str, Any]], shortage_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    materials = {(row["material_code"], row["plant"]): row for row in snapshot.get("materials", [])}
    inventory = {(row["material_code"], row["plant"]): row for row in snapshot.get("inventory", [])}
    mrp = {(row["material_code"], row["plant"]): row for row in snapshot.get("mrp_parameters", [])}
    demand = _demand_45d(snapshot)
    pr_po = _purchase_amounts(snapshot)
    delays = _supplier_delay_by_material(snapshot)
    shortage_by_key = {(row["material_code"], row["plant"]): row for row in shortage_rows}
    cash_by_key: dict[tuple[str, str], float] = defaultdict(float)
    for row in cash_rows:
        if row.get("selected"):
            cash_by_key[(row["material_code"], row["plant"])] += float(row.get("cash_impact") or 0)
    chosen_keys = []
    for row in shortage_rows[:8]:
        chosen_keys.append((row["material_code"], row["plant"]))
    for row in sorted(cash_rows, key=lambda item: float(item.get("cash_impact") or 0), reverse=True):
        key = (row["material_code"], row["plant"])
        if row.get("selected") and key not in chosen_keys:
            chosen_keys.append(key)
        if len(chosen_keys) >= 14:
            break
    profiles = []
    for key in chosen_keys[:14]:
        material = materials.get(key, {})
        inv = inventory.get(key, {})
        params = mrp.get(key, {})
        shortage = shortage_by_key.get(key, {})
        profiles.append(
            {
                "material_code": key[0],
                "material_name": material.get("material_name", ""),
                "plant": key[1],
                "product_line": material.get("product_line", ""),
                "segment": _segment_label(material),
                "inventory": inv.get("unrestricted_qty", 0),
                "safety_stock": params.get("safety_stock") or inv.get("safety_stock", 0),
                "demand_45d": demand.get(key, 0),
                "purchase_amount": pr_po.get(key, 0),
                "avg_delay_days": delays.get(key, 0),
                "shortage_probability": shortage.get("shortage_probability_14d", 0),
                "selected_cash": cash_by_key.get(key, 0),
            }
        )
    return profiles


def _blocked_reason_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter(row.get("blocked_reason") or "可处理" for row in rows)
    return [{"label": label, "count": count} for label, count in counts.most_common()]


def _constraint_cases(snapshot: dict[str, Any], cash_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    expectation_cases = snapshot.get("mock_expectations", {}).get("constraint_cases") or []
    blocked = Counter(row.get("blocked_reason") or "可处理" for row in cash_rows)
    selected_materials = sorted({row.get("material_code") for row in cash_rows if row.get("selected")})
    return [
        {
            "case": row.get("case"),
            "examples": row.get("examples") or [],
            "evidence": _case_evidence(row.get("case") or "", blocked, selected_materials),
        }
        for row in expectation_cases
    ]


def _case_evidence(case: str, blocked: Counter, selected_materials: list[str]) -> str:
    if case == "冻结期":
        return f"冻结期阻断 {blocked.get('交期落在冻结期内，不能作为资金优化动作。', 0) + blocked.get('订单交期在冻结期内，不允许延期。', 0)} 条"
    if case == "最小采购量/包装量":
        return f"最小采购量/包装量阻断 {blocked.get('调整后数量低于最小采购量。', 0) + blocked.get('调整数量不满足最小包装量。', 0)} 条"
    if case == "保护物料":
        return f"保护物料阻断 {blocked.get('保护物料，不允许自动下调采购申请。', 0) + blocked.get('保护物料，不允许自动延期采购订单。', 0)} 条"
    if case == "供应商确认":
        return "已确认订单进入人工确认层"
    if case == "同物料多单联动":
        return f"已选动作覆盖 {len(selected_materials)} 个物料"
    if case == "审批容量":
        return "动作数量、复核数量、供应商确认数量和审批金额同时受控"
    return "已覆盖"


def _sample_tables(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    materials = {(row["material_code"], row["plant"]): row for row in snapshot.get("materials", [])}
    mrp = {(row["material_code"], row["plant"]): row for row in snapshot.get("mrp_parameters", [])}
    demand = _demand_45d(snapshot)
    return [
        {
            "title": "物料与计划参数",
            "count": len(snapshot.get("materials", [])),
            "columns": ["物料", "名称", "工厂", "产品线", "分层", "安全库存", "最小采购量", "采购组"],
            "rows": [
                [
                    row.get("material_code"),
                    row.get("material_name"),
                    row.get("plant"),
                    row.get("product_line"),
                    _segment_label(row),
                    _qty(mrp.get((row["material_code"], row["plant"]), {}).get("safety_stock", 0)),
                    _qty(mrp.get((row["material_code"], row["plant"]), {}).get("moq", 0)),
                    row.get("purchasing_group"),
                ]
                for row in snapshot.get("materials", [])[:14]
            ],
        },
        {
            "title": "库存与需求",
            "count": len(snapshot.get("inventory", [])),
            "columns": ["物料", "工厂", "可用库存", "质检/冻结", "45 天需求", "安全库存", "库存状态"],
            "rows": [
                [
                    row.get("material_code"),
                    row.get("plant"),
                    _qty(row.get("unrestricted_qty", 0)),
                    f"{_qty(row.get('quality_qty', 0))} / {_qty(row.get('blocked_qty', 0))}",
                    _qty(demand.get((row["material_code"], row["plant"]), 0)),
                    _qty(row.get("safety_stock", 0)),
                    _inventory_status(row, demand.get((row["material_code"], row["plant"]), 0)),
                ]
                for row in snapshot.get("inventory", [])[:14]
            ],
        },
        {
            "title": "采购申请",
            "count": len(snapshot.get("pr_lines", [])),
            "columns": ["单据行", "物料", "工厂", "供应商", "未清数量", "交货日期", "未清金额", "采购组"],
            "rows": [
                [
                    f"{row.get('pr_no')}/{row.get('pr_item')}",
                    row.get("material_code"),
                    row.get("plant"),
                    row.get("supplier"),
                    _qty(row.get("open_qty", 0)),
                    row.get("delivery_date"),
                    _money(float(row.get("open_qty") or 0) * float(row.get("unit_price") or 0)),
                    row.get("purchasing_group"),
                ]
                for row in snapshot.get("pr_lines", [])[:16]
            ],
        },
        {
            "title": "采购订单",
            "count": len(snapshot.get("po_lines", [])),
            "columns": ["单据行", "物料", "工厂", "供应商", "未清数量", "交货日期", "供应商确认", "未清金额"],
            "rows": [
                [
                    f"{row.get('po_no')}/{row.get('po_item')}",
                    row.get("material_code"),
                    row.get("plant"),
                    row.get("supplier"),
                    _qty(row.get("open_qty", 0)),
                    row.get("delivery_date"),
                    "已确认" if row.get("confirmed_flag") else "未确认",
                    _money(float(row.get("open_qty") or 0) * float(row.get("unit_price") or 0)),
                ]
                for row in snapshot.get("po_lines", [])[:16]
            ],
        },
        {
            "title": "供应商履约",
            "count": len(snapshot.get("supplier_performance", [])),
            "columns": ["供应商", "物料", "工厂", "计划交货", "实际收货", "延迟天数", "收货数量", "质量异常"],
            "rows": [
                [
                    row.get("supplier"),
                    row.get("material_code"),
                    row.get("plant"),
                    row.get("planned_delivery_date"),
                    row.get("actual_gr_date"),
                    str(_delay_days(row)),
                    _qty(row.get("delivered_qty", 0)),
                    "是" if row.get("quality_issue_flag") else "否",
                ]
                for row in snapshot.get("supplier_performance", [])[:16]
            ],
        },
        {
            "title": "需求与成品关联",
            "count": len(snapshot.get("planned_demands", [])),
            "columns": ["需求号", "物料", "工厂", "需求日期", "需求数量", "来源", "生产/销售单", "成品"],
            "rows": [
                [
                    row.get("demand_id"),
                    row.get("material_code"),
                    row.get("plant"),
                    row.get("demand_date"),
                    _qty(row.get("demand_qty", 0)),
                    "生产订单" if row.get("source_type") == "MO" else "销售/预测",
                    row.get("production_order"),
                    row.get("finished_good"),
                ]
                for row in snapshot.get("planned_demands", [])[:16]
            ],
        },
    ]


def _demand_45d(snapshot: dict[str, Any]) -> dict[tuple[str, str], float]:
    base_date = _snapshot_date(snapshot)
    rows: dict[tuple[str, str], float] = defaultdict(float)
    for row in snapshot.get("planned_demands", []):
        demand_date = datetime.fromisoformat(row["demand_date"]).date()
        if 0 <= (demand_date - base_date).days <= 45:
            rows[(row["material_code"], row["plant"])] += float(row.get("demand_qty") or 0)
    return rows


def _purchase_amounts(snapshot: dict[str, Any]) -> dict[tuple[str, str], float]:
    amounts: dict[tuple[str, str], float] = defaultdict(float)
    for row in snapshot.get("pr_lines", []) + snapshot.get("po_lines", []):
        amounts[(row["material_code"], row["plant"])] += float(row.get("open_qty") or 0) * float(row.get("unit_price") or 0)
    return amounts


def _supplier_delay_by_material(snapshot: dict[str, Any]) -> dict[tuple[str, str], float]:
    delays: dict[tuple[str, str], list[int]] = defaultdict(list)
    for row in snapshot.get("supplier_performance", []):
        delays[(row["material_code"], row["plant"])].append(_delay_days(row))
    return {key: round(sum(values) / len(values), 1) for key, values in delays.items() if values}


def _average_supplier_delay(rows: list[dict[str, Any]]) -> float:
    values = [_delay_days(row) for row in rows]
    return round(sum(values) / len(values), 1) if values else 0


def _delay_days(row: dict[str, Any]) -> int:
    planned = datetime.fromisoformat(row["planned_delivery_date"]).date()
    actual = datetime.fromisoformat(row["actual_gr_date"]).date()
    return max(0, (actual - planned).days)


def _inventory_status(row: dict[str, Any], demand_45d: float) -> str:
    available = float(row.get("unrestricted_qty") or 0)
    safety = float(row.get("safety_stock") or 0)
    if available < safety:
        return "低于安全库存"
    if demand_45d and available < demand_45d * 0.5:
        return "需求压力高"
    if available > max(safety, demand_45d) * 2:
        return "库存偏高"
    return "正常"


def _segment_label(material: dict[str, Any]) -> str:
    abc_labels = {"A": "关键", "B": "常规", "C": "低值"}
    xyz_labels = {"X": "稳定", "Y": "波动", "Z": "高波动"}
    abc = abc_labels.get(str(material.get("abc_class") or "").upper(), "未分层")
    xyz = xyz_labels.get(str(material.get("xyz_class") or "").upper(), "未分层")
    return f"{abc}/{xyz}"


def _snapshot_date(snapshot: dict[str, Any]):
    value = snapshot.get("snapshot", {}).get("snapshot_time") or "2026-05-29"
    return datetime.fromisoformat(str(value).replace(" ", "T")).date()


def _qty(value: Any) -> str:
    amount = float(value or 0)
    if amount.is_integer():
        return f"{int(amount):,}"
    return f"{amount:,.2f}"


def _money(value: float) -> str:
    if abs(value) >= 10000:
        return f"{value / 10000:,.1f} 万元"
    return f"{value:,.0f} 元"
