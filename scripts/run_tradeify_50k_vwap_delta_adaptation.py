#!/usr/bin/env python3
"""Adapt the proven MNQ VWAP/delta signal to Tradeify 50K Select."""

from __future__ import annotations

import argparse
import csv
import random
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_mnq_eval_live_final_validation as legacy  # noqa: E402
import run_mnq_eval_pass_wave_rider as wave  # noqa: E402
import run_tradeify_50k_mnq_strategy_research as account  # noqa: E402


DEFAULT_OUTPUT = "reports/tradeify-50k-vwap-delta-adaptation-sweep.csv"
DEFAULT_REPORT = "reports/tradeify-50k-vwap-delta-adaptation.md"
DEFAULT_AUDIT = "reports/tradeify-50k-vwap-delta-adaptation-trade-audit.csv"
INTERNAL_MAX_TRADE_LOSS_USD = 600.0


@dataclass(frozen=True)
class Metrics:
    trades: int
    net_usd: float
    average_trade_usd: float
    profit_factor: float
    win_rate: float
    first_target_rate: float
    runner_target_rate: float
    stop_rate: float
    max_drawdown_usd: float
    net_to_drawdown: float
    worst_day_usd: float
    max_loss_streak: int
    average_holding_minutes: float


CSV_HEADER = [
    "schema_version",
    "profile_id",
    "first_leg_quantity",
    "runner_quantity",
    "total_quantity",
    "first_target_points",
    "stop_points",
    "runner_target_points",
    "runner_stop_mode",
    "nominal_stop_loss_usd",
    "maximum_target_profit_usd",
    "trades",
    "trades_per_week",
    "net_usd",
    "average_trade_usd",
    "profit_factor",
    "win_rate",
    "first_target_rate",
    "runner_target_rate",
    "stop_rate",
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
    "pass_90_rate",
    "fail_90_rate",
    "median_90_calendar_days",
    "pass_180_rate",
    "fail_180_rate",
    "median_180_calendar_days",
    "robust_eligible",
    "account_eligible",
    "rank",
]


AUDIT_HEADER = [
    "schema_version",
    "profile_id",
    "direction",
    "entry_time",
    "exit_time",
    "entry_price",
    "leg1_exit_price",
    "runner_exit_price",
    "stop_price",
    "first_target_price",
    "runner_target_price",
    "exit_reason",
    "first_target_hit",
    "gross_point_contracts",
    "base_net_usd",
    "stress_net_usd",
    "holding_minutes",
    "notes",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Adapt the MNQ VWAP/delta signal to Tradeify 50K Select.",
    )
    parser.add_argument("input", nargs="?", default=wave.DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT)
    parser.add_argument("--audit-output", default=DEFAULT_AUDIT)
    parser.add_argument("--seed", type=int, default=20260805)
    args = parser.parse_args()

    bars = wave._load_feature_bars(args.input)
    bars_by_date = wave._bars_by_date(bars)
    rows_by_index = wave._rows_by_global_index(bars_by_date)
    trade_dates = sorted(bars_by_date)
    train_dates, validation_dates, later_dates = account._split_dates(trade_dates)
    date_sets = {
        "train": set(train_dates),
        "validation": set(validation_dates),
        "later": set(later_dates),
    }
    sample_weeks = max((trade_dates[-1] - trade_dates[0]).days / 7.0, 1.0)
    entry_spec = legacy._live_spec()
    raw_signals = legacy._signals_for_spec(entry_spec, bars_by_date, symbol="MNQ")
    specs = _management_specs()
    print(
        f"loaded {len(raw_signals)} frozen VWAP/delta signals and "
        f"{len(specs)} management profiles",
        flush=True,
    )

    rows: list[dict[str, object]] = []
    outcomes_by_id: dict[str, list[legacy.ScaledOutcome]] = {}
    spec_by_id = {spec.strategy_id: spec for spec in specs}
    for spec in specs:
        outcomes = legacy._evaluate_signals(
            spec,
            raw_signals,
            bars_by_date,
            rows_by_index,
            slippage_ticks=0.0,
            live_sequenced=True,
        )
        full = _metrics(outcomes, spec)
        periods = {
            label: _metrics(_outcomes_for_dates(outcomes, dates), spec)
            for label, dates in date_sets.items()
        }
        windows = _window_metrics(outcomes, spec, trade_dates, window_count=6)
        nominal_stop = _nominal_stop_loss(spec)
        maximum_target = _maximum_target_profit(spec)
        robust = _robust_eligible(
            full,
            periods,
            windows,
            nominal_stop=nominal_stop,
            maximum_target=maximum_target,
        )
        pass_90 = _historical_attempts(
            outcomes,
            spec,
            trade_dates,
            horizon_calendar_days=90,
        )
        pass_180 = _historical_attempts(
            outcomes,
            spec,
            trade_dates,
            horizon_calendar_days=180,
        )
        account_eligible = (
            robust and pass_180.pass_rate >= 0.25 and pass_180.fail_rate <= 0.20
        )
        row = _row(
            spec,
            full,
            periods,
            windows,
            pass_90,
            pass_180,
            nominal_stop=nominal_stop,
            maximum_target=maximum_target,
            sample_weeks=sample_weeks,
            robust=robust,
            account_eligible=account_eligible,
        )
        rows.append(row)
        outcomes_by_id[spec.strategy_id] = outcomes

    ranked = sorted(
        (row for row in rows if bool(row["account_eligible"])),
        key=_rank_key,
    )
    ranks = {str(row["profile_id"]): rank for rank, row in enumerate(ranked, start=1)}
    for row in rows:
        row["rank"] = ranks.get(str(row["profile_id"]), "")
    rows.sort(key=_report_key)
    _write_csv(args.output, rows)

    selected = ranked[0] if ranked else None
    stress: dict[str, object] = {}
    selected_outcomes: list[legacy.ScaledOutcome] = []
    if selected is not None:
        selected_id = str(selected["profile_id"])
        selected_spec = spec_by_id[selected_id]
        selected_outcomes = outcomes_by_id[selected_id]
        stress = _stress_summary(
            selected_outcomes,
            selected_spec,
            trade_dates,
            date_sets,
            seed=args.seed,
        )
        _write_audit(args.audit_output, selected_outcomes, selected_spec)

    _write_report(
        args.report_output,
        bars=bars,
        raw_signals=raw_signals,
        trade_dates=trade_dates,
        train_dates=train_dates,
        validation_dates=validation_dates,
        later_dates=later_dates,
        rows=rows,
        selected=selected,
        stress=stress,
    )
    if selected is None:
        print(f"wrote {len(rows)} rows; no Tradeify-eligible profile", flush=True)
    else:
        print(
            f"wrote {len(rows)} rows; selected={selected['profile_id']} "
            f"pf={selected['profit_factor']} win={selected['win_rate']} "
            f"pass180={selected['pass_180_rate']}",
            flush=True,
        )
    return 0


def _management_specs() -> list[legacy.MnqEvalSpec]:
    specs = []
    for first_quantity, runner_quantity in (
        (1, 1),
        (2, 1),
        (3, 1),
        (3, 2),
        (4, 2),
        (5, 1),
        (6, 2),
    ):
        for first_target in (20.0, 25.0, 30.0):
            for stop_points in (60.0, 80.0, 100.0, 120.0, 140.0):
                for runner_target in (40.0, 60.0, 80.0, 100.0, 120.0):
                    if runner_target <= first_target:
                        continue
                    for runner_stop_mode in ("initial", "breakeven"):
                        profile_id = (
                            "tradeify_vwap_delta:"
                            f"split{first_quantity}-{runner_quantity}:"
                            f"t1{first_target:g}:s{stop_points:g}:"
                            f"runner{runner_target:g}:{runner_stop_mode}"
                        )
                        specs.append(
                            legacy.MnqEvalSpec(
                                strategy_id=profile_id,
                                label="Tradeify 50K adaptation",
                                vwap_threshold=80.0,
                                delta_threshold=400.0,
                                close_location_threshold=0.4,
                                spacing_seconds=900,
                                skip_friday=True,
                                skip_11_hour=True,
                                skip_15_hour=True,
                                first_target_points=first_target,
                                stop_points=stop_points,
                                runner_target_points=runner_target,
                                runner_stop_mode=runner_stop_mode,
                                first_leg_quantity=first_quantity,
                                runner_quantity=runner_quantity,
                            ),
                        )
    return specs


def _metrics(
    outcomes: list[legacy.ScaledOutcome],
    spec: legacy.MnqEvalSpec,
    *,
    total_slippage_ticks: int = account.BASE_TOTAL_SLIPPAGE_TICKS,
) -> Metrics:
    values = [
        _net(outcome, spec, total_slippage_ticks=total_slippage_ticks)
        for outcome in outcomes
    ]
    positives = [value for value in values if value > 0.0]
    negatives = [value for value in values if value < 0.0]
    daily: dict[date, float] = defaultdict(float)
    for outcome, value in zip(outcomes, values, strict=True):
        daily[outcome.entry_time.date()] += value
    net = sum(values)
    drawdown = account._max_drawdown(values)
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
            sum(outcome.exit_reason == "runner_target_hit" for outcome in outcomes)
            / len(outcomes)
            if outcomes
            else 0.0
        ),
        stop_rate=(
            sum("stop_hit" in outcome.exit_reason for outcome in outcomes)
            / len(outcomes)
            if outcomes
            else 0.0
        ),
        max_drawdown_usd=drawdown,
        net_to_drawdown=net / abs(drawdown) if drawdown < 0.0 else 999.0,
        worst_day_usd=min(daily.values()) if daily else 0.0,
        max_loss_streak=account._max_loss_streak(values),
        average_holding_minutes=(
            statistics.mean(outcome.holding_minutes for outcome in outcomes)
            if outcomes
            else 0.0
        ),
    )


def _window_metrics(
    outcomes: list[legacy.ScaledOutcome],
    spec: legacy.MnqEvalSpec,
    trade_dates: list[date],
    *,
    window_count: int,
) -> list[Metrics]:
    windows = []
    for index in range(window_count):
        start = round(index * len(trade_dates) / window_count)
        end = round((index + 1) * len(trade_dates) / window_count)
        dates = set(trade_dates[start:end])
        windows.append(_metrics(_outcomes_for_dates(outcomes, dates), spec))
    return windows


def _robust_eligible(
    full: Metrics,
    periods: dict[str, Metrics],
    windows: list[Metrics],
    *,
    nominal_stop: float,
    maximum_target: float,
) -> bool:
    return (
        full.trades >= 120
        and full.net_usd > 0.0
        and full.profit_factor >= 1.60
        and full.win_rate >= 0.65
        and full.max_drawdown_usd > -1800.0
        and nominal_stop <= INTERNAL_MAX_TRADE_LOSS_USD
        and maximum_target <= account.INTERNAL_MAX_TARGET_PROFIT_USD
        and all(metrics.trades >= 25 for metrics in periods.values())
        and all(metrics.net_usd > 0.0 for metrics in periods.values())
        and all(metrics.profit_factor >= 1.20 for metrics in periods.values())
        and sum(metrics.net_usd > 0.0 for metrics in windows) >= 5
        and min(metrics.net_usd for metrics in windows) > -700.0
    )


def _row(
    spec: legacy.MnqEvalSpec,
    full: Metrics,
    periods: dict[str, Metrics],
    windows: list[Metrics],
    pass_90: account.AttemptSummary,
    pass_180: account.AttemptSummary,
    *,
    nominal_stop: float,
    maximum_target: float,
    sample_weeks: float,
    robust: bool,
    account_eligible: bool,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "profile_id": spec.strategy_id,
        "first_leg_quantity": spec.first_leg_quantity,
        "runner_quantity": spec.runner_quantity,
        "total_quantity": spec.first_leg_quantity + spec.runner_quantity,
        "first_target_points": account._fmt(spec.first_target_points),
        "stop_points": account._fmt(spec.stop_points),
        "runner_target_points": account._fmt(spec.runner_target_points),
        "runner_stop_mode": spec.runner_stop_mode,
        "nominal_stop_loss_usd": account._fmt(-nominal_stop),
        "maximum_target_profit_usd": account._fmt(maximum_target),
        "trades": full.trades,
        "trades_per_week": account._fmt(full.trades / sample_weeks),
        "net_usd": account._fmt(full.net_usd),
        "average_trade_usd": account._fmt(full.average_trade_usd),
        "profit_factor": account._fmt(full.profit_factor),
        "win_rate": account._fmt(full.win_rate),
        "first_target_rate": account._fmt(full.first_target_rate),
        "runner_target_rate": account._fmt(full.runner_target_rate),
        "stop_rate": account._fmt(full.stop_rate),
        "max_drawdown_usd": account._fmt(full.max_drawdown_usd),
        "net_to_drawdown": account._fmt(full.net_to_drawdown),
        "train_net_usd": account._fmt(periods["train"].net_usd),
        "train_profit_factor": account._fmt(periods["train"].profit_factor),
        "validation_net_usd": account._fmt(periods["validation"].net_usd),
        "validation_profit_factor": account._fmt(periods["validation"].profit_factor),
        "later_net_usd": account._fmt(periods["later"].net_usd),
        "later_profit_factor": account._fmt(periods["later"].profit_factor),
        "positive_windows": sum(metrics.net_usd > 0.0 for metrics in windows),
        "negative_windows": sum(metrics.net_usd < 0.0 for metrics in windows),
        "worst_window_net_usd": account._fmt(
            min(metrics.net_usd for metrics in windows)
        ),
        "pass_90_rate": account._fmt(pass_90.pass_rate),
        "fail_90_rate": account._fmt(pass_90.fail_rate),
        "median_90_calendar_days": account._fmt(pass_90.median_calendar_days_to_pass),
        "pass_180_rate": account._fmt(pass_180.pass_rate),
        "fail_180_rate": account._fmt(pass_180.fail_rate),
        "median_180_calendar_days": account._fmt(pass_180.median_calendar_days_to_pass),
        "robust_eligible": robust,
        "account_eligible": account_eligible,
        "rank": "",
    }


def _historical_attempts(
    outcomes: list[legacy.ScaledOutcome],
    spec: legacy.MnqEvalSpec,
    trade_dates: list[date],
    *,
    horizon_calendar_days: int,
) -> account.AttemptSummary:
    value_by_date: dict[date, float] = defaultdict(float)
    for outcome in outcomes:
        value_by_date[outcome.entry_time.date()] += _net(
            outcome,
            spec,
            total_slippage_ticks=account.BASE_TOTAL_SLIPPAGE_TICKS,
        )
    results = []
    for start_index, start_date in enumerate(trade_dates):
        end_date = start_date.fromordinal(
            start_date.toordinal() + horizon_calendar_days
        )
        values = [
            (trade_date, value_by_date.get(trade_date, 0.0))
            for trade_date in trade_dates[start_index:]
            if trade_date <= end_date
        ]
        results.append(account._simulate_attempt(values))
    return account._summarize_attempts(results)


def _stress_summary(
    outcomes: list[legacy.ScaledOutcome],
    spec: legacy.MnqEvalSpec,
    trade_dates: list[date],
    date_sets: dict[str, set[date]],
    *,
    seed: int,
) -> dict[str, object]:
    base = _metrics(outcomes, spec)
    stress = _metrics(
        outcomes,
        spec,
        total_slippage_ticks=account.STRESS_TOTAL_SLIPPAGE_TICKS,
    )
    later_stress = _metrics(
        _outcomes_for_dates(outcomes, date_sets["later"]),
        spec,
        total_slippage_ticks=account.STRESS_TOTAL_SLIPPAGE_TICKS,
    )
    value_by_date: dict[date, float] = defaultdict(float)
    for outcome in outcomes:
        value_by_date[outcome.entry_time.date()] += _net(
            outcome,
            spec,
            total_slippage_ticks=account.STRESS_TOTAL_SLIPPAGE_TICKS,
        )
    source = [value_by_date.get(trade_date, 0.0) for trade_date in trade_dates]
    blocks = [
        source[index : index + account.MONTE_CARLO_BLOCK_DAYS]
        for index in range(len(source) - account.MONTE_CARLO_BLOCK_DAYS + 1)
    ]
    rng = random.Random(seed)
    synthetic_start = date(2030, 1, 1)
    attempts = []
    for _ in range(account.MONTE_CARLO_RUNS):
        values: list[float] = []
        while len(values) < 130:
            values.extend(rng.choice(blocks))
        dated = [
            (synthetic_start.fromordinal(synthetic_start.toordinal() + index), value)
            for index, value in enumerate(values[:130])
        ]
        attempts.append(account._simulate_attempt(dated))
    monte_carlo = account._summarize_attempts(attempts)

    trade_values = [
        _net(
            outcome,
            spec,
            total_slippage_ticks=account.STRESS_TOTAL_SLIPPAGE_TICKS,
        )
        for outcome in outcomes
    ]
    drawdowns = []
    for _ in range(account.MONTE_CARLO_RUNS):
        shuffled = list(trade_values)
        rng.shuffle(shuffled)
        drawdowns.append(account._max_drawdown(shuffled))
    drawdowns.sort()
    funded = _funded_lock_attempts(outcomes, spec, trade_dates)
    return {
        "base": base,
        "stress": stress,
        "later_stress": later_stress,
        "monte_carlo": monte_carlo,
        "median_drawdown": statistics.median(drawdowns),
        "p95_drawdown": account._percentile(drawdowns, 0.05),
        "p99_drawdown": account._percentile(drawdowns, 0.01),
        "funded": funded,
    }


def _funded_lock_attempts(
    outcomes: list[legacy.ScaledOutcome],
    spec: legacy.MnqEvalSpec,
    trade_dates: list[date],
) -> account.AttemptSummary:
    value_by_date: dict[date, float] = defaultdict(float)
    for outcome in outcomes:
        value_by_date[outcome.entry_time.date()] += _net(
            outcome,
            spec,
            total_slippage_ticks=account.BASE_TOTAL_SLIPPAGE_TICKS,
        )
    results = []
    for start_index, start_date in enumerate(trade_dates):
        end_date = start_date.fromordinal(start_date.toordinal() + 180)
        values = [
            (trade_date, value_by_date.get(trade_date, 0.0))
            for trade_date in trade_dates[start_index:]
            if trade_date <= end_date
        ]
        results.append(
            account._simulate_attempt(
                values,
                profit_target_usd=account.FUNDED_LOCK_TARGET_USD,
                consistency_fraction=1.0,
            ),
        )
    return account._summarize_attempts(results)


def _rank_key(row: dict[str, object]) -> tuple[float, ...]:
    minimum_period_pf = min(
        float(row["train_profit_factor"]),
        float(row["validation_profit_factor"]),
        float(row["later_profit_factor"]),
    )
    return (
        -float(row["pass_90_rate"]),
        float(row["fail_90_rate"]),
        -float(row["pass_180_rate"]),
        float(row["fail_180_rate"]),
        -min(minimum_period_pf, 4.0),
        -min(float(row["profit_factor"]), 4.0),
        -float(row["win_rate"]),
        -float(row["net_to_drawdown"]),
    )


def _report_key(row: dict[str, object]) -> tuple[float, ...]:
    rank = row["rank"]
    return (
        0.0 if rank != "" else 1.0,
        float(rank) if rank != "" else 999999.0,
        0.0 if bool(row["robust_eligible"]) else 1.0,
        -float(row["profit_factor"]),
        -float(row["net_usd"]),
    )


def _nominal_stop_loss(spec: legacy.MnqEvalSpec) -> float:
    quantity = spec.first_leg_quantity + spec.runner_quantity
    return spec.stop_points * account.MNQ_POINT_VALUE_USD * quantity + _cost(
        quantity, account.BASE_TOTAL_SLIPPAGE_TICKS
    )


def _maximum_target_profit(spec: legacy.MnqEvalSpec) -> float:
    quantity = spec.first_leg_quantity + spec.runner_quantity
    gross = account.MNQ_POINT_VALUE_USD * (
        spec.first_target_points * spec.first_leg_quantity
        + spec.runner_target_points * spec.runner_quantity
    )
    return gross - _cost(quantity, account.BASE_TOTAL_SLIPPAGE_TICKS)


def _net(
    outcome: legacy.ScaledOutcome,
    spec: legacy.MnqEvalSpec,
    *,
    total_slippage_ticks: int,
) -> float:
    quantity = spec.first_leg_quantity + spec.runner_quantity
    gross = outcome.gross_points * account.MNQ_POINT_VALUE_USD
    return gross - _cost(quantity, total_slippage_ticks)


def _cost(quantity: int, total_slippage_ticks: int) -> float:
    return quantity * (
        account.MNQ_ROUND_TURN_FEE_USD
        + total_slippage_ticks * account.MNQ_TICK_VALUE_USD
    )


def _outcomes_for_dates(
    outcomes: list[legacy.ScaledOutcome],
    dates: set[date],
) -> list[legacy.ScaledOutcome]:
    return [outcome for outcome in outcomes if outcome.entry_time.date() in dates]


def _write_report(
    path: str,
    *,
    bars: list[wave.Bar],
    raw_signals: list[wave.Signal],
    trade_dates: list[date],
    train_dates: list[date],
    validation_dates: list[date],
    later_dates: list[date],
    rows: list[dict[str, object]],
    selected: dict[str, object] | None,
    stress: dict[str, object],
) -> None:
    robust_count = sum(bool(row["robust_eligible"]) for row in rows)
    account_count = sum(bool(row["account_eligible"]) for row in rows)
    lines = [
        "# Tradeify 50K VWAP/Delta Adaptation",
        "",
        "Status: Tradeify-specific strategy research using the strongest existing MNQ entry. No NinjaTrader code is included.",
        "",
        "## Why This Seed",
        "",
        "The fresh opening-drive, gap-fade, prior-session sweep, and VWAP trend-pullback families did not produce a production candidate. The frozen MNQ VWAP/delta exhaustion entry remains the only local signal with the requested high-win/high-PF shape, so this pass changes management and sizing without re-optimizing the entry.",
        "",
        "## Scope",
        "",
        f"- source: `{len(bars)}` MNQ three-minute bars, `{trade_dates[0]}` through `{trade_dates[-1]}`;",
        f"- frozen raw entry signals: `{len(raw_signals)}`;",
        f"- chronological periods: `{len(train_dates)} / {len(validation_dates)} / {len(later_dates)}` dates;",
        "- entry: 80-point VWAP extension, delta 400, close-location 0.4, no Friday, no 11:00 or 15:00 entries, 900-second raw spacing;",
        "- management grid: `2-8 MNQ`, first target `20/25/30`, stop `60-140`, runner `40-120`, initial or break-even runner stop;",
        "- Tradeify cost: `$1.82` round trip plus two total slippage ticks per MNQ;",
        "- same-bar ambiguity: stop first; live sequencing blocks overlapping trades;",
        f"- profiles evaluated: `{len(rows)}`; robust: `{robust_count}`; account-eligible: `{account_count}`.",
        "",
        "## Top Account Rows",
        "",
        "| Rank | Split | T1 / Stop / Runner / Mode | Trades | /Wk | Net | PF | Win | DD | Period PFs | 90d Pass/Fail | 180d Pass/Fail |",
        "| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |",
    ]
    account_rows = [row for row in rows if bool(row["account_eligible"])]
    for row in account_rows[:20]:
        lines.append(
            "| "
            f"{row['rank']} | `{row['first_leg_quantity']}+{row['runner_quantity']}` | "
            f"`{row['first_target_points']} / {row['stop_points']} / "
            f"{row['runner_target_points']} / {row['runner_stop_mode']}` | "
            f"{row['trades']} | {row['trades_per_week']} | {row['net_usd']} | "
            f"{row['profit_factor']} | {float(row['win_rate']) * 100:.1f}% | "
            f"{row['max_drawdown_usd']} | "
            f"`{row['train_profit_factor']} / {row['validation_profit_factor']} / "
            f"{row['later_profit_factor']}` | "
            f"{float(row['pass_90_rate']) * 100:.1f}% / {float(row['fail_90_rate']) * 100:.1f}% | "
            f"{float(row['pass_180_rate']) * 100:.1f}% / {float(row['fail_180_rate']) * 100:.1f}% |",
        )

    lines.extend(["", "## Decision", ""])
    if selected is None:
        lines.extend(
            [
                "No profile combined robust profitability with acceptable Tradeify pass/fail geometry. The current dataset does not support building the requested production bot yet.",
                "",
                "The next research representation should be MNQ/NQ tick or range bars with actual NQ order flow, not another parameter sweep on the same three-minute export.",
            ],
        )
        Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    base = stress["base"]
    stressed = stress["stress"]
    later_stress = stress["later_stress"]
    monte_carlo = stress["monte_carlo"]
    funded = stress["funded"]
    assert isinstance(base, Metrics)
    assert isinstance(stressed, Metrics)
    assert isinstance(later_stress, Metrics)
    assert isinstance(monte_carlo, account.AttemptSummary)
    assert isinstance(funded, account.AttemptSummary)
    promoted = (
        stressed.profit_factor >= 1.50
        and stressed.win_rate >= 0.65
        and later_stress.net_usd > 0.0
        and later_stress.profit_factor >= 1.20
        and monte_carlo.fail_rate <= 0.20
        and float(stress["p95_drawdown"]) > -account.TRADEIFY_MAX_DRAWDOWN_USD
    )
    lines.extend(
        [
            f"Frozen strategy profile: `{selected['profile_id']}`.",
            "",
            "| Metric | Base | Six-tick stress | Later stress |",
            "| --- | ---: | ---: | ---: |",
            f"| Trades | {base.trades} | {stressed.trades} | {later_stress.trades} |",
            f"| Net | {account._fmt(base.net_usd)} | {account._fmt(stressed.net_usd)} | {account._fmt(later_stress.net_usd)} |",
            f"| PF | {account._fmt(base.profit_factor)} | {account._fmt(stressed.profit_factor)} | {account._fmt(later_stress.profit_factor)} |",
            f"| Win rate | {base.win_rate * 100:.1f}% | {stressed.win_rate * 100:.1f}% | {later_stress.win_rate * 100:.1f}% |",
            f"| Drawdown | {account._fmt(base.max_drawdown_usd)} | {account._fmt(stressed.max_drawdown_usd)} | {account._fmt(later_stress.max_drawdown_usd)} |",
            "",
            f"- 130-trading-day block Monte Carlo: `{monte_carlo.pass_rate * 100:.1f}%` pass, `{monte_carlo.fail_rate * 100:.1f}%` fail;",
            f"- shuffled trade-order DD: median `${account._fmt(float(stress['median_drawdown']))}`, P95 `${account._fmt(float(stress['p95_drawdown']))}`, P99 `${account._fmt(float(stress['p99_drawdown']))}`;",
            f"- funded `$2100` drawdown-lock objective within 180 calendar days: `{funded.pass_rate * 100:.1f}%` pass, `{funded.fail_rate * 100:.1f}%` fail;",
            f"- verdict: `{'NON_REJECTED_STRATEGY_CANDIDATE' if promoted else 'REJECT_AFTER_STRESS'}`.",
        ],
    )
    if promoted:
        lines.extend(
            [
                "",
                "This is strategy-only approval for a future NinjaTrader prototype. It is not live authorization. The next gate is NinjaTrader historical fill parity and Market Replay on Windows.",
            ],
        )
    else:
        lines.extend(
            [
                "",
                "The profile passed the coarse account screen but failed final stress. Do not implement it as the production bot.",
            ],
        )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_csv(path: str, rows: list[dict[str, object]]) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_HEADER)
        writer.writeheader()
        writer.writerows(rows)


def _write_audit(
    path: str,
    outcomes: list[legacy.ScaledOutcome],
    spec: legacy.MnqEvalSpec,
) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUDIT_HEADER)
        writer.writeheader()
        for outcome in outcomes:
            writer.writerow(
                {
                    "schema_version": 1,
                    "profile_id": spec.strategy_id,
                    "direction": outcome.direction,
                    "entry_time": outcome.entry_time.isoformat(sep=" "),
                    "exit_time": outcome.exit_time.isoformat(sep=" "),
                    "entry_price": account._fmt(outcome.entry_price),
                    "leg1_exit_price": account._fmt(outcome.leg1_exit_price),
                    "runner_exit_price": account._fmt(outcome.runner_exit_price),
                    "stop_price": account._fmt(outcome.stop_price),
                    "first_target_price": account._fmt(outcome.first_target_price),
                    "runner_target_price": account._fmt(outcome.runner_target_price),
                    "exit_reason": outcome.exit_reason,
                    "first_target_hit": outcome.first_target_hit,
                    "gross_point_contracts": account._fmt(outcome.gross_points),
                    "base_net_usd": account._fmt(
                        _net(
                            outcome,
                            spec,
                            total_slippage_ticks=account.BASE_TOTAL_SLIPPAGE_TICKS,
                        ),
                    ),
                    "stress_net_usd": account._fmt(
                        _net(
                            outcome,
                            spec,
                            total_slippage_ticks=account.STRESS_TOTAL_SLIPPAGE_TICKS,
                        ),
                    ),
                    "holding_minutes": account._fmt(outcome.holding_minutes),
                    "notes": outcome.notes,
                },
            )


if __name__ == "__main__":
    raise SystemExit(main())
