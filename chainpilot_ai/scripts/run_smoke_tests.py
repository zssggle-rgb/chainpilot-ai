from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SMOKE_SUMMARY_PATH = ROOT / "tmp" / "phase0_smoke_test_summary.json"


def run() -> dict[str, object]:
    command = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True)
    summary = {
        "ok": completed.returncode == 0,
        "command": " ".join(command),
        "returncode": completed.returncode,
        "summary": "phase 0 smoke tests passed" if completed.returncode == 0 else "phase 0 smoke tests failed",
        "stdout": completed.stdout[-4000:],
        "stderr": completed.stderr[-4000:],
    }
    SMOKE_SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SMOKE_SUMMARY_PATH.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)
    return summary


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
