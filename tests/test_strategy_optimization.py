from __future__ import annotations

from chainpilot_ai.strategy.backtest import run_strategy_backtest, tune_strategy_presets
from chainpilot_ai.strategy.mock_history import generate_mock_history
from chainpilot_ai.strategy.policy import scenario_from_strategy, strategy_presets
from chainpilot_ai.strategy.service import get_strategy_optimization_dashboard


def test_strategy_presets_are_draft_only() -> None:
    strategies = strategy_presets()
    assert [strategy["strategy_type"] for strategy in strategies] == ["Conservative", "Recommended", "Aggressive"]
    for strategy in strategies:
        scenario = scenario_from_strategy(strategy)
        assert scenario["sap_writeback_mode"] == "draft_only"
        assert scenario["shortage_thresholds"]["AX"]["shortage_alert_threshold"] < scenario["shortage_thresholds"]["CZ"]["shortage_alert_threshold"]


def test_mock_history_contains_actual_outcomes() -> None:
    history = generate_mock_history(history_days=45, sample_interval_days=14)
    assert len(history) >= 4
    assert history[0]["snapshot"]["source_system"] == "SAP_MOCK_HISTORY"
    assert "_actual_outcomes" in history[0]
    assert "shortage_materials" in history[0]["_actual_outcomes"]


def test_backtest_returns_strategy_metrics() -> None:
    strategy = strategy_presets()[1]
    result = run_strategy_backtest(strategy, history_days=45, sample_interval_days=14)
    assert result["strategy_id"] == strategy["strategy_id"]
    assert result["sample_count"] >= 4
    assert 0 <= result["recall_rate"] <= 1
    assert 0 <= result["precision_rate"] <= 1
    assert result["cash_release_total"] > 0
    assert result["hard_constraint_violations"] == 0


def test_strategy_dashboard_compares_three_presets() -> None:
    dashboard = get_strategy_optimization_dashboard(45)
    assert dashboard["ok"]
    assert len(dashboard["strategies"]) == 3
    assert len(dashboard["backtests"]) == 3
    assert dashboard["requires_human_approval"] is True
    assert dashboard["recommended_strategy_id"]


def test_tune_strategy_presets_recommends_existing_strategy() -> None:
    tuned = tune_strategy_presets(history_days=45)
    strategy_ids = {strategy["strategy_id"] for strategy in tuned["strategies"]}
    assert tuned["recommended_strategy_id"] in strategy_ids
