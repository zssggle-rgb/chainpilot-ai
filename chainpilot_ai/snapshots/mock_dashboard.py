from __future__ import annotations

from collections import Counter
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
def get_mock_data_dashboard(history_days: int = 120) -> dict[str, Any]:
    snapshot = load_mock_sap_snapshot()
    validation = validate_mock_sap_snapshot(snapshot)
    runtime = run_mvp_algorithms(snapshot)
    tuned = tune_strategy_presets(int(history_days or 120))
    cash_rows = [row["raw"] for row in runtime["results"] if row["result_type"] == "CASH_RELEASE_ACTION"]
    shortage_rows = [row["raw"] for row in runtime["results"] if row["result_type"] == "SHORTAGE_RISK"]
    selected_cash = [row for row in cash_rows if row.get("selected")]
    cash_summary = next((run["summary"] for run in runtime["runs"] if run["run"]["algorithm_code"] == "CASH_RELEASE_PR_PO_OPT"), {})
    return {
        "ok": True,
        "snapshot": snapshot.get("snapshot") or {},
        "counts": snapshot_counts(snapshot),
        "validation": validation,
        "expectations": snapshot.get("mock_expectations") or {},
        "algorithm_counts": runtime["counts"],
        "cash_summary": cash_summary,
        "shortage_rows": shortage_rows[:12],
        "selected_cash_rows": selected_cash[:14],
        "blocked_reasons": _blocked_reason_rows(cash_rows),
        "constraint_cases": _constraint_cases(snapshot, cash_rows),
        "sample_tables": _sample_tables(snapshot),
        "backtests": tuned["backtests"],
        "recommended_strategy_id": tuned["recommended_strategy_id"],
        "recommended_strategy_name": tuned["recommended_strategy_name"],
    }


def _blocked_reason_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter(row.get("blocked_reason") or "通过" for row in rows)
    return [{"label": label, "count": count} for label, count in counts.most_common()]


def _constraint_cases(snapshot: dict[str, Any], cash_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    expectation_cases = snapshot.get("mock_expectations", {}).get("constraint_cases") or []
    blocked = Counter(row.get("blocked_reason") or "通过" for row in cash_rows)
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
    if case == "MOQ/MPQ":
        return f"最小采购量/包装量阻断 {blocked.get('调整后数量低于最小采购量。', 0) + blocked.get('调整数量不满足最小包装量。', 0)} 条"
    if case == "保护物料":
        return f"保护物料阻断 {blocked.get('保护物料，不允许自动下调采购申请。', 0) + blocked.get('保护物料，不允许自动延期采购订单。', 0)} 条"
    if case == "供应商确认":
        return "确认订单进入供应商确认分层，不允许自动写回"
    if case == "同物料多单联动":
        return f"已选动作覆盖 {len(selected_materials)} 个物料，按物料余量统一约束"
    if case == "审批容量":
        return "求解器同时限制动作数量、复核数量、供应商确认数量和审批金额"
    return "已纳入验收集"


def _sample_tables(snapshot: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    return {
        "materials": snapshot.get("materials", [])[:8],
        "pr_lines": snapshot.get("pr_lines", [])[:10],
        "po_lines": snapshot.get("po_lines", [])[:10],
        "planned_demands": snapshot.get("planned_demands", [])[:10],
        "mrp_parameters": snapshot.get("mrp_parameters", [])[:8],
    }
