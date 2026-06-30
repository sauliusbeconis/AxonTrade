from __future__ import annotations

import pytest

from axontrade.research import (
    SIGNAL_HEALTH_GATE_SWEEP_HEADER,
    SIGNAL_HEALTH_GATE_WALK_FORWARD_HEADER,
    SignalHealthGateExperimentError,
    run_signal_health_gate_sweep,
    run_signal_health_gate_walk_forward_sweep,
)


def _diagnostic_row(
    index: int,
    *,
    entry_time: str,
    direction: str = "long",
    exit_reason: str = "target_hit",
    net_usd: float = 100.0,
) -> dict[str, object]:
    return {
        "diagnostic_id": f"diagnostic-{index}",
        "outcome_id": f"outcome-{index}",
        "signal_id": f"test_strategy_ESU26-CME_{index}",
        "symbol": "ESU26-CME",
        "direction": direction,
        "entry_time": entry_time,
        "exit_reason": exit_reason,
        "net_usd": net_usd,
    }


def _loss(index: int, entry_time: str, net_usd: float = -100.0) -> dict[str, object]:
    return _diagnostic_row(
        index,
        entry_time=entry_time,
        exit_reason="stop_hit",
        net_usd=net_usd,
    )


def test_health_gate_blocks_rest_of_day_after_daily_loss_limit() -> None:
    rows = [
        _loss(1, "2026-06-10 10:00:00", -200),
        _loss(2, "2026-06-10 11:00:00", -100),
        _diagnostic_row(3, entry_time="2026-06-10 12:00:00", net_usd=500),
    ]

    experiment_rows = run_signal_health_gate_sweep(
        rows,
        maximum_daily_losses=[999],
        daily_loss_limits_usd=[150],
        maximum_consecutive_losses=[999],
        consecutive_loss_pause_trade_dates=[0],
        maximum_equity_drawdowns_usd=[999999],
        drawdown_pause_trade_dates=[0],
    )

    assert list(experiment_rows[0].keys()) == SIGNAL_HEALTH_GATE_SWEEP_HEADER
    assert experiment_rows[0]["accepted_trades"] == 1
    assert experiment_rows[0]["skipped_trades"] == 2
    assert experiment_rows[0]["losses"] == 1
    assert experiment_rows[0]["skipped_losses"] == 1
    assert experiment_rows[0]["skipped_target_hits"] == 1
    assert experiment_rows[0]["net_usd"] == "-200"
    assert experiment_rows[0]["skipped_net_usd"] == "400"


def test_health_gate_pauses_next_trade_date_after_consecutive_loss() -> None:
    rows = [
        _loss(1, "2026-06-10 10:00:00", -100),
        _diagnostic_row(2, entry_time="2026-06-11 10:00:00", net_usd=500),
        _diagnostic_row(3, entry_time="2026-06-12 10:00:00", net_usd=100),
    ]

    experiment_rows = run_signal_health_gate_sweep(
        rows,
        maximum_daily_losses=[999],
        daily_loss_limits_usd=[999999],
        maximum_consecutive_losses=[1],
        consecutive_loss_pause_trade_dates=[1],
        maximum_equity_drawdowns_usd=[999999],
        drawdown_pause_trade_dates=[0],
    )

    assert experiment_rows[0]["accepted_trades"] == 2
    assert experiment_rows[0]["skipped_trades"] == 1
    assert experiment_rows[0]["target_hits"] == 1
    assert experiment_rows[0]["skipped_target_hits"] == 1
    assert experiment_rows[0]["net_usd"] == "0"
    assert experiment_rows[0]["skipped_net_usd"] == "500"


def test_health_gate_counts_scaled_exit_labels() -> None:
    rows = [
        _diagnostic_row(
            1,
            entry_time="2026-06-10 10:00:00",
            exit_reason="runner_target_hit",
            net_usd=718,
        ),
        _diagnostic_row(
            2,
            entry_time="2026-06-10 11:00:00",
            exit_reason="full_stop_hit",
            net_usd=-1032,
        ),
    ]

    experiment_rows = run_signal_health_gate_sweep(
        rows,
        maximum_daily_losses=[999],
        daily_loss_limits_usd=[999999],
        maximum_consecutive_losses=[999],
        consecutive_loss_pause_trade_dates=[0],
        maximum_equity_drawdowns_usd=[999999],
        drawdown_pause_trade_dates=[0],
    )

    assert experiment_rows[0]["target_hits"] == 1
    assert experiment_rows[0]["losses"] == 1
    assert experiment_rows[0]["other_exits"] == 0


def test_health_gate_walk_forward_warms_holdout_state_from_train() -> None:
    rows = [
        _diagnostic_row(1, entry_time="2026-06-10 10:00:00", net_usd=100),
        _diagnostic_row(2, entry_time="2026-06-11 10:00:00", net_usd=100),
        _diagnostic_row(3, entry_time="2026-06-12 10:00:00", net_usd=100),
        _loss(4, "2026-06-13 10:00:00", -100),
        _diagnostic_row(5, entry_time="2026-06-14 10:00:00", net_usd=500),
    ]

    split_rows = run_signal_health_gate_walk_forward_sweep(
        rows,
        train_date_count=4,
        holdout_date_count=1,
        maximum_daily_losses=[999],
        daily_loss_limits_usd=[999999],
        maximum_consecutive_losses=[1],
        consecutive_loss_pause_trade_dates=[1],
        maximum_equity_drawdowns_usd=[999999],
        drawdown_pause_trade_dates=[0],
        minimum_train_accepted_trades=4,
    )

    assert list(split_rows[0].keys()) == SIGNAL_HEALTH_GATE_WALK_FORWARD_HEADER
    assert [row["sample"] for row in split_rows] == ["train", "holdout"]
    assert split_rows[0]["accepted_trades"] == 4
    assert split_rows[1]["state_warmup_rows"] == 4
    assert split_rows[1]["accepted_trades"] == 0
    assert split_rows[1]["skipped_trades"] == 1
    assert split_rows[1]["skipped_target_hits"] == 1
    assert split_rows[1]["selected_on_train"] == "true"


def test_health_gate_walk_forward_supports_nonoverlapping_step() -> None:
    rows = [
        _diagnostic_row(index, entry_time=f"2026-06-{index:02d} 10:00:00")
        for index in range(1, 8)
    ]

    split_rows = run_signal_health_gate_walk_forward_sweep(
        rows,
        train_date_count=2,
        holdout_date_count=2,
        window_step_date_count=2,
        maximum_daily_losses=[999],
        daily_loss_limits_usd=[999999],
        maximum_consecutive_losses=[999],
        consecutive_loss_pause_trade_dates=[0],
        maximum_equity_drawdowns_usd=[999999],
        drawdown_pause_trade_dates=[0],
        minimum_train_accepted_trades=2,
    )

    assert [row["trade_dates"] for row in split_rows if row["sample"] == "holdout"] == [
        "2026-06-03;2026-06-04",
        "2026-06-05;2026-06-06",
    ]


def test_health_gate_walk_forward_requires_enough_dates() -> None:
    with pytest.raises(SignalHealthGateExperimentError, match="train_date_count"):
        run_signal_health_gate_walk_forward_sweep(
            [_diagnostic_row(1, entry_time="2026-06-10 10:00:00")],
            train_date_count=1,
            holdout_date_count=1,
            maximum_daily_losses=[999],
            daily_loss_limits_usd=[999999],
            maximum_consecutive_losses=[999],
            consecutive_loss_pause_trade_dates=[0],
            maximum_equity_drawdowns_usd=[999999],
            drawdown_pause_trade_dates=[0],
        )
