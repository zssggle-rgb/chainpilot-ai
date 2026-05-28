from __future__ import annotations


def summarize_package(recommendation_count: int, total_cash_release: float) -> dict[str, object]:
    if recommendation_count < 0:
        raise ValueError("recommendation_count cannot be negative.")
    return {
        "recommendation_count": recommendation_count,
        "total_cash_release": round(float(total_cash_release), 2),
    }
