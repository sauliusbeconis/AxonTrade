from __future__ import annotations

import pytest

from axontrade.research import (
    SIGNAL_AUCTION_REGIME_FILTER_SWEEP_HEADER,
    SignalAuctionRegimeFilterExperimentError,
    run_signal_auction_regime_filter_sweep,
    run_signal_auction_regime_filter_train_holdout_sweep,
    run_signal_auction_regime_filter_walk_forward_sweep,
)


def _regime_row(
    index: int,
    *,
    trade_date: str,
    direction: str = "long",
    reward_risk: float = 2.0,
    minutes: int = 90,
    session_range: float = 20.0,
    fade_edge_score: float = 0.75,
    vwap_stretch: float = 5.0,
    open_stretch: float = 5.0,
    exit_reason: str = "target_hit",
    net_usd: float = 100.0,
) -> dict[str, object]:
    return {
        "outcome_id": f"outcome-{index}",
        "signal_id": f"test_strategy_ESU26-CME_{index}",
        "symbol": "ESU26-CME",
        "direction": direction,
        "entry_time": f"{trade_date} 10:00:00",
        "minutes_after_rth_open": minutes,
        "original_reward_risk": reward_risk,
        "session_range_points": session_range,
        "fade_edge_score": fade_edge_score,
        "direction_aware_vwap_stretch_points": vwap_stretch,
        "direction_aware_open_stretch_points": open_stretch,
        "exit_reason": exit_reason,
        "net_usd": net_usd,
    }


def test_runs_signal_auction_regime_filter_sweep() -> None:
    rows = [
        _regime_row(1, trade_date="2026-06-10", net_usd=100),
        _regime_row(
            2,
            trade_date="2026-06-10",
            reward_risk=4,
            exit_reason="stop_hit",
            net_usd=-50,
        ),
        _regime_row(
            3,
            trade_date="2026-06-10",
            vwap_stretch=20,
            exit_reason="stop_hit",
            net_usd=-50,
        ),
    ]

    experiment_rows = run_signal_auction_regime_filter_sweep(
        rows,
        max_original_reward_risks=[3],
        min_minutes_after_rth_open_values=[0],
        max_minutes_after_rth_open_values=[180],
        max_session_range_points_values=[30],
        max_fade_edge_scores=[0.85],
        max_vwap_stretch_points_values=[10],
        max_open_stretch_points_values=[10],
        direction_filters=["all"],
    )

    assert list(experiment_rows[0].keys()) == SIGNAL_AUCTION_REGIME_FILTER_SWEEP_HEADER
    assert experiment_rows[0]["evaluated_trades"] == 1
    assert experiment_rows[0]["target_hits"] == 1
    assert experiment_rows[0]["net_usd"] == "100"


def test_runs_signal_auction_regime_train_holdout_sweep() -> None:
    rows = [
        _regime_row(1, trade_date="2026-06-10", reward_risk=2, net_usd=100),
        _regime_row(2, trade_date="2026-06-11", reward_risk=2, net_usd=100),
        _regime_row(
            3,
            trade_date="2026-06-12",
            reward_risk=4,
            exit_reason="stop_hit",
            net_usd=-150,
        ),
    ]

    split_rows = run_signal_auction_regime_filter_train_holdout_sweep(
        rows,
        train_date_count=2,
        max_original_reward_risks=[2, 4],
        min_minutes_after_rth_open_values=[0],
        max_minutes_after_rth_open_values=[390],
        max_session_range_points_values=[999],
        max_fade_edge_scores=[1],
        max_vwap_stretch_points_values=[999],
        max_open_stretch_points_values=[999],
        minimum_train_trades=2,
    )

    selected_train = next(
        row
        for row in split_rows
        if row["sample"] == "train" and row["selected_on_train"] == "true"
    )
    selected_holdout = next(
        row
        for row in split_rows
        if row["sample"] == "holdout" and row["selected_on_train"] == "true"
    )

    assert selected_train["max_original_reward_risk"] == "2"
    assert selected_train["net_usd"] == "200"
    assert selected_holdout["evaluated_trades"] == 0


def test_runs_signal_auction_regime_walk_forward_sweep() -> None:
    rows = [
        _regime_row(1, trade_date="2026-06-10", reward_risk=2, net_usd=100),
        _regime_row(2, trade_date="2026-06-11", reward_risk=2, net_usd=100),
        _regime_row(
            3,
            trade_date="2026-06-11",
            reward_risk=4,
            exit_reason="stop_hit",
            net_usd=-150,
        ),
        _regime_row(4, trade_date="2026-06-12", reward_risk=2, net_usd=100),
    ]

    split_rows = run_signal_auction_regime_filter_walk_forward_sweep(
        rows,
        train_date_count=2,
        holdout_date_count=1,
        max_original_reward_risks=[2, 4],
        min_minutes_after_rth_open_values=[0],
        max_minutes_after_rth_open_values=[390],
        max_session_range_points_values=[999],
        max_fade_edge_scores=[1],
        max_vwap_stretch_points_values=[999],
        max_open_stretch_points_values=[999],
        minimum_train_trades=2,
    )

    assert [row["sample"] for row in split_rows] == ["train", "holdout"]
    assert all(row["selected_on_train"] == "true" for row in split_rows)
    assert split_rows[0]["max_original_reward_risk"] == "2"
    assert split_rows[1]["evaluated_trades"] == 1
    assert split_rows[1]["net_usd"] == "100"


def test_signal_auction_regime_filter_requires_valid_time_window() -> None:
    with pytest.raises(SignalAuctionRegimeFilterExperimentError, match="min/max minute"):
        run_signal_auction_regime_filter_sweep(
            [],
            max_original_reward_risks=[2],
            min_minutes_after_rth_open_values=[180],
            max_minutes_after_rth_open_values=[90],
            max_session_range_points_values=[999],
            max_fade_edge_scores=[1],
            max_vwap_stretch_points_values=[999],
            max_open_stretch_points_values=[999],
        )
