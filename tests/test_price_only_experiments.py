from __future__ import annotations

import pytest

from axontrade.research import (
    PRICE_ONLY_PARAMETER_SWEEP_HEADER,
    PRICE_ONLY_TRAIN_HOLDOUT_SWEEP_HEADER,
    PriceOnlyExperimentError,
    run_price_only_parameter_sweep,
    run_price_only_train_holdout_sweep,
)


def _bar(
    bar_index: int,
    close: float,
    vwap: float,
    *,
    trade_date: str = "2026-06-19",
    high: float | None = None,
    low: float | None = None,
) -> dict[str, object]:
    return {
        "timestamp": f"{trade_date} 10:{bar_index:02d}:00",
        "symbol": "ESU26-CME",
        "chart_number": 1,
        "bar_index": bar_index,
        "open": close - 0.5,
        "high": high if high is not None else close + 1,
        "low": low if low is not None else close - 1,
        "close": close,
        "vwap": vwap,
        "opening_range_high": 100.0,
        "opening_range_low": 90.0,
        "session_phase": "rth",
    }


def test_runs_price_only_parameter_sweep() -> None:
    rows = [
        _bar(0, close=99, vwap=100),
        _bar(1, close=101, vwap=100, high=101.5, low=99.5),
        _bar(2, close=103, vwap=101, high=106, low=102),
    ]

    experiment_rows = run_price_only_parameter_sweep(
        rows,
        target_r_multiples=[1, 2],
        stop_buffer_points=[0.25],
        minimum_opening_range_width_points=[1],
        direction_filters=["all"],
    )

    assert list(experiment_rows[0].keys()) == PRICE_ONLY_PARAMETER_SWEEP_HEADER
    assert len(experiment_rows) == 2
    assert experiment_rows[0]["signal_rows"] == 3
    assert experiment_rows[0]["candidate_signals"] == 1
    assert experiment_rows[0]["evaluated_trades"] == 1
    assert experiment_rows[0]["long_trades"] == 1
    assert experiment_rows[0]["short_trades"] == 0
    assert experiment_rows[0]["direction_filter"] == "all"
    assert experiment_rows[0]["target_r_multiple"] == "1"
    assert experiment_rows[1]["target_r_multiple"] == "2"


def test_direction_filters_limit_evaluated_trades() -> None:
    rows = [
        _bar(0, close=99, vwap=100),
        _bar(1, close=101, vwap=100, high=101.5, low=99.5),
        _bar(2, close=103, vwap=101, high=106, low=102),
    ]

    experiment_rows = run_price_only_parameter_sweep(
        rows,
        target_r_multiples=[1],
        stop_buffer_points=[0.25],
        minimum_opening_range_width_points=[1],
        direction_filters=["all", "long", "short"],
    )

    by_filter = {row["direction_filter"]: row for row in experiment_rows}

    assert by_filter["all"]["evaluated_trades"] == 1
    assert by_filter["long"]["evaluated_trades"] == 1
    assert by_filter["short"]["evaluated_trades"] == 0


def test_rejects_empty_parameter_grid() -> None:
    with pytest.raises(PriceOnlyExperimentError, match="target_r_multiples"):
        run_price_only_parameter_sweep(
            [],
            target_r_multiples=[],
            stop_buffer_points=[0.25],
            minimum_opening_range_width_points=[1],
        )


def test_rejects_invalid_direction_filter() -> None:
    with pytest.raises(PriceOnlyExperimentError, match="unsupported"):
        run_price_only_parameter_sweep(
            [],
            target_r_multiples=[1],
            stop_buffer_points=[0.25],
            minimum_opening_range_width_points=[1],
            direction_filters=["sideways"],
        )


def test_runs_train_holdout_parameter_sweep() -> None:
    rows = [
        _bar(0, close=99, vwap=100, trade_date="2026-06-19"),
        _bar(1, close=101, vwap=100, trade_date="2026-06-19", high=101.5, low=99.5),
        _bar(2, close=103, vwap=101, trade_date="2026-06-19", high=106, low=102),
        _bar(3, close=99, vwap=100, trade_date="2026-06-20"),
        _bar(4, close=101, vwap=100, trade_date="2026-06-20", high=101.5, low=99.5),
        _bar(5, close=103, vwap=101, trade_date="2026-06-20", high=106, low=102),
    ]

    split_rows = run_price_only_train_holdout_sweep(
        rows,
        train_date_count=1,
        target_r_multiples=[1],
        stop_buffer_points=[0.25],
        minimum_opening_range_width_points=[1],
        direction_filters=["all", "short"],
    )

    assert list(split_rows[0].keys()) == PRICE_ONLY_TRAIN_HOLDOUT_SWEEP_HEADER
    assert len(split_rows) == 4
    assert {row["sample"] for row in split_rows} == {"train", "holdout"}
    assert [row for row in split_rows if row["selected_on_train"] == "true"]
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
    assert selected_train["direction_filter"] == "all"
    assert selected_train["trade_dates"] == "2026-06-19"
    assert selected_holdout["trade_dates"] == "2026-06-20"
    assert selected_holdout["experiment_id"] == selected_train["experiment_id"]


def test_rejects_invalid_train_holdout_split() -> None:
    rows = [_bar(0, close=99, vwap=100)]

    with pytest.raises(PriceOnlyExperimentError, match="train_date_count"):
        run_price_only_train_holdout_sweep(
            rows,
            train_date_count=1,
            target_r_multiples=[1],
            stop_buffer_points=[0.25],
            minimum_opening_range_width_points=[1],
        )


def test_rejects_negative_stop_buffer() -> None:
    with pytest.raises(PriceOnlyExperimentError, match="nonnegative"):
        run_price_only_parameter_sweep(
            [],
            target_r_multiples=[1],
            stop_buffer_points=[-0.25],
            minimum_opening_range_width_points=[1],
        )
