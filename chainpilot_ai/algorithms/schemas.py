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
            "version": "1.1.0",
            "enabled": 1,
            "assumptions": "使用 Mock SAP 行级库存、需求、采购订单和供应商交付历史；先对历史消耗执行模型候选回测并选择最佳预测模型，再把预测不确定性纳入确定性种子的 Monte Carlo 仿真。",
            "limitations": "当前预测模型竞赛覆盖移动平均、趋势组合和稳健中位数；真实上线前需接入两年 SAP 历史、供应商日历和异常事件做模型再训练。",
            "input_schema_json": {"required_sections": ["inventory", "po_lines", "planned_demands", "consumption_history", "supplier_performance", "mrp_parameters"]},
            "output_schema_json": {"result_type": "SHORTAGE_RISK", "required_fields": ["shortage_probability_14d", "shortage_date_p50", "shortage_qty_p90", "forecast_model", "forecast_wape"]},
        },
        {
            "algorithm_code": CASH_RELEASE_PR_PO_OPT,
            "algorithm_name": "PR/PO 现金释放动作包优化",
            "hard_goal_code": "CASH_RELEASE_PR_PO",
            "algorithm_level": "Professional-lite",
            "implementation_mode": "Embedded Python",
            "entrypoint": "chainpilot_ai.algorithms.cash_release_pr_po.run",
            "version": "1.1.0",
            "enabled": 1,
            "assumptions": "使用候选动作生成、硬约束过滤和整数规划求解；优先调用 HiGHS MILP，运行环境缺少 SciPy 时使用同一约束模型的精确整数枚举，并输出目标函数、决策变量、约束利用率和 MIP Gap。",
            "limitations": "当前覆盖单工厂 PR/PO 动作包，真实上线前仍需用两年 SAP 历史回测校准策略阈值。",
            "input_schema_json": {"required_sections": ["materials", "inventory", "pr_lines", "po_lines", "planned_demands", "mrp_parameters"]},
            "output_schema_json": {"result_type": "CASH_RELEASE_ACTION", "required_fields": ["selected_actions", "blocked_actions", "cash_impact", "objective_components", "constraint_utilization", "mip_gap"]},
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
