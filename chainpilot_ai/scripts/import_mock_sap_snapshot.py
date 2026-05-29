from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from chainpilot_ai.snapshots.mock_loader import DEFAULT_MOCK_SAP_SNAPSHOT_PATH, load_mock_sap_snapshot
from chainpilot_ai.snapshots.snapshot_service import import_mock_snapshot
from chainpilot_ai.snapshots.validators import validate_mock_sap_snapshot

ROOT = Path(__file__).resolve().parents[2]
LOCAL_IMPORT_SUMMARY_PATH = ROOT / "tmp" / "mock_sap_snapshot_import_summary.json"


def run(path: str | None = None, dry_run: bool = False) -> dict[str, Any]:
    data = load_mock_sap_snapshot(path or DEFAULT_MOCK_SAP_SNAPSHOT_PATH)
    validation = validate_mock_sap_snapshot(data)
    if not validation["ok"]:
        return {"ok": False, "validation": validation}
    result = import_mock_snapshot(data, dry_run=dry_run)
    LOCAL_IMPORT_SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_IMPORT_SUMMARY_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run(dry_run=True), ensure_ascii=False, indent=2, default=str))
