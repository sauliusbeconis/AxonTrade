from __future__ import annotations

import pytest

from axontrade.research import (
    SIGNAL_TARGET_R_SWEEP_HEADER,
    SIGNAL_TARGET_R_WALK_FORWARD_SWEEP_HEADER,
    SignalTargetExperimentError,
    run_signal_target_r_sweep,
    run_signal_target_r_walk_forward_sweep,
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


def _candidate_on(trade_date: str) -> dict[str, object]:
    candidate = _candidate()
    candidate["event_key"] = f"ESU26-CME:1:{trade_date}:test:candidate_signal:long"
    candidate["signal_id"] = f"test_strategy_ESU26-CME_{trade_date}"
    candidate["bar_start_time"] = f"{trade_date} 10:00:00"
    return candidate


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


def test_runs_signal_target_r_walk_forward_sweep() -> None:
    bars = []
    signals = []
    for trade_date in ("2026-06-10", "2026-06-11", "2026-06-12"):
        bars.extend(
            [
                _bar(0, timestamp=f"{trade_date} 10:00:00", high=100, low=99.75, close=100),
                _bar(1, timestamp=f"{trade_date} 10:01:00", high=102.25, low=99.5, close=102),
            ],
        )
        signals.append(_candidate_on(trade_date))

    split_rows = run_signal_target_r_walk_forward_sweep(
        bars,
        signals,
        train_date_count=2,
        holdout_date_count=1,
        target_r_multiples=[1, 2],
        minimum_train_trades=2,
    )

    assert list(split_rows[0].keys()) == SIGNAL_TARGET_R_WALK_FORWARD_SWEEP_HEADER
    assert [row["sample"] for row in split_rows] == ["train", "holdout"]
    assert all(row["selected_on_train"] == "true" for row in split_rows)
    assert split_rows[0]["target_r_multiple"] == "2"
    assert split_rows[0]["evaluated_trades"] == 2
    assert split_rows[0]["net_usd"] == "143"
    assert split_rows[1]["trade_dates"] == "2026-06-12"
    assert split_rows[1]["evaluated_trades"] == 1
    assert split_rows[1]["net_usd"] == "71.5"


def test_signal_target_r_walk_forward_requires_enough_dates() -> None:
    with pytest.raises(SignalTargetExperimentError, match="candidate trade dates"):
        run_signal_target_r_walk_forward_sweep(
            [],
            [_candidate_on("2026-06-10")],
            train_date_count=1,
            holdout_date_count=1,
            target_r_multiples=[1],
        )
