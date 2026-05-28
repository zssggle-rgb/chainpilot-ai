from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from chainpilot_ai.sap_connector.service import get_entity_set, test_connection
from chainpilot_ai.scripts.import_demo_data import DEFAULT_DEMO_PATH, load_demo_data, validate_demo_data


ROOT = Path(__file__).resolve().parents[2]
VERIFY_REPORT_PATH = ROOT / "tmp" / "m1_verify_report.json"


def _status(status: str, evidence: str, notes: str = "") -> dict[str, str]:
    return {"status": status, "evidence": evidence, "notes": notes}


def check_m1_01_demo_contract() -> dict[str, str]:
    validation = validate_demo_data(load_demo_data(DEFAULT_DEMO_PATH))
    if validation["ok"] and validation["counts"]["scenarios"] >= 1 and validation["counts"]["recommendations"] >= 10:
        return _status("Pass", str(DEFAULT_DEMO_PATH), json.dumps(validation["counts"], ensure_ascii=False))
    return _status("Fail", str(DEFAULT_DEMO_PATH), "; ".join(validation["errors"]))


def check_m1_02_commercial_ui_assets() -> dict[str, str]:
    css_path = ROOT / "chainpilot_ai" / "public" / "css" / "chainpilot_ai.css"
    command_center = ROOT / "chainpilot_ai" / "chainpilot_ai" / "page" / "chainpilot_ai_command_center" / "chainpilot_ai_command_center.js"
    action_inbox = ROOT / "chainpilot_ai" / "chainpilot_ai" / "page" / "action_inbox" / "action_inbox.js"
    scenario_studio = ROOT / "chainpilot_ai" / "chainpilot_ai" / "page" / "scenario_studio" / "scenario_studio.js"
    detail_js = ROOT / "chainpilot_ai" / "chainpilot_ai" / "doctype" / "recommendation" / "recommendation.js"
    required = {
        css_path: [".chainpilot-hero", ".chainpilot-action-card", ".chainpilot-detail-panel"],
        command_center: ["5月采购优化决策台", "方案组合", "高价值动作"],
        action_inbox: ["推荐动作收件箱", "全部动作", "风险关注"],
        scenario_studio: ["Scenario Studio", "业务目标", "方案对比"],
        detail_js: ["建议详情", "证据", "约束校验", "AI 解释草稿"],
    }
    missing: list[str] = []
    for path, tokens in required.items():
        if not path.exists():
            missing.append(str(path))
            continue
        text = path.read_text(encoding="utf-8")
        missing.extend(f"{path}: {token}" for token in tokens if token not in text)
    if missing:
        return _status("Fail", "M1 UI assets", "; ".join(missing))
    return _status("Pass", "commercial Command Center, Action Inbox, Recommendation Detail assets")


def check_m1_03_no_phase0_placeholder() -> dict[str, str]:
    paths = [
        ROOT / "chainpilot_ai" / "chainpilot_ai" / "page" / "chainpilot_ai_command_center" / "chainpilot_ai_command_center.js",
        ROOT / "chainpilot_ai" / "chainpilot_ai" / "page" / "action_inbox" / "action_inbox.js",
    ]
    placeholders = ["Phase 0 Demo Control Tower", "Phase 0 inbox skeleton", "frappe-card text-center"]
    found = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        found.extend(f"{path}: {token}" for token in placeholders if token in text)
    if found:
        return _status("Fail", "placeholder scan", "; ".join(found))
    return _status("Pass", "page placeholder scan", "No Phase 0 placeholder UI copy remains in M1 pages.")


def check_m1_04_sap_mock_adapter() -> dict[str, str]:
    connection = test_connection({"mode": "mock"})
    pr_rows = get_entity_set("purchase_requisition_items", {"mode": "mock", "plant": "CN01"})
    non_mock_rows = get_entity_set("purchase_requisition_items")
    if connection["ok"] and pr_rows and non_mock_rows == []:
        return _status("Pass", "chainpilot_ai.sap_connector.service", f"{connection['status']}; mock PR rows={len(pr_rows)}")
    return _status("Fail", "chainpilot_ai.sap_connector.service", json.dumps({"connection": connection, "pr_rows": pr_rows, "non_mock_rows": non_mock_rows}, ensure_ascii=False))


def check_m1_05_scenario_doctype() -> dict[str, str]:
    scenario_path = ROOT / "chainpilot_ai" / "chainpilot_ai" / "doctype" / "scenario" / "scenario.json"
    result_path = ROOT / "chainpilot_ai" / "chainpilot_ai" / "doctype" / "scenario_result" / "scenario_result.json"
    workspace_path = ROOT / "chainpilot_ai" / "fixtures" / "workspace.json"
    required = {
        scenario_path: ["Scenario ID", "Business Goal", "Constraint JSON"],
        result_path: ["scenario_id", "\"options\": \"Scenario\""],
        workspace_path: ["Scenario Studio", "scenario-studio", "Scenario"],
    }
    missing: list[str] = []
    for path, tokens in required.items():
        if not path.exists():
            missing.append(str(path))
            continue
        text = path.read_text(encoding="utf-8")
        missing.extend(f"{path}: {token}" for token in tokens if token not in text)
    if missing:
        return _status("Fail", "Scenario Studio contract", "; ".join(missing))
    return _status("Pass", "Scenario DocType, Scenario Result link, Workspace shortcut")


CHECKS = {
    "M1-UI-001": check_m1_01_demo_contract,
    "M1-UI-002": check_m1_02_commercial_ui_assets,
    "M1-UI-003": check_m1_03_no_phase0_placeholder,
    "M1-SAP-001": check_m1_04_sap_mock_adapter,
    "M1-SCENARIO-001": check_m1_05_scenario_doctype,
}


def run() -> dict[str, Any]:
    results = {check_id: check() for check_id, check in CHECKS.items()}
    counts: dict[str, int] = {}
    for result in results.values():
        counts[result["status"]] = counts.get(result["status"], 0) + 1
    report = {"ok": all(result["status"] == "Pass" for result in results.values()), "counts": counts, "results": results}
    VERIFY_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with VERIFY_REPORT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return report


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
