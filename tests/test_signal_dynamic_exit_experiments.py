from __future__ import annotations

import pytest

from axontrade.research import (
    SIGNAL_BREAKEVEN_STOP_SWEEP_HEADER,
    SIGNAL_BREAKEVEN_STOP_WALK_FORWARD_HEADER,
    SignalDynamicExitExperimentError,
    evaluate_signal_breakeven_stop_outcomes,
    run_signal_breakeven_stop_sweep,
    run_signal_breakeven_stop_walk_forward_sweep,
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
        "stop_price": "99" if direction == "long" else "101",
        "target_price": "104",
    }


def _candidate_on(trade_date: str) -> dict[str, object]:
    candidate = _candidate()
    candidate["event_key"] = f"ESU26-CME:1:{trade_date}:test:candidate_signal:long"
    candidate["signal_id"] = f"test_strategy_ESU26-CME_{trade_date}"
    candidate["bar_start_time"] = f"{trade_date} 10:00:00"
    return candidate


def test_evaluates_breakeven_stop_after_trigger() -> None:
    bars = [
        _bar(0, timestamp="2026-06-19 10:00:00", high=100, low=99.75, close=100),
        _bar(1, timestamp="2026-06-19 10:01:00", high=101.25, low=100.5, close=101),
        _bar(2, timestamp="2026-06-19 10:02:00", high=101.25, low=99.75, close=100),
    ]

    outcomes = evaluate_signal_breakeven_stop_outcomes(
        bars,
        [_candidate()],
        target_r_multiple=1.5,
        breakeven_trigger_r=1,
    )

    assert outcomes[0]["exit_reason"] == "breakeven_stop_hit"
    assert outcomes[0]["exit_price"] == "100"
    assert outcomes[0]["gross_points"] == "0"
    assert outcomes[0]["net_usd"] == "-28.5"


def test_evaluates_dynamic_target_before_breakeven_stop() -> None:
    bars = [
        _bar(0, timestamp="2026-06-19 10:00:00", high=100, low=99.75, close=100),
        _bar(1, timestamp="2026-06-19 10:01:00", high=101.75, low=100.5, close=101.5),
    ]

    outcomes = evaluate_signal_breakeven_stop_outcomes(
        bars,
        [_candidate()],
        target_r_multiple=1.5,
        breakeven_trigger_r=1,
    )

    assert outcomes[0]["exit_reason"] == "target_hit"
    assert outcomes[0]["exit_price"] == "101.5"
    assert outcomes[0]["net_usd"] == "46.5"


def test_evaluates_original_stop_before_breakeven_trigger() -> None:
    bars = [
        _bar(0, timestamp="2026-06-19 10:00:00", high=100, low=99.75, close=100),
        _bar(1, timestamp="2026-06-19 10:01:00", high=100.75, low=98.75, close=99),
    ]

    outcomes = evaluate_signal_breakeven_stop_outcomes(
        bars,
        [_candidate()],
        target_r_multiple=1.5,
        breakeven_trigger_r=1,
    )

    assert outcomes[0]["exit_reason"] == "stop_hit"
    assert outcomes[0]["exit_price"] == "99"
    assert outcomes[0]["net_usd"] == "-78.5"


def test_runs_signal_breakeven_stop_sweep() -> None:
    bars = [
        _bar(0, timestamp="2026-06-19 10:00:00", high=100, low=99.75, close=100),
        _bar(1, timestamp="2026-06-19 10:01:00", high=101.25, low=100.5, close=101),
        _bar(2, timestamp="2026-06-19 10:02:00", high=101.25, low=99.75, close=100),
    ]

    rows = run_signal_breakeven_stop_sweep(
        bars,
        [_candidate()],
        target_r_multiples=[1, 1.5],
        breakeven_trigger_r_multiples=[1],
    )

    assert list(rows[0].keys()) == SIGNAL_BREAKEVEN_STOP_SWEEP_HEADER
    assert len(rows) == 1
    assert rows[0]["target_r_multiple"] == "1.5"
    assert rows[0]["breakeven_trigger_r"] == "1"
    assert rows[0]["breakeven_exits"] == 1
    assert rows[0]["losses"] == 0
    assert rows[0]["net_usd"] == "-28.5"


def test_runs_signal_breakeven_stop_walk_forward_sweep() -> None:
    bars = []
    signals = []
    for trade_date in ("2026-06-10", "2026-06-11", "2026-06-12"):
        bars.extend(
            [
                _bar(0, timestamp=f"{trade_date} 10:00:00", high=100, low=99.75, close=100),
                _bar(1, timestamp=f"{trade_date} 10:01:00", high=101.75, low=100.5, close=101.5),
            ],
        )
        signals.append(_candidate_on(trade_date))

    split_rows = run_signal_breakeven_stop_walk_forward_sweep(
        bars,
        signals,
        train_date_count=2,
        holdout_date_count=1,
        target_r_multiples=[1.5, 2],
        breakeven_trigger_r_multiples=[1],
        minimum_train_trades=2,
    )

    assert list(split_rows[0].keys()) == SIGNAL_BREAKEVEN_STOP_WALK_FORWARD_HEADER
    assert [row["sample"] for row in split_rows] == ["train", "holdout"]
    assert all(row["selected_on_train"] == "true" for row in split_rows)
    assert split_rows[0]["target_r_multiple"] == "1.5"
    assert split_rows[0]["evaluated_trades"] == 2
    assert split_rows[0]["net_usd"] == "93"
    assert split_rows[1]["trade_dates"] == "2026-06-12"
    assert split_rows[1]["evaluated_trades"] == 1


def test_signal_breakeven_stop_rejects_trigger_at_or_above_target() -> None:
    with pytest.raises(SignalDynamicExitExperimentError, match="below target"):
        evaluate_signal_breakeven_stop_outcomes(
            [],
            [],
            target_r_multiple=1,
            breakeven_trigger_r=1,
        )
