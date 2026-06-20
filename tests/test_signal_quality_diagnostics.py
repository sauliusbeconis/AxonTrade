from __future__ import annotations

import pytest

from axontrade.research import (
    SIGNAL_QUALITY_DIAGNOSTIC_HEADER,
    SignalQualityDiagnosticError,
    run_signal_quality_diagnostics,
)


def test_runs_signal_quality_diagnostics() -> None:
    rows = run_signal_quality_diagnostics(
        signal_rows=[
            {
                "event_type": "candidate_signal",
                "signal_id": "signal-1",
                "notes": (
                    "short absorption reversal; sweep_bar_index=10; sweep_delta=120; "
                    "sweep_ratio=2.5; confirmation_close_location=0.25"
                ),
            },
        ],
        outcome_rows=[
            {
                "outcome_id": "outcome-1",
                "signal_id": "signal-1",
                "symbol": "ESU26-CME",
                "direction": "short",
                "entry_time": "2026-06-10 10:10:00",
                "entry_bar_index": "12",
                "entry_price": "100",
                "stop_price": "102",
                "target_price": "97",
                "exit_reason": "target_hit",
                "net_usd": "150",
            },
        ],
        path_diagnostic_rows=[
            {
                "outcome_id": "outcome-1",
                "max_favorable_r": "1.75",
                "max_adverse_r": "0.25",
            },
        ],
    )

    assert list(rows[0].keys()) == SIGNAL_QUALITY_DIAGNOSTIC_HEADER
    assert rows[0]["risk_points"] == "2"
    assert rows[0]["target_distance_points"] == "3"
    assert rows[0]["original_reward_risk"] == "1.5"
    assert rows[0]["sweep_bar_index"] == 10
    assert rows[0]["bars_after_sweep"] == 2
    assert rows[0]["sweep_delta"] == "120"
    assert rows[0]["sweep_abs_delta"] == "120"
    assert rows[0]["sweep_aggression_ratio"] == "2.5"
    assert rows[0]["confirmation_close_location"] == "0.25"
    assert rows[0]["max_favorable_r"] == "1.75"
    assert rows[0]["max_adverse_r"] == "0.25"
    assert rows[0]["minutes_after_rth_open"] == 40


def test_signal_quality_diagnostics_require_matching_signal_row() -> None:
    with pytest.raises(SignalQualityDiagnosticError, match="Missing candidate signal row"):
        run_signal_quality_diagnostics(
            signal_rows=[],
            outcome_rows=[
                {
                    "outcome_id": "outcome-1",
                    "signal_id": "missing",
                },
            ],
        )


def test_signal_quality_diagnostics_require_parseable_signal_notes() -> None:
    with pytest.raises(SignalQualityDiagnosticError, match="Missing sweep_delta"):
        run_signal_quality_diagnostics(
            signal_rows=[
                {
                    "event_type": "candidate_signal",
                    "signal_id": "signal-1",
                    "notes": "short absorption reversal; sweep_bar_index=10",
                },
            ],
            outcome_rows=[
                {
                    "outcome_id": "outcome-1",
                    "signal_id": "signal-1",
                    "symbol": "ESU26-CME",
                    "direction": "short",
                    "entry_time": "2026-06-10 10:10:00",
                    "entry_bar_index": "12",
                    "entry_price": "100",
                    "stop_price": "102",
                    "target_price": "97",
                    "exit_reason": "target_hit",
                    "net_usd": "150",
                },
            ],
        )
