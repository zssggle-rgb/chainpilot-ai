from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from chainpilot_ai.scripts.import_demo_data import DEFAULT_DEMO_PATH, LOCAL_IMPORT_SUMMARY_PATH, load_demo_data, validate_demo_data


ROOT = Path(__file__).resolve().parents[2]
VERIFY_REPORT_PATH = ROOT / "tmp" / "phase0_verify_report.json"
SMOKE_SUMMARY_PATH = ROOT / "tmp" / "phase0_smoke_test_summary.json"

REQUIRED_MODULES = [
    "sap_connector",
    "snapshots",
    "scenario",
    "optimization",
    "agent",
    "recommendation",
    "approval",
    "writeback",
    "monitoring",
    "learning",
]

REQUIRED_ROLES = {
    "ChainPilot Admin",
    "ChainPilot Supply Chain Director",
    "ChainPilot Planning Manager",
    "ChainPilot Procurement Manager",
    "ChainPilot Planner",
    "ChainPilot Buyer",
    "ChainPilot Finance BP",
}

REQUIRED_DOCTYPES = {
    "Optimization Session": ROOT / "chainpilot_ai" / "chainpilot_ai" / "doctype" / "optimization_session" / "optimization_session.json",
    "Scenario Result": ROOT / "chainpilot_ai" / "chainpilot_ai" / "doctype" / "scenario_result" / "scenario_result.json",
    "Recommendation": ROOT / "chainpilot_ai" / "chainpilot_ai" / "doctype" / "recommendation" / "recommendation.json",
    "Recommendation Evidence": ROOT / "chainpilot_ai" / "chainpilot_ai" / "doctype" / "recommendation_evidence" / "recommendation_evidence.json",
    "Constraint Check Result": ROOT / "chainpilot_ai" / "chainpilot_ai" / "doctype" / "constraint_check_result" / "constraint_check_result.json",
}

GO_REQUIRED_PASS = {"V-001", "V-002", "V-003", "V-006", "V-007", "V-010", "V-011", "V-012"}
GO_MINIMUM_PARTIAL = {"V-008", "V-009"}
GO_DISALLOWED_STATUSES = {"Fail", "Blocked", "Not Started"}


def _status(status: str, evidence: str, notes: str = "") -> dict[str, str]:
    return {"status": status, "evidence": evidence, "notes": notes}


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def check_v001() -> dict[str, str]:
    product_design = (ROOT / "docs" / "PRODUCT_DESIGN.md").read_text(encoding="utf-8")
    backlog = (ROOT / "docs" / "MVP_IMPLEMENTATION_BACKLOG.md").read_text(encoding="utf-8")
    starter = (ROOT / "docs" / "PHASE_0_STARTER_PACK.md").read_text(encoding="utf-8")
    required = ["PDF 是需求依据", "HTML", "真实 SAP"]
    if all(token in product_design for token in required) and "HTML 报告只作为真实现状参考" in backlog and "HTML 是现状参考" in starter:
        return _status("Pass", "docs/PRODUCT_DESIGN.md, docs/MVP_IMPLEMENTATION_BACKLOG.md, docs/PHASE_0_STARTER_PACK.md")
    return _status("Fail", "documentation boundary check", "Source boundary wording is inconsistent.")


def check_v002() -> dict[str, str]:
    try:
        import frappe  # type: ignore

        if getattr(frappe.local, "site", None) and "chainpilot_ai" in frappe.get_installed_apps():
            frappe.db.sql("select 1")
            return _status("Pass", f"bench site {frappe.local.site}", "chainpilot_ai is installed and database is reachable.")
    except Exception:
        pass

    if not shutil.which("bench"):
        return _status("Blocked", "bench not found", "Install frappe-bench before running bench checks.")
    bench_path = Path("/Users/sjs/chainpilot-ai-bench")
    if bench_path.exists() and (bench_path / "apps" / "frappe").exists():
        return _status("Partial", str(bench_path), "Bench exists; site install/migrate evidence is recorded separately.")
    return _status("Partial", "bench found", "Bench command is installed but project bench has not been initialized.")


def check_v003() -> dict[str, str]:
    missing = [module for module in REQUIRED_MODULES if not (ROOT / "chainpilot_ai" / module).is_dir()]
    if not missing:
        return _status("Pass", "chainpilot_ai module directories")
    return _status("Fail", "chainpilot_ai module directories", f"Missing modules: {', '.join(missing)}")


def check_v004() -> dict[str, str]:
    role_path = ROOT / "chainpilot_ai" / "fixtures" / "role.json"
    roles = {row.get("role_name") for row in _load_json(role_path)}
    missing = sorted(REQUIRED_ROLES - roles)
    if not missing:
        return _status("Pass", str(role_path))
    return _status("Fail", str(role_path), f"Missing roles: {', '.join(missing)}")


def check_v005() -> dict[str, str]:
    workspace_path = ROOT / "chainpilot_ai" / "fixtures" / "workspace.json"
    workspaces = _load_json(workspace_path)
    if any(row.get("name") == "ChainPilot AI" for row in workspaces):
        return _status("Pass", str(workspace_path))
    return _status("Fail", str(workspace_path), "ChainPilot AI Workspace fixture not found.")


def check_v006() -> dict[str, str]:
    missing = [name for name, path in REQUIRED_DOCTYPES.items() if not path.exists()]
    if missing:
        return _status("Fail", "DocType JSON files", f"Missing DocTypes: {', '.join(missing)}")
    invalid = []
    for name, path in REQUIRED_DOCTYPES.items():
        payload = _load_json(path)
        if payload.get("name") != name:
            invalid.append(f"{name}: expected name {name}, got {payload.get('name')}")
    if invalid:
        return _status("Fail", "DocType JSON files", "; ".join(invalid))
    return _status("Pass", ", ".join(str(path) for path in REQUIRED_DOCTYPES.values()))


def check_v007() -> dict[str, str]:
    validation = validate_demo_data(load_demo_data(DEFAULT_DEMO_PATH))
    if validation["ok"]:
        return _status("Pass", str(DEFAULT_DEMO_PATH), json.dumps(validation["counts"], ensure_ascii=False))
    return _status("Fail", str(DEFAULT_DEMO_PATH), "; ".join(validation["errors"]))


def check_v008() -> dict[str, str]:
    if not LOCAL_IMPORT_SUMMARY_PATH.exists():
        return _status("Not Started", str(LOCAL_IMPORT_SUMMARY_PATH), "Run python3 -m chainpilot_ai.scripts.import_demo_data.")
    summary = _load_json(LOCAL_IMPORT_SUMMARY_PATH)
    counts = summary.get("counts", {})
    if (
        summary.get("ok")
        and counts.get("optimization_sessions", 0) >= 1
        and counts.get("scenario_results", 0) >= 3
        and counts.get("recommendations", 0) >= 10
        and counts.get("evidence", 0) >= 10
    ):
        return _status("Pass", str(LOCAL_IMPORT_SUMMARY_PATH), json.dumps(counts, ensure_ascii=False))
    return _status("Fail", str(LOCAL_IMPORT_SUMMARY_PATH), json.dumps(summary, ensure_ascii=False))


def check_v009() -> dict[str, str]:
    required = [
        ROOT / "chainpilot_ai" / "chainpilot_ai" / "page" / "chainpilot_ai_command_center" / "chainpilot_ai_command_center.js",
        ROOT / "chainpilot_ai" / "chainpilot_ai" / "page" / "action_inbox" / "action_inbox.js",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        return _status("Fail", "page skeletons", f"Missing pages: {', '.join(missing)}")
    return _status("Partial", ", ".join(str(path) for path in required), "Runtime screenshot requires a running Frappe site.")


def check_v010() -> dict[str, str]:
    data = load_demo_data(DEFAULT_DEMO_PATH)
    evidence_by_recommendation: dict[str, list[str]] = {}
    for evidence in data["evidence"]:
        evidence_by_recommendation.setdefault(evidence["recommendation_id"], []).append(evidence["evidence_id"])
    missing = [
        recommendation["recommendation_id"]
        for recommendation in data["recommendations"]
        if recommendation["explanation_status"] == "Ready" and not evidence_by_recommendation.get(recommendation["recommendation_id"])
    ]
    if not missing:
        return _status("Pass", str(DEFAULT_DEMO_PATH), "All Ready Recommendations have Evidence.")
    return _status("Fail", str(DEFAULT_DEMO_PATH), f"Ready Recommendations without Evidence: {', '.join(missing)}")


def check_v011() -> dict[str, str]:
    scan_roots = [ROOT / "chainpilot_ai", ROOT / "demo_data", ROOT / "README.md", ROOT / "pyproject.toml"]
    suspicious: list[str] = []
    secret_tokens = (
        "A" + "KIA",
        "BEGIN " + "PRIVATE KEY",
        "sap_" + "password =",
        "api_" + "key =",
        "llm_" + "key =",
        "secret_" + "key =",
    )
    write_tokens = (
        "requests." + "post(",
        "requests." + "put(",
        "requests." + "patch(",
        "." + "delete(",
    )
    for root in scan_roots:
        paths = [root] if root.is_file() else list(root.rglob("*"))
        for path in paths:
            if path.is_dir() or path.suffix in {".pyc", ".png"}:
                continue
            text = path.read_text(encoding="utf-8", errors="ignore")
            for token in secret_tokens + write_tokens:
                if token in text:
                    suspicious.append(f"{path}: {token}")
    if suspicious:
        return _status("Fail", "security scan", "; ".join(suspicious))
    return _status("Pass", "chainpilot_ai/, demo_data/, README.md, pyproject.toml", "No obvious secrets or production SAP write calls found.")


def check_v012() -> dict[str, str]:
    if SMOKE_SUMMARY_PATH.exists():
        summary = _load_json(SMOKE_SUMMARY_PATH)
        if summary.get("ok"):
            return _status("Pass", str(SMOKE_SUMMARY_PATH), summary.get("summary", "smoke tests passed"))
        return _status("Fail", str(SMOKE_SUMMARY_PATH), json.dumps(summary, ensure_ascii=False))
    test_path = ROOT / "tests" / "test_phase_0_contract.py"
    if test_path.exists():
        return _status("Partial", str(test_path), "Smoke test file exists; run python3 -m chainpilot_ai.scripts.run_smoke_tests.")
    return _status("Not Started", str(test_path), "Smoke test file missing.")


CHECKS = {
    "V-001": check_v001,
    "V-002": check_v002,
    "V-003": check_v003,
    "V-004": check_v004,
    "V-005": check_v005,
    "V-006": check_v006,
    "V-007": check_v007,
    "V-008": check_v008,
    "V-009": check_v009,
    "V-010": check_v010,
    "V-011": check_v011,
    "V-012": check_v012,
}


def _meets_go_no_go(results: dict[str, dict[str, str]]) -> bool:
    required_pass_ok = all(results[check_id]["status"] == "Pass" for check_id in GO_REQUIRED_PASS)
    minimum_partial_ok = all(results[check_id]["status"] in {"Pass", "Partial"} for check_id in GO_MINIMUM_PARTIAL)
    no_disallowed_status = all(result["status"] not in GO_DISALLOWED_STATUSES for result in results.values())
    return required_pass_ok and minimum_partial_ok and no_disallowed_status


def run() -> dict[str, Any]:
    results = {check_id: check() for check_id, check in CHECKS.items()}
    counts: dict[str, int] = {}
    for result in results.values():
        counts[result["status"]] = counts.get(result["status"], 0) + 1
    all_pass = all(result["status"] == "Pass" for result in results.values())
    go_no_go_ok = _meets_go_no_go(results)
    report = {
        "ok": go_no_go_ok,
        "all_pass": all_pass,
        "counts": counts,
        "go_no_go": {
            "ok": go_no_go_ok,
            "required_pass": sorted(GO_REQUIRED_PASS),
            "minimum_partial": sorted(GO_MINIMUM_PARTIAL),
            "disallowed_statuses": sorted(GO_DISALLOWED_STATUSES),
        },
        "results": results,
    }
    VERIFY_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with VERIFY_REPORT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return report


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
