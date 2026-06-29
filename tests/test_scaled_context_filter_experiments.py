from __future__ import annotations

import pytest

from axontrade.research import (
    SCALED_CONTEXT_FILTER_SWEEP_HEADER,
    SCALED_CONTEXT_FILTER_WALK_FORWARD_HEADER,
    ScaledContextFilterExperimentError,
    run_scaled_context_filter_sweep,
    run_scaled_context_filter_walk_forward_sweep,
)


def _context_row(
    index: int,
    *,
    trade_date: str,
    direction: str = "long",
    minutes: int = 60,
    risk_ratio: float = 5,
    runner_ratio: float = 4,
    signal_delta_ratio: float = 25,
    volume_ratio: float = 1,
    trade_ratio: float = 1,
    exit_reason: str = "runner_target_hit",
    net_usd: float = 593,
) -> dict[str, object]:
    return {
        "outcome_id": f"outcome-{index}",
        "signal_id": f"strategy_ESU26-CME_{index}",
        "symbol": "ESU26-CME",
        "direction": direction,
        "entry_time": f"{trade_date} 10:00:00",
        "minutes_after_rth_open": minutes,
        "risk_to_average_bar_range": risk_ratio,
        "runner_target_to_average_bar_range": runner_ratio,
        "signal_abs_delta_sum_to_average_abs_delta": signal_delta_ratio,
        "entry_volume_to_average_volume": volume_ratio,
        "entry_trades_to_average_trades": trade_ratio,
        "exit_reason": exit_reason,
        "net_usd": net_usd,
    }


def test_runs_scaled_context_filter_sweep() -> None:
    rows = [
        _context_row(1, trade_date="2026-06-10"),
        _context_row(2, trade_date="2026-06-10", risk_ratio=20, exit_reason="full_stop_hit", net_usd=-1057),
        _context_row(3, trade_date="2026-06-10", volume_ratio=0.25, exit_reason="full_stop_hit", net_usd=-1057),
    ]

    experiment_rows = run_scaled_context_filter_sweep(
        rows,
        min_minutes_after_rth_open_values=[0],
        max_minutes_after_rth_open_values=[120],
        max_risk_to_average_bar_ranges=[8],
        max_runner_target_to_average_bar_ranges=[8],
        min_signal_abs_delta_sum_to_average_abs_deltas=[0],
        max_signal_abs_delta_sum_to_average_abs_deltas=[50],
        min_entry_volume_to_average_volumes=[1],
        min_entry_trades_to_average_trades=[1],
        direction_filters=["all"],
    )

    assert list(experiment_rows[0].keys()) == SCALED_CONTEXT_FILTER_SWEEP_HEADER
    assert experiment_rows[0]["evaluated_trades"] == 1
    assert experiment_rows[0]["runner_target_hits"] == 1
    assert experiment_rows[0]["full_stops"] == 0
    assert experiment_rows[0]["net_usd"] == "593"


def test_runs_scaled_context_filter_walk_forward_sweep() -> None:
    rows = [
        _context_row(1, trade_date="2026-06-10", net_usd=593),
        _context_row(2, trade_date="2026-06-11", net_usd=593),
        _context_row(3, trade_date="2026-06-11", risk_ratio=20, exit_reason="full_stop_hit", net_usd=-1057),
        _context_row(4, trade_date="2026-06-12", net_usd=593),
        _context_row(5, trade_date="2026-06-12", risk_ratio=20, exit_reason="full_stop_hit", net_usd=-1057),
    ]

    split_rows = run_scaled_context_filter_walk_forward_sweep(
        rows,
        train_date_count=2,
        holdout_date_count=1,
        min_minutes_after_rth_open_values=[0],
        max_minutes_after_rth_open_values=[120],
        max_risk_to_average_bar_ranges=[8, 999],
        max_runner_target_to_average_bar_ranges=[8],
        min_signal_abs_delta_sum_to_average_abs_deltas=[0],
        max_signal_abs_delta_sum_to_average_abs_deltas=[50],
        min_entry_volume_to_average_volumes=[0],
        min_entry_trades_to_average_trades=[0],
        minimum_train_trades=2,
    )

    assert list(split_rows[0].keys()) == SCALED_CONTEXT_FILTER_WALK_FORWARD_HEADER
    assert [row["sample"] for row in split_rows] == ["train", "holdout"]
    assert split_rows[0]["selected_on_train"] == "true"
    assert split_rows[0]["max_risk_to_average_bar_range"] == "8"
    assert split_rows[1]["trade_dates"] == "2026-06-12"
    assert split_rows[1]["evaluated_trades"] == 1
    assert split_rows[1]["net_usd"] == "593"


def test_scaled_context_filter_requires_valid_signal_delta_window() -> None:
    with pytest.raises(ScaledContextFilterExperimentError, match="signal delta"):
        run_scaled_context_filter_sweep(
            [],
            min_minutes_after_rth_open_values=[0],
            max_minutes_after_rth_open_values=[120],
            max_risk_to_average_bar_ranges=[8],
            max_runner_target_to_average_bar_ranges=[8],
            min_signal_abs_delta_sum_to_average_abs_deltas=[10],
            max_signal_abs_delta_sum_to_average_abs_deltas=[5],
            min_entry_volume_to_average_volumes=[0],
            min_entry_trades_to_average_trades=[0],
        )
