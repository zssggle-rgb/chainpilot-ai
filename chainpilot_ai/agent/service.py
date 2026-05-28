from __future__ import annotations

import json
from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from chainpilot_ai.scenario.service import parse_user_goal
from chainpilot_ai.scripts.import_demo_data import DEFAULT_DEMO_PATH, load_demo_data

try:
    import frappe
except Exception:  # pragma: no cover - local smoke tests can run without a Frappe site.
    frappe = None


AGENT_STATES = (
    "CREATED",
    "PARSE_USER_GOAL",
    "BUILD_SCENARIO_CONSTRAINTS",
    "CHECK_DATA_QUALITY",
    "RUN_OPTIMIZATION",
    "RUN_RISK_SIMULATION",
    "CHECK_CONSTRAINTS",
    "GENERATE_ACTION_CARDS",
    "GENERATE_EXPLANATION",
    "CREATE_APPROVAL_PACKAGE",
    "WAITING_FOR_APPROVAL",
    "CREATE_WRITEBACK_DRAFT",
    "MONITOR_EXECUTION",
    "LEARN_FROM_FEEDBACK",
)


def _whitelist(fn):
    if frappe:
        return frappe.whitelist()(fn)
    return fn


def _frappe_ready() -> bool:
    try:
        return bool(frappe and getattr(frappe.local, "site", None) and getattr(frappe, "db", None))
    except Exception:
        return False


def _now() -> str:
    if _frappe_ready():
        return str(frappe.utils.now_datetime())
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _unique_id(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    return f"{prefix}-{stamp}"


def next_state(current_state: str) -> str | None:
    if current_state not in AGENT_STATES:
        raise ValueError(f"Unknown Agent state: {current_state}")
    index = AGENT_STATES.index(current_state)
    if index == len(AGENT_STATES) - 1:
        return None
    return AGENT_STATES[index + 1]


def run_agent(user_goal: str, dry_run: bool = False) -> dict[str, Any]:
    """Run the deterministic M3 mock agent from goal parsing to action generation."""
    started_perf = perf_counter()
    agent_run_id = _unique_id("ARUN")
    started_at = _now()
    tool_logs: list[dict[str, Any]] = []

    constraints = _record_tool(tool_logs, agent_run_id, "parse_user_goal", user_goal, lambda: parse_user_goal(user_goal))
    demo_data = load_demo_data(DEFAULT_DEMO_PATH)
    scenario = _record_tool(tool_logs, agent_run_id, "build_scenario_constraints", constraints, lambda: _build_scenario(agent_run_id, constraints, demo_data))
    issues = _record_tool(tool_logs, agent_run_id, "check_data_quality", scenario, lambda: _build_data_quality_issues(agent_run_id))
    scenario_result = _record_tool(tool_logs, agent_run_id, "run_optimization", scenario, lambda: _build_scenario_result(agent_run_id, scenario, constraints, demo_data))
    generated = _record_tool(tool_logs, agent_run_id, "generate_action_cards", scenario_result, lambda: _build_recommendations(agent_run_id, scenario_result, demo_data))
    _record_tool(tool_logs, agent_run_id, "collect_evidence", generated["recommendations"], lambda: generated["evidence"])
    _record_tool(tool_logs, agent_run_id, "explain_recommendation", generated["evidence"], lambda: _explanation_summary(generated["evidence"]))

    output_summary = (
        f"Generated {len(generated['recommendations'])} recommendations, "
        f"{len(generated['checks'])} constraint checks, {len(generated['evidence'])} evidence records."
    )
    result = {
        "ok": True,
        "agent_run_id": agent_run_id,
        "status": "Success",
        "current_state": "GENERATE_EXPLANATION",
        "started_at": started_at,
        "finished_at": _now(),
        "duration_ms": int((perf_counter() - started_perf) * 1000),
        "scenario": scenario,
        "scenario_result": scenario_result,
        "constraints": constraints,
        "recommendations": generated["recommendations"],
        "evidence": generated["evidence"],
        "checks": generated["checks"],
        "issues": issues,
        "tool_logs": tool_logs,
        "output_summary": output_summary,
    }

    if _frappe_ready() and not dry_run:
        _persist_agent_result(result, user_goal)
    return result


@_whitelist
def run_agent_rpc(user_goal: str) -> dict[str, Any]:
    return run_agent(user_goal, dry_run=False)


@_whitelist
def get_agent_dashboard() -> dict[str, Any]:
    if not _frappe_ready():
        return {
            "ok": True,
            "runs": [],
            "tool_logs": [],
            "issues": [],
            "counts": {"Agent Run": 0, "Agent Tool Log": 0, "Data Quality Issue": 0},
        }
    return {
        "ok": True,
        "runs": frappe.get_all(
            "Agent Run",
            fields=["agent_run_id", "scenario_id", "status", "current_state", "user_goal", "output_summary", "started_at", "finished_at"],
            order_by="started_at desc",
            limit=8,
        ),
        "tool_logs": frappe.get_all(
            "Agent Tool Log",
            fields=["tool_log_id", "agent_run", "tool_name", "status", "duration_ms", "output_summary"],
            order_by="modified desc",
            limit=7,
        ),
        "issues": frappe.get_all(
            "Data Quality Issue",
            fields=["issue_id", "agent_run", "issue_type", "severity", "message", "recommendation", "status"],
            order_by="modified desc",
            limit=8,
        ),
        "counts": {
            "Agent Run": frappe.db.count("Agent Run"),
            "Agent Tool Log": frappe.db.count("Agent Tool Log"),
            "Data Quality Issue": frappe.db.count("Data Quality Issue"),
        },
    }


def _record_tool(logs: list[dict[str, Any]], agent_run_id: str, tool_name: str, input_value: Any, fn):
    started = perf_counter()
    try:
        output = fn()
    except Exception as exc:
        logs.append(
            {
                "tool_log_id": _unique_id("TLOG"),
                "agent_run": agent_run_id,
                "tool_name": tool_name,
                "status": "Failed",
                "duration_ms": int((perf_counter() - started) * 1000),
                "input_summary": _summary(input_value),
                "output_summary": "",
                "error_message": str(exc),
            }
        )
        raise
    logs.append(
        {
            "tool_log_id": _unique_id("TLOG"),
            "agent_run": agent_run_id,
            "tool_name": tool_name,
            "status": "Success",
            "duration_ms": int((perf_counter() - started) * 1000),
            "input_summary": _summary(input_value),
            "output_summary": _tool_output_summary(tool_name, output),
            "error_message": "",
        }
    )
    return output


def _build_scenario(agent_run_id: str, constraints: dict[str, Any], demo_data: dict[str, Any]) -> dict[str, Any]:
    session = demo_data["optimization_sessions"][0]
    target = constraints.get("cash_release_target") or 80_000_000
    return {
        "scenario_id": agent_run_id.replace("ARUN", "SCN"),
        "session_id": session["session_id"],
        "scenario_name": "Agent 生成现金释放方案",
        "business_goal": constraints["user_goal"],
        "target_cash_release": target,
        "planning_horizon_start": "2026-06-01",
        "planning_horizon_end": "2026-07-31",
        "constraint_json": json.dumps(constraints, ensure_ascii=False),
        "status": "Generated",
        "owner_role": "ChainPilot Planner",
    }


def _build_scenario_result(agent_run_id: str, scenario: dict[str, Any], constraints: dict[str, Any], demo_data: dict[str, Any]) -> dict[str, Any]:
    session = demo_data["optimization_sessions"][0]
    cash_release = min(float(constraints.get("cash_release_target") or 80_000_000) * 1.08, 193_000_000)
    baseline = float(session["baseline_amount"])
    return {
        "result_id": agent_run_id.replace("ARUN", "RES"),
        "session_id": session["session_id"],
        "scenario_id": scenario["scenario_id"],
        "strategy_name": "Agent 推荐方案",
        "strategy_type": "Recommended",
        "purchase_amount": max(baseline - cash_release, 0),
        "cash_release": cash_release,
        "cash_release_rate": round(cash_release / baseline * 100, 2),
        "risk_level": "Low" if cash_release <= 120_000_000 else "Medium",
        "recommendation_count": 10,
        "ai_recommendation": "优先处理 PR 数量下调和未确认 PO 延期，保持安全库存和冻结期约束。",
    }


def _build_recommendations(agent_run_id: str, scenario_result: dict[str, Any], demo_data: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    recommendations = []
    evidence = []
    checks = []
    for index, rec in enumerate(demo_data["recommendations"][:10], start=1):
        recommendation_id = f"REC-{agent_run_id[-14:]}-{index:03d}"
        copied = {**rec, "recommendation_id": recommendation_id, "result_id": scenario_result["result_id"]}
        copied["approval_status"] = "Pending"
        copied["writeback_status"] = "Not Created"
        copied["explanation_status"] = "Ready"
        recommendations.append(copied)

        evidence_id = f"EVD-{agent_run_id[-14:]}-{index:03d}"
        evidence.append(
            {
                "evidence_id": evidence_id,
                "recommendation_id": recommendation_id,
                "source_type": "Snapshot",
                "source_id": f"SAP_MOCK_{copied['plant']}_{copied['material_code']}",
                "metric_name": "inventory_days_after",
                "metric_value": str(copied.get("inventory_days_after", "")),
                "threshold_value": "28",
                "verdict": "PASS" if float(copied.get("inventory_days_after") or 0) >= 28 else "WARN",
                "summary": "Agent 生成动作已绑定库存覆盖证据。",
            }
        )
        verdict = "PASS_WITH_APPROVAL" if copied["approval_status"] == "Pending" and float(copied.get("cash_release") or 0) >= 20_000_000 else "PASS"
        checks.append(
            {
                "check_id": f"CHK-{agent_run_id[-14:]}-{index:03d}",
                "recommendation_id": recommendation_id,
                "rule_code": "M3_SAFE_STOCK",
                "verdict": verdict,
                "message": "安全库存、冻结期和回写草稿约束已通过；高金额动作需审批。" if verdict == "PASS_WITH_APPROVAL" else "安全库存和冻结期约束已通过。",
                "evidence_id": evidence_id,
            }
        )
    return {"recommendations": recommendations, "evidence": evidence, "checks": checks}


def _build_data_quality_issues(agent_run_id: str) -> list[dict[str, Any]]:
    return [
        {
            "issue_id": agent_run_id.replace("ARUN", "DQI"),
            "agent_run": agent_run_id,
            "issue_type": "Stale Snapshot",
            "severity": "Low",
            "object_type": "SAP Mock Snapshot",
            "object_id": "M2_MOCK",
            "message": "当前为 mock 快照，接入真实 SAP 后需复核快照日期和字段映射。",
            "recommendation": "上线真实 OData 前先运行 M2 同步并比对 PR/PO/库存字段。",
            "status": "Open",
        }
    ]


def _explanation_summary(evidence: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "explanation_status": "Ready" if evidence else "NEED_EVIDENCE",
        "evidence_count": len(evidence),
        "summary": "每条推荐动作均包含 evidence_id，可进入解释和审批链路。",
    }


def _persist_agent_result(result: dict[str, Any], user_goal: str) -> None:
    _insert_doc("Scenario", result["scenario"])
    _insert_doc("Scenario Result", result["scenario_result"])
    run_doc = frappe.get_doc(
        {
            "doctype": "Agent Run",
            "agent_run_id": result["agent_run_id"],
            "scenario_id": result["scenario"]["scenario_id"],
            "status": "Running",
            "current_state": "PARSE_USER_GOAL",
            "user_goal": user_goal,
            "constraint_json": json.dumps(result["constraints"], ensure_ascii=False),
            "started_at": result["started_at"],
        }
    )
    run_doc.insert(ignore_permissions=True)

    for recommendation in result["recommendations"]:
        _insert_doc("Recommendation", recommendation)
    for evidence in result["evidence"]:
        _insert_doc("Recommendation Evidence", evidence)
    for check in result["checks"]:
        _insert_doc("Constraint Check Result", check)
    for issue in result["issues"]:
        _insert_doc("Data Quality Issue", issue)
    for log in result["tool_logs"]:
        _insert_doc("Agent Tool Log", log)

    run_doc.status = result["status"]
    run_doc.current_state = result["current_state"]
    run_doc.output_summary = result["output_summary"]
    run_doc.finished_at = result["finished_at"]
    run_doc.save(ignore_permissions=True)
    frappe.db.commit()


def _insert_doc(doctype: str, payload: dict[str, Any]) -> str:
    name_field = {
        "Scenario": "scenario_id",
        "Scenario Result": "result_id",
        "Recommendation": "recommendation_id",
        "Recommendation Evidence": "evidence_id",
        "Constraint Check Result": "check_id",
        "Data Quality Issue": "issue_id",
        "Agent Tool Log": "tool_log_id",
    }[doctype]
    existing = frappe.db.exists(doctype, payload[name_field])
    if existing:
        doc = frappe.get_doc(doctype, existing)
        doc.update(payload)
        doc.save(ignore_permissions=True)
        return doc.name
    doc = frappe.get_doc({"doctype": doctype, **payload})
    doc.insert(ignore_permissions=True)
    return doc.name


def _summary(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, default=str)
    return text[:500]


def _tool_output_summary(tool_name: str, output: Any) -> str:
    if tool_name == "parse_user_goal":
        target = output.get("cash_release_target") or 0
        protected = ",".join(output.get("protected_product_lines") or []) or "-"
        actions = ",".join(output.get("preferred_actions") or []) or "-"
        return f"目标释放 {target:,.0f}；保护品类 {protected}；优先动作 {actions}。"
    if tool_name == "build_scenario_constraints":
        return f"生成场景 {output.get('scenario_id')}，约束模式 draft_only。"
    if tool_name == "check_data_quality":
        return f"发现 {len(output)} 条数据质量提示，最高严重级别 Low。"
    if tool_name == "run_optimization":
        return f"生成 {output.get('strategy_name')}，预计释放 {float(output.get('cash_release') or 0):,.0f}，风险 {output.get('risk_level')}。"
    if tool_name == "generate_action_cards":
        return f"生成 {len(output.get('recommendations') or [])} 条动作、{len(output.get('checks') or [])} 条约束校验。"
    if tool_name == "collect_evidence":
        return f"收集 {len(output)} 条 evidence_id，覆盖每条推荐动作。"
    if tool_name == "explain_recommendation":
        return str(output.get("summary") or "")
    return _summary(output)
