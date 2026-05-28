from __future__ import annotations

import json
from pathlib import Path

from chainpilot_ai.agent.service import run_agent
from chainpilot_ai.scenario.service import parse_user_goal, validate_constraint_schema

ROOT = Path(__file__).resolve().parents[2]

M3_DOCTYPE_FILES = [
    "agent_run/agent_run.json",
    "agent_tool_log/agent_tool_log.json",
    "data_quality_issue/data_quality_issue.json",
]


def _status(status: str, evidence: str, notes: str = "") -> dict[str, str]:
    return {"status": status, "evidence": evidence, "notes": notes}


def check_m3_doctype_contract() -> dict[str, str]:
    base = ROOT / "chainpilot_ai" / "chainpilot_ai" / "doctype"
    missing = [relative for relative in M3_DOCTYPE_FILES if not (base / relative).exists()]
    if missing:
        return _status("Fail", str(base), json.dumps({"missing": missing}, ensure_ascii=False))
    for relative in M3_DOCTYPE_FILES:
        payload = json.loads((base / relative).read_text(encoding="utf-8"))
        if payload.get("doctype") != "DocType" or not payload.get("fields"):
            return _status("Fail", str(base / relative), "Invalid DocType JSON.")
    return _status("Pass", str(base), f"{len(M3_DOCTYPE_FILES)} M3 DocType JSON files")


def check_m3_goal_parser() -> dict[str, str]:
    parsed = parse_user_goal("释放 8000 万，不影响空调，优先改 PR，并保持安全库存不低于 28 天。")
    if parsed["cash_release_target"] == 80_000_000 and "空调" in parsed["protected_product_lines"] and "REDUCE_PR_QTY" in parsed["preferred_actions"]:
        return _status("Pass", "chainpilot_ai.scenario.service.parse_user_goal", json.dumps(parsed, ensure_ascii=False))
    return _status("Fail", "chainpilot_ai.scenario.service.parse_user_goal", json.dumps(parsed, ensure_ascii=False))


def check_m3_constraint_schema() -> dict[str, str]:
    try:
        validate_constraint_schema({"user_goal": "x", "sap_writeback_mode": "direct_write"})
    except ValueError as exc:
        if "draft_only" in str(exc):
            return _status("Pass", "chainpilot_ai.scenario.service.validate_constraint_schema", str(exc))
    return _status("Fail", "chainpilot_ai.scenario.service.validate_constraint_schema", "Invalid writeback mode was not rejected.")


def check_m3_agent_run() -> dict[str, str]:
    result = run_agent("释放 8000 万，不影响空调，优先改 PR，并保持安全库存不低于 28 天。", dry_run=True)
    ok = (
        result["ok"]
        and len(result["recommendations"]) >= 10
        and len(result["evidence"]) >= 10
        and len(result["checks"]) >= 10
        and len(result["tool_logs"]) >= 6
        and result["issues"]
    )
    notes = json.dumps(
        {
            "agent_run_id": result["agent_run_id"],
            "recommendations": len(result["recommendations"]),
            "evidence": len(result["evidence"]),
            "checks": len(result["checks"]),
            "tool_logs": len(result["tool_logs"]),
            "issues": len(result["issues"]),
        },
        ensure_ascii=False,
    )
    return _status("Pass" if ok else "Fail", "chainpilot_ai.agent.service.run_agent", notes)


def check_m3_console_assets() -> dict[str, str]:
    page_js = ROOT / "chainpilot_ai" / "chainpilot_ai" / "page" / "ai_copilot" / "ai_copilot.js"
    workspace = ROOT / "chainpilot_ai" / "fixtures" / "workspace.json"
    text = page_js.read_text(encoding="utf-8") if page_js.exists() else ""
    required = ["智能助手", "run_agent_rpc", "运行历史", "工具调用", "数据质量提示"]
    if all(token in text for token in required) and "ai-copilot" in workspace.read_text(encoding="utf-8"):
        return _status("Pass", f"{page_js}; {workspace}", "")
    return _status("Fail", f"{page_js}; {workspace}", "M3 Copilot route or core copy missing.")


CHECKS = {
    "M3-AGENT-001": check_m3_doctype_contract,
    "M3-AGENT-002": check_m3_goal_parser,
    "M3-AGENT-003": check_m3_constraint_schema,
    "M3-AGENT-004": check_m3_agent_run,
    "M3-AGENT-005": check_m3_console_assets,
}


def run() -> dict[str, object]:
    results = {name: check() for name, check in CHECKS.items()}
    counts: dict[str, int] = {}
    for result in results.values():
        counts[result["status"]] = counts.get(result["status"], 0) + 1
    return {"ok": counts.get("Fail", 0) == 0, "counts": counts, "results": results}


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
