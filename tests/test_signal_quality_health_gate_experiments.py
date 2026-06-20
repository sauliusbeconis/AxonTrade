from __future__ import annotations

import pytest

from axontrade.research import (
    SIGNAL_QUALITY_HEALTH_GATE_WALK_FORWARD_HEADER,
    SignalQualityHealthGateExperimentError,
    run_signal_quality_health_gate_walk_forward_sweep,
)


def _diagnostic_row(
    index: int,
    *,
    trade_date: str,
    direction: str = "long",
    reward_risk: float = 2.0,
    minutes: int = 90,
    sweep_abs_delta: float = 3.0,
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
        "sweep_abs_delta": sweep_abs_delta,
        "exit_reason": exit_reason,
        "net_usd": net_usd,
    }


def test_runs_signal_quality_health_gate_walk_forward_sweep() -> None:
    rows = [
        _diagnostic_row(1, trade_date="2026-06-10", reward_risk=2, net_usd=100),
        _diagnostic_row(2, trade_date="2026-06-11", reward_risk=2, net_usd=100),
        _diagnostic_row(
            3,
            trade_date="2026-06-11",
            reward_risk=4,
            exit_reason="stop_hit",
            net_usd=-150,
        ),
        _diagnostic_row(4, trade_date="2026-06-12", reward_risk=2, net_usd=100),
        _diagnostic_row(
            5,
            trade_date="2026-06-12",
            reward_risk=4,
            exit_reason="stop_hit",
            net_usd=-150,
        ),
    ]

    split_rows = run_signal_quality_health_gate_walk_forward_sweep(
        rows,
        train_date_count=2,
        holdout_date_count=1,
        max_original_reward_risks=[2, 4],
        min_minutes_after_rth_open_values=[0],
        max_minutes_after_rth_open_values=[390],
        max_sweep_abs_deltas=[999],
        maximum_daily_losses=[999],
        daily_loss_limits_usd=[999999],
        maximum_consecutive_losses=[999],
        consecutive_loss_pause_trade_dates=[0],
        maximum_equity_drawdowns_usd=[999999],
        drawdown_pause_trade_dates=[0],
        minimum_train_accepted_trades=2,
    )

    assert list(split_rows[0].keys()) == SIGNAL_QUALITY_HEALTH_GATE_WALK_FORWARD_HEADER
    assert [row["sample"] for row in split_rows] == ["train", "holdout"]
    assert all(row["selected_on_train"] == "true" for row in split_rows)
    assert split_rows[0]["max_original_reward_risk"] == "2"
    assert split_rows[0]["accepted_trades"] == 2
    assert split_rows[0]["net_usd"] == "200"
    assert split_rows[1]["trade_dates"] == "2026-06-12"
    assert split_rows[1]["state_warmup_rows"] == 2
    assert split_rows[1]["accepted_trades"] == 1
    assert split_rows[1]["net_usd"] == "100"


def test_quality_health_gate_warms_holdout_after_selected_filter() -> None:
    rows = [
        _diagnostic_row(1, trade_date="2026-06-10", reward_risk=2, net_usd=100),
        _diagnostic_row(2, trade_date="2026-06-11", reward_risk=2, net_usd=100),
        _diagnostic_row(3, trade_date="2026-06-12", reward_risk=2, net_usd=100),
        _diagnostic_row(
            4,
            trade_date="2026-06-13",
            reward_risk=2,
            exit_reason="stop_hit",
            net_usd=-100,
        ),
        _diagnostic_row(5, trade_date="2026-06-14", reward_risk=2, net_usd=500),
        _diagnostic_row(6, trade_date="2026-06-14", reward_risk=4, net_usd=500),
    ]

    split_rows = run_signal_quality_health_gate_walk_forward_sweep(
        rows,
        train_date_count=4,
        holdout_date_count=1,
        max_original_reward_risks=[2, 4],
        min_minutes_after_rth_open_values=[0],
        max_minutes_after_rth_open_values=[390],
        max_sweep_abs_deltas=[999],
        maximum_daily_losses=[999],
        daily_loss_limits_usd=[999999],
        maximum_consecutive_losses=[1],
        consecutive_loss_pause_trade_dates=[1],
        maximum_equity_drawdowns_usd=[999999],
        drawdown_pause_trade_dates=[0],
        minimum_train_accepted_trades=4,
    )

    assert split_rows[0]["max_original_reward_risk"] == "2"
    assert split_rows[1]["state_warmup_rows"] == 4
    assert split_rows[1]["input_diagnostic_rows"] == 1
    assert split_rows[1]["accepted_trades"] == 0
    assert split_rows[1]["skipped_trades"] == 1
    assert split_rows[1]["skipped_target_hits"] == 1


def test_quality_health_gate_requires_valid_time_window() -> None:
    with pytest.raises(SignalQualityHealthGateExperimentError, match="min/max minute"):
        run_signal_quality_health_gate_walk_forward_sweep(
            [
                _diagnostic_row(1, trade_date="2026-06-10"),
                _diagnostic_row(2, trade_date="2026-06-11"),
            ],
            train_date_count=1,
            holdout_date_count=1,
            max_original_reward_risks=[2],
            min_minutes_after_rth_open_values=[180],
            max_minutes_after_rth_open_values=[90],
            max_sweep_abs_deltas=[999],
            maximum_daily_losses=[999],
            daily_loss_limits_usd=[999999],
            maximum_consecutive_losses=[999],
            consecutive_loss_pause_trade_dates=[0],
            maximum_equity_drawdowns_usd=[999999],
            drawdown_pause_trade_dates=[0],
        )
