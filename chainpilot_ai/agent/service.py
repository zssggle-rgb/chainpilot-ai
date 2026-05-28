from __future__ import annotations


AGENT_STATES = (
    "CREATED",
    "PARSE_USER_GOAL",
    "BUILD_SCENARIO_CONSTRAINTS",
    "CHECK_DATA_QUALITY",
    "RUN_OPTIMIZATION",
    "RUN_RISK_SIMULATION",
    "CHECK_CONSTRAINTS",
    "GENERATE_ACTION_CARDS",
    "GENERATE_EXPLANATION",
    "CREATE_APPROVAL_PACKAGE",
    "WAITING_FOR_APPROVAL",
    "CREATE_WRITEBACK_DRAFT",
    "MONITOR_EXECUTION",
    "LEARN_FROM_FEEDBACK",
)


def next_state(current_state: str) -> str | None:
    if current_state not in AGENT_STATES:
        raise ValueError(f"Unknown Agent state: {current_state}")
    index = AGENT_STATES.index(current_state)
    if index == len(AGENT_STATES) - 1:
        return None
    return AGENT_STATES[index + 1]
