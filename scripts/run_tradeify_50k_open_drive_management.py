#!/usr/bin/env python3
"""Refine the Tradeify MNQ opening-drive lead with scale-out management."""

from __future__ import annotations

import argparse
import csv
import random
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_mnq_eval_pass_wave_rider as wave  # noqa: E402
import run_tradeify_50k_mnq_strategy_research as core  # noqa: E402


DEFAULT_OUTPUT = "reports/tradeify-50k-open-drive-management-sweep.csv"
DEFAULT_REPORT = "reports/tradeify-50k-open-drive-management.md"
DEFAULT_AUDIT = "reports/tradeify-50k-open-drive-management-trade-audit.csv"


@dataclass(frozen=True)
class ManagementProfile:
    first_units: int
    runner_units: int
    first_target_points: float
    initial_stop_points: float
    runner_target_points: float
    breakeven_offset_points: float

    @property
    def total_units(self) -> int:
        return self.first_units + self.runner_units

    @property
    def profile_id(self) -> str:
        return (
            f"split{self.first_units}-{self.runner_units}:"
            f"t1{self.first_target_points:g}:s{self.initial_stop_points:g}:"
            f"runner{self.runner_target_points:g}:be{self.breakeven_offset_points:g}"
        )


@dataclass(frozen=True)
class ManagedOutcome:
    strategy_id: str
    direction: str
    entry_time: datetime
    exit_time: datetime
    entry_bar_index: int
    exit_bar_index: int
    entry_price: float
    first_exit_price: float
    runner_exit_price: float
    initial_stop_price: float
    first_target_price: float
    runner_target_price: float
    exit_reason: str
    first_target_hit: bool
    runner_target_hit: bool
    gross_point_contracts: float
    contracts: int
    holding_minutes: float
    notes: str


@dataclass(frozen=True)
class Metrics:
    trades: int
    net_usd: float
    average_trade_usd: float
    profit_factor: float
    win_rate: float
    first_target_rate: float
    runner_target_rate: float
    max_drawdown_usd: float
    net_to_drawdown: float
    worst_day_usd: float
    max_loss_streak: int
    average_holding_minutes: float


CSV_HEADER = [
    "schema_version",
    "strategy_id",
    "profile_id",
    "first_units",
    "runner_units",
    "total_units",
    "first_target_points",
    "initial_stop_points",
    "runner_target_points",
    "breakeven_offset_points",
    "trades",
    "trades_per_week",
    "net_usd",
    "average_trade_usd",
    "profit_factor",
    "win_rate",
    "first_target_rate",
    "runner_target_rate",
    "max_drawdown_usd",
    "net_to_drawdown",
    "train_net_usd",
    "train_profit_factor",
    "validation_net_usd",
    "validation_profit_factor",
    "later_net_usd",
    "later_profit_factor",
    "positive_windows",
    "negative_windows",
    "worst_window_net_usd",
    "eligible",
    "rank",
]


AUDIT_HEADER = [
    "schema_version",
    "strategy_id",
    "profile_id",
    "direction",
    "entry_time",
    "exit_time",
    "entry_price",
    "first_exit_price",
    "runner_exit_price",
    "initial_stop_price",
    "first_target_price",
    "runner_target_price",
    "exit_reason",
    "first_target_hit",
    "runner_target_hit",
    "gross_point_contracts",
    "base_net_usd",
    "holding_minutes",
    "notes",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refine the robust Tradeify MNQ opening-drive entry with scale-outs.",
    )
    parser.add_argument("input", nargs="?", default=wave.DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT)
    parser.add_argument("--audit-output", default=DEFAULT_AUDIT)
    parser.add_argument("--seed", type=int, default=20260805)
    args = parser.parse_args()

    bars = wave._load_feature_bars(args.input)
    bars_by_date = wave._bars_by_date(bars)
    contexts = core._build_day_contexts(bars_by_date)
    trade_dates = sorted(contexts)
    train_dates, validation_dates, later_dates = core._split_dates(trade_dates)
    date_sets = {
        "train": set(train_dates),
        "validation": set(validation_dates),
        "later": set(later_dates),
    }
    signal_sets = _robust_open_drive_signal_sets(contexts)
    profiles = _management_profiles()
    sample_weeks = max((trade_dates[-1] - trade_dates[0]).days / 7.0, 1.0)
    print(
        f"generated {len(signal_sets)} robust opening-drive variants and "
        f"{len(profiles)} management profiles",
        flush=True,
    )

    rows: list[dict[str, object]] = []
    outcomes_by_key: dict[tuple[str, str], list[ManagedOutcome]] = {}
    profile_by_id = {profile.profile_id: profile for profile in profiles}
    for strategy_id, signals in signal_sets.items():
        for profile in profiles:
            outcomes = _evaluate_signals(signals, bars_by_date, profile)
            if len(outcomes) < 90:
                continue
            full = _metrics(outcomes)
            period_metrics = {
                label: _metrics(_outcomes_for_dates(outcomes, dates))
                for label, dates in date_sets.items()
            }
            windows = _window_metrics(outcomes, trade_dates, window_count=6)
            eligible = _eligible(full, period_metrics, windows)
            row = _row(
                strategy_id,
                profile,
                full,
                period_metrics,
                windows,
                sample_weeks=sample_weeks,
                eligible=eligible,
            )
            rows.append(row)
            outcomes_by_key[(strategy_id, profile.profile_id)] = outcomes

    ranked = sorted((row for row in rows if bool(row["eligible"])), key=_rank_key)
    ranks = {_key(row): rank for rank, row in enumerate(ranked, start=1)}
    for row in rows:
        row["rank"] = ranks.get(_key(row), "")
    rows.sort(key=_report_key)
    _write_csv(args.output, rows)

    selected = ranked[0] if ranked else None
    selected_outcomes: list[ManagedOutcome] = []
    sizing_rows: list[dict[str, object]] = []
    stress: dict[str, object] = {}
    if selected is not None:
        selected_outcomes = outcomes_by_key[_key(selected)]
        selected_profile = profile_by_id[str(selected["profile_id"])]
        sizing_rows = _sizing_rows(
            selected_outcomes,
            selected_profile,
            trade_dates,
            seed=args.seed,
        )
        stress = _stress_summary(
            selected_outcomes,
            selected_profile,
            sizing_rows,
            date_sets,
            seed=args.seed,
        )
        _write_audit(args.audit_output, selected_outcomes, selected_profile)

    _write_report(
        args.report_output,
        bars=bars,
        trade_dates=trade_dates,
        train_dates=train_dates,
        validation_dates=validation_dates,
        later_dates=later_dates,
        rows=rows,
        selected=selected,
        selected_outcomes=selected_outcomes,
        sizing_rows=sizing_rows,
        stress=stress,
    )
    if selected is None:
        print(f"wrote {len(rows)} rows; no management profile survived", flush=True)
    else:
        print(
            f"wrote {len(rows)} rows; selected={selected['strategy_id']} "
            f"profile={selected['profile_id']} pf={selected['profit_factor']} "
            f"win={selected['win_rate']}",
            flush=True,
        )
    return 0


def _robust_open_drive_signal_sets(
    contexts: dict[date, core.DayContext],
) -> dict[str, list[wave.Signal]]:
    signal_sets: dict[str, list[wave.Signal]] = {}
    for pullback_points in (10.0, 20.0):
        for entry_delta in (0.0, 400.0):
            for entry_end in (time(11, 30), time(12, 30)):
                strategy_id = (
                    "tradeify_open_drive_managed:or15:drive20:ocl0.7:dr0:"
                    f"gapaligned:pb{pullback_points:g}:ed{entry_delta:g}:"
                    f"end{core._time_id(entry_end)}"
                )
                signal_sets[strategy_id] = core._open_drive_pullback_signals(
                    contexts,
                    strategy_id=strategy_id,
                    opening_minutes=15,
                    drive_points=20.0,
                    opening_close_location=0.70,
                    delta_ratio_threshold=0.0,
                    gap_mode="aligned",
                    pullback_points=pullback_points,
                    entry_delta_threshold=entry_delta,
                    entry_end=entry_end,
                    symbol="MNQ",
                )
    return signal_sets


def _management_profiles() -> list[ManagementProfile]:
    profiles = []
    for first_units, runner_units in ((1, 1), (2, 1), (3, 1), (3, 2)):
        for first_target in (20.0, 30.0, 40.0):
            for initial_stop in (30.0, 40.0, 50.0):
                for runner_target in (60.0, 80.0, 100.0, 120.0):
                    if runner_target <= first_target:
                        continue
                    for breakeven_offset in (0.0, 2.0):
                        profiles.append(
                            ManagementProfile(
                                first_units=first_units,
                                runner_units=runner_units,
                                first_target_points=first_target,
                                initial_stop_points=initial_stop,
                                runner_target_points=runner_target,
                                breakeven_offset_points=breakeven_offset,
                            ),
                        )
    return profiles


def _evaluate_signals(
    signals: list[wave.Signal],
    bars_by_date: dict[date, list[wave.Bar]],
    profile: ManagementProfile,
) -> list[ManagedOutcome]:
    local_index = {
        row.index: index
        for rows in bars_by_date.values()
        for index, row in enumerate(rows)
    }
    outcomes = []
    traded_dates: set[date] = set()
    for signal in sorted(signals, key=lambda item: item.bar.timestamp):
        if signal.bar.trade_date in traded_dates:
            continue
        day_rows = bars_by_date[signal.bar.trade_date]
        following = [
            row
            for row in day_rows[local_index[signal.bar.index] + 1 :]
            if row.timestamp.time() <= core.FLATTEN_TIME
        ]
        outcomes.append(_evaluate_signal(signal, following, profile))
        traded_dates.add(signal.bar.trade_date)
    return outcomes


def _evaluate_signal(
    signal: wave.Signal,
    following: list[wave.Bar],
    profile: ManagementProfile,
) -> ManagedOutcome:
    is_long = signal.direction == "long"
    entry = signal.bar.close
    initial_stop = (
        entry - profile.initial_stop_points
        if is_long
        else entry + profile.initial_stop_points
    )
    first_target = (
        entry + profile.first_target_points
        if is_long
        else entry - profile.first_target_points
    )
    runner_target = (
        entry + profile.runner_target_points
        if is_long
        else entry - profile.runner_target_points
    )
    runner_stop = (
        entry + profile.breakeven_offset_points
        if is_long
        else entry - profile.breakeven_offset_points
    )

    first_exit = entry
    runner_exit = entry
    first_hit = False
    runner_hit = False
    exit_reason = "no_following_bar"
    exit_bar = signal.bar
    runner_rows: list[wave.Bar] = []
    for index, row in enumerate(following):
        initial_stop_hit = (
            row.low <= initial_stop if is_long else row.high >= initial_stop
        )
        first_target_hit = (
            row.high >= first_target if is_long else row.low <= first_target
        )
        if initial_stop_hit:
            first_exit = initial_stop
            runner_exit = initial_stop
            exit_bar = row
            exit_reason = "initial_stop"
            break
        if first_target_hit:
            first_exit = first_target
            first_hit = True
            exit_bar = row
            exit_reason = "first_target_then_eod"
            runner_rows = following[index + 1 :]
            break
    else:
        if following:
            exit_bar = following[-1]
            first_exit = exit_bar.close
            runner_exit = exit_bar.close
            exit_reason = "end_of_session_before_first"

    if first_hit:
        runner_exit = runner_rows[-1].close if runner_rows else first_target
        if runner_rows:
            exit_bar = runner_rows[-1]
        for row in runner_rows:
            runner_stop_hit = (
                row.low <= runner_stop if is_long else row.high >= runner_stop
            )
            runner_target_hit = (
                row.high >= runner_target if is_long else row.low <= runner_target
            )
            if runner_stop_hit:
                runner_exit = runner_stop
                exit_bar = row
                exit_reason = "first_target_then_breakeven"
                break
            if runner_target_hit:
                runner_exit = runner_target
                exit_bar = row
                runner_hit = True
                exit_reason = "runner_target"
                break

    first_points = first_exit - entry if is_long else entry - first_exit
    runner_points = runner_exit - entry if is_long else entry - runner_exit
    gross_point_contracts = (
        first_points * profile.first_units + runner_points * profile.runner_units
    )
    return ManagedOutcome(
        strategy_id=signal.strategy_id,
        direction=signal.direction,
        entry_time=signal.bar.timestamp,
        exit_time=exit_bar.timestamp,
        entry_bar_index=signal.bar.index,
        exit_bar_index=exit_bar.index,
        entry_price=entry,
        first_exit_price=first_exit,
        runner_exit_price=runner_exit,
        initial_stop_price=initial_stop,
        first_target_price=first_target,
        runner_target_price=runner_target,
        exit_reason=exit_reason,
        first_target_hit=first_hit,
        runner_target_hit=runner_hit,
        gross_point_contracts=gross_point_contracts,
        contracts=profile.total_units,
        holding_minutes=(exit_bar.timestamp - signal.bar.timestamp).total_seconds()
        / 60.0,
        notes=signal.notes,
    )


def _metrics(
    outcomes: list[ManagedOutcome],
    *,
    multiplier: int = 1,
    total_slippage_ticks: int = core.BASE_TOTAL_SLIPPAGE_TICKS,
) -> Metrics:
    values = [
        _net(outcome, multiplier, total_slippage_ticks=total_slippage_ticks)
        for outcome in outcomes
    ]
    positives = [value for value in values if value > 0.0]
    negatives = [value for value in values if value < 0.0]
    daily: dict[date, float] = defaultdict(float)
    for outcome, value in zip(outcomes, values, strict=True):
        daily[outcome.entry_time.date()] += value
    net = sum(values)
    drawdown = core._max_drawdown(values)
    return Metrics(
        trades=len(outcomes),
        net_usd=net,
        average_trade_usd=statistics.mean(values) if values else 0.0,
        profit_factor=sum(positives) / abs(sum(negatives)) if negatives else 999.0,
        win_rate=len(positives) / len(values) if values else 0.0,
        first_target_rate=(
            sum(outcome.first_target_hit for outcome in outcomes) / len(outcomes)
            if outcomes
            else 0.0
        ),
        runner_target_rate=(
            sum(outcome.runner_target_hit for outcome in outcomes) / len(outcomes)
            if outcomes
            else 0.0
        ),
        max_drawdown_usd=drawdown,
        net_to_drawdown=net / abs(drawdown) if drawdown < 0.0 else 999.0,
        worst_day_usd=min(daily.values()) if daily else 0.0,
        max_loss_streak=core._max_loss_streak(values),
        average_holding_minutes=(
            statistics.mean(outcome.holding_minutes for outcome in outcomes)
            if outcomes
            else 0.0
        ),
    )


def _window_metrics(
    outcomes: list[ManagedOutcome],
    trade_dates: list[date],
    *,
    window_count: int,
) -> list[Metrics]:
    windows = []
    for index in range(window_count):
        start = round(index * len(trade_dates) / window_count)
        end = round((index + 1) * len(trade_dates) / window_count)
        dates = set(trade_dates[start:end])
        windows.append(_metrics(_outcomes_for_dates(outcomes, dates)))
    return windows


def _eligible(
    full: Metrics,
    periods: dict[str, Metrics],
    windows: list[Metrics],
) -> bool:
    return (
        full.trades >= 100
        and full.net_usd > 0.0
        and full.profit_factor >= 1.50
        and full.win_rate >= 0.60
        and full.max_drawdown_usd > -1500.0
        and all(metrics.trades >= 20 for metrics in periods.values())
        and all(metrics.net_usd > 0.0 for metrics in periods.values())
        and all(metrics.profit_factor >= 1.15 for metrics in periods.values())
        and sum(metrics.net_usd > 0.0 for metrics in windows) >= 5
        and min(metrics.net_usd for metrics in windows) > -350.0
    )


def _row(
    strategy_id: str,
    profile: ManagementProfile,
    full: Metrics,
    periods: dict[str, Metrics],
    windows: list[Metrics],
    *,
    sample_weeks: float,
    eligible: bool,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "strategy_id": strategy_id,
        "profile_id": profile.profile_id,
        "first_units": profile.first_units,
        "runner_units": profile.runner_units,
        "total_units": profile.total_units,
        "first_target_points": core._fmt(profile.first_target_points),
        "initial_stop_points": core._fmt(profile.initial_stop_points),
        "runner_target_points": core._fmt(profile.runner_target_points),
        "breakeven_offset_points": core._fmt(profile.breakeven_offset_points),
        "trades": full.trades,
        "trades_per_week": core._fmt(full.trades / sample_weeks),
        "net_usd": core._fmt(full.net_usd),
        "average_trade_usd": core._fmt(full.average_trade_usd),
        "profit_factor": core._fmt(full.profit_factor),
        "win_rate": core._fmt(full.win_rate),
        "first_target_rate": core._fmt(full.first_target_rate),
        "runner_target_rate": core._fmt(full.runner_target_rate),
        "max_drawdown_usd": core._fmt(full.max_drawdown_usd),
        "net_to_drawdown": core._fmt(full.net_to_drawdown),
        "train_net_usd": core._fmt(periods["train"].net_usd),
        "train_profit_factor": core._fmt(periods["train"].profit_factor),
        "validation_net_usd": core._fmt(periods["validation"].net_usd),
        "validation_profit_factor": core._fmt(periods["validation"].profit_factor),
        "later_net_usd": core._fmt(periods["later"].net_usd),
        "later_profit_factor": core._fmt(periods["later"].profit_factor),
        "positive_windows": sum(metrics.net_usd > 0.0 for metrics in windows),
        "negative_windows": sum(metrics.net_usd < 0.0 for metrics in windows),
        "worst_window_net_usd": core._fmt(min(metrics.net_usd for metrics in windows)),
        "eligible": eligible,
        "rank": "",
    }


def _rank_key(row: dict[str, object]) -> tuple[float, ...]:
    minimum_period_pf = min(
        float(row["train_profit_factor"]),
        float(row["validation_profit_factor"]),
        float(row["later_profit_factor"]),
    )
    return (
        -min(minimum_period_pf, 4.0),
        -int(row["positive_windows"]),
        -float(row["worst_window_net_usd"]) / int(row["total_units"]),
        -min(float(row["profit_factor"]), 4.0),
        -float(row["win_rate"]),
        -float(row["net_to_drawdown"]),
        -float(row["trades_per_week"]),
    )


def _report_key(row: dict[str, object]) -> tuple[float, ...]:
    rank = row["rank"]
    return (
        0.0 if rank != "" else 1.0,
        float(rank) if rank != "" else 999999.0,
        -float(row["profit_factor"]),
        -float(row["net_usd"]),
    )


def _sizing_rows(
    outcomes: list[ManagedOutcome],
    profile: ManagementProfile,
    trade_dates: list[date],
    *,
    seed: int,
) -> list[dict[str, object]]:
    rows = []
    max_multiplier = core.MAX_FUNDED_STARTING_MICROS // profile.total_units
    for multiplier in range(1, max_multiplier + 1):
        contracts = profile.total_units * multiplier
        cost = contracts * (
            core.MNQ_ROUND_TURN_FEE_USD
            + core.BASE_TOTAL_SLIPPAGE_TICKS * core.MNQ_TICK_VALUE_USD
        )
        stop_loss = (
            profile.initial_stop_points * core.MNQ_POINT_VALUE_USD * contracts + cost
        )
        maximum_target = (
            profile.first_target_points * profile.first_units
            + profile.runner_target_points * profile.runner_units
        ) * core.MNQ_POINT_VALUE_USD * multiplier - cost
        metrics = _metrics(outcomes, multiplier=multiplier)
        historical = _historical_attempts(
            outcomes,
            trade_dates,
            multiplier=multiplier,
        )
        monte_carlo = _monte_carlo_attempts(
            outcomes,
            trade_dates,
            multiplier=multiplier,
            seed=seed + multiplier,
        )
        funded = _historical_attempts(
            outcomes,
            trade_dates,
            multiplier=multiplier,
            profit_target_usd=core.FUNDED_LOCK_TARGET_USD,
            consistency_fraction=1.0,
        )
        eligible = (
            stop_loss <= core.INTERNAL_MAX_STOP_LOSS_USD
            and maximum_target <= core.INTERNAL_MAX_TARGET_PROFIT_USD
            and metrics.max_drawdown_usd > -1500.0
            and historical.pass_rate >= 0.25
            and monte_carlo.pass_rate >= 0.25
            and monte_carlo.fail_rate <= 0.20
        )
        rows.append(
            {
                "multiplier": multiplier,
                "contracts": contracts,
                "stop_loss_usd": core._fmt(-stop_loss),
                "maximum_target_usd": core._fmt(maximum_target),
                "net_usd": core._fmt(metrics.net_usd),
                "max_drawdown_usd": core._fmt(metrics.max_drawdown_usd),
                "historical_pass_rate": core._fmt(historical.pass_rate),
                "historical_fail_rate": core._fmt(historical.fail_rate),
                "historical_timeout_rate": core._fmt(historical.timeout_rate),
                "historical_median_days": core._fmt(
                    historical.median_calendar_days_to_pass,
                ),
                "historical_median_trade_days": core._fmt(
                    historical.median_trade_days_to_pass,
                ),
                "monte_carlo_pass_rate": core._fmt(monte_carlo.pass_rate),
                "monte_carlo_fail_rate": core._fmt(monte_carlo.fail_rate),
                "monte_carlo_timeout_rate": core._fmt(monte_carlo.timeout_rate),
                "funded_lock_rate": core._fmt(funded.pass_rate),
                "funded_fail_rate": core._fmt(funded.fail_rate),
                "eligible": eligible,
            },
        )
    return rows


def _historical_attempts(
    outcomes: list[ManagedOutcome],
    trade_dates: list[date],
    *,
    multiplier: int,
    profit_target_usd: float = core.TRADEIFY_PROFIT_TARGET_USD,
    consistency_fraction: float = core.TRADEIFY_CONSISTENCY_FRACTION,
    horizon_calendar_days: int = 90,
) -> core.AttemptSummary:
    value_by_date = {
        outcome.entry_time.date(): _net(
            outcome,
            multiplier,
            total_slippage_ticks=core.BASE_TOTAL_SLIPPAGE_TICKS,
        )
        for outcome in outcomes
    }
    results = []
    for start_index, start_date in enumerate(trade_dates):
        end_date = start_date + timedelta(days=horizon_calendar_days)
        values = [
            (trade_date, value_by_date.get(trade_date, 0.0))
            for trade_date in trade_dates[start_index:]
            if trade_date <= end_date
        ]
        results.append(
            core._simulate_attempt(
                values,
                profit_target_usd=profit_target_usd,
                consistency_fraction=consistency_fraction,
            ),
        )
    return core._summarize_attempts(results)


def _monte_carlo_attempts(
    outcomes: list[ManagedOutcome],
    trade_dates: list[date],
    *,
    multiplier: int,
    seed: int,
) -> core.AttemptSummary:
    value_by_date = {
        outcome.entry_time.date(): _net(
            outcome,
            multiplier,
            total_slippage_ticks=core.STRESS_TOTAL_SLIPPAGE_TICKS,
        )
        for outcome in outcomes
    }
    source = [value_by_date.get(trade_date, 0.0) for trade_date in trade_dates]
    blocks = [
        source[index : index + core.MONTE_CARLO_BLOCK_DAYS]
        for index in range(len(source) - core.MONTE_CARLO_BLOCK_DAYS + 1)
    ]
    rng = random.Random(seed)
    synthetic_start = date(2030, 1, 1)
    results = []
    for _ in range(core.MONTE_CARLO_RUNS):
        values: list[float] = []
        while len(values) < core.MONTE_CARLO_DAYS:
            values.extend(rng.choice(blocks))
        dated_values = [
            (synthetic_start + timedelta(days=index), value)
            for index, value in enumerate(values[: core.MONTE_CARLO_DAYS])
        ]
        results.append(core._simulate_attempt(dated_values))
    return core._summarize_attempts(results)


def _stress_summary(
    outcomes: list[ManagedOutcome],
    profile: ManagementProfile,
    sizing_rows: list[dict[str, object]],
    date_sets: dict[str, set[date]],
    *,
    seed: int,
) -> dict[str, object]:
    eligible = [row for row in sizing_rows if bool(row["eligible"])]
    if not eligible:
        return {"multiplier": 0}
    selected = max(
        eligible,
        key=lambda row: (
            float(row["historical_pass_rate"]),
            -float(row["monte_carlo_fail_rate"]),
            int(row["contracts"]),
        ),
    )
    multiplier = int(selected["multiplier"])
    base = _metrics(outcomes, multiplier=multiplier)
    stress = _metrics(
        outcomes,
        multiplier=multiplier,
        total_slippage_ticks=core.STRESS_TOTAL_SLIPPAGE_TICKS,
    )
    later_stress = _metrics(
        _outcomes_for_dates(outcomes, date_sets["later"]),
        multiplier=multiplier,
        total_slippage_ticks=core.STRESS_TOTAL_SLIPPAGE_TICKS,
    )
    values = [
        _net(
            outcome,
            multiplier,
            total_slippage_ticks=core.STRESS_TOTAL_SLIPPAGE_TICKS,
        )
        for outcome in outcomes
    ]
    rng = random.Random(seed + 7000)
    drawdowns = []
    for _ in range(core.MONTE_CARLO_RUNS):
        shuffled = list(values)
        rng.shuffle(shuffled)
        drawdowns.append(core._max_drawdown(shuffled))
    drawdowns.sort()
    yearly: dict[int, float] = defaultdict(float)
    for outcome in outcomes:
        yearly[outcome.entry_time.year] += _net(
            outcome,
            multiplier,
            total_slippage_ticks=core.STRESS_TOTAL_SLIPPAGE_TICKS,
        )
    return {
        "multiplier": multiplier,
        "contracts": profile.total_units * multiplier,
        "base": base,
        "stress": stress,
        "later_stress": later_stress,
        "median_drawdown": statistics.median(drawdowns),
        "p95_drawdown": core._percentile(drawdowns, 0.05),
        "p99_drawdown": core._percentile(drawdowns, 0.01),
        "all_years_positive": bool(yearly) and min(yearly.values()) > 0.0,
    }


def _write_report(
    path: str,
    *,
    bars: list[wave.Bar],
    trade_dates: list[date],
    train_dates: list[date],
    validation_dates: list[date],
    later_dates: list[date],
    rows: list[dict[str, object]],
    selected: dict[str, object] | None,
    selected_outcomes: list[ManagedOutcome],
    sizing_rows: list[dict[str, object]],
    stress: dict[str, object],
) -> None:
    lines = [
        "# Tradeify 50K Opening-Drive Management",
        "",
        "Status: second-stage research on the only fresh family that remained broadly positive across the initial chronological split. No NinjaTrader code is included.",
        "",
        "## Scope",
        "",
        f"- source: `{len(bars)}` MNQ three-minute bars, `{trade_dates[0]}` through `{trade_dates[-1]}`;",
        f"- periods: `{len(train_dates)}` training, `{len(validation_dates)}` validation, `{len(later_dates)}` later-validation dates;",
        "- the later period is no longer called untouched holdout because family selection used its first-pass result;",
        "- fixed entry neighborhood: aligned 15-minute opening drive, minimum 20-point drive, opening close-location 0.70, then a real pullback and resumption;",
        "- management search: partial target, protected runner, conservative stop-first bar handling, one trade per day;",
        f"- evaluated rows: `{len(rows)}`.",
        "",
        "## Top Robust Rows",
        "",
        "| Rank | Split | T1 / Stop / Runner / BE | Trades | /Wk | Net | PF | Win | T1 Hit | Runner Hit | DD | Period PFs | Windows | Worst Window |",
        "| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: |",
    ]
    eligible_rows = [row for row in rows if bool(row["eligible"])]
    for row in eligible_rows[:20]:
        lines.append(
            "| "
            f"{row['rank']} | `{row['first_units']}+{row['runner_units']}` | "
            f"`{row['first_target_points']} / {row['initial_stop_points']} / "
            f"{row['runner_target_points']} / {row['breakeven_offset_points']}` | "
            f"{row['trades']} | {row['trades_per_week']} | {row['net_usd']} | "
            f"{row['profit_factor']} | {float(row['win_rate']) * 100:.1f}% | "
            f"{float(row['first_target_rate']) * 100:.1f}% | "
            f"{float(row['runner_target_rate']) * 100:.1f}% | "
            f"{row['max_drawdown_usd']} | "
            f"`{row['train_profit_factor']} / {row['validation_profit_factor']} / "
            f"{row['later_profit_factor']}` | "
            f"{row['positive_windows']}/{int(row['positive_windows']) + int(row['negative_windows'])} | "
            f"{row['worst_window_net_usd']} |",
        )

    lines.extend(["", "## Frozen Result", ""])
    if selected is None:
        lines.append(
            "No scale-out profile cleared the stability gates. The opening-drive family remains rejected for a production bot."
        )
        Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    lines.extend(
        [
            f"Entry: `{selected['strategy_id']}`.",
            f"Management: `{selected['profile_id']}`.",
            "",
            "| Metric | Value |",
            "| --- | ---: |",
            f"| Trades | `{selected['trades']}` |",
            f"| Trades/week | `{selected['trades_per_week']}` |",
            f"| Net at base split | `${selected['net_usd']}` |",
            f"| PF | `{selected['profit_factor']}` |",
            f"| Win rate | `{float(selected['win_rate']) * 100:.1f}%` |",
            f"| First-target hit rate | `{float(selected['first_target_rate']) * 100:.1f}%` |",
            f"| Runner-target hit rate | `{float(selected['runner_target_rate']) * 100:.1f}%` |",
            f"| Drawdown | `${selected['max_drawdown_usd']}` |",
            f"| Average holding time | `{core._fmt(statistics.mean(outcome.holding_minutes for outcome in selected_outcomes))}` minutes |",
            "",
            "## Account Sizing",
            "",
            "| MNQ | Stop | Max Target | Net | DD | Hist Pass | Hist Fail | Median Days | MC Pass | MC Fail | Funded Lock | Risk |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ],
    )
    for row in sizing_rows:
        lines.append(
            "| "
            f"{row['contracts']} | {row['stop_loss_usd']} | {row['maximum_target_usd']} | "
            f"{row['net_usd']} | {row['max_drawdown_usd']} | "
            f"{float(row['historical_pass_rate']) * 100:.1f}% | "
            f"{float(row['historical_fail_rate']) * 100:.1f}% | "
            f"{row['historical_median_days']} | "
            f"{float(row['monte_carlo_pass_rate']) * 100:.1f}% | "
            f"{float(row['monte_carlo_fail_rate']) * 100:.1f}% | "
            f"{float(row['funded_lock_rate']) * 100:.1f}% | "
            f"{'eligible' if row['eligible'] else 'reject'} |",
        )

    lines.extend(["", "## Decision", ""])
    multiplier = int(stress.get("multiplier", 0))
    if multiplier == 0:
        lines.append(
            "No size can both make reasonable evaluation progress and remain inside the internal risk gates. Do not build this as the production bot."
        )
    else:
        base = stress["base"]
        stressed = stress["stress"]
        later_stress = stress["later_stress"]
        assert isinstance(base, Metrics)
        assert isinstance(stressed, Metrics)
        assert isinstance(later_stress, Metrics)
        promoted = (
            stressed.profit_factor >= 1.45
            and stressed.win_rate >= 0.60
            and later_stress.net_usd > 0.0
            and later_stress.profit_factor >= 1.15
            and float(stress["p95_drawdown"]) > -core.TRADEIFY_MAX_DRAWDOWN_USD
            and bool(stress["all_years_positive"])
        )
        lines.extend(
            [
                f"Selected size: `{stress['contracts']} MNQ`.",
                "",
                "| Test | Net | PF | Win | DD |",
                "| --- | ---: | ---: | ---: | ---: |",
                f"| Base | {core._fmt(base.net_usd)} | {core._fmt(base.profit_factor)} | {base.win_rate * 100:.1f}% | {core._fmt(base.max_drawdown_usd)} |",
                f"| Six-tick stress | {core._fmt(stressed.net_usd)} | {core._fmt(stressed.profit_factor)} | {stressed.win_rate * 100:.1f}% | {core._fmt(stressed.max_drawdown_usd)} |",
                f"| Later-period stress | {core._fmt(later_stress.net_usd)} | {core._fmt(later_stress.profit_factor)} | {later_stress.win_rate * 100:.1f}% | {core._fmt(later_stress.max_drawdown_usd)} |",
                f"| Shuffled median DD | {core._fmt(float(stress['median_drawdown']))} |  |  |  |",
                f"| Shuffled P95 DD | {core._fmt(float(stress['p95_drawdown']))} |  |  |  |",
                f"| Shuffled P99 DD | {core._fmt(float(stress['p99_drawdown']))} |  |  |  |",
                "",
                f"Verdict: `{'NON_REJECTED_RESEARCH_CANDIDATE' if promoted else 'REJECT_OR_REFINE'}`.",
            ],
        )
        if promoted:
            lines.extend(
                [
                    "",
                    "This is the first non-rejected strategy candidate for the Tradeify/NinjaTrader direction. It remains strategy research only; NinjaTrader implementation waits for a Windows/NT environment and a fresh replay gate.",
                ],
            )
        else:
            lines.extend(
                [
                    "",
                    "The management idea improved the entry economics but did not clear every account-level gate. Do not implement it as the production bot.",
                ],
            )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _key(row: dict[str, object]) -> tuple[str, str]:
    return str(row["strategy_id"]), str(row["profile_id"])


def _outcomes_for_dates(
    outcomes: list[ManagedOutcome],
    dates: set[date],
) -> list[ManagedOutcome]:
    return [outcome for outcome in outcomes if outcome.entry_time.date() in dates]


def _net(
    outcome: ManagedOutcome,
    multiplier: int,
    *,
    total_slippage_ticks: int,
) -> float:
    gross = outcome.gross_point_contracts * core.MNQ_POINT_VALUE_USD * multiplier
    contracts = outcome.contracts * multiplier
    cost = contracts * (
        core.MNQ_ROUND_TURN_FEE_USD + total_slippage_ticks * core.MNQ_TICK_VALUE_USD
    )
    return gross - cost


def _write_csv(path: str, rows: list[dict[str, object]]) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_HEADER)
        writer.writeheader()
        writer.writerows(rows)


def _write_audit(
    path: str,
    outcomes: list[ManagedOutcome],
    profile: ManagementProfile,
) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUDIT_HEADER)
        writer.writeheader()
        for outcome in outcomes:
            writer.writerow(
                {
                    "schema_version": 1,
                    "strategy_id": outcome.strategy_id,
                    "profile_id": profile.profile_id,
                    "direction": outcome.direction,
                    "entry_time": outcome.entry_time.isoformat(sep=" "),
                    "exit_time": outcome.exit_time.isoformat(sep=" "),
                    "entry_price": core._fmt(outcome.entry_price),
                    "first_exit_price": core._fmt(outcome.first_exit_price),
                    "runner_exit_price": core._fmt(outcome.runner_exit_price),
                    "initial_stop_price": core._fmt(outcome.initial_stop_price),
                    "first_target_price": core._fmt(outcome.first_target_price),
                    "runner_target_price": core._fmt(outcome.runner_target_price),
                    "exit_reason": outcome.exit_reason,
                    "first_target_hit": outcome.first_target_hit,
                    "runner_target_hit": outcome.runner_target_hit,
                    "gross_point_contracts": core._fmt(outcome.gross_point_contracts),
                    "base_net_usd": core._fmt(_net(outcome, 1, total_slippage_ticks=2)),
                    "holding_minutes": core._fmt(outcome.holding_minutes),
                    "notes": outcome.notes,
                },
            )


if __name__ == "__main__":
    raise SystemExit(main())
