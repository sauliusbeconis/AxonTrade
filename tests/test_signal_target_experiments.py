from __future__ import annotations

import pytest

from axontrade.research import (
    SIGNAL_TARGET_R_SWEEP_HEADER,
    SignalTargetExperimentError,
    run_signal_target_r_sweep,
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


def _candidate() -> dict[str, object]:
    return {
        "event_type": "candidate_signal",
        "event_key": "ESU26-CME:1:0:test:candidate_signal:long",
        "strategy_id": "test_strategy",
        "signal_id": "test_strategy_ESU26-CME_0",
        "symbol": "ESU26-CME",
        "bar_index": 0,
        "bar_start_time": "2026-06-19 10:00:00",
        "direction": "long",
        "signal_price": "100",
        "stop_price": "99",
        "target_price": "104",
    }


def test_runs_signal_target_r_sweep() -> None:
    bars = [
        _bar(0, timestamp="2026-06-19 10:00:00", high=100, low=99.75, close=100),
        _bar(1, timestamp="2026-06-19 10:01:00", high=101.25, low=99.5, close=101),
        _bar(2, timestamp="2026-06-19 10:02:00", high=101.5, low=98.75, close=99),
    ]

    experiment_rows = run_signal_target_r_sweep(
        bars,
        [_candidate()],
        target_r_multiples=[1, 2],
    )

    assert list(experiment_rows[0].keys()) == SIGNAL_TARGET_R_SWEEP_HEADER
    by_target = {row["target_r_multiple"]: row for row in experiment_rows}
    assert by_target["1"]["target_hits"] == 1
    assert by_target["1"]["losses"] == 0
    assert by_target["1"]["net_usd"] == "21.5"
    assert by_target["2"]["target_hits"] == 0
    assert by_target["2"]["losses"] == 1
    assert by_target["2"]["net_usd"] == "-78.5"
    assert by_target["2"]["strategy_id"] == "test_strategy"


def test_signal_target_r_sweep_can_filter_direction() -> None:
    bars = [
        _bar(0, timestamp="2026-06-19 10:00:00", high=100, low=99.75, close=100),
        _bar(1, timestamp="2026-06-19 10:01:00", high=101.25, low=99.5, close=101),
    ]

    experiment_rows = run_signal_target_r_sweep(
        bars,
        [_candidate()],
        target_r_multiples=[1],
        direction_filters=["short"],
    )

    assert experiment_rows[0]["input_candidates"] == 0
    assert experiment_rows[0]["evaluated_trades"] == 0
    assert experiment_rows[0]["strategy_id"] == "none"


def test_signal_target_r_sweep_rejects_invalid_target_grid() -> None:
    with pytest.raises(SignalTargetExperimentError, match="positive"):
        run_signal_target_r_sweep(
            [],
            [],
            target_r_multiples=[0],
        )
