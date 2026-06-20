from __future__ import annotations

import pytest

from axontrade.research import (
    SIGNAL_CONTEXT_DIAGNOSTIC_HEADER,
    SignalContextDiagnosticError,
    run_signal_context_diagnostics,
)


def _bar(
    bar_index: int,
    *,
    timestamp: str = "2026-06-19 10:00:00",
    high: float = 101.0,
    low: float = 100.0,
    volume: float = 10.0,
    trades: float = 5.0,
    delta: float = 2.0,
) -> dict[str, object]:
    return {
        "timestamp": timestamp,
        "symbol": "ESU26-CME",
        "bar_index": bar_index,
        "high": high,
        "low": low,
        "volume": volume,
        "number_of_trades": trades,
        "delta": delta,
    }


def _quality_row() -> dict[str, object]:
    return {
        "diagnostic_id": "outcome-1:quality",
        "outcome_id": "outcome-1",
        "signal_id": "signal-1",
        "symbol": "ESU26-CME",
        "direction": "long",
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


def test_runs_signal_context_diagnostics() -> None:
    rows = run_signal_context_diagnostics(
        bar_rows=[
            _bar(0, timestamp="2026-06-19 10:00:00", high=101, low=100, volume=10, trades=5, delta=2),
            _bar(1, timestamp="2026-06-19 10:01:00", high=103, low=101, volume=20, trades=15, delta=-4),
            _bar(2, timestamp="2026-06-19 10:02:00", high=102, low=101, volume=30, trades=10, delta=6),
            _bar(3, timestamp="2026-06-19 10:03:00", high=104, low=102, volume=40, trades=20, delta=8),
        ],
        quality_diagnostic_rows=[_quality_row()],
        lookback_bars=3,
    )

    assert list(rows[0].keys()) == SIGNAL_CONTEXT_DIAGNOSTIC_HEADER
    assert rows[0]["lookback_bars_available"] == 3
    assert rows[0]["lookback_range_points"] == "3"
    assert rows[0]["average_bar_range_points"] == "1.33333333"
    assert rows[0]["average_volume"] == "20"
    assert rows[0]["average_trades"] == "10"
    assert rows[0]["average_abs_delta"] == "4"
    assert rows[0]["entry_bar_range_points"] == "2"
    assert rows[0]["entry_bar_volume"] == "40"
    assert rows[0]["entry_bar_trades"] == "20"
    assert rows[0]["entry_bar_delta"] == "8"
    assert rows[0]["risk_to_average_bar_range"] == "1.5"
    assert rows[0]["target_distance_to_average_bar_range"] == "3"
    assert rows[0]["sweep_abs_delta_to_average_abs_delta"] == "1.5"
    assert rows[0]["entry_volume_to_average_volume"] == "2"
    assert rows[0]["entry_trades_to_average_trades"] == "2"
    assert rows[0]["entry_abs_delta_to_average_abs_delta"] == "2"


def test_context_diagnostics_can_fallback_to_bid_ask_for_volume_and_delta() -> None:
    row = _bar(0)
    row.pop("volume")
    row.pop("delta")
    row["bid_volume"] = "3"
    row["ask_volume"] = "7"
    entry = _bar(1, timestamp="2026-06-19 10:03:00")
    entry.pop("volume")
    entry.pop("delta")
    entry["bid_volume"] = "4"
    entry["ask_volume"] = "10"
    quality = _quality_row()
    quality["entry_bar_index"] = "1"

    rows = run_signal_context_diagnostics(
        bar_rows=[row, entry],
        quality_diagnostic_rows=[quality],
        lookback_bars=1,
    )

    assert rows[0]["average_volume"] == "10"
    assert rows[0]["average_abs_delta"] == "4"
    assert rows[0]["entry_bar_volume"] == "14"
    assert rows[0]["entry_bar_delta"] == "6"


def test_context_diagnostics_requires_positive_lookback() -> None:
    with pytest.raises(SignalContextDiagnosticError, match="lookback_bars"):
        run_signal_context_diagnostics(
            bar_rows=[],
            quality_diagnostic_rows=[],
            lookback_bars=0,
        )
