from __future__ import annotations

from axontrade.research import (
    VAP_ABSORPTION_DIAGNOSTIC_HEADER,
    run_vap_absorption_diagnostics,
    summarize_vap_absorption_diagnostics,
)


def test_runs_vap_absorption_diagnostics_for_short_sweep() -> None:
    rows = run_vap_absorption_diagnostics(
        outcome_rows=[
            {
                "outcome_id": "outcome-1",
                "signal_id": "signal-1",
                "symbol": "ESU26-CME",
                "direction": "short",
                "entry_bar_index": "12",
                "stop_price": "101.25",
                "exit_reason": "target_hit",
                "net_usd": "50",
            },
        ],
        signal_rows=[
            {
                "signal_id": "signal-1",
                "event_type": "candidate_signal",
                "notes": "short absorption reversal; sweep_bar_index=10",
            },
        ],
        vap_rows=[
            {"symbol": "ESU26-CME", "bar_index": "10", "price": "101", "bid_volume": "4", "ask_volume": "12"},
            {"symbol": "ESU26-CME", "bar_index": "10", "price": "99.75", "bid_volume": "10", "ask_volume": "2"},
        ],
        sweep_zone_points=0.25,
        stop_buffer_points=0.25,
        minimum_zone_aggression_ratio=1.25,
        minimum_zone_volume=10,
    )

    assert list(rows[0].keys()) == VAP_ABSORPTION_DIAGNOSTIC_HEADER
    assert rows[0]["sweep_extreme_price"] == "101"
    assert rows[0]["zone_levels"] == 1
    assert rows[0]["zone_ask_volume"] == "12"
    assert rows[0]["zone_aggression_ratio"] == "3"
    assert rows[0]["level_absorption_pass"] == "true"


def test_vap_absorption_diagnostics_can_require_zone_volume() -> None:
    rows = run_vap_absorption_diagnostics(
        outcome_rows=[
            {
                "outcome_id": "outcome-1",
                "signal_id": "signal-1",
                "symbol": "ESU26-CME",
                "direction": "short",
                "entry_bar_index": "12",
                "stop_price": "101.25",
                "exit_reason": "target_hit",
                "net_usd": "50",
            },
        ],
        signal_rows=[
            {
                "signal_id": "signal-1",
                "event_type": "candidate_signal",
                "notes": "short absorption reversal; sweep_bar_index=10",
            },
        ],
        vap_rows=[
            {"symbol": "ESU26-CME", "bar_index": "10", "price": "101", "bid_volume": "1", "ask_volume": "2"},
        ],
        sweep_zone_points=0.25,
        stop_buffer_points=0.25,
        minimum_zone_aggression_ratio=1.25,
        minimum_zone_volume=10,
    )

    assert rows[0]["level_absorption_pass"] == "false"


def test_summarizes_vap_absorption_diagnostics() -> None:
    summary_rows = summarize_vap_absorption_diagnostics(
        [
            {"level_absorption_pass": "true", "exit_reason": "target_hit", "net_usd": "50"},
            {"level_absorption_pass": "true", "exit_reason": "stop_hit", "net_usd": "-25"},
            {"level_absorption_pass": "false", "exit_reason": "stop_hit", "net_usd": "-10"},
        ],
    )

    by_bucket = {row["level_absorption_pass"]: row for row in summary_rows}

    assert by_bucket["true"]["trades"] == 2
    assert by_bucket["true"]["target_hits"] == 1
    assert by_bucket["true"]["net_usd"] == "25"
    assert by_bucket["false"]["trades"] == 1
    assert by_bucket["false"]["net_usd"] == "-10"
