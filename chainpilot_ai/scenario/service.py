from __future__ import annotations


def build_default_constraint(user_goal: str) -> dict[str, object]:
    if not user_goal.strip():
        raise ValueError("user_goal is required.")
    return {
        "user_goal": user_goal,
        "cash_release_target": None,
        "protected_product_lines": [],
        "preferred_actions": [],
        "source": "phase_0_template",
    }
