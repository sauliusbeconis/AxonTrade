from __future__ import annotations

from axontrade.research import (
    VAP_ABSORPTION_DIAGNOSTIC_HEADER,
    VAP_ABSORPTION_THRESHOLD_SWEEP_HEADER,
    run_vap_absorption_diagnostics,
    run_vap_absorption_threshold_sweep,
    run_vap_absorption_threshold_train_holdout_sweep,
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
                "entry_time": "2026-06-10 10:10:00",
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
                "entry_time": "2026-06-10 10:10:00",
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


def test_runs_vap_absorption_threshold_sweep() -> None:
    rows = [
        _diagnostic_row(0, trade_date="2026-06-10", direction="short", zone_bid=4, zone_ask=12, net_usd=50),
        _diagnostic_row(1, trade_date="2026-06-10", direction="long", zone_bid=5, zone_ask=10, net_usd=-25),
    ]

    sweep_rows = run_vap_absorption_threshold_sweep(
        rows,
        minimum_zone_aggression_ratios=[1.25],
        minimum_zone_volumes=[0, 20],
        direction_filters=["all"],
    )

    assert list(sweep_rows[0].keys()) == VAP_ABSORPTION_THRESHOLD_SWEEP_HEADER
    assert len(sweep_rows) == 2
    assert sweep_rows[0]["evaluated_trades"] == 1
    assert sweep_rows[0]["net_usd"] == "50"
    assert sweep_rows[1]["evaluated_trades"] == 0


def test_runs_vap_absorption_threshold_train_holdout_sweep() -> None:
    rows = [
        _diagnostic_row(0, trade_date="2026-06-10", direction="short", zone_bid=4, zone_ask=12, net_usd=50),
        _diagnostic_row(1, trade_date="2026-06-11", direction="long", zone_bid=12, zone_ask=4, net_usd=50),
        _diagnostic_row(2, trade_date="2026-06-12", direction="short", zone_bid=1, zone_ask=3, net_usd=-25),
    ]

    split_rows = run_vap_absorption_threshold_train_holdout_sweep(
        rows,
        train_date_count=2,
        minimum_zone_aggression_ratios=[1.25],
        minimum_zone_volumes=[0, 10],
        direction_filters=["all"],
    )

    assert len(split_rows) == 4
    assert {row["sample"] for row in split_rows} == {"train", "holdout"}
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
    assert selected_train["minimum_zone_volume"] == "0"
    assert selected_train["net_usd"] == "100"
    assert selected_holdout["evaluated_trades"] == 1
    assert selected_holdout["net_usd"] == "-25"


def _diagnostic_row(
    index: int,
    *,
    trade_date: str,
    direction: str,
    zone_bid: float,
    zone_ask: float,
    net_usd: float,
) -> dict[str, object]:
    zone_delta = zone_ask - zone_bid
    if direction == "short":
        ratio = zone_ask / zone_bid if zone_bid else float("inf")
        exit_reason = "target_hit" if net_usd >= 0 else "stop_hit"
    else:
        ratio = zone_bid / zone_ask if zone_ask else float("inf")
        exit_reason = "target_hit" if net_usd >= 0 else "stop_hit"
    return {
        "entry_time": f"{trade_date} 10:{index:02d}:00",
        "direction": direction,
        "zone_levels": 1,
        "zone_bid_volume": zone_bid,
        "zone_ask_volume": zone_ask,
        "zone_delta": zone_delta,
        "zone_aggression_ratio": ratio,
        "exit_reason": exit_reason,
        "net_usd": net_usd,
    }
