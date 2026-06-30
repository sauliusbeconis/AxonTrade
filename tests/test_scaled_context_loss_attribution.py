from __future__ import annotations

from axontrade.research import (
    SCALED_CONTEXT_DAILY_SUMMARY_HEADER,
    SCALED_CONTEXT_FEATURE_BUCKET_HEADER,
    SCALED_CONTEXT_GUARD_EVALUATION_HEADER,
    SCALED_CONTEXT_GUARD_ROBUSTNESS_HEADER,
    SCALED_CONTEXT_GUARD_WALK_FORWARD_HEADER,
    GuardCondition,
    ScaledContextGuardRule,
    bucket_scaled_context_features,
    evaluate_scaled_context_fixed_guards,
    render_scaled_context_guard_robustness_report,
    render_scaled_context_loss_attribution_report,
    run_scaled_context_guard_robustness,
    run_scaled_context_guard_walk_forward,
    summarize_scaled_context_daily_performance,
)


def _context_row(
    index: int,
    *,
    trade_date: str,
    net_usd: float,
    lookback_move: float = -3,
    session_range: float = 35,
    risk_ratio: float = 2,
    minutes: int = 100,
    direction: str = "long",
) -> dict[str, object]:
    return {
        "signal_id": f"strategy_ESU26-CME_{index}",
        "symbol": "ESU26-CME",
        "direction": direction,
        "entry_time": f"{trade_date} 10:00:00",
        "entry_bar_index": index,
        "exit_reason": "runner_target_hit" if net_usd > 0 else "full_stop_hit",
        "net_usd": net_usd,
        "minutes_after_rth_open": minutes,
        "entry_bar_delta": index,
        "signal_abs_delta_sum_to_average_abs_delta": 1,
        "entry_position_in_session_range": 0.2,
        "fade_edge_score": 0.8,
        "opening_range_fade_edge_score": 1.2,
        "directional_open_distance_points": -20,
        "directional_opening_range_breakout_points": -10,
        "lookback_directional_move_points": lookback_move,
        "lookback_efficiency_ratio": 0.2,
        "lookback_choppiness_score": 0.8,
        "session_range_points": session_range,
        "entry_volume_to_session_average_volume": 1,
        "entry_trades_to_session_average_trades": 1,
        "lookback_volume_to_session_average_volume": 1,
        "lookback_trades_to_session_average_trades": 1,
        "risk_to_average_bar_range": risk_ratio,
        "runner_target_to_average_bar_range": risk_ratio,
    }


def _push_guard() -> ScaledContextGuardRule:
    return ScaledContextGuardRule(
        "push_guard",
        (GuardCondition("lookback_directional_move_points", "<=", -2.5),),
    )


def test_summarizes_daily_performance() -> None:
    rows = summarize_scaled_context_daily_performance(
        [
            _context_row(1, trade_date="2026-06-10", net_usd=200),
            _context_row(2, trade_date="2026-06-10", net_usd=-100),
            _context_row(3, trade_date="2026-06-11", net_usd=300),
        ],
    )

    assert list(rows[0].keys()) == SCALED_CONTEXT_DAILY_SUMMARY_HEADER
    assert rows[0]["trade_date"] == "2026-06-10"
    assert rows[0]["trades"] == 2
    assert rows[0]["net_usd"] == "100"
    assert rows[1]["cumulative_net_usd"] == "400"


def test_buckets_feature_performance() -> None:
    rows = [
        _context_row(index, trade_date="2026-06-10", net_usd=100, lookback_move=-index)
        for index in range(1, 5)
    ]

    bucket_rows = bucket_scaled_context_features(
        rows,
        features=["lookback_directional_move_points"],
        bucket_count=2,
        minimum_bucket_trades=1,
    )

    assert list(bucket_rows[0].keys()) == SCALED_CONTEXT_FEATURE_BUCKET_HEADER
    assert [row["trades"] for row in bucket_rows] == [2, 2]
    assert bucket_rows[0]["feature"] == "lookback_directional_move_points"


def test_evaluates_fixed_guard_rules() -> None:
    rows = evaluate_scaled_context_fixed_guards(
        [
            _context_row(1, trade_date="2026-06-10", net_usd=200, lookback_move=-3),
            _context_row(2, trade_date="2026-06-10", net_usd=-100, lookback_move=1),
        ],
        guard_rules=[ScaledContextGuardRule("none", ()), _push_guard()],
    )

    assert list(rows[0].keys()) == SCALED_CONTEXT_GUARD_EVALUATION_HEADER
    assert rows[1]["guard_name"] == "push_guard"
    assert rows[1]["kept_trades"] == 1
    assert rows[1]["net_usd"] == "200"
    assert rows[1]["guard_net_improvement_usd"] == "100"


def test_runs_guard_walk_forward_selected_on_train() -> None:
    context_rows = [
        _context_row(1, trade_date="2026-06-10", net_usd=200, lookback_move=-3),
        _context_row(2, trade_date="2026-06-10", net_usd=-100, lookback_move=1),
        _context_row(3, trade_date="2026-06-11", net_usd=200, lookback_move=-3),
        _context_row(4, trade_date="2026-06-11", net_usd=-100, lookback_move=1),
        _context_row(5, trade_date="2026-06-12", net_usd=200, lookback_move=-3),
        _context_row(6, trade_date="2026-06-12", net_usd=-100, lookback_move=1),
    ]

    split_rows = run_scaled_context_guard_walk_forward(
        context_rows,
        train_date_count=2,
        holdout_date_count=1,
        window_step_date_count=1,
        minimum_train_trades=1,
        minimum_train_participation_rate=0,
        guard_rules=[ScaledContextGuardRule("none", ()), _push_guard()],
    )

    assert list(split_rows[0].keys()) == SCALED_CONTEXT_GUARD_WALK_FORWARD_HEADER
    assert [row["sample"] for row in split_rows] == ["train", "holdout"]
    assert split_rows[0]["guard_name"] == "push_guard"
    assert split_rows[1]["input_trades"] == 2
    assert split_rows[1]["kept_trades"] == 1
    assert split_rows[1]["net_usd"] == "200"


def test_runs_guard_robustness_summary() -> None:
    context_rows = [
        _context_row(1, trade_date="2026-06-10", net_usd=200, lookback_move=-3),
        _context_row(2, trade_date="2026-06-10", net_usd=-100, lookback_move=1),
        _context_row(3, trade_date="2026-06-11", net_usd=200, lookback_move=-3),
        _context_row(4, trade_date="2026-06-11", net_usd=-100, lookback_move=1),
        _context_row(5, trade_date="2026-06-12", net_usd=200, lookback_move=-3),
        _context_row(6, trade_date="2026-06-12", net_usd=-100, lookback_move=1),
    ]

    robustness_rows = run_scaled_context_guard_robustness(
        context_rows,
        window_configs=[(2, 1, 1)],
        minimum_train_trades=1,
        minimum_train_participation_rate=0,
        guard_rules=[ScaledContextGuardRule("none", ()), _push_guard()],
    )

    assert list(robustness_rows[0].keys()) == SCALED_CONTEXT_GUARD_ROBUSTNESS_HEADER
    assert robustness_rows[0]["holdout_windows"] == 1
    assert robustness_rows[0]["unfiltered_holdout_trades"] == 2
    assert robustness_rows[0]["guarded_holdout_trades"] == 1
    assert robustness_rows[0]["guarded_holdout_net_usd"] == "200"
    assert robustness_rows[0]["selected_guard_counts"] == "push_guard=1"


def test_renders_guard_robustness_report() -> None:
    robustness_rows = [
        {
            "train_date_count": 2,
            "holdout_date_count": 1,
            "window_step_date_count": 1,
            "holdout_windows": 1,
            "unfiltered_holdout_net_usd": "100",
            "guarded_holdout_net_usd": "200",
            "guard_net_improvement_usd": "100",
            "guarded_holdout_trades": 1,
            "guarded_average_net_usd": "200",
            "negative_holdout_windows": 0,
            "worst_guarded_window_net_usd": "200",
        },
    ]

    report = render_scaled_context_guard_robustness_report(
        robustness_rows,
        context_source="context.csv",
    )

    assert "Scaled Context Guard Robustness" in report
    assert "`context.csv`" in report
    assert "| 2 | 1 | 1 | 1 | 100 | 200 | 100 | 1 | 200 | 0 | 200 |" in report


def test_renders_loss_attribution_report() -> None:
    context_rows = [
        _context_row(1, trade_date="2026-06-10", net_usd=200, lookback_move=-3),
        _context_row(2, trade_date="2026-06-10", net_usd=-100, lookback_move=1),
        _context_row(3, trade_date="2026-06-11", net_usd=200, lookback_move=-3),
        _context_row(4, trade_date="2026-06-11", net_usd=-100, lookback_move=1),
        _context_row(5, trade_date="2026-06-12", net_usd=200, lookback_move=-3),
        _context_row(6, trade_date="2026-06-12", net_usd=-100, lookback_move=1),
    ]
    daily_rows = summarize_scaled_context_daily_performance(context_rows)
    fixed_rows = evaluate_scaled_context_fixed_guards(
        context_rows,
        guard_rules=[ScaledContextGuardRule("none", ()), _push_guard()],
    )
    walk_forward_rows = run_scaled_context_guard_walk_forward(
        context_rows,
        train_date_count=2,
        holdout_date_count=1,
        minimum_train_trades=1,
        minimum_train_participation_rate=0,
        guard_rules=[ScaledContextGuardRule("none", ()), _push_guard()],
    )

    report = render_scaled_context_loss_attribution_report(
        context_rows=context_rows,
        daily_rows=daily_rows,
        fixed_guard_rows=fixed_rows,
        walk_forward_rows=walk_forward_rows,
    )

    assert "Scaled Context Loss Attribution" in report
    assert "push_guard" in report
