from __future__ import annotations


def calculate_cash_release(before_amount: float, after_amount: float) -> float:
    return round(float(before_amount) - float(after_amount), 2)
