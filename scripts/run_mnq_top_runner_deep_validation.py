#!/usr/bin/env python3
"""Deep validation for frozen MNQ Top Runner candidates."""

from __future__ import annotations

import argparse
import csv
import random
import statistics
import sys
from collections import defaultdict
from datetime import date, time
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_mnq_eval_pass_wave_rider as wave  # noqa: E402
import run_mnq_top_runner_research as runner  # noqa: E402
import run_mnq_top_runner_validation as validation  # noqa: E402


DEFAULT_SUMMARY_OUTPUT = "reports/mnq-top-runner-deep-validation-summary.csv"
DEFAULT_HOLDOUT_OUTPUT = "reports/mnq-top-runner-deep-validation-holdout.csv"
DEFAULT_PERIOD_OUTPUT = "reports/mnq-top-runner-deep-validation-periods.csv"
DEFAULT_MONTE_CARLO_OUTPUT = "reports/mnq-top-runner-deep-validation-monte-carlo.csv"
DEFAULT_NEIGHBORHOOD_OUTPUT = "reports/mnq-top-runner-deep-validation-neighborhood.csv"
DEFAULT_OVERLAP_OUTPUT = "reports/mnq-top-runner-deep-validation-overlap.csv"
DEFAULT_REPORT_OUTPUT = "reports/mnq-top-runner-deep-validation.md"


SUMMARY_HEADER = [
    "schema_version",
    "candidate_id",
    "label",
    "slippage_ticks",
    "trades",
    "trades_per_week",
    "net_usd",
    "average_trade_usd",
    "profit_factor",
    "win_rate",
    "target_hit_rate",
    "stop_hit_rate",
    "eod_exit_rate",
    "max_drawdown_usd",
    "net_to_drawdown",
    "latest_year_net_usd",
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
    "candidate_id",
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
    "candidate_id",
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
    "candidate_id",
    "iterations",
    "seed",
    "chronological_drawdown_usd",
    "median_drawdown_usd",
    "p90_drawdown_usd",
    "p95_drawdown_usd",
    "p99_drawdown_usd",
    "prob_dd_lte_1000",
    "prob_dd_lte_1500",
    "prob_dd_lte_2000",
    "prob_dd_lte_3000",
    "median_max_loss_streak",
    "p95_max_loss_streak",
]

NEIGHBORHOOD_HEADER = [
    "schema_version",
    "strategy_id",
    "lookback_bars",
    "delta_threshold",
    "close_location_threshold",
    "entry_end",
    "target_points",
    "stop_points",
    "trades",
    "trades_per_week",
    "net_usd",
    "average_trade_usd",
    "profit_factor",
    "win_rate",
    "max_drawdown_usd",
    "net_to_drawdown",
    "latest_year_net_usd",
    "worst_quarter_net_usd",
    "accepted",
]

OVERLAP_HEADER = [
    "schema_version",
    "left_candidate",
    "right_candidate",
    "left_trades",
    "right_trades",
    "overlap_trades",
    "left_overlap_rate",
    "right_overlap_rate",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run deeper robustness tests for frozen MNQ Top Runner candidates.",
    )
    parser.add_argument("input", nargs="?", default=wave.DEFAULT_INPUT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--holdout-output", default=DEFAULT_HOLDOUT_OUTPUT)
    parser.add_argument("--period-output", default=DEFAULT_PERIOD_OUTPUT)
    parser.add_argument("--monte-carlo-output", default=DEFAULT_MONTE_CARLO_OUTPUT)
    parser.add_argument("--neighborhood-output", default=DEFAULT_NEIGHBORHOOD_OUTPUT)
    parser.add_argument("--overlap-output", default=DEFAULT_OVERLAP_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--symbol", default="MNQU26-CME")
    parser.add_argument("--monte-carlo-iterations", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260705)
    args = parser.parse_args()

    bars = wave._load_feature_bars(args.input)
    bars_by_date = wave._bars_by_date(bars)
    rows_by_index = wave._rows_by_global_index(bars_by_date)
    flatten_index_by_date = runner._flatten_index_by_date(bars_by_date)
    sample_info = runner._sample_info(bars)
    candidates = validation._candidate_specs()
    candidate_signals = validation._candidate_signals(
        candidates,
        bars_by_date,
        rows_by_index,
        symbol=args.symbol,
    )

    outcomes_by_candidate: dict[str, list[runner.RunnerOutcome]] = {}
    summary_rows = []
    for candidate in candidates:
        for slippage_ticks in (1.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0):
            risk = validation._risk(candidate, slippage_ticks)
            outcomes = runner._evaluate_signals(
                candidate_signals[candidate.candidate_id],
                bars_by_date,
                rows_by_index,
                flatten_index_by_date,
                risk,
                family="runner_lookback_breakout_deep_validation",
            )
            if slippage_ticks == 1.0:
                outcomes_by_candidate[candidate.candidate_id] = outcomes
            summary_rows.append(
                _summary_row(candidate, slippage_ticks, outcomes, sample_info),
            )

    holdout_rows = _holdout_rows(outcomes_by_candidate, sorted(bars_by_date))
    period_rows = _period_rows(outcomes_by_candidate)
    monte_carlo_rows = _monte_carlo_rows(
        outcomes_by_candidate,
        iterations=args.monte_carlo_iterations,
        seed=args.seed,
    )
    neighborhood_rows = _neighborhood_rows(
        bars_by_date,
        rows_by_index,
        flatten_index_by_date,
        sample_info,
        symbol=args.symbol,
    )
    overlap_rows = _overlap_rows(outcomes_by_candidate)

    _write_csv(args.summary_output, SUMMARY_HEADER, summary_rows)
    _write_csv(args.holdout_output, HOLDOUT_HEADER, holdout_rows)
    _write_csv(args.period_output, PERIOD_HEADER, period_rows)
    _write_csv(args.monte_carlo_output, MONTE_CARLO_HEADER, monte_carlo_rows)
    _write_csv(args.neighborhood_output, NEIGHBORHOOD_HEADER, neighborhood_rows)
    _write_csv(args.overlap_output, OVERLAP_HEADER, overlap_rows)
    _write_report(
        args.report_output,
        bars,
        candidates,
        summary_rows,
        holdout_rows,
        period_rows,
        monte_carlo_rows,
        neighborhood_rows,
        overlap_rows,
    )

    accepted_neighborhood = sum(row["accepted"] == "yes" for row in neighborhood_rows)
    print(
        "wrote MNQ Top Runner deep validation: "
        f"summary={len(summary_rows)} rows, holdout={len(holdout_rows)} rows, "
        f"neighborhood={len(neighborhood_rows)} rows, "
        f"accepted_neighborhood={accepted_neighborhood}",
    )
    return 0


def _summary_row(
    candidate: validation.CandidateSpec,
    slippage_ticks: float,
    outcomes: list[runner.RunnerOutcome],
    sample_info: runner.SampleInfo,
) -> dict[str, object]:
    metrics = _metrics(outcomes)
    periods = _period_groups(outcomes)
    years = [sum(outcome.net_usd for outcome in values) for key, values in periods.items() if key.startswith("year:")]
    quarters = [sum(outcome.net_usd for outcome in values) for key, values in periods.items() if key.startswith("quarter:")]
    months = [sum(outcome.net_usd for outcome in values) for key, values in periods.items() if key.startswith("month:")]
    gaps = _gap_days(outcomes)
    return {
        "schema_version": 1,
        "candidate_id": candidate.candidate_id,
        "label": candidate.label,
        "slippage_ticks": _fmt(slippage_ticks),
        "trades": len(outcomes),
        "trades_per_week": _fmt(len(outcomes) / sample_info.weeks if sample_info.weeks else 0.0),
        "net_usd": _fmt(metrics["net"]),
        "average_trade_usd": _fmt(metrics["average"]),
        "profit_factor": _fmt(metrics["profit_factor"]),
        "win_rate": _fmt(metrics["win_rate"]),
        "target_hit_rate": _fmt(_exit_rate(outcomes, "target_hit")),
        "stop_hit_rate": _fmt(_exit_rate(outcomes, "stop_hit")),
        "eod_exit_rate": _fmt(_exit_rate(outcomes, "end_of_session")),
        "max_drawdown_usd": _fmt(metrics["drawdown"]),
        "net_to_drawdown": _fmt(_net_to_drawdown(metrics["net"], metrics["drawdown"])),
        "latest_year_net_usd": _fmt(sum(o.net_usd for o in outcomes if o.entry_time.year == sample_info.latest_year)),
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
    outcomes_by_candidate: dict[str, list[runner.RunnerOutcome]],
    trade_dates: list[date],
) -> list[dict[str, object]]:
    configs = ((60, 20), (90, 30), (120, 40), (180, 40), (240, 60), (320, 60))
    rows = []
    for candidate_id, outcomes in outcomes_by_candidate.items():
        by_date: dict[date, list[runner.RunnerOutcome]] = defaultdict(list)
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
                metrics = _metrics(sorted(holdout_outcomes, key=lambda outcome: outcome.entry_time))
                rows.append(
                    {
                        "schema_version": 1,
                        "candidate_id": candidate_id,
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


def _period_rows(
    outcomes_by_candidate: dict[str, list[runner.RunnerOutcome]],
) -> list[dict[str, object]]:
    rows = []
    for candidate_id, outcomes in outcomes_by_candidate.items():
        for period_id, period_outcomes in sorted(_period_groups(outcomes).items()):
            period_type, period = period_id.split(":", 1)
            metrics = _metrics(period_outcomes)
            rows.append(
                {
                    "schema_version": 1,
                    "candidate_id": candidate_id,
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
    outcomes_by_candidate: dict[str, list[runner.RunnerOutcome]],
    *,
    iterations: int,
    seed: int,
) -> list[dict[str, object]]:
    rows = []
    rng = random.Random(seed)
    for candidate_id, outcomes in outcomes_by_candidate.items():
        values = [outcome.net_usd for outcome in outcomes]
        chronological_drawdown = wave._max_drawdown(values)
        simulated_drawdowns = []
        simulated_loss_streaks = []
        for _ in range(iterations):
            shuffled = values[:]
            rng.shuffle(shuffled)
            simulated_drawdowns.append(wave._max_drawdown(shuffled))
            simulated_loss_streaks.append(_max_loss_streak_count(shuffled))
        sorted_dd = sorted(simulated_drawdowns)
        sorted_streaks = sorted(simulated_loss_streaks)
        rows.append(
            {
                "schema_version": 1,
                "candidate_id": candidate_id,
                "iterations": iterations,
                "seed": seed,
                "chronological_drawdown_usd": _fmt(chronological_drawdown),
                "median_drawdown_usd": _fmt(_quantile(sorted_dd, 0.50)),
                "p90_drawdown_usd": _fmt(_quantile(sorted_dd, 0.10)),
                "p95_drawdown_usd": _fmt(_quantile(sorted_dd, 0.05)),
                "p99_drawdown_usd": _fmt(_quantile(sorted_dd, 0.01)),
                "prob_dd_lte_1000": _fmt(sum(dd <= -1000.0 for dd in simulated_drawdowns) / iterations),
                "prob_dd_lte_1500": _fmt(sum(dd <= -1500.0 for dd in simulated_drawdowns) / iterations),
                "prob_dd_lte_2000": _fmt(sum(dd <= -2000.0 for dd in simulated_drawdowns) / iterations),
                "prob_dd_lte_3000": _fmt(sum(dd <= -3000.0 for dd in simulated_drawdowns) / iterations),
                "median_max_loss_streak": _fmt(_quantile(sorted_streaks, 0.50)),
                "p95_max_loss_streak": _fmt(_quantile(sorted_streaks, 0.95)),
            },
        )
    return rows


def _neighborhood_rows(
    bars_by_date: dict[date, list[wave.Bar]],
    rows_by_index: dict[int, int],
    flatten_index_by_date: dict[date, int],
    sample_info: runner.SampleInfo,
    *,
    symbol: str,
) -> list[dict[str, object]]:
    rows = []
    for lookback_bars in (15, 20, 25, 30):
        for delta_threshold in (400.0, 600.0, 800.0):
            for close_location_threshold in (0.80, 0.85, 0.90, 0.95):
                for entry_end in (time(10, 30), time(11, 0), time(11, 30)):
                    strategy_id = (
                        "mnq_top_runner_deep_neighborhood:"
                        f"lb{lookback_bars}:delta{delta_threshold:g}:"
                        f"cl{close_location_threshold:g}:end{wave._time_id(entry_end)}"
                    )
                    signals = []
                    for day_rows in bars_by_date.values():
                        signals.extend(
                            runner._lookback_breakout_signals(
                                day_rows,
                                strategy_id=strategy_id,
                                lookback_bars=lookback_bars,
                                buffer_points=0.0,
                                delta_threshold=delta_threshold,
                                close_location_threshold=close_location_threshold,
                                entry_end=entry_end,
                                skip_friday=True,
                                symbol=symbol,
                            ),
                        )
                    for target_points in (100.0, 120.0, 140.0, 160.0):
                        for stop_points in (60.0, 70.0, 80.0):
                            risk = runner.RunnerRisk(
                                quantity=2,
                                target_points=target_points,
                                stop_points=stop_points,
                                round_turn_cost_usd=2 * runner.ROUND_TURN_COST_PER_CONTRACT_USD,
                            )
                            outcomes = runner._evaluate_signals(
                                signals,
                                bars_by_date,
                                rows_by_index,
                                flatten_index_by_date,
                                risk,
                                family="runner_lookback_breakout_deep_neighborhood",
                            )
                            metrics = _metrics(outcomes)
                            latest_year_net = sum(
                                outcome.net_usd
                                for outcome in outcomes
                                if outcome.entry_time.year == sample_info.latest_year
                            )
                            quarters = [
                                sum(outcome.net_usd for outcome in values)
                                for key, values in _period_groups(outcomes).items()
                                if key.startswith("quarter:")
                            ]
                            worst_quarter = min(quarters) if quarters else 0.0
                            net_to_drawdown = _net_to_drawdown(metrics["net"], metrics["drawdown"])
                            accepted = (
                                len(outcomes) >= 70
                                and metrics["net"] > 0.0
                                and metrics["profit_factor"] >= 1.70
                                and metrics["drawdown"] > -2500.0
                                and latest_year_net > 0.0
                                and worst_quarter > -1500.0
                            )
                            rows.append(
                                {
                                    "schema_version": 1,
                                    "strategy_id": strategy_id,
                                    "lookback_bars": lookback_bars,
                                    "delta_threshold": _fmt(delta_threshold),
                                    "close_location_threshold": _fmt(close_location_threshold),
                                    "entry_end": entry_end.strftime("%H:%M"),
                                    "target_points": _fmt(target_points),
                                    "stop_points": _fmt(stop_points),
                                    "trades": len(outcomes),
                                    "trades_per_week": _fmt(len(outcomes) / sample_info.weeks if sample_info.weeks else 0.0),
                                    "net_usd": _fmt(metrics["net"]),
                                    "average_trade_usd": _fmt(metrics["average"]),
                                    "profit_factor": _fmt(metrics["profit_factor"]),
                                    "win_rate": _fmt(metrics["win_rate"]),
                                    "max_drawdown_usd": _fmt(metrics["drawdown"]),
                                    "net_to_drawdown": _fmt(net_to_drawdown),
                                    "latest_year_net_usd": _fmt(latest_year_net),
                                    "worst_quarter_net_usd": _fmt(worst_quarter),
                                    "accepted": "yes" if accepted else "no",
                                },
                            )
    rows.sort(key=_neighborhood_sort_key)
    return rows


def _overlap_rows(
    outcomes_by_candidate: dict[str, list[runner.RunnerOutcome]],
) -> list[dict[str, object]]:
    rows = []
    keys = sorted(outcomes_by_candidate)
    for left_index, left_candidate in enumerate(keys):
        for right_candidate in keys[left_index + 1:]:
            left = _entry_keys(outcomes_by_candidate[left_candidate])
            right = _entry_keys(outcomes_by_candidate[right_candidate])
            overlap = left & right
            rows.append(
                {
                    "schema_version": 1,
                    "left_candidate": left_candidate,
                    "right_candidate": right_candidate,
                    "left_trades": len(left),
                    "right_trades": len(right),
                    "overlap_trades": len(overlap),
                    "left_overlap_rate": _fmt(len(overlap) / len(left) if left else 0.0),
                    "right_overlap_rate": _fmt(len(overlap) / len(right) if right else 0.0),
                },
            )
    return rows


def _write_report(
    report_output: str,
    bars: list[wave.Bar],
    candidates: list[validation.CandidateSpec],
    summary_rows: list[dict[str, object]],
    holdout_rows: list[dict[str, object]],
    period_rows: list[dict[str, object]],
    monte_carlo_rows: list[dict[str, object]],
    neighborhood_rows: list[dict[str, object]],
    overlap_rows: list[dict[str, object]],
) -> None:
    base_rows = [
        row for row in summary_rows
        if float(row["slippage_ticks"]) == 1.0
    ]
    accepted_neighborhood = [row for row in neighborhood_rows if row["accepted"] == "yes"]
    live_row = _find_neighborhood_live_row(neighborhood_rows)
    direct_high_pf_row = _find_neighborhood_row(neighborhood_rows, 20, 600.0, 0.9, "11:00", 160.0, 70.0)
    direct_cl80_row = _find_neighborhood_row(neighborhood_rows, 20, 600.0, 0.8, "11:00", 160.0, 70.0)
    filtered_lower_row = _find_summary_row(base_rows, "mnq_top_runner_lb20_cl90_t120_s70")
    lines = [
        "# MNQ Top-Runner Deep Validation",
        "",
        "Status: final offline research battery for the MNQ Top Runner family on the current export.",
        "",
        "## Scope",
        "",
        f"- source rows: `{len(bars)}`",
        f"- dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        f"- unique trading dates: `{len({bar.trade_date for bar in bars})}`",
        "- instrument: `MNQ`, fixed `2 MNQ` sizing",
        "- base cost model: `$0.50/side` commission plus `1` total slippage tick per contract",
        "- same-bar handling: stop first",
        "- tests added here: extended slippage, wider rolling holdouts, period attribution, Monte Carlo trade-order risk, parameter-neighborhood stability, and candidate overlap",
        "",
        "## Frozen Candidate Scorecard",
        "",
        "| Candidate | Label | Trades | /Wk | Net | PF | Win | Target | DD | Net/DD | Latest | Worst Q | Worst Month | Max Gap |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    candidate_labels = {candidate.candidate_id: candidate.label for candidate in candidates}
    for row in sorted(base_rows, key=_summary_rank_key):
        lines.append(
            "| "
            f"`{row['candidate_id']}` | {candidate_labels[str(row['candidate_id'])]} | "
            f"{row['trades']} | {row['trades_per_week']} | {row['net_usd']} | "
            f"{row['profit_factor']} | {float(row['win_rate']) * 100:.1f}% | "
            f"{float(row['target_hit_rate']) * 100:.1f}% | {row['max_drawdown_usd']} | "
            f"{row['net_to_drawdown']} | {row['latest_year_net_usd']} | "
            f"{row['worst_quarter_net_usd']} | {row['worst_month_net_usd']} | "
            f"{row['max_gap_days']} |"
        )
    lines.extend(
        [
            "",
            "## Extended Slippage Stress",
            "",
            "| Candidate | 1 tick Net/PF | 6 tick Net/PF | 12 tick Net/PF |",
            "| --- | ---: | ---: | ---: |",
        ],
    )
    for candidate in candidates:
        rows = {
            float(row["slippage_ticks"]): row
            for row in summary_rows
            if row["candidate_id"] == candidate.candidate_id
        }
        lines.append(
            "| "
            f"`{candidate.candidate_id}` | "
            f"{rows[1.0]['net_usd']} / {rows[1.0]['profit_factor']} | "
            f"{rows[6.0]['net_usd']} / {rows[6.0]['profit_factor']} | "
            f"{rows[12.0]['net_usd']} / {rows[12.0]['profit_factor']} |"
        )
    lines.extend(
        [
            "",
            "## Rolling Holdout Summary",
            "",
            "| Candidate | Config | Windows | Positive | Negative | No Trade | Net | Worst | Median |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    for row in _holdout_summary_rows(holdout_rows):
        lines.append(
            "| "
            f"`{row['candidate_id']}` | {row['config']} | {row['windows']} | "
            f"{row['positive']} | {row['negative']} | {row['no_trade']} | "
            f"{row['net_usd']} | {row['worst_net_usd']} | {row['median_net_usd']} |"
        )
    lines.extend(
        [
            "",
            "## Monte Carlo Trade-Order Risk",
            "",
            "This shuffles the same trade outcomes to estimate path-risk sensitivity. It does not change the edge; it only changes trade order.",
            "",
            "| Candidate | Chron DD | Median DD | P95 DD | P99 DD | P(DD <= -1000) | P(DD <= -1500) | P(DD <= -2000) | P95 Loss Streak |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    for row in monte_carlo_rows:
        lines.append(
            "| "
            f"`{row['candidate_id']}` | {row['chronological_drawdown_usd']} | "
            f"{row['median_drawdown_usd']} | {row['p95_drawdown_usd']} | "
            f"{row['p99_drawdown_usd']} | {float(row['prob_dd_lte_1000']) * 100:.1f}% | "
            f"{float(row['prob_dd_lte_1500']) * 100:.1f}% | "
            f"{float(row['prob_dd_lte_2000']) * 100:.1f}% | "
            f"{row['p95_max_loss_streak']} |"
        )
    lines.extend(
        [
            "",
            "## Parameter-Neighborhood Stability",
            "",
            f"- neighborhood rows tested: `{len(neighborhood_rows)}`",
            f"- accepted by the deep lens: `{len(accepted_neighborhood)}`",
            "- accepted lens: at least `70` trades, positive net/latest year, PF `>= 1.70`, DD better than `-$2500`, and worst quarter better than `-$1500`",
        ],
    )
    if live_row is not None:
        lines.extend(
            [
                f"- live default row rank in neighborhood: `{_neighborhood_rank(neighborhood_rows, live_row)}` of `{len(neighborhood_rows)}`",
                f"- live default row accepted by deep lens: `{live_row['accepted']}`",
            ],
        )
    lines.extend(
        [
            "",
            "| Rank | Strategy | Target / Stop | Trades | Net | PF | DD | Latest | Worst Q | Accepted |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ],
    )
    for rank, row in enumerate(neighborhood_rows[:15], start=1):
        lines.append(
            "| "
            f"{rank} | `{row['strategy_id']}` | {row['target_points']} / {row['stop_points']} | "
            f"{row['trades']} | {row['net_usd']} | {row['profit_factor']} | "
            f"{row['max_drawdown_usd']} | {row['latest_year_net_usd']} | "
            f"{row['worst_quarter_net_usd']} | {row['accepted']} |"
        )
    alignment_rows = []
    if filtered_lower_row is not None:
        alignment_rows.append(
            (
                "Frozen filtered lower-DD rule",
                filtered_lower_row["trades"],
                filtered_lower_row["net_usd"],
                filtered_lower_row["profit_factor"],
                filtered_lower_row["max_drawdown_usd"],
                filtered_lower_row["latest_year_net_usd"],
                filtered_lower_row["worst_quarter_net_usd"],
            ),
        )
    if live_row is not None:
        alignment_rows.append(
            (
                "Direct strict rule, 120 / 70",
                live_row["trades"],
                live_row["net_usd"],
                live_row["profit_factor"],
                live_row["max_drawdown_usd"],
                live_row["latest_year_net_usd"],
                live_row["worst_quarter_net_usd"],
            ),
        )
    if direct_high_pf_row is not None:
        alignment_rows.append(
            (
                "Direct strict rule, 160 / 70",
                direct_high_pf_row["trades"],
                direct_high_pf_row["net_usd"],
                direct_high_pf_row["profit_factor"],
                direct_high_pf_row["max_drawdown_usd"],
                direct_high_pf_row["latest_year_net_usd"],
                direct_high_pf_row["worst_quarter_net_usd"],
            ),
        )
    if direct_cl80_row is not None:
        alignment_rows.append(
            (
                "Direct strict CL 0.8 rule, 160 / 70",
                direct_cl80_row["trades"],
                direct_cl80_row["net_usd"],
                direct_cl80_row["profit_factor"],
                direct_cl80_row["max_drawdown_usd"],
                direct_cl80_row["latest_year_net_usd"],
                direct_cl80_row["worst_quarter_net_usd"],
            ),
        )
    if alignment_rows:
        lines.extend(
            [
                "",
                "## Implementation Alignment Finding",
                "",
                "The original frozen candidate is a two-stage rule: a broad raw `10:00-12:30` lookback-breakout stream using close-location `0.65`, followed by a final `10:00-11:00` directional close-location filter. The raw stream applies the one-hour spacing before the final filter.",
                "",
                "A direct strict ACSIL interpretation using only `10:00-11:00` and close-location `0.9` is not equivalent and tested worse.",
                "",
                "| Rule | Trades | Net | PF | DD | Latest | Worst Q |",
                "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            ],
        )
        for label, trades, net, pf, dd, latest, worst_q in alignment_rows:
            lines.append(
                f"| {label} | {trades} | {net} | {pf} | {dd} | {latest} | {worst_q} |",
            )
    lines.extend(
        [
            "",
            "## Candidate Overlap",
            "",
            "| Left | Right | Left Trades | Right Trades | Overlap | Left Rate | Right Rate |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    for row in overlap_rows:
        lines.append(
            "| "
            f"`{row['left_candidate']}` | `{row['right_candidate']}` | "
            f"{row['left_trades']} | {row['right_trades']} | {row['overlap_trades']} | "
            f"{float(row['left_overlap_rate']) * 100:.1f}% | "
            f"{float(row['right_overlap_rate']) * 100:.1f}% |"
        )
    lines.extend(
        [
            "",
            "## Worst Periods",
            "",
            "| Candidate | Worst Year | Worst Quarter | Worst Month |",
            "| --- | ---: | ---: | ---: |",
        ],
    )
    for candidate in candidates:
        rows = [row for row in period_rows if row["candidate_id"] == candidate.candidate_id]
        worst_year = _worst_period(rows, "year")
        worst_quarter = _worst_period(rows, "quarter")
        worst_month = _worst_period(rows, "month")
        lines.append(
            "| "
            f"`{candidate.candidate_id}` | {worst_year} | {worst_quarter} | {worst_month} |"
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            "Offline research on the current MNQ export is complete enough to mark the Top Runner family as `100%` researched for this dataset. That means the available static-rule research budget is exhausted; it does not mean the bot has a 100% chance of making money.",
            "",
            "The lower-DD `120 / 70` live build remains the correct first live-staging variant. The high-PF `160 / 70` variant has higher net/PF, but its drawdown and Monte Carlo path risk are materially larger. The `cl >= 0.8` higher-sample sibling is a research backup, not the current live default.",
            "",
            "The ACSIL implementation must use the filtered frozen rule before inheriting the stronger research stats. After that alignment, the next gates are operational: fresh replay/mechanics validation, controlled live staging, forward sample, and aggregate account-risk tooling before account scaling.",
            "",
        ],
    )
    Path(report_output).write_text("\n".join(lines), encoding="utf-8")


def _metrics(outcomes: list[runner.RunnerOutcome]) -> dict[str, float | int]:
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
    return {
        "net": sum(values),
        "average": statistics.mean(values),
        "profit_factor": sum(positive) / abs(sum(negative)) if negative else 999.0,
        "win_rate": len(positive) / len(values),
        "drawdown": wave._max_drawdown(values),
        "worst_trade": min(values),
        "max_loss_streak_trades": loss_count,
        "max_loss_streak_usd": loss_usd,
    }


def _period_groups(
    outcomes: list[runner.RunnerOutcome],
) -> dict[str, list[runner.RunnerOutcome]]:
    groups: dict[str, list[runner.RunnerOutcome]] = defaultdict(list)
    for outcome in outcomes:
        groups[f"year:{outcome.entry_time.year}"].append(outcome)
        quarter = (outcome.entry_time.month - 1) // 3 + 1
        groups[f"quarter:{outcome.entry_time.year}Q{quarter}"].append(outcome)
        groups[f"month:{outcome.entry_time.year}-{outcome.entry_time.month:02d}"].append(outcome)
    return groups


def _holdout_summary_rows(holdout_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in holdout_rows:
        grouped[(str(row["candidate_id"]), str(row["config"]))].append(row)
    rows = []
    for (candidate_id, config), group in sorted(grouped.items()):
        nets = [float(row["net_usd"]) for row in group]
        trades = [int(row["trades"]) for row in group]
        rows.append(
            {
                "candidate_id": candidate_id,
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


def _worst_period(rows: list[dict[str, object]], period_type: str) -> str:
    filtered = [row for row in rows if row["period_type"] == period_type]
    if not filtered:
        return "`none`"
    worst = min(filtered, key=lambda row: float(row["net_usd"]))
    return f"`{worst['period']}={worst['net_usd']}`"


def _find_neighborhood_live_row(rows: list[dict[str, object]]) -> dict[str, object] | None:
    return _find_neighborhood_row(rows, 20, 600.0, 0.9, "11:00", 120.0, 70.0)


def _find_neighborhood_row(
    rows: list[dict[str, object]],
    lookback_bars: int,
    delta_threshold: float,
    close_location_threshold: float,
    entry_end: str,
    target_points: float,
    stop_points: float,
) -> dict[str, object] | None:
    for row in rows:
        if (
            int(row["lookback_bars"]) == lookback_bars
            and float(row["delta_threshold"]) == delta_threshold
            and float(row["close_location_threshold"]) == close_location_threshold
            and row["entry_end"] == entry_end
            and float(row["target_points"]) == target_points
            and float(row["stop_points"]) == stop_points
        ):
            return row
    return None


def _find_summary_row(rows: list[dict[str, object]], candidate_id: str) -> dict[str, object] | None:
    for row in rows:
        if row["candidate_id"] == candidate_id:
            return row
    return None


def _neighborhood_rank(rows: list[dict[str, object]], target: dict[str, object]) -> int:
    return rows.index(target) + 1


def _summary_rank_key(row: dict[str, object]) -> tuple[float, ...]:
    return (
        0.0 if str(row["candidate_id"]).endswith("t120_s70") else 1.0,
        -float(row["net_to_drawdown"]),
        -float(row["profit_factor"]),
        -float(row["net_usd"]),
    )


def _neighborhood_sort_key(row: dict[str, object]) -> tuple[float, ...]:
    accepted_rank = 0.0 if row["accepted"] == "yes" else 1.0
    return (
        accepted_rank,
        -float(row["profit_factor"]),
        -float(row["net_to_drawdown"]),
        -float(row["net_usd"]),
        float(row["max_drawdown_usd"]),
    )


def _gap_days(outcomes: list[runner.RunnerOutcome]) -> list[float]:
    ordered = sorted(outcomes, key=lambda outcome: outcome.entry_time)
    return [
        (right.entry_time.date() - left.entry_time.date()).days
        for left, right in zip(ordered, ordered[1:])
    ]


def _exit_rate(outcomes: list[runner.RunnerOutcome], exit_reason: str) -> float:
    return sum(outcome.exit_reason == exit_reason for outcome in outcomes) / len(outcomes) if outcomes else 0.0


def _worst_group(
    outcomes: list[runner.RunnerOutcome],
    *,
    key,
) -> float:
    groups: dict[object, float] = defaultdict(float)
    for outcome in outcomes:
        groups[key(outcome)] += outcome.net_usd
    return min(groups.values()) if groups else 0.0


def _net_to_drawdown(net: float, drawdown: float) -> float:
    if drawdown >= 0.0:
        return 999.0 if net > 0 else 0.0
    return net / abs(drawdown)


def _max_loss_streak(values: list[float]) -> tuple[int, float]:
    best_count = 0
    best_sum = 0.0
    current_count = 0
    current_sum = 0.0
    for value in values:
        if value < 0.0:
            current_count += 1
            current_sum += value
            if current_count > best_count or (
                current_count == best_count and current_sum < best_sum
            ):
                best_count = current_count
                best_sum = current_sum
        else:
            current_count = 0
            current_sum = 0.0
    return best_count, best_sum


def _max_loss_streak_count(values: list[float]) -> int:
    return _max_loss_streak(values)[0]


def _quantile(sorted_values: list[float | int], probability: float) -> float:
    if not sorted_values:
        return 0.0
    index = int(round((len(sorted_values) - 1) * probability))
    index = max(0, min(index, len(sorted_values) - 1))
    return float(sorted_values[index])


def _entry_keys(outcomes: list[runner.RunnerOutcome]) -> set[tuple[str, str]]:
    return {
        (outcome.entry_time.isoformat(), outcome.direction)
        for outcome in outcomes
    }


def _write_csv(path: str, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _fmt(value: float | int) -> str:
    return wave._format_number(float(value))


if __name__ == "__main__":
    raise SystemExit(main())
