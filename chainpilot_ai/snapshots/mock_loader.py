from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MOCK_SAP_SNAPSHOT_PATH = ROOT / "demo_data" / "mock_sap_snapshot_v1.json"


def load_mock_sap_snapshot(path: str | Path | None = None) -> dict[str, Any]:
    snapshot_path = Path(path) if path else DEFAULT_MOCK_SAP_SNAPSHOT_PATH
    with snapshot_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
