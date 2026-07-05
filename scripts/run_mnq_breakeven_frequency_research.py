#!/usr/bin/env python3
"""Research frequent MNQ entries with target-one protection and runner breakeven."""

from __future__ import annotations

import argparse
import csv
import math
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import date, datetime, time
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_mnq_eval_pass_wave_rider as wave  # noqa: E402


DEFAULT_SWEEP_OUTPUT = "reports/mnq-breakeven-frequency-research.csv"
DEFAULT_TRADE_AUDIT_OUTPUT = "reports/mnq-breakeven-frequency-best-trade-audit.csv"
DEFAULT_REPORT_OUTPUT = "reports/mnq-breakeven-frequency-research.md"
ROUND_TURN_COST_PER_CONTRACT_USD = (
    2.0 * wave.COMMISSION_PER_SIDE_USD
    + wave.SLIPPAGE_TICKS_PER_CONTRACT * wave.TICK_VALUE_USD
)


@dataclass(frozen=True)
class ManagedRisk:
    quantity: int
    first_leg_quantity: int
    runner_quantity: int
    first_target_points: float
    initial_stop_points: float
    runner_target_points: float
    round_turn_cost_usd: float


@dataclass(frozen=True)
class ManagedOutcome:
    strategy_id: str
    direction: str
    entry_time: datetime
    exit_time: datetime
    entry_bar_index: int
    exit_bar_index: int
    entry_price: float
    first_target_price: float
    runner_target_price: float
    initial_stop_price: float
    first_target_hit: bool
    runner_exit_reason: str
    exit_reason: str
    holding_minutes: float
    first_leg_points: float
    runner_points: float
    gross_points_contracts: float
    net_usd: float
    notes: str


@dataclass(frozen=True)
class SampleInfo:
    trading_dates: tuple[date, ...]
    weeks: float
    latest_year: int


SWEEP_HEADER = [
    "schema_version",
    "strategy_id",
    "family",
    "quantity",
    "first_leg_quantity",
    "runner_quantity",
    "first_target_points",
    "initial_stop_points",
    "runner_target_points",
    "raw_signals",
    "evaluated_trades",
    "signal_days",
    "trades_per_week",
    "first_target_rate",
    "full_stop_rate",
    "runner_breakeven_rate",
    "runner_target_rate",
    "end_of_session_rate",
    "positive_trade_rate",
    "win_rate",
    "net_usd",
    "average_trade_usd",
    "profit_factor",
    "max_trade_sequence_drawdown_usd",
    "latest_year",
    "latest_year_trades",
    "latest_year_net_usd",
    "worst_quarter_net_usd",
    "worst_day_usd",
    "average_holding_minutes",
    "median_holding_minutes",
    "worst_trade_usd",
    "notes",
]

TRADE_AUDIT_HEADER = [
    "schema_version",
    "strategy_id",
    "quantity",
    "first_leg_quantity",
    "runner_quantity",
    "first_target_points",
    "initial_stop_points",
    "runner_target_points",
    "direction",
    "entry_time",
    "exit_time",
    "entry_bar_index",
    "exit_bar_index",
    "entry_price",
    "first_target_price",
    "runner_target_price",
    "initial_stop_price",
    "first_target_hit",
    "runner_exit_reason",
    "exit_reason",
    "holding_minutes",
    "first_leg_points",
    "runner_points",
    "gross_points_contracts",
    "net_usd",
    "notes",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Sweep MNQ strategies for frequent target-one reaches where the "
            "runner stop moves to breakeven after target one."
        ),
    )
    parser.add_argument("input", nargs="?", default=wave.DEFAULT_INPUT)
    parser.add_argument("--sweep-output", default=DEFAULT_SWEEP_OUTPUT)
    parser.add_argument("--trade-audit-output", default=DEFAULT_TRADE_AUDIT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--symbol", default="MNQU26-CME")
    parser.add_argument("--minimum-raw-signals", type=int, default=80)
    parser.add_argument("--minimum-trades", type=int, default=80)
    parser.add_argument(
        "--risk-grid",
        choices=("focused", "standard"),
        default="focused",
        help="Focused is the fast first pass; standard expands the exit grid.",
    )
    args = parser.parse_args()

    bars = wave._load_feature_bars(args.input)
    bars_by_date = wave._bars_by_date(bars)
    sample_info = _sample_info(bars)
    rows_by_index = wave._rows_by_global_index(bars_by_date)
    flatten_index_by_date = _flatten_index_by_date(bars_by_date)
    signals_by_strategy = _generate_signals_by_strategy(bars_by_date, symbol=args.symbol)
    path_profiles = _path_profiles(args.risk_grid)

    sweep_rows: list[dict[str, object]] = []
    best_row: dict[str, object] | None = None
    best_path_outcomes: list[ManagedOutcome] = []
    best_risk: ManagedRisk | None = None
    for strategy_id, signals in signals_by_strategy.items():
        if len(signals) < args.minimum_raw_signals:
            continue
        family = strategy_id.split(":", 1)[0]
        for path_risk in path_profiles:
            path_outcomes = _evaluate_signals(
                signals,
                bars_by_date,
                rows_by_index,
                flatten_index_by_date,
                path_risk,
            )
            if len(path_outcomes) < args.minimum_trades:
                continue
            for risk in _split_profiles(path_risk):
                row = _sweep_row(
                    strategy_id=strategy_id,
                    family=family,
                    raw_signal_count=len(signals),
                    outcomes=path_outcomes,
                    risk=risk,
                    sample_info=sample_info,
                )
                sweep_rows.append(row)
                if _is_better_row(row, best_row):
                    best_row = row
                    best_path_outcomes = path_outcomes
                    best_risk = risk

    sweep_rows.sort(key=_ranking_key)
    _write_csv(args.sweep_output, SWEEP_HEADER, sweep_rows)
    if best_row is not None and best_risk is not None:
        best_trades = _with_priced_outcomes(best_path_outcomes, best_risk)
        _write_trade_audit(args.trade_audit_output, best_trades, best_row)
    _write_report(args.report_output, bars, sweep_rows, best_row)

    best_summary = "none"
    if best_row is not None:
        best_summary = (
            f"{best_row['strategy_id']} "
            f"qty={best_row['quantity']} "
            f"t1={best_row['first_target_points']} "
            f"stop={best_row['initial_stop_points']} "
            f"runner={best_row['runner_target_points']} "
            f"target1={float(best_row['first_target_rate']) * 100:.1f}% "
            f"full_stop={float(best_row['full_stop_rate']) * 100:.1f}% "
            f"net=${best_row['net_usd']}"
        )
    print(
        f"wrote {len(sweep_rows)} MNQ breakeven-frequency rows to "
        f"{args.sweep_output}; best={best_summary}",
    )
    return 0


def _generate_signals_by_strategy(
    bars_by_date: dict[date, list[wave.Bar]],
    *,
    symbol: str,
) -> dict[str, list[wave.Signal]]:
    signals_by_strategy: dict[str, list[wave.Signal]] = {}
    for skip_friday in (False, True):
        for entry_end in (time(12, 30), time(14, 30)):
            for max_per_day in (1, 2):
                min_spacing_seconds = 30 * 60
                for lookback_bars in (5, 10, 20):
                    for buffer_points in (0.0, 2.5):
                        for delta_threshold in (0.0, 600.0):
                            for close_location_threshold in (0.45, 0.55):
                                strategy_id = (
                                    "lookback_be_frequency:"
                                    f"lb{lookback_bars}:buf{buffer_points:g}:"
                                    f"delta{delta_threshold:g}:"
                                    f"cl{close_location_threshold:g}:"
                                    f"end{wave._time_id(entry_end)}:"
                                    f"skipfri{int(skip_friday)}:"
                                    f"maxday{max_per_day}:space30"
                                )
                                signals = []
                                for rows in bars_by_date.values():
                                    signals.extend(
                                        _lookback_breakout_signals(
                                            rows,
                                            strategy_id=strategy_id,
                                            lookback_bars=lookback_bars,
                                            buffer_points=buffer_points,
                                            delta_threshold=delta_threshold,
                                            close_location_threshold=close_location_threshold,
                                            entry_end=entry_end,
                                            skip_friday=skip_friday,
                                            max_per_day=max_per_day,
                                            min_spacing_seconds=min_spacing_seconds,
                                            symbol=symbol,
                                        ),
                                    )
                                signals_by_strategy[strategy_id] = signals

                for stretch_points in (30.0, 60.0, 90.0):
                    for pullback_points in (5.0, 10.0, 20.0):
                        for delta_threshold in (0.0, 600.0):
                            for close_location_threshold in (0.45, 0.55):
                                strategy_id = (
                                    "vwap_pullback_be_frequency:"
                                    f"stretch{stretch_points:g}:"
                                    f"pb{pullback_points:g}:"
                                    f"delta{delta_threshold:g}:"
                                    f"cl{close_location_threshold:g}:"
                                    f"end{wave._time_id(entry_end)}:"
                                    f"skipfri{int(skip_friday)}:"
                                    f"maxday{max_per_day}:space30"
                                )
                                signals = []
                                for rows in bars_by_date.values():
                                    signals.extend(
                                        _vwap_pullback_signals(
                                            rows,
                                            strategy_id=strategy_id,
                                            stretch_points=stretch_points,
                                            pullback_points=pullback_points,
                                            delta_threshold=delta_threshold,
                                            close_location_threshold=close_location_threshold,
                                            entry_end=entry_end,
                                            skip_friday=skip_friday,
                                            max_per_day=max_per_day,
                                            min_spacing_seconds=min_spacing_seconds,
                                            symbol=symbol,
                                        ),
                                    )
                                signals_by_strategy[strategy_id] = signals
    return signals_by_strategy


def _lookback_breakout_signals(
    rows: list[wave.Bar],
    *,
    strategy_id: str,
    lookback_bars: int,
    buffer_points: float,
    delta_threshold: float,
    close_location_threshold: float,
    entry_end: time,
    skip_friday: bool,
    max_per_day: int,
    min_spacing_seconds: int,
    symbol: str,
) -> list[wave.Signal]:
    if wave._skip_day(rows, skip_friday=skip_friday):
        return []
    signals: list[wave.Signal] = []
    for index in range(lookback_bars, len(rows)):
        row = rows[index]
        if not wave._entry_time_allowed(row.timestamp.time(), entry_end):
            continue
        if not _spacing_allows(signals, row, max_per_day, min_spacing_seconds):
            continue
        lookback = rows[index - lookback_bars:index]
        previous_close = rows[index - 1].close
        lookback_high = max(previous.high for previous in lookback)
        lookback_low = min(previous.low for previous in lookback)
        high_break = lookback_high + buffer_points
        low_break = lookback_low - buffer_points
        if (
            previous_close <= high_break < row.close
            and row.close >= row.vwap
            and row.delta >= delta_threshold
            and row.close_location >= close_location_threshold
        ):
            signals.append(
                wave.Signal(
                    strategy_id,
                    "long",
                    row,
                    f"{symbol} frequent lookback high breakout",
                ),
            )
        elif (
            previous_close >= low_break > row.close
            and row.close <= row.vwap
            and row.delta <= -delta_threshold
            and row.close_location <= 1.0 - close_location_threshold
        ):
            signals.append(
                wave.Signal(
                    strategy_id,
                    "short",
                    row,
                    f"{symbol} frequent lookback low breakout",
                ),
            )
    return signals


def _vwap_pullback_signals(
    rows: list[wave.Bar],
    *,
    strategy_id: str,
    stretch_points: float,
    pullback_points: float,
    delta_threshold: float,
    close_location_threshold: float,
    entry_end: time,
    skip_friday: bool,
    max_per_day: int,
    min_spacing_seconds: int,
    symbol: str,
) -> list[wave.Signal]:
    if wave._skip_day(rows, skip_friday=skip_friday):
        return []
    signals: list[wave.Signal] = []
    stretched_high = False
    stretched_low = False
    for row in rows:
        row_time = row.timestamp.time()
        distance_from_vwap = row.close - row.vwap
        if distance_from_vwap >= stretch_points:
            stretched_high = True
        if distance_from_vwap <= -stretch_points:
            stretched_low = True
        if not wave._entry_time_allowed(row_time, entry_end):
            continue
        if not _spacing_allows(signals, row, max_per_day, min_spacing_seconds):
            continue
        if (
            stretched_high
            and row.low <= row.vwap + pullback_points
            and row.close > row.vwap + pullback_points
            and row.delta >= delta_threshold
            and row.close_location >= close_location_threshold
        ):
            signals.append(
                wave.Signal(
                    strategy_id,
                    "long",
                    row,
                    f"{symbol} frequent VWAP pullback continuation",
                ),
            )
            stretched_high = False
        elif (
            stretched_low
            and row.high >= row.vwap - pullback_points
            and row.close < row.vwap - pullback_points
            and row.delta <= -delta_threshold
            and row.close_location <= 1.0 - close_location_threshold
        ):
            signals.append(
                wave.Signal(
                    strategy_id,
                    "short",
                    row,
                    f"{symbol} frequent VWAP pullback continuation",
                ),
            )
            stretched_low = False
    return signals


def _spacing_allows(
    signals: list[wave.Signal],
    row: wave.Bar,
    max_per_day: int,
    min_spacing_seconds: int,
) -> bool:
    if len(signals) >= max_per_day:
        return False
    if not signals:
        return True
    elapsed = (row.timestamp - signals[-1].bar.timestamp).total_seconds()
    return elapsed >= min_spacing_seconds


def _path_profiles(grid: str) -> list[ManagedRisk]:
    if grid == "focused":
        first_targets = (10.0, 15.0, 20.0, 25.0)
        initial_stops = (10.0, 15.0, 20.0, 30.0, 40.0)
        runner_targets = (20.0, 40.0, 60.0, 80.0)
    else:
        first_targets = (10.0, 15.0, 20.0, 25.0)
        initial_stops = (30.0, 40.0, 60.0)
        runner_targets = (40.0, 60.0, 80.0)
    profiles = []
    for first_target_points in first_targets:
        for initial_stop_points in initial_stops:
            for runner_target_points in runner_targets:
                if runner_target_points <= first_target_points:
                    continue
                profiles.append(
                    ManagedRisk(
                        quantity=2,
                        first_leg_quantity=1,
                        runner_quantity=1,
                        first_target_points=first_target_points,
                        initial_stop_points=initial_stop_points,
                        runner_target_points=runner_target_points,
                        round_turn_cost_usd=2 * ROUND_TURN_COST_PER_CONTRACT_USD,
                    ),
                )
    return profiles


def _split_profiles(path_risk: ManagedRisk) -> list[ManagedRisk]:
    profiles = []
    for quantity, first_leg_quantity, runner_quantity in (
        (2, 1, 1),
        (3, 2, 1),
        (4, 3, 1),
        (4, 2, 2),
    ):
        profiles.append(
            ManagedRisk(
                quantity=quantity,
                first_leg_quantity=first_leg_quantity,
                runner_quantity=runner_quantity,
                first_target_points=path_risk.first_target_points,
                initial_stop_points=path_risk.initial_stop_points,
                runner_target_points=path_risk.runner_target_points,
                round_turn_cost_usd=quantity * ROUND_TURN_COST_PER_CONTRACT_USD,
            ),
        )
    return profiles


def _evaluate_signals(
    signals: list[wave.Signal],
    bars_by_date: dict[date, list[wave.Bar]],
    rows_by_index: dict[int, int],
    flatten_index_by_date: dict[date, int],
    risk: ManagedRisk,
) -> list[ManagedOutcome]:
    outcomes = []
    next_available_time = datetime.min
    for signal in sorted(signals, key=lambda value: value.bar.timestamp):
        if signal.bar.timestamp <= next_available_time:
            continue
        day_rows = bars_by_date[signal.bar.trade_date]
        local_index = rows_by_index[signal.bar.index]
        flatten_index = flatten_index_by_date[signal.bar.trade_date]
        following_rows = (
            day_rows[local_index + 1:flatten_index + 1]
            if local_index < flatten_index
            else []
        )
        outcome = _evaluate_signal(signal, following_rows, risk)
        outcomes.append(outcome)
        next_available_time = outcome.exit_time
    return outcomes


def _flatten_index_by_date(
    bars_by_date: dict[date, list[wave.Bar]],
) -> dict[date, int]:
    result = {}
    for trade_date, rows in bars_by_date.items():
        flatten_index = len(rows) - 1
        for local_index, row in enumerate(rows):
            if row.timestamp.time() > wave.FLATTEN_TIME:
                flatten_index = max(0, local_index - 1)
                break
        result[trade_date] = flatten_index
    return result


def _evaluate_signal(
    signal: wave.Signal,
    following_rows: list[wave.Bar],
    risk: ManagedRisk,
) -> ManagedOutcome:
    is_long = signal.direction == "long"
    entry_price = signal.bar.close
    first_target_price = (
        entry_price + risk.first_target_points
        if is_long
        else entry_price - risk.first_target_points
    )
    runner_target_price = (
        entry_price + risk.runner_target_points
        if is_long
        else entry_price - risk.runner_target_points
    )
    initial_stop_price = (
        entry_price - risk.initial_stop_points
        if is_long
        else entry_price + risk.initial_stop_points
    )

    exit_bar = following_rows[-1] if following_rows else signal.bar
    first_target_hit = False
    runner_exit_reason = "no_following_bar" if not following_rows else "end_of_session"
    exit_reason = runner_exit_reason
    first_leg_points = 0.0
    runner_points = 0.0

    for row in following_rows:
        stop_hit = row.low <= initial_stop_price if is_long else row.high >= initial_stop_price
        first_target_touched = (
            row.high >= first_target_price if is_long else row.low <= first_target_price
        )
        if stop_hit and not first_target_hit:
            exit_bar = row
            first_leg_points = -risk.initial_stop_points
            runner_points = -risk.initial_stop_points
            runner_exit_reason = "full_stop"
            exit_reason = "full_stop"
            break
        if first_target_touched and not first_target_hit:
            first_target_hit = True
            first_leg_points = risk.first_target_points
            breakeven_hit_same_bar = row.low <= entry_price if is_long else row.high >= entry_price
            runner_target_hit_same_bar = (
                row.high >= runner_target_price if is_long else row.low <= runner_target_price
            )
            if breakeven_hit_same_bar:
                exit_bar = row
                runner_points = 0.0
                runner_exit_reason = "breakeven_stop"
                exit_reason = "first_target_then_breakeven"
                break
            if runner_target_hit_same_bar:
                exit_bar = row
                runner_points = risk.runner_target_points
                runner_exit_reason = "runner_target"
                exit_reason = "first_target_then_runner_target"
                break
            continue

        if first_target_hit:
            breakeven_hit = row.low <= entry_price if is_long else row.high >= entry_price
            runner_target_hit = (
                row.high >= runner_target_price if is_long else row.low <= runner_target_price
            )
            if breakeven_hit:
                exit_bar = row
                runner_points = 0.0
                runner_exit_reason = "breakeven_stop"
                exit_reason = "first_target_then_breakeven"
                break
            if runner_target_hit:
                exit_bar = row
                runner_points = risk.runner_target_points
                runner_exit_reason = "runner_target"
                exit_reason = "first_target_then_runner_target"
                break
    else:
        if first_target_hit:
            exit_price = exit_bar.close
            runner_points = exit_price - entry_price if is_long else entry_price - exit_price
            runner_exit_reason = "end_of_session"
            exit_reason = "first_target_then_end_of_session"
        else:
            exit_price = exit_bar.close
            first_leg_points = exit_price - entry_price if is_long else entry_price - exit_price
            runner_points = first_leg_points
            runner_exit_reason = "end_of_session" if following_rows else "no_following_bar"
            exit_reason = runner_exit_reason

    gross_points_contracts, net_usd = _priced_points(
        first_leg_points=first_leg_points,
        runner_points=runner_points,
        risk=risk,
    )
    return ManagedOutcome(
        strategy_id=signal.strategy_id,
        direction=signal.direction,
        entry_time=signal.bar.timestamp,
        exit_time=exit_bar.timestamp,
        entry_bar_index=signal.bar.index,
        exit_bar_index=exit_bar.index,
        entry_price=entry_price,
        first_target_price=first_target_price,
        runner_target_price=runner_target_price,
        initial_stop_price=initial_stop_price,
        first_target_hit=first_target_hit,
        runner_exit_reason=runner_exit_reason,
        exit_reason=exit_reason,
        holding_minutes=(exit_bar.timestamp - signal.bar.timestamp).total_seconds() / 60.0,
        first_leg_points=first_leg_points,
        runner_points=runner_points,
        gross_points_contracts=gross_points_contracts,
        net_usd=net_usd,
        notes=signal.notes,
    )


def _with_priced_outcomes(
    outcomes: list[ManagedOutcome],
    risk: ManagedRisk,
) -> list[ManagedOutcome]:
    priced = []
    for outcome in outcomes:
        gross_points_contracts, net_usd = _priced_points(
            first_leg_points=outcome.first_leg_points,
            runner_points=outcome.runner_points,
            risk=risk,
        )
        priced.append(
            replace(
                outcome,
                gross_points_contracts=gross_points_contracts,
                net_usd=net_usd,
            ),
        )
    return priced


def _priced_points(
    *,
    first_leg_points: float,
    runner_points: float,
    risk: ManagedRisk,
) -> tuple[float, float]:
    gross_points_contracts = (
        first_leg_points * risk.first_leg_quantity
        + runner_points * risk.runner_quantity
    )
    gross_usd = gross_points_contracts * wave.POINT_VALUE_USD
    return gross_points_contracts, gross_usd - risk.round_turn_cost_usd


def _net_usd_for_outcome(outcome: ManagedOutcome, risk: ManagedRisk) -> float:
    _, net_usd = _priced_points(
        first_leg_points=outcome.first_leg_points,
        runner_points=outcome.runner_points,
        risk=risk,
    )
    return net_usd


def _sweep_row(
    *,
    strategy_id: str,
    family: str,
    raw_signal_count: int,
    outcomes: list[ManagedOutcome],
    risk: ManagedRisk,
    sample_info: SampleInfo,
) -> dict[str, object]:
    net_values = [_net_usd_for_outcome(outcome, risk) for outcome in outcomes]
    positive = [value for value in net_values if value > 0.0]
    negative = [value for value in net_values if value < 0.0]
    latest_year_values = [
        _net_usd_for_outcome(outcome, risk)
        for outcome in outcomes
        if outcome.entry_time.year == sample_info.latest_year
    ]
    quarterly_net: dict[tuple[int, int], float] = defaultdict(float)
    daily_net: dict[date, float] = defaultdict(float)
    for outcome in outcomes:
        net_usd = _net_usd_for_outcome(outcome, risk)
        quarter = (outcome.entry_time.month - 1) // 3 + 1
        quarterly_net[(outcome.entry_time.year, quarter)] += net_usd
        daily_net[outcome.entry_time.date()] += net_usd

    target_hits = sum(outcome.first_target_hit for outcome in outcomes)
    full_stops = sum(outcome.exit_reason == "full_stop" for outcome in outcomes)
    runner_breakeven = sum(
        outcome.runner_exit_reason == "breakeven_stop"
        for outcome in outcomes
    )
    runner_targets = sum(
        outcome.runner_exit_reason == "runner_target"
        for outcome in outcomes
    )
    end_of_session = sum(
        outcome.runner_exit_reason in {"end_of_session", "no_following_bar"}
        for outcome in outcomes
    )
    return {
        "schema_version": 1,
        "strategy_id": strategy_id,
        "family": family,
        "quantity": risk.quantity,
        "first_leg_quantity": risk.first_leg_quantity,
        "runner_quantity": risk.runner_quantity,
        "first_target_points": wave._format_number(risk.first_target_points),
        "initial_stop_points": wave._format_number(risk.initial_stop_points),
        "runner_target_points": wave._format_number(risk.runner_target_points),
        "raw_signals": raw_signal_count,
        "evaluated_trades": len(outcomes),
        "signal_days": len({outcome.entry_time.date() for outcome in outcomes}),
        "trades_per_week": wave._format_number(len(outcomes) / sample_info.weeks),
        "first_target_rate": wave._format_number(target_hits / len(outcomes)),
        "full_stop_rate": wave._format_number(full_stops / len(outcomes)),
        "runner_breakeven_rate": wave._format_number(runner_breakeven / len(outcomes)),
        "runner_target_rate": wave._format_number(runner_targets / len(outcomes)),
        "end_of_session_rate": wave._format_number(end_of_session / len(outcomes)),
        "positive_trade_rate": wave._format_number(len(positive) / len(outcomes)),
        "win_rate": wave._format_number(len(positive) / len(outcomes)),
        "net_usd": wave._format_number(sum(net_values)),
        "average_trade_usd": wave._format_number(statistics.mean(net_values)),
        "profit_factor": wave._format_number(
            sum(positive) / abs(sum(negative)) if negative else 999.0,
        ),
        "max_trade_sequence_drawdown_usd": wave._format_number(wave._max_drawdown(net_values)),
        "latest_year": sample_info.latest_year,
        "latest_year_trades": len(latest_year_values),
        "latest_year_net_usd": wave._format_number(sum(latest_year_values)),
        "worst_quarter_net_usd": wave._format_number(
            min(quarterly_net.values()) if quarterly_net else 0.0,
        ),
        "worst_day_usd": wave._format_number(min(daily_net.values()) if daily_net else 0.0),
        "average_holding_minutes": wave._format_number(
            statistics.mean(outcome.holding_minutes for outcome in outcomes),
        ),
        "median_holding_minutes": wave._format_number(
            statistics.median(outcome.holding_minutes for outcome in outcomes),
        ),
        "worst_trade_usd": wave._format_number(min(net_values)),
        "notes": (
            "2 MNQ default; one contract exits at target one; runner stop moves "
            "to breakeven; overlapping strategy trades skipped; same-bar "
            "ambiguity handled conservatively"
        ),
    }


def _sample_info(bars: list[wave.Bar]) -> SampleInfo:
    trading_dates = tuple(sorted({bar.trade_date for bar in bars}))
    weeks = max(1.0, (trading_dates[-1] - trading_dates[0]).days / 7.0)
    return SampleInfo(
        trading_dates=trading_dates,
        weeks=weeks,
        latest_year=trading_dates[-1].year,
    )


def _write_report(
    report_output: str,
    bars: list[wave.Bar],
    sweep_rows: list[dict[str, object]],
    best_row: dict[str, object] | None,
) -> None:
    robust_rows = [
        row for row in sweep_rows
        if int(row["evaluated_trades"]) >= 150
        and float(row["trades_per_week"]) >= 2.0
        and float(row["first_target_rate"]) >= 0.55
        and float(row["full_stop_rate"]) <= 0.35
        and float(row["profit_factor"]) >= 1.20
        and float(row["net_usd"]) > 0.0
        and float(row["latest_year_net_usd"]) > 0.0
        and float(row["worst_quarter_net_usd"]) > -1000.0
    ]
    top_rows = sweep_rows[:12]
    lines = [
        "# MNQ Breakeven-Frequency Research",
        "",
        "Status: first-pass risk-management scan for frequent MNQ entries.",
        "",
        "## Thought Being Tested",
        "",
        "The key event is not the final runner target. The key event is whether a "
        "setup reaches target one often enough to pay the first leg, move the "
        "runner stop to breakeven, and turn many uncertain trades into protected "
        "outcomes. A target-one hit followed by breakeven is acceptable in this "
        "research pass.",
        "",
        "## Source",
        "",
        f"- rows: `{len(bars)}`",
        f"- dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        f"- unique dates: `{len({bar.trade_date for bar in bars})}`",
        "- instrument: `MNQ`, point value `$2`, tick value `$0.50`",
        "- cost model: `$0.50/side` commission plus `1` total slippage tick per contract",
        "",
        "## Search Shape",
        "",
        "- tested sizes/splits: `2 MNQ = 1 + 1`, `3 MNQ = 2 + 1`, "
        "`4 MNQ = 3 + 1`, and `4 MNQ = 2 + 2`",
        "- entries: frequent lookback breakouts and VWAP pullback continuations",
        "- trade cap: `1` or `2` raw signals per day, with at least `30` minutes spacing",
        "- management: first leg exits at target one; runner target is separate; "
        "runner stop moves to entry immediately after target one",
        "- no overlapping trades inside a strategy; later signals are skipped while a "
        "prior managed trade is open",
        "- same-bar ambiguity is conservative: initial stop wins before target one; "
        "after target one, breakeven wins before runner target",
        "",
        "## Result",
        "",
    ]
    if best_row is None:
        lines.append("No rows passed the minimum sample gates.")
    else:
        lines.extend(
            [
                "Best first-pass row by risk-management ranking:",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Strategy | `{best_row['strategy_id']}` |",
                f"| Quantity | `{best_row['quantity']}` |",
                f"| Split | `{best_row['first_leg_quantity']} + {best_row['runner_quantity']}` |",
                f"| First target / initial stop / runner target | "
                f"`{best_row['first_target_points']} / {best_row['initial_stop_points']} / {best_row['runner_target_points']}` |",
                f"| Evaluated trades | `{best_row['evaluated_trades']}` |",
                f"| Trades/week | `{best_row['trades_per_week']}` |",
                f"| First-target reach | `{float(best_row['first_target_rate']) * 100:.1f}%` |",
                f"| Full-stop rate | `{float(best_row['full_stop_rate']) * 100:.1f}%` |",
                f"| Runner breakeven rate | `{float(best_row['runner_breakeven_rate']) * 100:.1f}%` |",
                f"| Runner target rate | `{float(best_row['runner_target_rate']) * 100:.1f}%` |",
                f"| Net | `${best_row['net_usd']}` |",
                f"| Avg trade | `${best_row['average_trade_usd']}` |",
                f"| Profit factor | `{best_row['profit_factor']}` |",
                f"| Max trade-sequence DD | `${best_row['max_trade_sequence_drawdown_usd']}` |",
                f"| Latest-year trades | `{best_row['latest_year_trades']}` |",
                f"| Latest-year net | `${best_row['latest_year_net_usd']}` |",
                f"| Worst quarter | `${best_row['worst_quarter_net_usd']}` |",
                f"| Median hold | `{best_row['median_holding_minutes']}` minutes |",
                "",
                f"Rows meeting the rough risk-first lens: `{len(robust_rows)}`.",
            ],
        )

    positive_rows = [row for row in sweep_rows if float(row["net_usd"]) > 0.0]
    positive_rows.sort(
        key=lambda row: (
            -float(row["net_usd"]),
            -float(row["profit_factor"]),
            float(row["max_trade_sequence_drawdown_usd"]),
        ),
    )
    lines.extend(
        [
            "",
            "## Positive Rows Audit",
            "",
        ],
    )
    if not positive_rows:
        lines.append("No positive rows were found in this pass.")
    else:
        lines.extend(
            [
                f"Positive rows found: `{len(positive_rows)}` out of `{len(sweep_rows)}`. "
                "These are not accepted candidates unless the latest-year and quarter risk "
                "also hold up.",
                "",
                "| Rank | Qty | Split | Trades | /Wk | T1 / Stop / Runner | T1 Hit | Full Stop | Net | PF | Latest-Year Net | Worst Quarter | Strategy |",
                "| ---: | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
            ],
        )
        for rank, row in enumerate(positive_rows[:8], start=1):
            lines.append(
                "| "
                f"{rank} | {row['quantity']} | "
                f"{row['first_leg_quantity']}+{row['runner_quantity']} | "
                f"{row['evaluated_trades']} | {row['trades_per_week']} | "
                f"{row['first_target_points']} / {row['initial_stop_points']} / {row['runner_target_points']} | "
                f"{float(row['first_target_rate']) * 100:.1f}% | "
                f"{float(row['full_stop_rate']) * 100:.1f}% | "
                f"{row['net_usd']} | {row['profit_factor']} | "
                f"{row['latest_year_net_usd']} | {row['worst_quarter_net_usd']} | "
                f"`{row['strategy_id']}` |"
            )

    lines.extend(
        [
            "",
            "## Top Rows",
            "",
            "| Rank | Family | Qty | Split | Trades | /Wk | T1 / Stop / Runner | T1 Hit | Full Stop | BE | Runner | Net | PF | Latest-Year Net | Strategy |",
            "| ---: | --- | ---: | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ],
    )
    for rank, row in enumerate(top_rows, start=1):
        lines.append(
            "| "
            f"{rank} | {row['family']} | {row['quantity']} | "
            f"{row['first_leg_quantity']}+{row['runner_quantity']} | "
            f"{row['evaluated_trades']} | "
            f"{row['trades_per_week']} | "
            f"{row['first_target_points']} / {row['initial_stop_points']} / {row['runner_target_points']} | "
            f"{float(row['first_target_rate']) * 100:.1f}% | "
            f"{float(row['full_stop_rate']) * 100:.1f}% | "
            f"{float(row['runner_breakeven_rate']) * 100:.1f}% | "
            f"{float(row['runner_target_rate']) * 100:.1f}% | "
            f"{row['net_usd']} | {row['profit_factor']} | "
            f"{row['latest_year_net_usd']} | `{row['strategy_id']}` |"
        )

    by_family: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in robust_rows:
        by_family[str(row["family"])].append(row)
    lines.extend(["", "## Robust Rows By Family", ""])
    if not by_family:
        lines.append(
            "No family produced a row that met the rough risk-first lens. The next "
            "step is to widen the entry families or adjust the target-one/stop grid.",
        )
    else:
        lines.extend(
            [
                "| Family | Rows | Best Net | Best PF | Best T1 Hit | Best Trades/Wk |",
                "| --- | ---: | ---: | ---: | ---: | ---: |",
            ],
        )
        for family, rows in sorted(by_family.items()):
            lines.append(
                "| "
                f"{family} | {len(rows)} | "
                f"{max(float(row['net_usd']) for row in rows):.2f} | "
                f"{max(float(row['profit_factor']) for row in rows):.2f} | "
                f"{max(float(row['first_target_rate']) for row in rows) * 100:.1f}% | "
                f"{max(float(row['trades_per_week']) for row in rows):.2f} |"
            )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This is not a deployment candidate yet. A usable candidate needs the "
            "same work we require elsewhere: expanded families if needed, slippage "
            "stress, walk-forward or holdout review, and replay/mechanics testing.",
            "",
            "The useful early signal is the relationship between first-target rate "
            "and full-stop rate. If target one is reached often and full stops stay "
            "controlled, then the idea has room for better runner research.",
            "",
        ],
    )
    Path(report_output).write_text("\n".join(lines), encoding="utf-8")


def _write_csv(path: str, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_trade_audit(
    path: str,
    trades: list[ManagedOutcome],
    row: dict[str, object],
) -> None:
    rows = [
        {
            "schema_version": 1,
            "strategy_id": trade.strategy_id,
            "quantity": row["quantity"],
            "first_leg_quantity": row["first_leg_quantity"],
            "runner_quantity": row["runner_quantity"],
            "first_target_points": row["first_target_points"],
            "initial_stop_points": row["initial_stop_points"],
            "runner_target_points": row["runner_target_points"],
            "direction": trade.direction,
            "entry_time": trade.entry_time.isoformat(sep=" "),
            "exit_time": trade.exit_time.isoformat(sep=" "),
            "entry_bar_index": trade.entry_bar_index,
            "exit_bar_index": trade.exit_bar_index,
            "entry_price": wave._format_number(trade.entry_price),
            "first_target_price": wave._format_number(trade.first_target_price),
            "runner_target_price": wave._format_number(trade.runner_target_price),
            "initial_stop_price": wave._format_number(trade.initial_stop_price),
            "first_target_hit": int(trade.first_target_hit),
            "runner_exit_reason": trade.runner_exit_reason,
            "exit_reason": trade.exit_reason,
            "holding_minutes": wave._format_number(trade.holding_minutes),
            "first_leg_points": wave._format_number(trade.first_leg_points),
            "runner_points": wave._format_number(trade.runner_points),
            "gross_points_contracts": wave._format_number(trade.gross_points_contracts),
            "net_usd": wave._format_number(trade.net_usd),
            "notes": trade.notes,
        }
        for trade in trades
    ]
    _write_csv(path, TRADE_AUDIT_HEADER, rows)


def _ranking_key(row: dict[str, object]) -> tuple[float, ...]:
    target_rate = float(row["first_target_rate"])
    full_stop_rate = float(row["full_stop_rate"])
    profit_factor = float(row["profit_factor"])
    net_usd = float(row["net_usd"])
    latest_year_net = float(row["latest_year_net_usd"])
    trades_per_week = float(row["trades_per_week"])
    worst_quarter = float(row["worst_quarter_net_usd"])
    sample_penalty = 0.0 if int(row["evaluated_trades"]) >= 150 else 1.0
    frequency_penalty = 0.0 if trades_per_week >= 2.0 else 1.0
    positive_penalty = 0.0 if net_usd > 0.0 else 1.0
    latest_year_penalty = 0.0 if latest_year_net > 0.0 else 1.0
    quarter_penalty = 0.0 if worst_quarter > -1000.0 else 1.0
    quality_penalty = (
        0.0
        if (
            target_rate >= 0.55
            and full_stop_rate <= 0.35
            and profit_factor >= 1.20
            and net_usd > 0.0
            and latest_year_net > 0.0
            and worst_quarter > -1000.0
        )
        else 1.0
    )
    return (
        quality_penalty,
        positive_penalty,
        latest_year_penalty,
        quarter_penalty,
        sample_penalty,
        frequency_penalty,
        -profit_factor,
        -net_usd,
        -target_rate,
        full_stop_rate,
        -trades_per_week,
    )


def _is_better_row(
    row: dict[str, object],
    current_best: dict[str, object] | None,
) -> bool:
    if current_best is None:
        return True
    return _ranking_key(row) < _ranking_key(current_best)


if __name__ == "__main__":
    raise SystemExit(main())
