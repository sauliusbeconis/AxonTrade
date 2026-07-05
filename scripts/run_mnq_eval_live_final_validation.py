#!/usr/bin/env python3
"""Final offline validation for AxonTrade MNQ Eval Live Bot."""

from __future__ import annotations

import argparse
import csv
import random
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Any, Callable, Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_mnq_eval_pass_wave_rider as wave  # noqa: E402


STRATEGY_ID = (
    "mnq_vwap_delta_local_fade_80pt_400d_cl0.4_nofri_no11_15"
    "_exit25_140_40_initial"
)

DEFAULT_SUMMARY_OUTPUT = "reports/mnq-eval-live-final-validation-summary.csv"
DEFAULT_HOLDOUT_OUTPUT = "reports/mnq-eval-live-final-validation-holdout.csv"
DEFAULT_PERIOD_OUTPUT = "reports/mnq-eval-live-final-validation-periods.csv"
DEFAULT_MONTE_CARLO_OUTPUT = "reports/mnq-eval-live-final-validation-monte-carlo.csv"
DEFAULT_NEIGHBORHOOD_OUTPUT = "reports/mnq-eval-live-final-validation-neighborhood.csv"
DEFAULT_REPORT_OUTPUT = "reports/mnq-eval-live-final-validation.md"

POINT_VALUE_USD = 2.0
TICK_VALUE_USD = 0.50
COMMISSION_PER_SIDE_USD = 0.50
SETUP_START = time(9, 45)
SETUP_END = time(15, 45)
FLATTEN_TIME = time(16, 40)


@dataclass(frozen=True)
class MnqEvalSpec:
    strategy_id: str
    label: str
    vwap_threshold: float
    delta_threshold: float
    close_location_threshold: float
    spacing_seconds: int
    skip_friday: bool
    skip_11_hour: bool
    skip_15_hour: bool
    first_target_points: float
    stop_points: float
    runner_target_points: float
    runner_stop_mode: str
    first_leg_quantity: int = 1
    runner_quantity: int = 1


@dataclass(frozen=True)
class ScaledOutcome:
    strategy_id: str
    direction: str
    entry_time: datetime
    exit_time: datetime
    entry_bar_index: int
    exit_bar_index: int
    entry_price: float
    stop_price: float
    first_target_price: float
    runner_target_price: float
    leg1_exit_price: float
    runner_exit_price: float
    exit_reason: str
    first_target_hit: bool
    holding_minutes: float
    gross_points: float
    net_usd: float
    notes: str


SUMMARY_HEADER = [
    "schema_version",
    "mode",
    "strategy_id",
    "slippage_ticks",
    "trades",
    "trades_per_week",
    "net_usd",
    "average_trade_usd",
    "profit_factor",
    "win_rate",
    "runner_target_rate",
    "stop_rate",
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
    "mode",
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
    "mode",
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
    "mode",
    "strategy_id",
    "slippage_ticks",
    "iterations",
    "seed",
    "chronological_drawdown_usd",
    "median_drawdown_usd",
    "p90_drawdown_usd",
    "p95_drawdown_usd",
    "p99_drawdown_usd",
    "prob_dd_lte_750",
    "prob_dd_lte_1000",
    "prob_dd_lte_1500",
    "prob_dd_lte_2000",
    "median_max_loss_streak",
    "p95_max_loss_streak",
]

NEIGHBORHOOD_HEADER = [
    "schema_version",
    "rank",
    "strategy_id",
    "vwap_threshold",
    "delta_threshold",
    "close_location_threshold",
    "spacing_seconds",
    "first_target_points",
    "stop_points",
    "runner_target_points",
    "runner_stop_mode",
    "independent_trades",
    "independent_net_usd",
    "independent_profit_factor",
    "independent_max_drawdown_usd",
    "live_trades",
    "live_net_usd",
    "live_average_trade_usd",
    "live_profit_factor",
    "live_win_rate",
    "live_max_drawdown_usd",
    "live_latest_year_net_usd",
    "live_worst_year_net_usd",
    "live_worst_quarter_net_usd",
    "live_wf40_windows",
    "live_wf40_positive_windows",
    "live_wf40_negative_windows",
    "live_wf40_net_usd",
    "live_wf40_worst_window_usd",
    "accepted",
    "decision",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run final offline validation for AxonTrade MNQ Eval Live Bot.",
    )
    parser.add_argument("input", nargs="?", default=wave.DEFAULT_INPUT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--holdout-output", default=DEFAULT_HOLDOUT_OUTPUT)
    parser.add_argument("--period-output", default=DEFAULT_PERIOD_OUTPUT)
    parser.add_argument("--monte-carlo-output", default=DEFAULT_MONTE_CARLO_OUTPUT)
    parser.add_argument("--neighborhood-output", default=DEFAULT_NEIGHBORHOOD_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--symbol", default="MNQ")
    parser.add_argument("--monte-carlo-iterations", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=20260705)
    args = parser.parse_args()

    bars = wave._load_feature_bars(args.input)
    bars_by_date = wave._bars_by_date(bars)
    rows_by_index = wave._rows_by_global_index(bars_by_date)
    trade_dates = sorted(bars_by_date)
    sample_weeks = _sample_weeks(bars)
    live_spec = _live_spec()

    raw_signals = _signals_for_spec(live_spec, bars_by_date, symbol=args.symbol)
    outcomes_by_key: dict[tuple[str, float], list[ScaledOutcome]] = {}
    summary_rows = []
    for mode in ("independent", "live_sequenced"):
        for slippage_ticks in (1.0, 2.0, 3.0, 4.0, 6.0, 8.0, 10.0, 12.0):
            outcomes = _evaluate_signals(
                live_spec,
                raw_signals,
                bars_by_date,
                rows_by_index,
                slippage_ticks=slippage_ticks,
                live_sequenced=mode == "live_sequenced",
            )
            outcomes_by_key[(mode, slippage_ticks)] = outcomes
            summary_rows.append(
                _summary_row(
                    mode,
                    live_spec.strategy_id,
                    slippage_ticks,
                    outcomes,
                    trade_dates,
                    sample_weeks,
                ),
            )

    holdout_rows = _holdout_rows(outcomes_by_key, trade_dates)
    period_rows = _period_rows(outcomes_by_key)
    monte_carlo_rows = _monte_carlo_rows(
        {
            ("independent", 1.0): outcomes_by_key[("independent", 1.0)],
            ("live_sequenced", 1.0): outcomes_by_key[("live_sequenced", 1.0)],
            ("live_sequenced", 6.0): outcomes_by_key[("live_sequenced", 6.0)],
        },
        iterations=args.monte_carlo_iterations,
        seed=args.seed,
    )
    neighborhood_rows = _neighborhood_rows(
        bars_by_date,
        rows_by_index,
        trade_dates,
        sample_weeks,
        symbol=args.symbol,
        current_live_net=float(_row_for(summary_rows, "live_sequenced", 1.0)["net_usd"]),
    )

    _write_csv(args.summary_output, SUMMARY_HEADER, summary_rows)
    _write_csv(args.holdout_output, HOLDOUT_HEADER, holdout_rows)
    _write_csv(args.period_output, PERIOD_HEADER, period_rows)
    _write_csv(args.monte_carlo_output, MONTE_CARLO_HEADER, monte_carlo_rows)
    _write_csv(args.neighborhood_output, NEIGHBORHOOD_HEADER, neighborhood_rows)
    _write_report(
        args.report_output,
        bars,
        raw_signals,
        summary_rows,
        holdout_rows,
        period_rows,
        monte_carlo_rows,
        neighborhood_rows,
    )

    independent = _row_for(summary_rows, "independent", 1.0)
    live = _row_for(summary_rows, "live_sequenced", 1.0)
    accepted = sum(row["accepted"] == "yes" for row in neighborhood_rows)
    print(
        "wrote MNQ Eval Live final validation: "
        f"independent={independent['trades']} trades/{independent['net_usd']} net; "
        f"live={live['trades']} trades/{live['net_usd']} net; "
        f"accepted_neighborhood={accepted}; report={args.report_output}",
    )
    return 0


def _live_spec() -> MnqEvalSpec:
    return MnqEvalSpec(
        strategy_id=STRATEGY_ID,
        label="current ACSIL defaults",
        vwap_threshold=80.0,
        delta_threshold=400.0,
        close_location_threshold=0.4,
        spacing_seconds=900,
        skip_friday=True,
        skip_11_hour=True,
        skip_15_hour=True,
        first_target_points=25.0,
        stop_points=140.0,
        runner_target_points=40.0,
        runner_stop_mode="initial",
    )


def _signals_for_spec(
    spec: MnqEvalSpec,
    bars_by_date: dict[date, list[wave.Bar]],
    *,
    symbol: str,
) -> list[wave.Signal]:
    signals = []
    for day_rows in bars_by_date.values():
        raw_count = 0
        last_raw_time: datetime | None = None
        for index, row in enumerate(day_rows):
            if not _schedule_allowed(row, spec):
                continue
            signal = _raw_signal(row, spec, symbol=symbol)
            if signal is None:
                continue
            if last_raw_time is not None:
                seconds_since_last = (row.timestamp - last_raw_time).total_seconds()
                if seconds_since_last < spec.spacing_seconds:
                    continue
            if raw_count >= 20:
                continue
            raw_count += 1
            last_raw_time = row.timestamp
            if index == 0:
                continue
            if day_rows[index - 1].high <= day_rows[index - 1].low:
                continue
            signals.append(signal)
    return sorted(signals, key=lambda signal: signal.bar.timestamp)


def _schedule_allowed(row: wave.Bar, spec: MnqEvalSpec) -> bool:
    if row.timestamp.time() < SETUP_START or row.timestamp.time() > SETUP_END:
        return False
    if spec.skip_friday and row.timestamp.weekday() == 4:
        return False
    if spec.skip_11_hour and row.timestamp.hour == 11:
        return False
    if spec.skip_15_hour and row.timestamp.hour == 15:
        return False
    return True


def _raw_signal(row: wave.Bar, spec: MnqEvalSpec, *, symbol: str) -> wave.Signal | None:
    distance_from_vwap = row.close - row.vwap
    if (
        distance_from_vwap >= spec.vwap_threshold
        and row.delta >= spec.delta_threshold
        and row.close_location <= spec.close_location_threshold
    ):
        return wave.Signal(spec.strategy_id, "short", row, f"{symbol} VWAP/delta upper fade")
    if (
        distance_from_vwap <= -spec.vwap_threshold
        and row.delta <= -spec.delta_threshold
        and row.close_location >= 1.0 - spec.close_location_threshold
    ):
        return wave.Signal(spec.strategy_id, "long", row, f"{symbol} VWAP/delta lower fade")
    return None


def _evaluate_signals(
    spec: MnqEvalSpec,
    signals: list[wave.Signal],
    bars_by_date: dict[date, list[wave.Bar]],
    rows_by_index: dict[int, int],
    *,
    slippage_ticks: float,
    live_sequenced: bool,
) -> list[ScaledOutcome]:
    outcomes = []
    busy_until = datetime.min
    for signal in signals:
        if live_sequenced and signal.bar.timestamp <= busy_until:
            continue
        rows = bars_by_date[signal.bar.trade_date]
        local_index = rows_by_index[signal.bar.index]
        following_rows = [
            row for row in rows[local_index + 1:]
            if row.timestamp.time() <= FLATTEN_TIME
        ]
        outcome = _evaluate_scaled_signal(
            spec,
            signal,
            following_rows,
            slippage_ticks=slippage_ticks,
        )
        outcomes.append(outcome)
        if live_sequenced:
            busy_until = outcome.exit_time
    return outcomes


def _evaluate_scaled_signal(
    spec: MnqEvalSpec,
    signal: wave.Signal,
    following_rows: list[wave.Bar],
    *,
    slippage_ticks: float,
) -> ScaledOutcome:
    is_long = signal.direction == "long"
    entry_price = signal.bar.close
    stop_price = entry_price - spec.stop_points if is_long else entry_price + spec.stop_points
    first_target_price = (
        entry_price + spec.first_target_points if is_long else entry_price - spec.first_target_points
    )
    runner_target_price = (
        entry_price + spec.runner_target_points if is_long else entry_price - spec.runner_target_points
    )
    runner_stop_price = stop_price
    first_target_hit = False
    leg1_exit_price = entry_price
    runner_exit_price = entry_price
    exit_bar = following_rows[-1] if following_rows else signal.bar
    exit_reason = "end_of_session" if following_rows else "no_following_bar"

    for row in following_rows:
        if not first_target_hit:
            stop_hit = row.low <= stop_price if is_long else row.high >= stop_price
            target_hit = row.high >= first_target_price if is_long else row.low <= first_target_price
            if stop_hit:
                exit_bar = row
                leg1_exit_price = stop_price
                runner_exit_price = stop_price
                exit_reason = "initial_stop_hit"
                break
            if target_hit:
                first_target_hit = True
                leg1_exit_price = first_target_price
                if spec.runner_stop_mode == "breakeven":
                    runner_stop_price = entry_price

        if first_target_hit:
            runner_stop_hit = row.low <= runner_stop_price if is_long else row.high >= runner_stop_price
            runner_target_hit = row.high >= runner_target_price if is_long else row.low <= runner_target_price
            if runner_stop_hit:
                exit_bar = row
                runner_exit_price = runner_stop_price
                exit_reason = (
                    "runner_breakeven_stop_hit"
                    if spec.runner_stop_mode == "breakeven"
                    else "runner_initial_stop_hit"
                )
                break
            if runner_target_hit:
                exit_bar = row
                runner_exit_price = runner_target_price
                exit_reason = "runner_target_hit"
                break

    if exit_reason == "end_of_session":
        runner_exit_price = exit_bar.close
        if not first_target_hit:
            leg1_exit_price = exit_bar.close

    leg1_points = (
        leg1_exit_price - entry_price if is_long else entry_price - leg1_exit_price
    ) * spec.first_leg_quantity
    runner_points = (
        runner_exit_price - entry_price if is_long else entry_price - runner_exit_price
    ) * spec.runner_quantity
    gross_points = leg1_points + runner_points
    gross_usd = gross_points * POINT_VALUE_USD
    total_quantity = spec.first_leg_quantity + spec.runner_quantity
    commission_usd = total_quantity * 2.0 * COMMISSION_PER_SIDE_USD
    slippage_usd = total_quantity * slippage_ticks * TICK_VALUE_USD
    net_usd = gross_usd - commission_usd - slippage_usd
    return ScaledOutcome(
        strategy_id=spec.strategy_id,
        direction=signal.direction,
        entry_time=signal.bar.timestamp,
        exit_time=exit_bar.timestamp,
        entry_bar_index=signal.bar.index,
        exit_bar_index=exit_bar.index,
        entry_price=entry_price,
        stop_price=stop_price,
        first_target_price=first_target_price,
        runner_target_price=runner_target_price,
        leg1_exit_price=leg1_exit_price,
        runner_exit_price=runner_exit_price,
        exit_reason=exit_reason,
        first_target_hit=first_target_hit,
        holding_minutes=(exit_bar.timestamp - signal.bar.timestamp).total_seconds() / 60.0,
        gross_points=gross_points,
        net_usd=net_usd,
        notes=signal.notes,
    )


def _summary_row(
    mode: str,
    strategy_id: str,
    slippage_ticks: float,
    outcomes: list[ScaledOutcome],
    trade_dates: list[date],
    sample_weeks: float,
) -> dict[str, object]:
    metrics = _metrics(outcomes)
    periods = _period_groups(outcomes)
    years = [sum(outcome.net_usd for outcome in values) for key, values in periods.items() if key.startswith("year:")]
    quarters = [sum(outcome.net_usd for outcome in values) for key, values in periods.items() if key.startswith("quarter:")]
    months = [sum(outcome.net_usd for outcome in values) for key, values in periods.items() if key.startswith("month:")]
    latest_year = max(trade_dates).year if trade_dates else 0
    recent_dates = set(trade_dates[-120:])
    gaps = _gap_days(outcomes)
    return {
        "schema_version": 1,
        "mode": mode,
        "strategy_id": strategy_id,
        "slippage_ticks": _fmt(slippage_ticks),
        "trades": len(outcomes),
        "trades_per_week": _fmt(len(outcomes) / sample_weeks if sample_weeks else 0.0),
        "net_usd": _fmt(metrics["net"]),
        "average_trade_usd": _fmt(metrics["average"]),
        "profit_factor": _fmt(metrics["profit_factor"]),
        "win_rate": _fmt(metrics["win_rate"]),
        "runner_target_rate": _fmt(_exit_rate(outcomes, "runner_target_hit")),
        "stop_rate": _fmt(_stop_rate(outcomes)),
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
    outcomes_by_key: dict[tuple[str, float], list[ScaledOutcome]],
    trade_dates: list[date],
) -> list[dict[str, object]]:
    configs = ((20, 5), (40, 10), (60, 10), (90, 15), (120, 20), (180, 30))
    rows = []
    for (mode, slippage_ticks), outcomes in outcomes_by_key.items():
        if slippage_ticks not in {1.0, 6.0}:
            continue
        by_date: dict[date, list[ScaledOutcome]] = defaultdict(list)
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
                        "mode": mode,
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


def _period_rows(
    outcomes_by_key: dict[tuple[str, float], list[ScaledOutcome]],
) -> list[dict[str, object]]:
    rows = []
    for (mode, slippage_ticks), outcomes in outcomes_by_key.items():
        if slippage_ticks not in {1.0, 6.0}:
            continue
        for period_id, period_outcomes in sorted(_period_groups(outcomes).items()):
            period_type, period = period_id.split(":", 1)
            metrics = _metrics(period_outcomes)
            rows.append(
                {
                    "schema_version": 1,
                    "mode": mode,
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
    outcomes_by_key: dict[tuple[str, float], list[ScaledOutcome]],
    *,
    iterations: int,
    seed: int,
) -> list[dict[str, object]]:
    rows = []
    rng = random.Random(seed)
    for (mode, slippage_ticks), outcomes in outcomes_by_key.items():
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
                "mode": mode,
                "strategy_id": STRATEGY_ID,
                "slippage_ticks": _fmt(slippage_ticks),
                "iterations": iterations,
                "seed": seed,
                "chronological_drawdown_usd": _fmt(chronological_drawdown),
                "median_drawdown_usd": _fmt(_quantile(sorted_dd, 0.50)),
                "p90_drawdown_usd": _fmt(_quantile(sorted_dd, 0.10)),
                "p95_drawdown_usd": _fmt(_quantile(sorted_dd, 0.05)),
                "p99_drawdown_usd": _fmt(_quantile(sorted_dd, 0.01)),
                "prob_dd_lte_750": _fmt(sum(dd <= -750.0 for dd in simulated_drawdowns) / iterations),
                "prob_dd_lte_1000": _fmt(sum(dd <= -1000.0 for dd in simulated_drawdowns) / iterations),
                "prob_dd_lte_1500": _fmt(sum(dd <= -1500.0 for dd in simulated_drawdowns) / iterations),
                "prob_dd_lte_2000": _fmt(sum(dd <= -2000.0 for dd in simulated_drawdowns) / iterations),
                "median_max_loss_streak": _fmt(_quantile(sorted_streaks, 0.50)),
                "p95_max_loss_streak": _fmt(_quantile(sorted_streaks, 0.95)),
            },
        )
    return rows


def _neighborhood_rows(
    bars_by_date: dict[date, list[wave.Bar]],
    rows_by_index: dict[int, int],
    trade_dates: list[date],
    sample_weeks: float,
    *,
    symbol: str,
    current_live_net: float,
) -> list[dict[str, object]]:
    rows = []
    rank = 0
    for vwap_threshold in (70.0, 75.0, 80.0, 85.0, 90.0, 100.0):
        for delta_threshold in (300.0, 350.0, 400.0, 450.0, 500.0, 600.0):
            for close_location_threshold in (0.375, 0.4, 0.425):
                for spacing_seconds in (900, 1200):
                    spec_base_id = (
                        "mnq_eval_live_final:"
                        f"vwap{vwap_threshold:g}:delta{delta_threshold:g}:"
                        f"cl{close_location_threshold:g}:space{spacing_seconds}"
                    )
                    signals = _signals_for_spec(
                        MnqEvalSpec(
                            strategy_id=spec_base_id,
                            label="neighborhood",
                            vwap_threshold=vwap_threshold,
                            delta_threshold=delta_threshold,
                            close_location_threshold=close_location_threshold,
                            spacing_seconds=spacing_seconds,
                            skip_friday=True,
                            skip_11_hour=True,
                            skip_15_hour=True,
                            first_target_points=25.0,
                            stop_points=140.0,
                            runner_target_points=40.0,
                            runner_stop_mode="initial",
                        ),
                        bars_by_date,
                        symbol=symbol,
                    )
                    for first_target_points in (20.0, 25.0, 30.0):
                        for stop_points in (130.0, 140.0, 150.0):
                            for runner_target_points in (35.0, 40.0, 45.0, 50.0):
                                for runner_stop_mode in ("initial", "breakeven"):
                                    if runner_target_points <= first_target_points:
                                        continue
                                    spec = MnqEvalSpec(
                                        strategy_id=(
                                            f"{spec_base_id}:t{first_target_points:g}:"
                                            f"s{stop_points:g}:r{runner_target_points:g}:"
                                            f"{runner_stop_mode}"
                                        ),
                                        label="neighborhood",
                                        vwap_threshold=vwap_threshold,
                                        delta_threshold=delta_threshold,
                                        close_location_threshold=close_location_threshold,
                                        spacing_seconds=spacing_seconds,
                                        skip_friday=True,
                                        skip_11_hour=True,
                                        skip_15_hour=True,
                                        first_target_points=first_target_points,
                                        stop_points=stop_points,
                                        runner_target_points=runner_target_points,
                                        runner_stop_mode=runner_stop_mode,
                                    )
                                    independent = _evaluate_signals(
                                        spec,
                                        signals,
                                        bars_by_date,
                                        rows_by_index,
                                        slippage_ticks=1.0,
                                        live_sequenced=False,
                                    )
                                    live = _evaluate_signals(
                                        spec,
                                        signals,
                                        bars_by_date,
                                        rows_by_index,
                                        slippage_ticks=1.0,
                                        live_sequenced=True,
                                    )
                                    independent_metrics = _metrics(independent)
                                    live_metrics = _metrics(live)
                                    live_summary = _summary_row(
                                        "live_sequenced",
                                        spec.strategy_id,
                                        1.0,
                                        live,
                                        trade_dates,
                                        sample_weeks,
                                    )
                                    wf40 = _one_holdout_summary(live, trade_dates, 40, 10)
                                    accepted, decision = _accept_neighborhood_row(
                                        live,
                                        live_metrics,
                                        live_summary,
                                        wf40,
                                        current_live_net,
                                    )
                                    rank += 1
                                    rows.append(
                                        {
                                            "schema_version": 1,
                                            "rank": rank,
                                            "strategy_id": spec.strategy_id,
                                            "vwap_threshold": _fmt(vwap_threshold),
                                            "delta_threshold": _fmt(delta_threshold),
                                            "close_location_threshold": _fmt(close_location_threshold),
                                            "spacing_seconds": spacing_seconds,
                                            "first_target_points": _fmt(first_target_points),
                                            "stop_points": _fmt(stop_points),
                                            "runner_target_points": _fmt(runner_target_points),
                                            "runner_stop_mode": runner_stop_mode,
                                            "independent_trades": len(independent),
                                            "independent_net_usd": _fmt(independent_metrics["net"]),
                                            "independent_profit_factor": _fmt(independent_metrics["profit_factor"]),
                                            "independent_max_drawdown_usd": _fmt(independent_metrics["drawdown"]),
                                            "live_trades": len(live),
                                            "live_net_usd": _fmt(live_metrics["net"]),
                                            "live_average_trade_usd": _fmt(live_metrics["average"]),
                                            "live_profit_factor": _fmt(live_metrics["profit_factor"]),
                                            "live_win_rate": _fmt(live_metrics["win_rate"]),
                                            "live_max_drawdown_usd": _fmt(live_metrics["drawdown"]),
                                            "live_latest_year_net_usd": live_summary["latest_year_net_usd"],
                                            "live_worst_year_net_usd": live_summary["worst_year_net_usd"],
                                            "live_worst_quarter_net_usd": live_summary["worst_quarter_net_usd"],
                                            "live_wf40_windows": wf40["windows"],
                                            "live_wf40_positive_windows": wf40["positive"],
                                            "live_wf40_negative_windows": wf40["negative"],
                                            "live_wf40_net_usd": wf40["net_usd"],
                                            "live_wf40_worst_window_usd": wf40["worst_window_usd"],
                                            "accepted": "yes" if accepted else "no",
                                            "decision": decision,
                                        },
                                    )
    rows.sort(key=_neighborhood_sort_key)
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
    return rows


def _accept_neighborhood_row(
    outcomes: list[ScaledOutcome],
    metrics: dict[str, float | int],
    summary: dict[str, object],
    wf40: dict[str, object],
    current_live_net: float,
) -> tuple[bool, str]:
    if len(outcomes) < 80:
        return False, "reject: too few live-sequenced trades"
    if float(metrics["net"]) <= current_live_net:
        return False, "reject: does not improve current live-sequenced net"
    if float(metrics["profit_factor"]) < 1.60:
        return False, "reject: PF below 1.60"
    if float(metrics["drawdown"]) <= -1200.0:
        return False, "reject: drawdown worse than -1200"
    if float(summary["latest_year_net_usd"]) <= 0.0 or float(summary["worst_year_net_usd"]) <= 0.0:
        return False, "reject: non-positive year"
    if float(summary["worst_quarter_net_usd"]) <= -800.0:
        return False, "reject: weak quarter"
    if int(wf40["windows"]) < 8 or int(wf40["negative"]) > 1:
        return False, "reject: holdout instability"
    if float(wf40["worst_window_usd"]) <= -500.0:
        return False, "reject: weak holdout window"
    return True, "accepted: stronger live-sequenced candidate"


def _one_holdout_summary(
    outcomes: list[ScaledOutcome],
    trade_dates: list[date],
    train_count: int,
    holdout_count: int,
) -> dict[str, object]:
    windows = []
    by_date: dict[date, list[ScaledOutcome]] = defaultdict(list)
    for outcome in outcomes:
        by_date[outcome.entry_time.date()].append(outcome)
    max_start = len(trade_dates) - train_count - holdout_count
    if max_start >= 0:
        for start in range(0, max_start + 1, holdout_count):
            holdout_dates = trade_dates[start + train_count:start + train_count + holdout_count]
            window_outcomes = []
            for trade_date in holdout_dates:
                window_outcomes.extend(by_date.get(trade_date, []))
            windows.append(sum(outcome.net_usd for outcome in window_outcomes))
    return {
        "windows": len(windows),
        "positive": sum(value > 0.0 for value in windows),
        "negative": sum(value < 0.0 for value in windows),
        "net_usd": _fmt(sum(windows)),
        "worst_window_usd": _fmt(min(windows) if windows else 0.0),
    }


def _write_report(
    report_output: str,
    bars: list[wave.Bar],
    raw_signals: list[wave.Signal],
    summary_rows: list[dict[str, object]],
    holdout_rows: list[dict[str, object]],
    period_rows: list[dict[str, object]],
    monte_carlo_rows: list[dict[str, object]],
    neighborhood_rows: list[dict[str, object]],
) -> None:
    independent_base = _row_for(summary_rows, "independent", 1.0)
    live_base = _row_for(summary_rows, "live_sequenced", 1.0)
    live_stress = _row_for(summary_rows, "live_sequenced", 6.0)
    accepted = [row for row in neighborhood_rows if row["accepted"] == "yes"]
    current_neighborhood_row = _find_current_neighborhood_row(neighborhood_rows)
    lines = [
        "# MNQ Eval Live Final Validation",
        "",
        "Status: final offline research battery for `AxonTrade MNQ Eval Live Bot` on the current MNQ export.",
        "",
        "## Scope",
        "",
        f"- source rows: `{len(bars)}`",
        f"- dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        f"- unique trading dates: `{len({bar.trade_date for bar in bars})}`",
        f"- raw accepted setup candidates after schedule/spacing/context: `{len(raw_signals)}`",
        "- instrument: `MNQ`, `1+1 MNQ` scaled exit",
        "- base cost model: `$0.50/side` commission plus `1` total slippage tick per contract",
        "- same-bar handling: stop first",
        "- implementation reality tested here: `independent` reproduces the old paper audit; `live_sequenced` rejects entries while the previous trade is still open, matching the ACSIL position/working-order gate.",
        "",
        "## Implemented Rule",
        "",
        f"- strategy: `{STRATEGY_ID}`",
        "- entry: VWAP/delta exhaustion fade, `80` point VWAP extension, bar delta `400`, close-location `0.4`",
        "- schedule: `09:45-15:45`, no Friday entries, no `11:00` or `15:00` exchange-hour entries",
        "- pacing: `900` seconds between raw candidates, max `20` raw candidates per day",
        "- exits: first target `25`, initial stop `140`, runner target `40`, runner stop remains initial",
        "",
        "## Scorecard",
        "",
        "| Mode | Slip | Trades | /Wk | Net | Avg | PF | Win | Runner Target | Stop | DD | Net/DD | Latest | Worst Year | Worst Q | Worst Month | Max Gap |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary_rows:
        if float(row["slippage_ticks"]) not in {1.0, 3.0, 6.0, 12.0}:
            continue
        lines.append(
            "| "
            f"`{row['mode']}` | {row['slippage_ticks']} | {row['trades']} | "
            f"{row['trades_per_week']} | {row['net_usd']} | {row['average_trade_usd']} | "
            f"{row['profit_factor']} | {float(row['win_rate']) * 100:.1f}% | "
            f"{float(row['runner_target_rate']) * 100:.1f}% | "
            f"{float(row['stop_rate']) * 100:.1f}% | {row['max_drawdown_usd']} | "
            f"{row['net_to_drawdown']} | {row['latest_year_net_usd']} | "
            f"{row['worst_year_net_usd']} | {row['worst_quarter_net_usd']} | "
            f"{row['worst_month_net_usd']} | {row['max_gap_days']} |"
        )
    lines.extend(
        [
            "",
            "## Live-Sequenced Holdouts",
            "",
            "| Slip | Config | Windows | Positive | Negative | No Trade | Net | Worst | Median |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    for row in _holdout_summary_rows(holdout_rows):
        if row["mode"] != "live_sequenced":
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
            "| Mode | Slip | Worst Year | Worst Quarter | Worst Month |",
            "| --- | ---: | ---: | ---: | ---: |",
        ],
    )
    for mode, slippage_ticks in (("independent", 1.0), ("live_sequenced", 1.0), ("live_sequenced", 6.0)):
        rows = [
            row for row in period_rows
            if row["mode"] == mode and float(row["slippage_ticks"]) == slippage_ticks
        ]
        lines.append(
            "| "
            f"`{mode}` | {_fmt(slippage_ticks)} | "
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
            "| Mode | Slip | Chron DD | Median DD | P95 DD | P99 DD | P(DD <= -1000) | P(DD <= -1500) | P95 Loss Streak |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    for row in monte_carlo_rows:
        lines.append(
            "| "
            f"`{row['mode']}` | {row['slippage_ticks']} | "
            f"{row['chronological_drawdown_usd']} | {row['median_drawdown_usd']} | "
            f"{row['p95_drawdown_usd']} | {row['p99_drawdown_usd']} | "
            f"{float(row['prob_dd_lte_1000']) * 100:.1f}% | "
            f"{float(row['prob_dd_lte_1500']) * 100:.1f}% | "
            f"{row['p95_max_loss_streak']} |"
        )
    lines.extend(
        [
            "",
            "## Neighborhood Search",
            "",
            f"- rows tested: `{len(neighborhood_rows)}`",
            f"- accepted by the live-sequenced final lens: `{len(accepted)}`",
            "- final lens: at least `80` live-sequenced trades, net above current live-sequenced net, PF `>= 1.60`, DD better than `-$1200`, positive latest/worst year, worst quarter better than `-$800`, at least `8` fixed `40x10` windows, at most one negative `40x10` window, and worst `40x10` window better than `-$500`.",
        ],
    )
    if current_neighborhood_row is not None:
        lines.append(
            f"- current implemented row rank in the live-sequenced neighborhood: `{current_neighborhood_row['rank']}` of `{len(neighborhood_rows)}`"
        )
    lines.extend(
        [
            "",
            "| Rank | Strategy | Trades | Net | PF | DD | Latest | Worst Year | Worst Q | WF40 | WF40 Worst | Decision |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ],
    )
    for row in neighborhood_rows[:20]:
        lines.append(
            "| "
            f"{row['rank']} | `{row['strategy_id']}` | {row['live_trades']} | "
            f"{row['live_net_usd']} | {row['live_profit_factor']} | "
            f"{row['live_max_drawdown_usd']} | {row['live_latest_year_net_usd']} | "
            f"{row['live_worst_year_net_usd']} | {row['live_worst_quarter_net_usd']} | "
            f"{row['live_wf40_positive_windows']}/{row['live_wf40_windows']} | "
            f"{row['live_wf40_worst_window_usd']} | {row['decision']} |"
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
        ],
    )
    if accepted:
        best = accepted[0]
        lines.extend(
            [
                "The current MNQ Eval Live bot is not yet `100%` complete as a live-executable rule because the deeper live-sequenced search found stronger candidates. Do not change live defaults without a replay/mechanics pass, but the leading replacement candidate is now clear:",
                "",
                (
                    f"- `{best['strategy_id']}`: `{best['live_trades']}` live-sequenced trades, "
                    f"`{best['live_net_usd']}` net, `{best['live_profit_factor']}` PF, "
                    f"`{best['live_max_drawdown_usd']}` DD, "
                    f"`{best['live_wf40_positive_windows']}/{best['live_wf40_windows']}` positive `40x10` holdouts."
                ),
                "",
            ],
        )
        next_gate = "Next gate is replay/mechanics validation for the replacement row before live defaults are changed."
    else:
        lines.extend(
            [
                "No neighborhood row replaces the current implemented rule under the live-sequenced final lens. The MNQ Eval Live VWAP/delta family is `100%` offline researched for the current export, with the caveat that live-sequenced stats are the real executable baseline.",
                "",
            ],
        )
        next_gate = "Next gate is monitored forward evidence, not more static tuning or default changes."
    lines.extend(
        [
            "Key finding:",
            "",
            (
                f"- Legacy independent audit: `{independent_base['trades']}` trades, "
                f"`{independent_base['net_usd']}` net, `{independent_base['profit_factor']}` PF, "
                f"`{independent_base['max_drawdown_usd']}` DD."
            ),
            (
                f"- Live-sequenced executable path: `{live_base['trades']}` trades, "
                f"`{live_base['net_usd']}` net, `{live_base['profit_factor']}` PF, "
                f"`{live_base['max_drawdown_usd']}` DD."
            ),
            (
                f"- Six-tick live-sequenced stress: `{live_stress['net_usd']}` net, "
                f"`{live_stress['profit_factor']}` PF, `{live_stress['max_drawdown_usd']}` DD."
            ),
            "",
            next_gate,
            "",
        ],
    )
    Path(report_output).write_text("\n".join(lines), encoding="utf-8")


def _metrics(outcomes: list[ScaledOutcome]) -> dict[str, float | int]:
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
        "drawdown": _max_drawdown(values),
        "worst_trade": min(values),
        "max_loss_streak_trades": loss_count,
        "max_loss_streak_usd": loss_usd,
    }


def _period_groups(outcomes: list[ScaledOutcome]) -> dict[str, list[ScaledOutcome]]:
    groups: dict[str, list[ScaledOutcome]] = defaultdict(list)
    for outcome in outcomes:
        groups[f"year:{outcome.entry_time.year}"].append(outcome)
        quarter = (outcome.entry_time.month - 1) // 3 + 1
        groups[f"quarter:{outcome.entry_time.year}Q{quarter}"].append(outcome)
        groups[f"month:{outcome.entry_time.year}-{outcome.entry_time.month:02d}"].append(outcome)
    return groups


def _holdout_summary_rows(holdout_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in holdout_rows:
        grouped[(str(row["mode"]), str(row["slippage_ticks"]), str(row["config"]))].append(row)
    rows = []
    for (mode, slippage_ticks, config), group in sorted(
        grouped.items(),
        key=lambda item: (item[0][0], float(item[0][1]), *_config_sort_key(item[0][2])),
    ):
        nets = [float(row["net_usd"]) for row in group]
        trades = [int(row["trades"]) for row in group]
        rows.append(
            {
                "mode": mode,
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


def _worst_period(rows: list[dict[str, object]], period_type: str) -> str:
    filtered = [row for row in rows if row["period_type"] == period_type]
    if not filtered:
        return "`none`"
    worst = min(filtered, key=lambda row: float(row["net_usd"]))
    return f"`{worst['period']}={worst['net_usd']}`"


def _worst_group(outcomes: list[ScaledOutcome], *, key: Callable[[ScaledOutcome], Any]) -> float:
    grouped: dict[Any, float] = defaultdict(float)
    for outcome in outcomes:
        grouped[key(outcome)] += outcome.net_usd
    return min(grouped.values()) if grouped else 0.0


def _exit_rate(outcomes: list[ScaledOutcome], exit_reason: str) -> float:
    return sum(outcome.exit_reason == exit_reason for outcome in outcomes) / len(outcomes) if outcomes else 0.0


def _stop_rate(outcomes: list[ScaledOutcome]) -> float:
    stop_reasons = {"initial_stop_hit", "runner_initial_stop_hit", "runner_breakeven_stop_hit"}
    return sum(outcome.exit_reason in stop_reasons for outcome in outcomes) / len(outcomes) if outcomes else 0.0


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


def _gap_days(outcomes: list[ScaledOutcome]) -> list[float]:
    ordered = sorted(outcomes, key=lambda outcome: outcome.entry_time)
    return [
        (right.entry_time.date() - left.entry_time.date()).days
        for left, right in zip(ordered, ordered[1:])
    ]


def _net_to_drawdown(net_usd: float, drawdown_usd: float) -> float:
    return net_usd / abs(drawdown_usd) if drawdown_usd else 0.0


def _sample_weeks(bars: list[wave.Bar]) -> float:
    if not bars:
        return 0.0
    days = (bars[-1].trade_date - bars[0].trade_date).days + 1
    return days / 7.0


def _row_for(rows: list[dict[str, object]], mode: str, slippage_ticks: float) -> dict[str, object]:
    for row in rows:
        if row["mode"] == mode and float(row["slippage_ticks"]) == slippage_ticks:
            return row
    raise KeyError((mode, slippage_ticks))


def _find_current_neighborhood_row(rows: list[dict[str, object]]) -> dict[str, object] | None:
    for row in rows:
        if (
            float(row["vwap_threshold"]) == 80.0
            and float(row["delta_threshold"]) == 400.0
            and float(row["close_location_threshold"]) == 0.4
            and int(row["spacing_seconds"]) == 900
            and float(row["first_target_points"]) == 25.0
            and float(row["stop_points"]) == 140.0
            and float(row["runner_target_points"]) == 40.0
            and row["runner_stop_mode"] == "initial"
        ):
            return row
    return None


def _neighborhood_sort_key(row: dict[str, object]) -> tuple[float, ...]:
    accepted_rank = 0.0 if row["accepted"] == "yes" else 1.0
    return (
        accepted_rank,
        -float(row["live_net_usd"]),
        -float(row["live_profit_factor"]),
        abs(float(row["live_max_drawdown_usd"])),
        -float(row["live_wf40_net_usd"]),
        -float(row["live_wf40_worst_window_usd"]),
    )


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
