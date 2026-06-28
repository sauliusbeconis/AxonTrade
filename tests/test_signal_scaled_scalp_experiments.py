from __future__ import annotations

import pytest

from axontrade.research import (
    SIGNAL_SCALED_SCALP_SWEEP_HEADER,
    SIGNAL_SCALED_SCALP_WALK_FORWARD_HEADER,
    SignalScaledScalpExperimentError,
    evaluate_signal_scaled_scalp_outcomes,
    run_signal_scaled_scalp_sweep,
    run_signal_scaled_scalp_walk_forward_sweep,
)


def _bar(
    bar_index: int,
    *,
    timestamp: str,
    high: float,
    low: float,
    close: float,
) -> dict[str, object]:
    return {
        "timestamp": timestamp,
        "symbol": "ESU26-CME",
        "bar_index": bar_index,
        "high": high,
        "low": low,
        "close": close,
    }


def _candidate(direction: str = "long") -> dict[str, object]:
    return {
        "event_type": "candidate_signal",
        "event_key": f"ESU26-CME:1:0:test:candidate_signal:{direction}",
        "strategy_id": "test_strategy",
        "signal_id": f"test_strategy_ESU26-CME_{direction}_0",
        "symbol": "ESU26-CME",
        "bar_index": 0,
        "bar_start_time": "2026-06-19 10:00:00",
        "direction": direction,
        "signal_price": "100",
    }


def _candidate_on(trade_date: str) -> dict[str, object]:
    candidate = _candidate()
    candidate["event_key"] = f"ESU26-CME:1:{trade_date}:test:candidate_signal:long"
    candidate["signal_id"] = f"test_strategy_ESU26-CME_{trade_date}"
    candidate["bar_start_time"] = f"{trade_date} 10:00:00"
    return candidate


def test_scaled_scalp_hits_runner_target_after_first_target() -> None:
    bars = [
        _bar(0, timestamp="2026-06-19 10:00:00", high=100, low=99.75, close=100),
        _bar(1, timestamp="2026-06-19 10:01:00", high=101.25, low=100.5, close=101),
        _bar(2, timestamp="2026-06-19 10:02:00", high=102.25, low=100.5, close=102),
    ]

    outcomes = evaluate_signal_scaled_scalp_outcomes(
        bars,
        [_candidate()],
        first_target_points=1,
        stop_points=2,
        runner_target_points=2,
        runner_stop_mode="breakeven",
    )

    assert outcomes[0]["exit_reason"] == "runner_target_hit"
    assert outcomes[0]["first_target_hit"] == "true"
    assert outcomes[0]["leg1_exit_price"] == "101"
    assert outcomes[0]["runner_exit_price"] == "102"
    assert outcomes[0]["gross_points"] == "3"
    assert outcomes[0]["gross_usd"] == "150"
    assert outcomes[0]["net_usd"] == "93"


def test_scaled_scalp_can_model_total_slippage_ticks_per_contract() -> None:
    bars = [
        _bar(0, timestamp="2026-06-19 10:00:00", high=100, low=99.75, close=100),
        _bar(1, timestamp="2026-06-19 10:01:00", high=101.25, low=100.5, close=101),
        _bar(2, timestamp="2026-06-19 10:02:00", high=102.25, low=100.5, close=102),
    ]

    outcomes = evaluate_signal_scaled_scalp_outcomes(
        bars,
        [_candidate()],
        first_target_points=1,
        stop_points=2,
        runner_target_points=2,
        runner_stop_mode="breakeven",
        slippage_ticks_per_contract=1,
    )

    assert outcomes[0]["gross_usd"] == "150"
    assert outcomes[0]["commission_usd"] == "7"
    assert outcomes[0]["slippage_usd"] == "25"
    assert outcomes[0]["net_usd"] == "118"


def test_scaled_scalp_moves_runner_stop_to_breakeven_after_first_target() -> None:
    bars = [
        _bar(0, timestamp="2026-06-19 10:00:00", high=100, low=99.75, close=100),
        _bar(1, timestamp="2026-06-19 10:01:00", high=101.25, low=100.5, close=101),
        _bar(2, timestamp="2026-06-19 10:02:00", high=101.25, low=99.75, close=100),
    ]

    outcomes = evaluate_signal_scaled_scalp_outcomes(
        bars,
        [_candidate()],
        first_target_points=1,
        stop_points=2,
        runner_target_points=2,
        runner_stop_mode="breakeven",
    )

    assert outcomes[0]["exit_reason"] == "runner_breakeven_stop_hit"
    assert outcomes[0]["first_target_hit"] == "true"
    assert outcomes[0]["leg1_exit_price"] == "101"
    assert outcomes[0]["runner_exit_price"] == "100"
    assert outcomes[0]["gross_points"] == "1"
    assert outcomes[0]["gross_usd"] == "50"
    assert outcomes[0]["net_usd"] == "-7"


def test_scaled_scalp_takes_full_stop_before_first_target() -> None:
    bars = [
        _bar(0, timestamp="2026-06-19 10:00:00", high=100, low=99.75, close=100),
        _bar(1, timestamp="2026-06-19 10:01:00", high=100.75, low=97.75, close=98),
    ]

    outcomes = evaluate_signal_scaled_scalp_outcomes(
        bars,
        [_candidate()],
        first_target_points=1,
        stop_points=2,
        runner_target_points=2,
        runner_stop_mode="breakeven",
    )

    assert outcomes[0]["exit_reason"] == "full_stop_hit"
    assert outcomes[0]["first_target_hit"] == "false"
    assert outcomes[0]["leg1_exit_price"] == "98"
    assert outcomes[0]["runner_exit_price"] == "98"
    assert outcomes[0]["gross_points"] == "-4"
    assert outcomes[0]["gross_usd"] == "-200"
    assert outcomes[0]["net_usd"] == "-257"


def test_scaled_scalp_sweep_rejects_runner_target_at_or_below_first_target() -> None:
    with pytest.raises(SignalScaledScalpExperimentError, match="above first_target"):
        run_signal_scaled_scalp_sweep(
            [],
            [],
            first_target_points_values=[2],
            stop_points_values=[2],
            runner_target_points_values=[1],
        )


def test_scaled_scalp_rejects_negative_total_slippage_ticks_per_contract() -> None:
    with pytest.raises(SignalScaledScalpExperimentError, match="nonnegative"):
        evaluate_signal_scaled_scalp_outcomes(
            [],
            [],
            first_target_points=1,
            stop_points=2,
            runner_target_points=3,
            slippage_ticks_per_contract=-1,
        )


def test_runs_signal_scaled_scalp_walk_forward_sweep() -> None:
    bars = []
    signals = []
    for trade_date in ("2026-06-10", "2026-06-11", "2026-06-12"):
        bars.extend(
            [
                _bar(0, timestamp=f"{trade_date} 10:00:00", high=100, low=99.75, close=100),
                _bar(1, timestamp=f"{trade_date} 10:01:00", high=101.25, low=100.5, close=101),
                _bar(2, timestamp=f"{trade_date} 10:02:00", high=102.25, low=100.5, close=102),
            ],
        )
        signals.append(_candidate_on(trade_date))

    split_rows = run_signal_scaled_scalp_walk_forward_sweep(
        bars,
        signals,
        train_date_count=2,
        holdout_date_count=1,
        first_target_points_values=[1],
        stop_points_values=[2],
        runner_target_points_values=[2],
        runner_stop_modes=["breakeven"],
        minimum_train_trades=2,
    )

    assert list(split_rows[0].keys()) == SIGNAL_SCALED_SCALP_WALK_FORWARD_HEADER
    assert [row["sample"] for row in split_rows] == ["train", "holdout"]
    assert all(row["selected_on_train"] == "true" for row in split_rows)
    assert split_rows[0]["first_target_points"] == "1"
    assert split_rows[0]["runner_target_points"] == "2"
    assert split_rows[0]["evaluated_trades"] == 2
    assert split_rows[0]["net_usd"] == "186"
    assert split_rows[1]["trade_dates"] == "2026-06-12"
    assert split_rows[1]["evaluated_trades"] == 1
    assert split_rows[1]["net_usd"] == "93"


def test_runs_signal_scaled_scalp_sweep_header() -> None:
    rows = run_signal_scaled_scalp_sweep(
        [],
        [],
        first_target_points_values=[1],
        stop_points_values=[2],
        runner_target_points_values=[2],
    )

    assert list(rows[0].keys()) == SIGNAL_SCALED_SCALP_SWEEP_HEADER
