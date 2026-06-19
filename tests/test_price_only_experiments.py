from __future__ import annotations

import pytest

from axontrade.research import (
    PRICE_ONLY_PARAMETER_SWEEP_HEADER,
    PriceOnlyExperimentError,
    run_price_only_parameter_sweep,
)


def _bar(
    bar_index: int,
    close: float,
    vwap: float,
    *,
    high: float | None = None,
    low: float | None = None,
) -> dict[str, object]:
    return {
        "timestamp": f"2026-06-19 10:{bar_index:02d}:00",
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
    )

    assert list(experiment_rows[0].keys()) == PRICE_ONLY_PARAMETER_SWEEP_HEADER
    assert len(experiment_rows) == 2
    assert experiment_rows[0]["signal_rows"] == 3
    assert experiment_rows[0]["candidate_signals"] == 1
    assert experiment_rows[0]["evaluated_trades"] == 1
    assert experiment_rows[0]["long_trades"] == 1
    assert experiment_rows[0]["short_trades"] == 0
    assert experiment_rows[0]["target_r_multiple"] == "1"
    assert experiment_rows[1]["target_r_multiple"] == "2"


def test_rejects_empty_parameter_grid() -> None:
    with pytest.raises(PriceOnlyExperimentError, match="target_r_multiples"):
        run_price_only_parameter_sweep(
            [],
            target_r_multiples=[],
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
