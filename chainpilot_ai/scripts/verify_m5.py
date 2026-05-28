from __future__ import annotations

import json
from pathlib import Path

from chainpilot_ai.learning.service import build_rule_adjustment, calculate_learning_metrics, seed_learning_mock_data

ROOT = Path(__file__).resolve().parents[2]

M5_DOCTYPE_FILES = [
    "learning_metric_snapshot/learning_metric_snapshot.json",
    "shortage_event/shortage_event.json",
    "rule_weight_adjustment/rule_weight_adjustment.json",
]


def _status(status: str, evidence: str, notes: str = "") -> dict[str, str]:
    return {"status": status, "evidence": evidence, "notes": notes}


def check_m5_doctype_contract() -> dict[str, str]:
    base = ROOT / "chainpilot_ai" / "chainpilot_ai" / "doctype"
    missing = [relative for relative in M5_DOCTYPE_FILES if not (base / relative).exists()]
    if missing:
        return _status("Fail", str(base), json.dumps({"missing": missing}, ensure_ascii=False))
    for relative in M5_DOCTYPE_FILES:
        payload = json.loads((base / relative).read_text(encoding="utf-8"))
        if payload.get("doctype") != "DocType" or not payload.get("fields"):
            return _status("Fail", str(base / relative), "Invalid DocType JSON.")
    return _status("Pass", str(base), f"{len(M5_DOCTYPE_FILES)} M5 DocType JSON files")


def check_m5_metrics() -> dict[str, str]:
    metrics = calculate_learning_metrics(
        packages=[{"status": "Approved"}, {"status": "Rejected"}],
        feedback=[
            {"feedback_type": "Rejected", "reason": "Supplier confirmation missing"},
            {"feedback_type": "Supplier Feedback", "supplier_response": "Accepted"},
        ],
        executions=[{"expected_cash_release": 100, "realized_cash_release": 80}],
        communications=[{"status": "Sent"}],
        shortage_events=[{"event_id": "SHE-1"}],
    )
    if metrics["adoption_rate"] == 50.0 and metrics["supplier_acceptance_rate"] == 100.0 and metrics["realization_rate"] == 80.0:
        return _status("Pass", "chainpilot_ai.learning.service.calculate_learning_metrics", json.dumps(metrics, ensure_ascii=False))
    return _status("Fail", "chainpilot_ai.learning.service.calculate_learning_metrics", json.dumps(metrics, ensure_ascii=False))


def check_m5_rule_adjustment() -> dict[str, str]:
    adjustment = build_rule_adjustment(
        {
            "signal_id": "LSIG-X",
            "target_type": "Action Type",
            "target": "DELAY_UNCONFIRMED_PO",
            "reason": "Supplier rejected delay.",
            "suggested_weight_delta": -0.1,
        },
        1.0,
    )
    if adjustment["status"] == "Draft" and adjustment["suggested_weight"] < adjustment["current_weight"]:
        return _status("Pass", "chainpilot_ai.learning.service.build_rule_adjustment", json.dumps(adjustment, ensure_ascii=False))
    return _status("Fail", "chainpilot_ai.learning.service.build_rule_adjustment", json.dumps(adjustment, ensure_ascii=False))


def check_m5_page_assets() -> dict[str, str]:
    page_js = ROOT / "chainpilot_ai" / "chainpilot_ai" / "page" / "learning_center" / "learning_center.js"
    workspace = ROOT / "chainpilot_ai" / "fixtures" / "workspace.json"
    text = page_js.read_text(encoding="utf-8") if page_js.exists() else ""
    required = ["学习中心", "seed_learning_mock_data", "规则调权草稿", "缺料事件"]
    if all(token in text for token in required) and "learning-center" in workspace.read_text(encoding="utf-8"):
        return _status("Pass", f"{page_js}; {workspace}", "")
    return _status("Fail", f"{page_js}; {workspace}", "M5 Learning Center route or core actions missing.")


def check_m5_mock_seed() -> dict[str, str]:
    dashboard = seed_learning_mock_data()
    if dashboard["ok"] and dashboard["metrics"]["shortage_event_count"] >= 1 and dashboard["adjustments"]:
        return _status("Pass", "chainpilot_ai.learning.service.seed_learning_mock_data", json.dumps(dashboard["metrics"], ensure_ascii=False))
    return _status("Fail", "chainpilot_ai.learning.service.seed_learning_mock_data", json.dumps(dashboard, ensure_ascii=False))


CHECKS = {
    "M5-LEARNING-001": check_m5_doctype_contract,
    "M5-LEARNING-002": check_m5_metrics,
    "M5-LEARNING-003": check_m5_rule_adjustment,
    "M5-LEARNING-004": check_m5_page_assets,
    "M5-LEARNING-005": check_m5_mock_seed,
}


def run() -> dict[str, object]:
    results = {name: check() for name, check in CHECKS.items()}
    counts: dict[str, int] = {}
    for result in results.values():
        counts[result["status"]] = counts.get(result["status"], 0) + 1
    return {"ok": counts.get("Fail", 0) == 0, "counts": counts, "results": results}


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
