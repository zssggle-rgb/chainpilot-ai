from __future__ import annotations

from typing import Any

SHORTAGE_RISK_14D_PROB = "SHORTAGE_RISK_14D_PROB"
CASH_RELEASE_PR_PO_OPT = "CASH_RELEASE_PR_PO_OPT"
MASTER_DATA_DIAGNOSIS_STAT = "MASTER_DATA_DIAGNOSIS_STAT"

ALGORITHM_CODES = [
    SHORTAGE_RISK_14D_PROB,
    CASH_RELEASE_PR_PO_OPT,
    MASTER_DATA_DIAGNOSIS_STAT,
]


def algorithm_definitions() -> list[dict[str, Any]]:
    return [
        {
            "algorithm_code": SHORTAGE_RISK_14D_PROB,
            "algorithm_name": "未来 14 天缺料风险概率",
            "hard_goal_code": "SHORTAGE_RADAR",
            "algorithm_level": "Professional-lite",
            "implementation_mode": "Embedded Python",
            "entrypoint": "chainpilot_ai.algorithms.shortage_risk_14d.run",
            "version": "1.0.0",
            "enabled": 1,
            "assumptions": "使用 Mock SAP 行级库存、需求、采购订单和供应商交付历史，执行确定性种子的轻量 Monte Carlo 仿真。",
            "limitations": "MVP 不调用真实 SAP，不建完整多级 BOM 约束；供应商历史不足时回退到物料组分布。",
            "input_schema_json": {"required_sections": ["inventory", "po_lines", "planned_demands", "consumption_history", "supplier_performance", "mrp_parameters"]},
            "output_schema_json": {"result_type": "SHORTAGE_RISK", "required_fields": ["shortage_probability_14d", "shortage_date_p50", "shortage_qty_p90"]},
        },
        {
            "algorithm_code": CASH_RELEASE_PR_PO_OPT,
            "algorithm_name": "PR/PO 现金释放动作包优化",
            "hard_goal_code": "CASH_RELEASE_PR_PO",
            "algorithm_level": "Professional-lite",
            "implementation_mode": "Embedded Python",
            "entrypoint": "chainpilot_ai.algorithms.cash_release_pr_po.run",
            "version": "1.0.0",
            "enabled": 1,
            "assumptions": "使用候选动作生成、硬约束过滤和整数规划求解；优先调用 HiGHS MILP，运行环境缺少 SciPy 时使用同一约束模型的精确整数枚举。",
            "limitations": "当前覆盖单工厂 PR/PO 动作包，真实上线前仍需用两年 SAP 历史回测校准策略阈值。",
            "input_schema_json": {"required_sections": ["materials", "inventory", "pr_lines", "po_lines", "planned_demands", "mrp_parameters"]},
            "output_schema_json": {"result_type": "CASH_RELEASE_ACTION", "required_fields": ["selected_actions", "blocked_actions", "cash_impact"]},
        },
        {
            "algorithm_code": MASTER_DATA_DIAGNOSIS_STAT,
            "algorithm_name": "SAP 主数据体检统计",
            "hard_goal_code": "MASTER_DATA_HEALTH",
            "algorithm_level": "Professional-lite",
            "implementation_mode": "Embedded Python",
            "entrypoint": "chainpilot_ai.algorithms.master_data_diagnosis.run",
            "version": "1.0.0",
            "enabled": 1,
            "assumptions": "使用供应商收货历史、消耗历史和 MRP 参数计算交期分位数、安全库存建议和 MOQ/MPQ 异常。",
            "limitations": "MVP 不修改 SAP 主数据，只生成复核建议。",
            "input_schema_json": {"required_sections": ["materials", "mrp_parameters", "supplier_performance", "consumption_history"]},
            "output_schema_json": {"result_type": "MASTER_DATA_ISSUE", "required_fields": ["metric_name", "metric_value", "confidence_score"]},
        },
    ]


def definition_by_code() -> dict[str, dict[str, Any]]:
    return {definition["algorithm_code"]: definition for definition in algorithm_definitions()}
