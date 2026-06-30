from __future__ import annotations

import pytest

from axontrade.research import (
    SCALED_CONTEXT_DIAGNOSTIC_HEADER,
    ScaledContextDiagnosticError,
    run_scaled_outcome_context_diagnostics,
)


def _bar(
    index: int,
    *,
    timestamp: str,
    high: float,
    low: float,
    open_: float | None = None,
    close: float | None = None,
    volume: float = 10,
    trades: float = 5,
    delta: float = 2,
) -> dict[str, object]:
    return {
        "timestamp": timestamp,
        "symbol": "ESU26-CME",
        "bar_index": index,
        "open": low if open_ is None else open_,
        "high": high,
        "low": low,
        "close": high if close is None else close,
        "volume": volume,
        "number_of_trades": trades,
        "delta": delta,
    }


def _outcome() -> dict[str, object]:
    return {
        "outcome_id": "outcome-1",
        "event_key": "event-1",
        "signal_id": "strategy_ESU26-CME_3",
        "symbol": "ESU26-CME",
        "direction": "long",
        "entry_time": "2026-06-19 10:03:00",
        "entry_bar_index": "3",
        "entry_price": "100",
        "stop_price": "90",
        "first_target_price": "105",
        "runner_target_price": "108",
        "exit_reason": "runner_target_hit",
        "first_target_hit": "true",
        "net_usd": "593",
    }


def test_runs_scaled_outcome_context_diagnostics() -> None:
    rows = run_scaled_outcome_context_diagnostics(
        bar_rows=[
            _bar(0, timestamp="2026-06-19 10:00:00", high=101, low=100, volume=10, trades=5, delta=2),
            _bar(1, timestamp="2026-06-19 10:01:00", high=103, low=101, volume=20, trades=15, delta=-4),
            _bar(2, timestamp="2026-06-19 10:02:00", high=102, low=101, volume=30, trades=10, delta=6),
            _bar(3, timestamp="2026-06-19 10:03:00", high=104, low=102, volume=40, trades=20, delta=8),
        ],
        scaled_outcome_rows=[_outcome()],
        signal_rows=[
            {
                "signal_id": "strategy_ESU26-CME_3",
                "notes": "long delta impulse continuation; price_move=3.5; delta_sum=120",
            },
        ],
        lookback_bars=3,
    )

    assert list(rows[0].keys()) == SCALED_CONTEXT_DIAGNOSTIC_HEADER
    assert rows[0]["minutes_after_rth_open"] == "33"
    assert rows[0]["risk_points"] == "10"
    assert rows[0]["first_target_points"] == "5"
    assert rows[0]["runner_target_points"] == "8"
    assert rows[0]["runner_reward_risk"] == "0.8"
    assert rows[0]["signal_price_move"] == "3.5"
    assert rows[0]["signal_delta_sum"] == "120"
    assert rows[0]["signal_abs_delta_sum"] == "120"
    assert rows[0]["average_bar_range_points"] == "1.33333333"
    assert rows[0]["signal_abs_delta_sum_to_average_abs_delta"] == "30"
    assert rows[0]["entry_volume_to_average_volume"] == "2"
    assert rows[0]["session_open_price"] == "100"
    assert rows[0]["session_range_points"] == "4"
    assert rows[0]["continuation_edge_score"] == "1"
    assert rows[0]["fade_edge_score"] == "0"
    assert rows[0]["directional_open_distance_points"] == "4"
    assert rows[0]["lookback_efficiency_ratio"] == "0.6"


def test_scaled_outcome_context_diagnostics_accepts_audit_rows_without_outcome_id() -> None:
    outcome = _outcome()
    del outcome["outcome_id"]
    del outcome["event_key"]

    rows = run_scaled_outcome_context_diagnostics(
        bar_rows=[
            _bar(0, timestamp="2026-06-19 10:00:00", high=101, low=100),
            _bar(1, timestamp="2026-06-19 10:01:00", high=103, low=101),
            _bar(2, timestamp="2026-06-19 10:02:00", high=102, low=101),
            _bar(3, timestamp="2026-06-19 10:03:00", high=104, low=102),
        ],
        scaled_outcome_rows=[outcome],
        lookback_bars=3,
    )

    assert rows[0]["outcome_id"] == "strategy_ESU26-CME_3:runner_target_hit::593"
    assert rows[0]["event_key"] == ""
    assert rows[0]["signal_delta_sum"] == "2"
    assert rows[0]["signal_abs_delta_sum"] == "2"


def test_scaled_outcome_context_diagnostics_requires_entry_bar() -> None:
    with pytest.raises(ScaledContextDiagnosticError, match="No entry context bar"):
        run_scaled_outcome_context_diagnostics(
            bar_rows=[
                _bar(0, timestamp="2026-06-19 10:00:00", high=101, low=100),
            ],
            scaled_outcome_rows=[_outcome()],
            lookback_bars=1,
        )
