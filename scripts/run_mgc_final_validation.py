#!/usr/bin/env python3
"""Final offline validation for the frozen MGC Normal BreakEven bot."""

from __future__ import annotations

import argparse
import csv
import random
import statistics
import sys
from collections import defaultdict
from datetime import date, time
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_mgc_comprehensive_normal_search as comp  # noqa: E402
import run_mgc_eval_pass_initial_scan as mgc_eval  # noqa: E402
import run_mgc_lookback_breakout_candidate_review as review  # noqa: E402
import run_mgc_lookback_breakout_refine as refine  # noqa: E402
import run_mgc_lookback_trade_management as management  # noqa: E402
import run_mgc_normal_bot_research as normal  # noqa: E402


STRATEGY_ID = (
    "mgc_lb_be_sensitivity:"
    "lb10:buf0:cl0.45:end1030:mtf:delta125:breakeven:t25:s15:trig20"
)

DEFAULT_SUMMARY_OUTPUT = "reports/mgc-final-validation-summary.csv"
DEFAULT_HOLDOUT_OUTPUT = "reports/mgc-final-validation-holdout.csv"
DEFAULT_PERIOD_OUTPUT = "reports/mgc-final-validation-periods.csv"
DEFAULT_MONTE_CARLO_OUTPUT = "reports/mgc-final-validation-monte-carlo.csv"
DEFAULT_SENSITIVITY_DIGEST_OUTPUT = "reports/mgc-final-validation-sensitivity-digest.csv"
DEFAULT_REPORT_OUTPUT = "reports/mgc-final-validation.md"
DEFAULT_SENSITIVITY_INPUT = "reports/mgc-lookback-breakeven-sensitivity.csv"
DEFAULT_EXCLUSION_INPUT = "reports/mgc-lookback-context-exclusions.csv"

SUMMARY_HEADER = [
    "schema_version",
    "strategy_id",
    "slippage_ticks",
    "round_turn_cost_usd",
    "trades",
    "trades_per_week",
    "net_usd",
    "average_trade_usd",
    "profit_factor",
    "win_rate",
    "target_hit_rate",
    "stop_hit_rate",
    "managed_stop_hit_rate",
    "end_of_session_rate",
    "max_drawdown_usd",
    "net_to_drawdown",
    "latest_year_net_usd",
    "recent_120_trade_days_net_usd",
    "worst_year_net_usd",
    "worst_quarter_net_usd",
    "worst_month_net_usd",
    "worst_day_usd",
    "worst_trade_usd",
    "max_loss_streak_trades",
    "max_loss_streak_usd",
    "average_holding_minutes",
    "median_holding_minutes",
    "average_gap_days",
    "max_gap_days",
]

HOLDOUT_HEADER = [
    "schema_version",
    "strategy_id",
    "slippage_ticks",
    "config",
    "window",
    "holdout_start_date",
    "holdout_end_date",
    "trades",
    "net_usd",
    "profit_factor",
    "win_rate",
    "max_drawdown_usd",
    "worst_trade_usd",
]

PERIOD_HEADER = [
    "schema_version",
    "strategy_id",
    "slippage_ticks",
    "period_type",
    "period",
    "trades",
    "net_usd",
    "profit_factor",
    "win_rate",
    "max_drawdown_usd",
    "worst_trade_usd",
]

MONTE_CARLO_HEADER = [
    "schema_version",
    "strategy_id",
    "slippage_ticks",
    "iterations",
    "seed",
    "chronological_drawdown_usd",
    "median_drawdown_usd",
    "p90_drawdown_usd",
    "p95_drawdown_usd",
    "p99_drawdown_usd",
    "prob_dd_lte_500",
    "prob_dd_lte_750",
    "prob_dd_lte_1000",
    "prob_dd_lte_1500",
    "median_max_loss_streak",
    "p95_max_loss_streak",
]

SENSITIVITY_DIGEST_HEADER = [
    "schema_version",
    "label",
    "rank",
    "variant_id",
    "trades",
    "base_net_usd",
    "base_profit_factor",
    "base_max_drawdown_usd",
    "base_holdout_net_usd",
    "base_holdout_positive_windows",
    "base_holdout_negative_windows",
    "base_holdout_worst_window_usd",
    "stress_net_usd",
    "stress_profit_factor",
    "stress_max_drawdown_usd",
    "stress_holdout_net_usd",
    "stress_holdout_positive_windows",
    "stress_holdout_negative_windows",
    "stress_holdout_worst_window_usd",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run final offline validation for the frozen MGC Normal BreakEven bot.",
    )
    parser.add_argument("input", nargs="?", default=normal.DEFAULT_INPUT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--holdout-output", default=DEFAULT_HOLDOUT_OUTPUT)
    parser.add_argument("--period-output", default=DEFAULT_PERIOD_OUTPUT)
    parser.add_argument("--monte-carlo-output", default=DEFAULT_MONTE_CARLO_OUTPUT)
    parser.add_argument("--sensitivity-digest-output", default=DEFAULT_SENSITIVITY_DIGEST_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--sensitivity-input", default=DEFAULT_SENSITIVITY_INPUT)
    parser.add_argument("--exclusion-input", default=DEFAULT_EXCLUSION_INPUT)
    parser.add_argument("--symbol", default="MGC")
    parser.add_argument("--monte-carlo-iterations", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260705)
    args = parser.parse_args()

    core = mgc_eval._load_mnq_core()
    mgc_eval._patch_core_for_mgc(core)

    bars = core._load_feature_bars(args.input)
    bars_by_date = mgc_eval._active_bars_by_date(core._bars_by_date(bars))
    rows_by_index = core._rows_by_global_index(bars_by_date)
    trade_dates = sorted(bars_by_date)
    sample_weeks = _sample_weeks(bars)

    signals = _lead_signals(
        core,
        bars_by_date,
        rows_by_index,
        symbol=args.symbol,
    )
    management_spec = management.ManagementSpec(
        "breakeven:t25:s15:trig20",
        25.0,
        15.0,
        "breakeven",
        time(16, 30),
        20.0,
        0.0,
    )

    outcomes_by_slippage: dict[float, list[Any]] = {}
    summary_rows = []
    for slippage_ticks in (1.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0):
        risk = review._risk(
            core,
            normal,
            target_points=management_spec.target_points,
            stop_points=management_spec.stop_points,
            slippage_ticks=slippage_ticks,
        )
        outcomes = management._evaluate_sequence(
            core,
            signals,
            bars_by_date,
            rows_by_index,
            risk,
            management_spec,
        )
        outcomes_by_slippage[slippage_ticks] = outcomes
        summary_rows.append(
            _summary_row(
                core,
                slippage_ticks,
                risk.round_turn_cost_usd,
                outcomes,
                trade_dates,
                sample_weeks,
            ),
        )

    holdout_rows = _holdout_rows(outcomes_by_slippage, trade_dates)
    period_rows = _period_rows(outcomes_by_slippage)
    monte_carlo_rows = _monte_carlo_rows(
        {1.0: outcomes_by_slippage[1.0], 6.0: outcomes_by_slippage[6.0]},
        iterations=args.monte_carlo_iterations,
        seed=args.seed,
    )
    sensitivity_rows = _read_csv(args.sensitivity_input)
    exclusion_rows = _read_csv(args.exclusion_input)
    sensitivity_digest_rows = _sensitivity_digest_rows(sensitivity_rows)

    _write_csv(args.summary_output, SUMMARY_HEADER, summary_rows)
    _write_csv(args.holdout_output, HOLDOUT_HEADER, holdout_rows)
    _write_csv(args.period_output, PERIOD_HEADER, period_rows)
    _write_csv(args.monte_carlo_output, MONTE_CARLO_HEADER, monte_carlo_rows)
    _write_csv(args.sensitivity_digest_output, SENSITIVITY_DIGEST_HEADER, sensitivity_digest_rows)
    _write_report(
        args.report_output,
        bars,
        signals,
        summary_rows,
        holdout_rows,
        period_rows,
        monte_carlo_rows,
        sensitivity_rows,
        sensitivity_digest_rows,
        exclusion_rows,
    )

    base_row = _row_for_slippage(summary_rows, 1.0)
    stress_row = _row_for_slippage(summary_rows, 6.0)
    print(
        "wrote MGC final validation: "
        f"trades={base_row['trades'] if base_row else 'n/a'} "
        f"base_net={base_row['net_usd'] if base_row else 'n/a'} "
        f"stress_net={stress_row['net_usd'] if stress_row else 'n/a'} "
        f"report={args.report_output}",
    )
    return 0


def _lead_signals(
    core: Any,
    bars_by_date: dict[date, list[Any]],
    rows_by_index: dict[int, int],
    *,
    symbol: str,
) -> list[Any]:
    raw_signals = comp._all_lookback_breakouts(
        core,
        bars_by_date,
        strategy_id=STRATEGY_ID,
        lookback_bars=10,
        buffer_points=0.0,
        delta_threshold=0.0,
        close_location_threshold=0.45,
        entry_end=time(10, 30),
        symbol=symbol,
    )
    signals = []
    for signal in sorted(raw_signals, key=lambda item: item.bar.timestamp):
        features = refine._features(signal, bars_by_date, rows_by_index)
        if int(features["weekday"]) not in {0, 1, 4}:
            continue
        if float(features["abs_delta"]) > 125.0:
            continue
        signals.append(signal)
    return signals


def _summary_row(
    core: Any,
    slippage_ticks: float,
    round_turn_cost_usd: float,
    outcomes: list[Any],
    trade_dates: list[date],
    sample_weeks: float,
) -> dict[str, object]:
    metrics = _metrics(core, outcomes)
    periods = _period_groups(outcomes)
    years = [sum(outcome.net_usd for outcome in values) for key, values in periods.items() if key.startswith("year:")]
    quarters = [sum(outcome.net_usd for outcome in values) for key, values in periods.items() if key.startswith("quarter:")]
    months = [sum(outcome.net_usd for outcome in values) for key, values in periods.items() if key.startswith("month:")]
    recent_dates = set(trade_dates[-120:])
    latest_year = max(trade_dates).year if trade_dates else 0
    gaps = _gap_days(outcomes)
    return {
        "schema_version": 1,
        "strategy_id": STRATEGY_ID,
        "slippage_ticks": _fmt(slippage_ticks),
        "round_turn_cost_usd": _fmt(round_turn_cost_usd),
        "trades": len(outcomes),
        "trades_per_week": _fmt(len(outcomes) / sample_weeks if sample_weeks else 0.0),
        "net_usd": _fmt(metrics["net"]),
        "average_trade_usd": _fmt(metrics["average"]),
        "profit_factor": _fmt(metrics["profit_factor"]),
        "win_rate": _fmt(metrics["win_rate"]),
        "target_hit_rate": _fmt(_exit_rate(outcomes, "target_hit")),
        "stop_hit_rate": _fmt(_exit_rate(outcomes, "stop_hit")),
        "managed_stop_hit_rate": _fmt(_exit_rate(outcomes, "managed_stop_hit")),
        "end_of_session_rate": _fmt(_exit_rate(outcomes, "end_of_session")),
        "max_drawdown_usd": _fmt(metrics["drawdown"]),
        "net_to_drawdown": _fmt(_net_to_drawdown(metrics["net"], metrics["drawdown"])),
        "latest_year_net_usd": _fmt(sum(o.net_usd for o in outcomes if o.entry_time.year == latest_year)),
        "recent_120_trade_days_net_usd": _fmt(sum(o.net_usd for o in outcomes if o.entry_time.date() in recent_dates)),
        "worst_year_net_usd": _fmt(min(years) if years else 0.0),
        "worst_quarter_net_usd": _fmt(min(quarters) if quarters else 0.0),
        "worst_month_net_usd": _fmt(min(months) if months else 0.0),
        "worst_day_usd": _fmt(_worst_group(outcomes, key=lambda outcome: outcome.entry_time.date())),
        "worst_trade_usd": _fmt(metrics["worst_trade"]),
        "max_loss_streak_trades": metrics["max_loss_streak_trades"],
        "max_loss_streak_usd": _fmt(metrics["max_loss_streak_usd"]),
        "average_holding_minutes": _fmt(statistics.mean([o.holding_minutes for o in outcomes]) if outcomes else 0.0),
        "median_holding_minutes": _fmt(statistics.median([o.holding_minutes for o in outcomes]) if outcomes else 0.0),
        "average_gap_days": _fmt(statistics.mean(gaps) if gaps else 0.0),
        "max_gap_days": _fmt(max(gaps) if gaps else 0.0),
    }


def _holdout_rows(
    outcomes_by_slippage: dict[float, list[Any]],
    trade_dates: list[date],
) -> list[dict[str, object]]:
    configs = ((60, 20), (90, 30), (120, 40), (180, 40), (240, 60), (320, 60))
    rows = []
    for slippage_ticks, outcomes in outcomes_by_slippage.items():
        by_date: dict[date, list[Any]] = defaultdict(list)
        for outcome in outcomes:
            by_date[outcome.entry_time.date()].append(outcome)
        for train_count, holdout_count in configs:
            max_start = len(trade_dates) - train_count - holdout_count
            if max_start < 0:
                continue
            for window, start in enumerate(range(0, max_start + 1, holdout_count)):
                holdout_dates = trade_dates[start + train_count:start + train_count + holdout_count]
                holdout_outcomes = []
                for trade_date in holdout_dates:
                    holdout_outcomes.extend(by_date.get(trade_date, []))
                metrics = _metrics(None, sorted(holdout_outcomes, key=lambda outcome: outcome.entry_time))
                rows.append(
                    {
                        "schema_version": 1,
                        "strategy_id": STRATEGY_ID,
                        "slippage_ticks": _fmt(slippage_ticks),
                        "config": f"{train_count}x{holdout_count}",
                        "window": window,
                        "holdout_start_date": holdout_dates[0].isoformat(),
                        "holdout_end_date": holdout_dates[-1].isoformat(),
                        "trades": len(holdout_outcomes),
                        "net_usd": _fmt(metrics["net"]),
                        "profit_factor": _fmt(metrics["profit_factor"]),
                        "win_rate": _fmt(metrics["win_rate"]),
                        "max_drawdown_usd": _fmt(metrics["drawdown"]),
                        "worst_trade_usd": _fmt(metrics["worst_trade"]),
                    },
                )
    return rows


def _period_rows(outcomes_by_slippage: dict[float, list[Any]]) -> list[dict[str, object]]:
    rows = []
    for slippage_ticks, outcomes in outcomes_by_slippage.items():
        if slippage_ticks not in {1.0, 6.0}:
            continue
        for period_id, period_outcomes in sorted(_period_groups(outcomes).items()):
            period_type, period = period_id.split(":", 1)
            metrics = _metrics(None, period_outcomes)
            rows.append(
                {
                    "schema_version": 1,
                    "strategy_id": STRATEGY_ID,
                    "slippage_ticks": _fmt(slippage_ticks),
                    "period_type": period_type,
                    "period": period,
                    "trades": len(period_outcomes),
                    "net_usd": _fmt(metrics["net"]),
                    "profit_factor": _fmt(metrics["profit_factor"]),
                    "win_rate": _fmt(metrics["win_rate"]),
                    "max_drawdown_usd": _fmt(metrics["drawdown"]),
                    "worst_trade_usd": _fmt(metrics["worst_trade"]),
                },
            )
    return rows


def _monte_carlo_rows(
    outcomes_by_slippage: dict[float, list[Any]],
    *,
    iterations: int,
    seed: int,
) -> list[dict[str, object]]:
    rows = []
    rng = random.Random(seed)
    for slippage_ticks, outcomes in outcomes_by_slippage.items():
        values = [outcome.net_usd for outcome in outcomes]
        chronological_drawdown = _max_drawdown(values)
        simulated_drawdowns = []
        simulated_loss_streaks = []
        for _ in range(iterations):
            shuffled = values[:]
            rng.shuffle(shuffled)
            simulated_drawdowns.append(_max_drawdown(shuffled))
            simulated_loss_streaks.append(_max_loss_streak_count(shuffled))
        sorted_dd = sorted(simulated_drawdowns)
        sorted_streaks = sorted(simulated_loss_streaks)
        rows.append(
            {
                "schema_version": 1,
                "strategy_id": STRATEGY_ID,
                "slippage_ticks": _fmt(slippage_ticks),
                "iterations": iterations,
                "seed": seed,
                "chronological_drawdown_usd": _fmt(chronological_drawdown),
                "median_drawdown_usd": _fmt(_quantile(sorted_dd, 0.50)),
                "p90_drawdown_usd": _fmt(_quantile(sorted_dd, 0.10)),
                "p95_drawdown_usd": _fmt(_quantile(sorted_dd, 0.05)),
                "p99_drawdown_usd": _fmt(_quantile(sorted_dd, 0.01)),
                "prob_dd_lte_500": _fmt(sum(dd <= -500.0 for dd in simulated_drawdowns) / iterations),
                "prob_dd_lte_750": _fmt(sum(dd <= -750.0 for dd in simulated_drawdowns) / iterations),
                "prob_dd_lte_1000": _fmt(sum(dd <= -1000.0 for dd in simulated_drawdowns) / iterations),
                "prob_dd_lte_1500": _fmt(sum(dd <= -1500.0 for dd in simulated_drawdowns) / iterations),
                "median_max_loss_streak": _fmt(_quantile(sorted_streaks, 0.50)),
                "p95_max_loss_streak": _fmt(_quantile(sorted_streaks, 0.95)),
            },
        )
    return rows


def _sensitivity_digest_rows(rows: list[dict[str, str]]) -> list[dict[str, object]]:
    refs = (
        (
            "implemented risk-balanced lead",
            STRATEGY_ID,
        ),
        (
            "higher-net growth monitor",
            "mgc_lb_be_sensitivity:lb10:buf0:cl0.45:end1045:mtf:delta125:breakeven:t25:s15:trig20",
        ),
        (
            "lowest-window-risk monitor",
            "mgc_lb_be_sensitivity:lb10:buf0:cl0.55:end1030:mtf:delta150:breakeven:t25:s15:trig20",
        ),
        (
            "old fixed-exit baseline",
            "mgc_lb_be_sensitivity:lb10:buf0:cl0.5:end1030:mtf:delta100:fixed:t25:s15:clock1630",
        ),
    )
    digest = []
    for label, variant_id in refs:
        row = _find_variant(rows, variant_id)
        if row is None:
            continue
        digest.append(
            {
                "schema_version": 1,
                "label": label,
                "rank": rows.index(row) + 1,
                "variant_id": row["variant_id"],
                "trades": row["trades"],
                "base_net_usd": row["base_net_usd"],
                "base_profit_factor": row["base_profit_factor"],
                "base_max_drawdown_usd": row["base_max_drawdown_usd"],
                "base_holdout_net_usd": row["base_holdout_net_usd"],
                "base_holdout_positive_windows": row["base_holdout_positive_windows"],
                "base_holdout_negative_windows": row["base_holdout_negative_windows"],
                "base_holdout_worst_window_usd": row["base_holdout_worst_window_usd"],
                "stress_net_usd": row["stress_net_usd"],
                "stress_profit_factor": row["stress_profit_factor"],
                "stress_max_drawdown_usd": row["stress_max_drawdown_usd"],
                "stress_holdout_net_usd": row["stress_holdout_net_usd"],
                "stress_holdout_positive_windows": row["stress_holdout_positive_windows"],
                "stress_holdout_negative_windows": row["stress_holdout_negative_windows"],
                "stress_holdout_worst_window_usd": row["stress_holdout_worst_window_usd"],
            },
        )
    return digest


def _write_report(
    report_output: str,
    bars: list[Any],
    signals: list[Any],
    summary_rows: list[dict[str, object]],
    holdout_rows: list[dict[str, object]],
    period_rows: list[dict[str, object]],
    monte_carlo_rows: list[dict[str, object]],
    sensitivity_rows: list[dict[str, str]],
    sensitivity_digest_rows: list[dict[str, object]],
    exclusion_rows: list[dict[str, str]],
) -> None:
    base_row = _row_for_slippage(summary_rows, 1.0)
    stress_row = _row_for_slippage(summary_rows, 6.0)
    accepted_sensitivity = _accepted_sensitivity_rows(sensitivity_rows)
    implemented_digest = _find_digest(sensitivity_digest_rows, "implemented risk-balanced lead")
    top_exclusion = exclusion_rows[0] if exclusion_rows else None

    lines = [
        "# MGC Final Validation",
        "",
        "Status: final offline research battery for the frozen MGC Normal BreakEven bot on the current export.",
        "",
        "## Scope",
        "",
        f"- source rows: `{len(bars)}`",
        f"- dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        f"- unique active trading dates: `{len({bar.trade_date for bar in bars})}`",
        f"- raw accepted setup candidates before one-trade-per-day sequencing: `{len(signals)}`",
        f"- sequenced live-rule trades: `{base_row['trades'] if base_row else 0}`",
        "- instrument: `MGC`, fixed `1 MGC` sizing",
        "- base cost model: `$0.50/side` commission plus `1` total slippage tick per contract",
        "- same-bar handling: stop first",
        "- tests added here: extended slippage, wider rolling holdouts, period attribution, Monte Carlo trade-order risk, sensitivity digest, and context-exclusion review",
        "",
        "## Implemented Rule",
        "",
        f"- strategy: `{STRATEGY_ID}`",
        "- entry: `10` bar lookback breakout, `0` buffer, directional close-location `>= 0.45`, entry through `10:30`, Monday/Tuesday/Friday only, entry-bar absolute delta `<= 125`",
        "- management: `25` point target, `15` point initial stop, move stop to breakeven after `+20` favorable points",
        "- operational limits: one submitted trade per chart date, `$500` daily loss lock, `16:30` flatten, exact account whitelist for live routing",
        "",
        "## Lead Scorecard",
        "",
        "| Slip Ticks | Cost | Trades | /Wk | Net | Avg | PF | Win | Target | BE Stop | DD | Net/DD | Latest | Recent120 | Worst Q | Worst Month | Max Gap |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary_rows:
        lines.append(
            "| "
            f"{row['slippage_ticks']} | {row['round_turn_cost_usd']} | "
            f"{row['trades']} | {row['trades_per_week']} | {row['net_usd']} | "
            f"{row['average_trade_usd']} | {row['profit_factor']} | "
            f"{float(row['win_rate']) * 100:.1f}% | "
            f"{float(row['target_hit_rate']) * 100:.1f}% | "
            f"{float(row['managed_stop_hit_rate']) * 100:.1f}% | "
            f"{row['max_drawdown_usd']} | {row['net_to_drawdown']} | "
            f"{row['latest_year_net_usd']} | {row['recent_120_trade_days_net_usd']} | "
            f"{row['worst_quarter_net_usd']} | {row['worst_month_net_usd']} | "
            f"{row['max_gap_days']} |"
        )
    lines.extend(
        [
            "",
            "## Rolling Holdout Summary",
            "",
            "Rows below use the wider holdout battery added in this pass. They are rolling trade-date windows, so aggregate net double-counts trades across windows and should be read as stability evidence, not a standalone P/L forecast.",
            "",
            "| Slip | Config | Windows | Positive | Negative | No Trade | Net | Worst | Median |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    for row in _holdout_summary_rows(holdout_rows):
        if float(row["slippage_ticks"]) not in {1.0, 6.0}:
            continue
        lines.append(
            "| "
            f"{row['slippage_ticks']} | {row['config']} | {row['windows']} | "
            f"{row['positive']} | {row['negative']} | {row['no_trade']} | "
            f"{row['net_usd']} | {row['worst_net_usd']} | {row['median_net_usd']} |"
        )
    lines.extend(
        [
            "",
            "## Period Stress",
            "",
            "| Slip | Worst Year | Worst Quarter | Worst Month |",
            "| ---: | ---: | ---: | ---: |",
        ],
    )
    for slippage_ticks in (1.0, 6.0):
        rows = [row for row in period_rows if float(row["slippage_ticks"]) == slippage_ticks]
        lines.append(
            "| "
            f"{_fmt(slippage_ticks)} | "
            f"{_worst_period(rows, 'year')} | "
            f"{_worst_period(rows, 'quarter')} | "
            f"{_worst_period(rows, 'month')} |"
        )
    lines.extend(
        [
            "",
            "## Monte Carlo Trade-Order Risk",
            "",
            "This shuffles the same trade outcomes to estimate path-risk sensitivity. It does not change the edge; it only changes trade order.",
            "",
            "| Slip | Chron DD | Median DD | P95 DD | P99 DD | P(DD <= -500) | P(DD <= -750) | P(DD <= -1000) | P95 Loss Streak |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    for row in monte_carlo_rows:
        lines.append(
            "| "
            f"{row['slippage_ticks']} | {row['chronological_drawdown_usd']} | "
            f"{row['median_drawdown_usd']} | {row['p95_drawdown_usd']} | "
            f"{row['p99_drawdown_usd']} | "
            f"{float(row['prob_dd_lte_500']) * 100:.1f}% | "
            f"{float(row['prob_dd_lte_750']) * 100:.1f}% | "
            f"{float(row['prob_dd_lte_1000']) * 100:.1f}% | "
            f"{row['p95_max_loss_streak']} |"
        )
    lines.extend(
        [
            "",
            "## Sensitivity Digest",
            "",
            f"- sensitivity rows available: `{len(sensitivity_rows)}`",
            f"- rows passing the strict final lens: `{len(accepted_sensitivity)}`",
            "- final lens: at least `250` trades, positive stress net, stress PF `>= 1.50`, stress DD better than `-$1100`, at most one stress holdout loser, and stress worst holdout better than `-$800`",
        ],
    )
    if implemented_digest is not None:
        lines.append(
            f"- implemented lead sensitivity rank: `{implemented_digest['rank']}` of `{len(sensitivity_rows)}` by the paired sensitivity sorter",
        )
    lines.extend(
        [
            "",
            "| Label | Rank | Trades | Base Net | Base PF | Base DD | Stress Net | Stress PF | Stress DD | Stress Holdout | Stress Pos | Stress Worst |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    for row in sensitivity_digest_rows:
        lines.append(
            "| "
            f"{row['label']} | {row['rank']} | {row['trades']} | "
            f"{row['base_net_usd']} | {row['base_profit_factor']} | {row['base_max_drawdown_usd']} | "
            f"{row['stress_net_usd']} | {row['stress_profit_factor']} | {row['stress_max_drawdown_usd']} | "
            f"{row['stress_holdout_net_usd']} | "
            f"{row['stress_holdout_positive_windows']}/{int(row['stress_holdout_positive_windows']) + int(row['stress_holdout_negative_windows'])} | "
            f"{row['stress_holdout_worst_window_usd']} |"
        )
    lines.extend(
        [
            "",
            "## Context Exclusion Review",
            "",
            "The context-stress pass found weak buckets, but no simple exclusion improved full-sample net, PF, drawdown, and holdout quality together.",
        ],
    )
    if top_exclusion is not None:
        lines.extend(
            [
                "",
                "Best exclusion by the prior context sorter:",
                "",
                (
                    f"- `{top_exclusion['exclusion_id']}`: trades `{top_exclusion['trades']}`, "
                    f"stress net `{top_exclusion['stress_net_usd']}` "
                    f"(`{top_exclusion['stress_net_delta_usd']}` versus lead), "
                    f"stress PF `{top_exclusion['stress_profit_factor']}`, "
                    f"stress holdout `{top_exclusion['stress_holdout_net_usd']}`, "
                    f"stress worst window `{top_exclusion['stress_holdout_worst_window_usd']}`"
                ),
            ],
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            "MGC is now `100%` researched for the current one-minute order-flow export. This means the fixed-rule offline research budget is saturated for this dataset; it does not mean the bot is guaranteed to remain profitable.",
            "",
            "The current `10:30 / cl0.45 / delta125 / 25-15 / BE+20` rule remains the live rule. The higher-net `10:45` row is only a monitor because it increases drawdown, while the lowest-window-risk `cl0.55 / delta150` row gives up too much net/PF to replace the live rule.",
            "",
            "Next gate is operational, not more offline tuning: run the approved `1 MGC` controlled live setup, keep account-level risk small, collect forward sample, and revisit research only after a materially larger export or a live-vs-research behavior mismatch.",
            "",
        ],
    )
    if base_row is not None and stress_row is not None:
        lines.extend(
            [
                "Current headline:",
                "",
                (
                    f"- base: `{base_row['trades']}` trades, `{base_row['net_usd']}` net, "
                    f"`{base_row['profit_factor']}` PF, `{base_row['max_drawdown_usd']}` DD, "
                    f"`{base_row['trades_per_week']}` trades/week"
                ),
                (
                    f"- six-tick stress: `{stress_row['net_usd']}` net, "
                    f"`{stress_row['profit_factor']}` PF, `{stress_row['max_drawdown_usd']}` DD"
                ),
                "",
            ],
        )
    Path(report_output).write_text("\n".join(lines), encoding="utf-8")


def _metrics(core: Any, outcomes: list[Any]) -> dict[str, float | int]:
    if not outcomes:
        return {
            "net": 0.0,
            "average": 0.0,
            "profit_factor": 0.0,
            "win_rate": 0.0,
            "drawdown": 0.0,
            "worst_trade": 0.0,
            "max_loss_streak_trades": 0,
            "max_loss_streak_usd": 0.0,
        }
    values = [outcome.net_usd for outcome in outcomes]
    positive = [value for value in values if value > 0.0]
    negative = [value for value in values if value < 0.0]
    loss_count, loss_usd = _max_loss_streak(values)
    drawdown = core._max_drawdown(values) if core is not None else _max_drawdown(values)
    return {
        "net": sum(values),
        "average": statistics.mean(values),
        "profit_factor": sum(positive) / abs(sum(negative)) if negative else 999.0,
        "win_rate": len(positive) / len(values),
        "drawdown": drawdown,
        "worst_trade": min(values),
        "max_loss_streak_trades": loss_count,
        "max_loss_streak_usd": loss_usd,
    }


def _period_groups(outcomes: list[Any]) -> dict[str, list[Any]]:
    groups: dict[str, list[Any]] = defaultdict(list)
    for outcome in outcomes:
        groups[f"year:{outcome.entry_time.year}"].append(outcome)
        quarter = (outcome.entry_time.month - 1) // 3 + 1
        groups[f"quarter:{outcome.entry_time.year}Q{quarter}"].append(outcome)
        groups[f"month:{outcome.entry_time.year}-{outcome.entry_time.month:02d}"].append(outcome)
    return groups


def _holdout_summary_rows(holdout_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in holdout_rows:
        grouped[(str(row["slippage_ticks"]), str(row["config"]))].append(row)
    rows = []
    for (slippage_ticks, config), group in sorted(
        grouped.items(),
        key=lambda item: (float(item[0][0]), *_config_sort_key(item[0][1])),
    ):
        nets = [float(row["net_usd"]) for row in group]
        trades = [int(row["trades"]) for row in group]
        rows.append(
            {
                "slippage_ticks": slippage_ticks,
                "config": config,
                "windows": len(group),
                "positive": sum(net > 0.0 for net in nets),
                "negative": sum(net < 0.0 for net in nets),
                "no_trade": sum(count == 0 for count in trades),
                "net_usd": _fmt(sum(nets)),
                "worst_net_usd": _fmt(min(nets) if nets else 0.0),
                "median_net_usd": _fmt(statistics.median(nets) if nets else 0.0),
            },
        )
    return rows


def _config_sort_key(config: str) -> tuple[int, int]:
    train_count, holdout_count = config.split("x", 1)
    return int(train_count), int(holdout_count)


def _accepted_sensitivity_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    accepted = []
    for row in rows:
        stress_windows = int(row["stress_holdout_positive_windows"]) + int(row["stress_holdout_negative_windows"])
        if (
            int(row["trades"]) >= 250
            and float(row["stress_net_usd"]) > 0.0
            and float(row["stress_profit_factor"]) >= 1.50
            and float(row["stress_max_drawdown_usd"]) > -1100.0
            and int(row["stress_holdout_negative_windows"]) <= 1
            and stress_windows > 0
            and float(row["stress_holdout_worst_window_usd"]) > -800.0
        ):
            accepted.append(row)
    return accepted


def _worst_period(rows: list[dict[str, object]], period_type: str) -> str:
    filtered = [row for row in rows if row["period_type"] == period_type]
    if not filtered:
        return "`none`"
    worst = min(filtered, key=lambda row: float(row["net_usd"]))
    return f"`{worst['period']}={worst['net_usd']}`"


def _worst_group(outcomes: list[Any], *, key: Any) -> float:
    grouped: dict[Any, float] = defaultdict(float)
    for outcome in outcomes:
        grouped[key(outcome)] += outcome.net_usd
    return min(grouped.values()) if grouped else 0.0


def _exit_rate(outcomes: list[Any], exit_reason: str) -> float:
    return sum(outcome.exit_reason == exit_reason for outcome in outcomes) / len(outcomes) if outcomes else 0.0


def _max_loss_streak(values: Iterable[float]) -> tuple[int, float]:
    max_count = 0
    max_usd = 0.0
    count = 0
    total = 0.0
    for value in values:
        if value < 0.0:
            count += 1
            total += value
            if count > max_count or (count == max_count and total < max_usd):
                max_count = count
                max_usd = total
        else:
            count = 0
            total = 0.0
    return max_count, max_usd


def _max_loss_streak_count(values: Iterable[float]) -> int:
    count, _usd = _max_loss_streak(values)
    return count


def _max_drawdown(values: Iterable[float]) -> float:
    peak = 0.0
    equity = 0.0
    drawdown = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = min(drawdown, equity - peak)
    return drawdown


def _quantile(sorted_values: list[float | int], quantile: float) -> float:
    if not sorted_values:
        return 0.0
    index = int(round((len(sorted_values) - 1) * quantile))
    return float(sorted_values[max(0, min(index, len(sorted_values) - 1))])


def _gap_days(outcomes: list[Any]) -> list[float]:
    ordered = sorted(outcomes, key=lambda outcome: outcome.entry_time)
    return [
        (right.entry_time.date() - left.entry_time.date()).days
        for left, right in zip(ordered, ordered[1:])
    ]


def _net_to_drawdown(net_usd: float, drawdown_usd: float) -> float:
    return net_usd / abs(drawdown_usd) if drawdown_usd else 0.0


def _sample_weeks(bars: list[Any]) -> float:
    if not bars:
        return 0.0
    days = (bars[-1].trade_date - bars[0].trade_date).days + 1
    return days / 7.0


def _row_for_slippage(rows: list[dict[str, object]], slippage_ticks: float) -> dict[str, object] | None:
    for row in rows:
        if float(row["slippage_ticks"]) == slippage_ticks:
            return row
    return None


def _find_variant(rows: list[dict[str, str]], variant_id: str) -> dict[str, str] | None:
    for row in rows:
        if row.get("variant_id") == variant_id:
            return row
    return None


def _find_digest(rows: list[dict[str, object]], label: str) -> dict[str, object] | None:
    for row in rows:
        if row["label"] == label:
            return row
    return None


def _read_csv(path: str) -> list[dict[str, str]]:
    input_path = Path(path)
    if not input_path.exists():
        return []
    with input_path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: str, header: list[str], rows: list[dict[str, object]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _fmt(value: float | int) -> str:
    if isinstance(value, int):
        return str(value)
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.8f}".rstrip("0").rstrip(".")


if __name__ == "__main__":
    raise SystemExit(main())
