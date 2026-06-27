from __future__ import annotations

import pytest

from axontrade.research import (
    SIGNAL_AUCTION_REGIME_DIAGNOSTIC_HEADER,
    SignalAuctionRegimeDiagnosticError,
    run_signal_auction_regime_diagnostics,
)


def _bar(
    bar_index: int,
    *,
    timestamp: str = "2026-06-19 10:00:00",
    open_price: float = 100.0,
    high: float = 101.0,
    low: float = 99.0,
    close: float = 100.0,
    vwap: float = 100.5,
    opening_range_high: float = 102.0,
    opening_range_low: float = 98.0,
) -> dict[str, object]:
    return {
        "timestamp": timestamp,
        "symbol": "ESU26-CME",
        "bar_index": bar_index,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "vwap": vwap,
        "opening_range_high": opening_range_high,
        "opening_range_low": opening_range_low,
    }


def _quality_row(*, direction: str = "long") -> dict[str, object]:
    return {
        "diagnostic_id": "outcome-1:quality",
        "outcome_id": "outcome-1",
        "signal_id": "signal-1",
        "symbol": "ESU26-CME",
        "direction": direction,
        "entry_time": "2026-06-19 10:03:00",
        "entry_bar_index": "3",
        "minutes_after_rth_open": "33",
        "risk_points": "2",
        "target_distance_points": "4",
        "original_reward_risk": "2",
        "sweep_abs_delta": "6",
        "exit_reason": "target_hit",
        "net_usd": "100",
    }


def test_runs_signal_auction_regime_diagnostics_for_long() -> None:
    rows = run_signal_auction_regime_diagnostics(
        bar_rows=[
            _bar(0, timestamp="2026-06-19 10:00:00", open_price=100, high=101, low=99, close=100),
            _bar(1, timestamp="2026-06-19 10:01:00", open_price=100, high=104, low=100, close=103),
            _bar(2, timestamp="2026-06-19 10:02:00", open_price=103, high=103, low=97, close=98),
            _bar(3, timestamp="2026-06-19 10:03:00", open_price=98, high=99, low=96, close=97, vwap=100),
        ],
        quality_diagnostic_rows=[_quality_row(direction="long")],
    )

    assert list(rows[0].keys()) == SIGNAL_AUCTION_REGIME_DIAGNOSTIC_HEADER
    assert rows[0]["session_open_price"] == "100"
    assert rows[0]["entry_close_price"] == "97"
    assert rows[0]["session_range_points"] == "8"
    assert rows[0]["entry_position_in_session_range"] == "0.125"
    assert rows[0]["fade_edge_score"] == "0.875"
    assert rows[0]["direction_aware_vwap_stretch_points"] == "3"
    assert rows[0]["direction_aware_open_stretch_points"] == "3"
    assert rows[0]["opening_range_edge_score"] == "1.25"
    assert rows[0]["direction_aware_outside_opening_range_points"] == "1"


def test_runs_signal_auction_regime_diagnostics_for_short() -> None:
    quality = _quality_row(direction="short")
    rows = run_signal_auction_regime_diagnostics(
        bar_rows=[
            _bar(0, timestamp="2026-06-19 10:00:00", open_price=100, high=101, low=99, close=100),
            _bar(3, timestamp="2026-06-19 10:03:00", open_price=100, high=105, low=99, close=104, vwap=101),
        ],
        quality_diagnostic_rows=[quality],
    )

    assert rows[0]["fade_edge_score"] == "0.83333333"
    assert rows[0]["direction_aware_vwap_stretch_points"] == "3"
    assert rows[0]["direction_aware_open_stretch_points"] == "4"
    assert rows[0]["direction_aware_outside_opening_range_points"] == "2"


def test_signal_auction_regime_diagnostics_requires_entry_bar() -> None:
    with pytest.raises(SignalAuctionRegimeDiagnosticError, match="No entry"):
        run_signal_auction_regime_diagnostics(
            bar_rows=[_bar(0)],
            quality_diagnostic_rows=[_quality_row()],
        )
