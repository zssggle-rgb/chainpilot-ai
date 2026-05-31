from __future__ import annotations

import json

from chainpilot_ai.algorithms.quality import evaluate_algorithm_quality


def run() -> dict:
    return evaluate_algorithm_quality(write_report=True)


if __name__ == "__main__":
    print(json.dumps(run(), ensure_ascii=False, indent=2))
