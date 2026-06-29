from __future__ import annotations

from axontrade.research import (
    SCALED_CONTEXT_SELECTED_TRADE_AUDIT_HEADER,
    SCALED_CONTEXT_SELECTED_VETO_WALK_FORWARD_HEADER,
    audit_scaled_context_selected_trades,
    run_scaled_context_selected_veto_walk_forward,
)


def _context_row(
    index: int,
    *,
    trade_date: str,
    direction: str = "long",
    directional_open_distance: float = 0,
    net_usd: float = 100,
) -> dict[str, object]:
    return {
        "outcome_id": f"outcome-{index}",
        "signal_id": f"strategy_ESU26-CME_{index}",
        "symbol": "ESU26-CME",
        "direction": direction,
        "entry_time": f"{trade_date} 10:00:00",
        "entry_bar_index": index,
        "exit_reason": "runner_target_hit" if net_usd > 0 else "full_stop_hit",
        "net_usd": net_usd,
        "minutes_after_rth_open": 30,
        "directional_open_distance_points": directional_open_distance,
        "directional_opening_range_breakout_points": directional_open_distance,
        "continuation_edge_score": 0.8,
        "opening_range_continuation_edge_score": 1.25,
        "lookback_directional_move_points": directional_open_distance,
        "lookback_efficiency_ratio": 0.4,
        "lookback_choppiness_score": 0.6,
        "signal_abs_delta_sum_to_average_abs_delta": 10,
        "entry_volume_to_average_volume": 1,
        "entry_trades_to_average_trades": 1,
        "entry_volume_to_session_average_volume": 1,
        "lookback_volume_to_session_average_volume": 1,
        "risk_to_average_bar_range": 2,
        "runner_target_to_average_bar_range": 2,
    }


def _selection_row(*, sample: str, dates: str) -> dict[str, object]:
    return {
        "split_id": "scaled_context_filter_walk_forward_window=1:train_dates=2:holdout_dates=1",
        "sample": sample,
        "selected_on_train": "true",
        "trade_dates": dates,
        "experiment_id": "selected-context-rule",
        "direction_filter": "all",
        "min_minutes_after_rth_open": 0,
        "max_minutes_after_rth_open": 120,
        "max_risk_to_average_bar_range": 4,
        "max_runner_target_to_average_bar_range": 4,
        "min_signal_abs_delta_sum_to_average_abs_delta": 0,
        "max_signal_abs_delta_sum_to_average_abs_delta": 20,
        "min_entry_volume_to_average_volume": 0,
        "min_entry_trades_to_average_trades": 0,
        "min_continuation_edge_score": 0,
        "min_opening_range_continuation_edge_score": 0,
        "min_directional_opening_range_breakout_points": -999999,
        "min_lookback_efficiency_ratio": 0,
        "max_lookback_choppiness_score": 1,
        "min_entry_volume_to_session_average_volume": 0,
        "min_lookback_volume_to_session_average_volume": 0,
    }


def test_audits_selected_context_trades() -> None:
    rows = audit_scaled_context_selected_trades(
        context_rows=[
            _context_row(1, trade_date="2026-06-10"),
            _context_row(2, trade_date="2026-06-11"),
            _context_row(3, trade_date="2026-06-12", direction="short"),
        ],
        selection_rows=[
            _selection_row(sample="train", dates="2026-06-10;2026-06-11"),
            _selection_row(sample="holdout", dates="2026-06-12"),
        ],
    )

    assert list(rows[0].keys()) == SCALED_CONTEXT_SELECTED_TRADE_AUDIT_HEADER
    assert [row["sample"] for row in rows] == ["train", "train", "holdout"]
    assert rows[2]["signal_id"] == "strategy_ESU26-CME_3"


def test_runs_selected_veto_walk_forward() -> None:
    split_rows = run_scaled_context_selected_veto_walk_forward(
        context_rows=[
            _context_row(1, trade_date="2026-06-10", directional_open_distance=0, net_usd=-100),
            _context_row(2, trade_date="2026-06-11", directional_open_distance=30, net_usd=200),
            _context_row(3, trade_date="2026-06-12", directional_open_distance=35, net_usd=200),
            _context_row(4, trade_date="2026-06-12", directional_open_distance=0, net_usd=-100),
        ],
        selection_rows=[
            _selection_row(sample="train", dates="2026-06-10;2026-06-11"),
            _selection_row(sample="holdout", dates="2026-06-12"),
        ],
        minimum_kept_train_trades=1,
        min_directional_open_distance_points=[-999999, 20],
        min_directional_opening_range_breakout_points=[-999999],
        min_continuation_edge_scores=[0],
        min_opening_range_continuation_edge_scores=[0],
        min_lookback_directional_move_points=[-999999],
        min_lookback_efficiency_ratios=[0],
        max_signal_abs_delta_sum_to_average_abs_deltas=[999999],
        max_entry_volume_to_average_volumes=[999999],
        max_entry_volume_to_session_average_volumes=[999999],
        max_risk_to_average_bar_ranges=[999999],
    )

    assert list(split_rows[0].keys()) == SCALED_CONTEXT_SELECTED_VETO_WALK_FORWARD_HEADER
    assert [row["sample"] for row in split_rows] == ["train", "holdout"]
    assert split_rows[0]["veto_name"] == "min_directional_open_distance_points"
    assert split_rows[1]["selected_input_trades"] == 2
    assert split_rows[1]["kept_trades"] == 1
    assert split_rows[1]["net_usd"] == "200"
