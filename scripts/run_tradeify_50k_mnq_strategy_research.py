#!/usr/bin/env python3
"""Research a fresh MNQ strategy for a Tradeify 50K Select account."""

from __future__ import annotations

import argparse
import csv
import math
import random
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Iterable

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_mnq_eval_pass_wave_rider as wave  # noqa: E402


DEFAULT_OUTPUT = "reports/tradeify-50k-mnq-strategy-sweep.csv"
DEFAULT_REPORT = "reports/tradeify-50k-mnq-strategy-research.md"
DEFAULT_AUDIT = "reports/tradeify-50k-mnq-strategy-trade-audit.csv"

NY_OPEN = time(9, 30)
FLATTEN_TIME = time(15, 45)
TRADEIFY_PROFIT_TARGET_USD = 3000.0
TRADEIFY_MAX_DRAWDOWN_USD = 2000.0
TRADEIFY_CONSISTENCY_FRACTION = 0.40
FUNDED_LOCK_TARGET_USD = 2100.0
MNQ_POINT_VALUE_USD = 2.0
MNQ_TICK_VALUE_USD = 0.50
MNQ_ROUND_TURN_FEE_USD = 1.82
BASE_TOTAL_SLIPPAGE_TICKS = 2
STRESS_TOTAL_SLIPPAGE_TICKS = 6
MAX_FUNDED_STARTING_MICROS = 20
INTERNAL_MAX_STOP_LOSS_USD = 450.0
INTERNAL_MAX_TARGET_PROFIT_USD = 1100.0
MONTE_CARLO_RUNS = 10000
MONTE_CARLO_DAYS = 65
MONTE_CARLO_BLOCK_DAYS = 5


@dataclass(frozen=True)
class OpeningSnapshot:
    minutes: int
    end_time: time
    open: float
    high: float
    low: float
    close: float
    close_location: float
    cumulative_delta: float
    volume: float

    @property
    def width(self) -> float:
        return self.high - self.low

    @property
    def move(self) -> float:
        return self.close - self.open

    @property
    def delta_ratio(self) -> float:
        return self.cumulative_delta / self.volume if self.volume > 0.0 else 0.0


@dataclass(frozen=True)
class DayContext:
    trade_date: date
    rows: tuple[wave.Bar, ...]
    previous_close: float | None
    previous_high: float | None
    previous_low: float | None
    opening_15: OpeningSnapshot
    opening_30: OpeningSnapshot

    @property
    def day_open(self) -> float:
        return self.opening_15.open

    @property
    def gap(self) -> float:
        if self.previous_close is None:
            return 0.0
        return self.day_open - self.previous_close


@dataclass(frozen=True)
class ExitProfile:
    target_points: float
    stop_points: float


@dataclass(frozen=True)
class PathOutcome:
    strategy_id: str
    family: str
    direction: str
    entry_time: datetime
    exit_time: datetime
    entry_bar_index: int
    exit_bar_index: int
    entry_price: float
    exit_price: float
    target_price: float
    stop_price: float
    exit_reason: str
    holding_minutes: float
    gross_points: float
    notes: str


@dataclass(frozen=True)
class PeriodMetrics:
    trades: int
    trade_dates: int
    net_usd: float
    average_trade_usd: float
    profit_factor: float
    win_rate: float
    max_drawdown_usd: float
    net_to_drawdown: float
    worst_day_usd: float
    max_loss_streak: int
    average_holding_minutes: float
    median_holding_minutes: float


@dataclass(frozen=True)
class AttemptSummary:
    attempts: int
    pass_rate: float
    fail_rate: float
    timeout_rate: float
    median_calendar_days_to_pass: float
    median_trade_days_to_pass: float


SWEEP_HEADER = [
    "schema_version",
    "strategy_id",
    "family",
    "target_points",
    "stop_points",
    "full_trades",
    "trades_per_week",
    "train_trades",
    "train_net_usd",
    "train_profit_factor",
    "train_win_rate",
    "train_max_drawdown_usd",
    "validation_trades",
    "validation_net_usd",
    "validation_profit_factor",
    "validation_win_rate",
    "validation_max_drawdown_usd",
    "development_net_usd",
    "development_profit_factor",
    "development_max_drawdown_usd",
    "holdout_trades",
    "holdout_net_usd",
    "holdout_profit_factor",
    "holdout_win_rate",
    "holdout_max_drawdown_usd",
    "full_net_usd",
    "full_profit_factor",
    "full_win_rate",
    "full_max_drawdown_usd",
    "full_worst_day_usd",
    "selection_eligible",
    "selection_rank",
]


AUDIT_HEADER = [
    "schema_version",
    "strategy_id",
    "family",
    "direction",
    "entry_time",
    "exit_time",
    "entry_bar_index",
    "exit_bar_index",
    "entry_price",
    "exit_price",
    "target_price",
    "stop_price",
    "exit_reason",
    "holding_minutes",
    "gross_points",
    "base_net_1_mnq_usd",
    "notes",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Research fresh MNQ opening-auction, prior-session sweep, gap-fade, "
            "and VWAP trend-pullback families for Tradeify 50K Select."
        ),
    )
    parser.add_argument("input", nargs="?", default=wave.DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT)
    parser.add_argument("--audit-output", default=DEFAULT_AUDIT)
    parser.add_argument("--symbol", default="MNQ")
    parser.add_argument("--seed", type=int, default=20260805)
    args = parser.parse_args()

    bars = wave._load_feature_bars(args.input)
    bars_by_date = wave._bars_by_date(bars)
    contexts = _build_day_contexts(bars_by_date)
    trade_dates = sorted(contexts)
    train_dates, validation_dates, holdout_dates = _split_dates(trade_dates)
    signal_sets = _generate_signal_sets(contexts, symbol=args.symbol)
    exit_profiles = _exit_profiles()
    print(
        f"generated {len(signal_sets)} signal sets and "
        f"{sum(len(signals) for signals in signal_sets.values())} raw signals",
        flush=True,
    )

    date_sets = {
        "train": set(train_dates),
        "validation": set(validation_dates),
        "development": set(train_dates + validation_dates),
        "holdout": set(holdout_dates),
        "full": set(trade_dates),
    }
    sample_weeks = max((trade_dates[-1] - trade_dates[0]).days / 7.0, 1.0)
    rows: list[dict[str, object]] = []
    outcomes_by_key: dict[tuple[str, float, float], list[PathOutcome]] = {}
    for strategy_id, signals in signal_sets.items():
        if len(signals) < 45:
            continue
        family = strategy_id.split(":", 1)[0]
        for exit_profile in exit_profiles:
            outcomes = _evaluate_signals(
                signals,
                bars_by_date,
                exit_profile,
                family=family,
            )
            if len(outcomes) < 40:
                continue
            metrics = {
                period: _metrics(
                    _outcomes_for_dates(outcomes, dates),
                    quantity=1,
                    total_slippage_ticks=BASE_TOTAL_SLIPPAGE_TICKS,
                )
                for period, dates in date_sets.items()
            }
            row = _sweep_row(
                strategy_id,
                family,
                exit_profile,
                metrics,
                sample_weeks=sample_weeks,
            )
            rows.append(row)
            outcomes_by_key[
                (strategy_id, exit_profile.target_points, exit_profile.stop_points)
            ] = outcomes

    ranked_eligible = sorted(
        (row for row in rows if bool(row["selection_eligible"])),
        key=_selection_key,
    )
    rank_by_key = {
        _row_key(row): rank for rank, row in enumerate(ranked_eligible, start=1)
    }
    for row in rows:
        row["selection_rank"] = rank_by_key.get(_row_key(row), "")
    rows.sort(key=_report_sort_key)
    _write_csv(args.output, SWEEP_HEADER, rows)

    selected_row = ranked_eligible[0] if ranked_eligible else None
    selected_outcomes: list[PathOutcome] = []
    if selected_row is not None:
        selected_outcomes = outcomes_by_key[_row_key(selected_row)]
        _write_audit(args.audit_output, selected_outcomes)

    sizing_rows: list[dict[str, object]] = []
    stress: dict[str, object] = {}
    family_leaders = _family_leaders(rows)
    if selected_row is not None:
        sizing_rows = _size_candidate(
            selected_outcomes,
            trade_dates,
            stop_points=float(selected_row["stop_points"]),
            target_points=float(selected_row["target_points"]),
            seed=args.seed,
        )
        stress = _stress_summary(
            selected_outcomes,
            date_sets,
            sizing_rows,
            seed=args.seed,
        )

    _write_report(
        args.report_output,
        bars=bars,
        trade_dates=trade_dates,
        train_dates=train_dates,
        validation_dates=validation_dates,
        holdout_dates=holdout_dates,
        signal_sets=signal_sets,
        rows=rows,
        family_leaders=family_leaders,
        selected_row=selected_row,
        selected_outcomes=selected_outcomes,
        sizing_rows=sizing_rows,
        stress=stress,
    )
    if selected_row is None:
        print(f"wrote {len(rows)} rows; no development-eligible candidate", flush=True)
    else:
        print(
            f"wrote {len(rows)} rows; selected={selected_row['strategy_id']} "
            f"target={selected_row['target_points']} stop={selected_row['stop_points']} "
            f"holdout_pf={selected_row['holdout_profit_factor']} ",
            flush=True,
        )
    return 0


def _build_day_contexts(
    bars_by_date: dict[date, list[wave.Bar]],
) -> dict[date, DayContext]:
    contexts: dict[date, DayContext] = {}
    previous_rows: list[wave.Bar] | None = None
    for trade_date in sorted(bars_by_date):
        rows = bars_by_date[trade_date]
        opening_15 = _opening_snapshot(rows, 15)
        opening_30 = _opening_snapshot(rows, 30)
        if opening_15 is None or opening_30 is None:
            previous_rows = rows
            continue
        contexts[trade_date] = DayContext(
            trade_date=trade_date,
            rows=tuple(rows),
            previous_close=previous_rows[-1].close if previous_rows else None,
            previous_high=max(row.high for row in previous_rows)
            if previous_rows
            else None,
            previous_low=min(row.low for row in previous_rows)
            if previous_rows
            else None,
            opening_15=opening_15,
            opening_30=opening_30,
        )
        previous_rows = rows
    return contexts


def _opening_snapshot(rows: list[wave.Bar], minutes: int) -> OpeningSnapshot | None:
    end = (
        datetime.combine(rows[0].trade_date, NY_OPEN) + timedelta(minutes=minutes)
    ).time()
    opening_rows = [row for row in rows if NY_OPEN <= row.timestamp.time() < end]
    if not opening_rows:
        return None
    high = max(row.high for row in opening_rows)
    low = min(row.low for row in opening_rows)
    close = opening_rows[-1].close
    return OpeningSnapshot(
        minutes=minutes,
        end_time=end,
        open=opening_rows[0].open,
        high=high,
        low=low,
        close=close,
        close_location=_close_location(low, high, close),
        cumulative_delta=sum(row.delta for row in opening_rows),
        volume=sum(row.volume for row in opening_rows),
    )


def _generate_signal_sets(
    contexts: dict[date, DayContext],
    *,
    symbol: str,
) -> dict[str, list[wave.Signal]]:
    signal_sets: dict[str, list[wave.Signal]] = {}

    for opening_minutes in (15, 30):
        for drive_points in (20.0, 35.0, 50.0):
            for opening_cl in (0.70, 0.80):
                for delta_ratio in (0.0, 0.02):
                    for gap_mode in ("any", "aligned"):
                        for pullback_points in (10.0, 20.0, 30.0):
                            for entry_delta in (0.0, 400.0):
                                for entry_end in (time(11, 30), time(12, 30)):
                                    strategy_id = (
                                        "tradeify_open_drive_pullback:"
                                        f"or{opening_minutes}:drive{drive_points:g}:"
                                        f"ocl{opening_cl:g}:dr{delta_ratio:g}:gap{gap_mode}:"
                                        f"pb{pullback_points:g}:ed{entry_delta:g}:"
                                        f"end{_time_id(entry_end)}"
                                    )
                                    signal_sets[strategy_id] = (
                                        _open_drive_pullback_signals(
                                            contexts,
                                            strategy_id=strategy_id,
                                            opening_minutes=opening_minutes,
                                            drive_points=drive_points,
                                            opening_close_location=opening_cl,
                                            delta_ratio_threshold=delta_ratio,
                                            gap_mode=gap_mode,
                                            pullback_points=pullback_points,
                                            entry_delta_threshold=entry_delta,
                                            entry_end=entry_end,
                                            symbol=symbol,
                                        )
                                    )

    for sweep_points in (5.0, 15.0, 30.0):
        for reclaim_points in (0.0, 5.0):
            for delta_threshold in (0.0, 400.0, 800.0):
                for close_location in (0.35, 0.45):
                    for vwap_stretch in (0.0, 20.0):
                        for entry_end in (time(11, 30), time(13, 0)):
                            strategy_id = (
                                "tradeify_prior_day_sweep_reversal:"
                                f"sweep{sweep_points:g}:reclaim{reclaim_points:g}:"
                                f"delta{delta_threshold:g}:cl{close_location:g}:"
                                f"stretch{vwap_stretch:g}:end{_time_id(entry_end)}"
                            )
                            signal_sets[strategy_id] = _prior_day_sweep_signals(
                                contexts,
                                strategy_id=strategy_id,
                                sweep_points=sweep_points,
                                reclaim_points=reclaim_points,
                                delta_threshold=delta_threshold,
                                close_location_threshold=close_location,
                                vwap_stretch_points=vwap_stretch,
                                entry_end=entry_end,
                                symbol=symbol,
                            )

    for gap_points in (20.0, 40.0, 60.0):
        for opening_minutes in (15, 30):
            for reversal_points in (10.0, 20.0):
                for delta_threshold in (0.0, 400.0):
                    for close_location in (0.55, 0.65):
                        for entry_end in (time(11, 30), time(12, 30)):
                            strategy_id = (
                                "tradeify_gap_fade_acceptance:"
                                f"gap{gap_points:g}:or{opening_minutes}:"
                                f"rev{reversal_points:g}:delta{delta_threshold:g}:"
                                f"cl{close_location:g}:end{_time_id(entry_end)}"
                            )
                            signal_sets[strategy_id] = _gap_fade_signals(
                                contexts,
                                strategy_id=strategy_id,
                                gap_points=gap_points,
                                opening_minutes=opening_minutes,
                                reversal_points=reversal_points,
                                delta_threshold=delta_threshold,
                                close_location_threshold=close_location,
                                entry_end=entry_end,
                                symbol=symbol,
                            )

    for trend_points in (30.0, 50.0, 80.0):
        for slope_points in (0.0, 5.0):
            for touch_points in (5.0, 15.0, 30.0):
                for delta_threshold in (0.0, 400.0):
                    for close_location in (0.60, 0.70):
                        for entry_end in (time(12, 30), time(14, 30)):
                            strategy_id = (
                                "tradeify_vwap_trend_pullback:"
                                f"trend{trend_points:g}:slope{slope_points:g}:"
                                f"touch{touch_points:g}:delta{delta_threshold:g}:"
                                f"cl{close_location:g}:end{_time_id(entry_end)}"
                            )
                            signal_sets[strategy_id] = _vwap_trend_pullback_signals(
                                contexts,
                                strategy_id=strategy_id,
                                trend_points=trend_points,
                                slope_points=slope_points,
                                touch_points=touch_points,
                                delta_threshold=delta_threshold,
                                close_location_threshold=close_location,
                                entry_end=entry_end,
                                symbol=symbol,
                            )
    return signal_sets


def _open_drive_pullback_signals(
    contexts: dict[date, DayContext],
    *,
    strategy_id: str,
    opening_minutes: int,
    drive_points: float,
    opening_close_location: float,
    delta_ratio_threshold: float,
    gap_mode: str,
    pullback_points: float,
    entry_delta_threshold: float,
    entry_end: time,
    symbol: str,
) -> list[wave.Signal]:
    signals: list[wave.Signal] = []
    for context in contexts.values():
        opening = context.opening_15 if opening_minutes == 15 else context.opening_30
        direction = ""
        if (
            opening.move >= drive_points
            and opening.close_location >= opening_close_location
            and opening.delta_ratio >= delta_ratio_threshold
        ):
            direction = "long"
        elif (
            opening.move <= -drive_points
            and opening.close_location <= 1.0 - opening_close_location
            and opening.delta_ratio <= -delta_ratio_threshold
        ):
            direction = "short"
        if not direction or opening.width > 220.0:
            continue
        directional_gap = context.gap if direction == "long" else -context.gap
        if gap_mode == "aligned" and directional_gap < 0.0:
            continue

        rows = list(context.rows)
        midpoint = (opening.high + opening.low) / 2.0
        extreme = opening.high if direction == "long" else opening.low
        pullback_seen = False
        previous: wave.Bar | None = None
        for row in rows:
            row_time = row.timestamp.time()
            if row_time < opening.end_time:
                continue
            if row_time > entry_end:
                break
            if direction == "long":
                if row.low <= extreme - pullback_points and row.close >= midpoint:
                    pullback_seen = True
                extreme = max(extreme, row.high)
                trigger = (
                    pullback_seen
                    and previous is not None
                    and row.close > previous.high
                    and row.close >= row.vwap
                    and row.close >= midpoint
                    and row.delta >= entry_delta_threshold
                    and row.close_location >= 0.60
                )
            else:
                if row.high >= extreme + pullback_points and row.close <= midpoint:
                    pullback_seen = True
                extreme = min(extreme, row.low)
                trigger = (
                    pullback_seen
                    and previous is not None
                    and row.close < previous.low
                    and row.close <= row.vwap
                    and row.close <= midpoint
                    and row.delta <= -entry_delta_threshold
                    and row.close_location <= 0.40
                )
            if trigger:
                signals.append(
                    wave.Signal(
                        strategy_id,
                        direction,
                        row,
                        f"{symbol} opening-drive pullback continuation",
                    ),
                )
                break
            previous = row
    return signals


def _prior_day_sweep_signals(
    contexts: dict[date, DayContext],
    *,
    strategy_id: str,
    sweep_points: float,
    reclaim_points: float,
    delta_threshold: float,
    close_location_threshold: float,
    vwap_stretch_points: float,
    entry_end: time,
    symbol: str,
) -> list[wave.Signal]:
    signals: list[wave.Signal] = []
    for context in contexts.values():
        if context.previous_high is None or context.previous_low is None:
            continue
        high_swept = False
        low_swept = False
        for row in context.rows:
            row_time = row.timestamp.time()
            if row_time < NY_OPEN:
                continue
            if row_time > entry_end:
                break
            high_swept = high_swept or row.high >= context.previous_high + sweep_points
            low_swept = low_swept or row.low <= context.previous_low - sweep_points
            if (
                high_swept
                and row.close <= context.previous_high - reclaim_points
                and row.close - row.vwap >= vwap_stretch_points
                and row.delta <= -delta_threshold
                and row.close_location <= close_location_threshold
            ):
                signals.append(
                    wave.Signal(
                        strategy_id,
                        "short",
                        row,
                        f"{symbol} prior-day-high sweep reversal",
                    ),
                )
                break
            if (
                low_swept
                and row.close >= context.previous_low + reclaim_points
                and row.vwap - row.close >= vwap_stretch_points
                and row.delta >= delta_threshold
                and row.close_location >= 1.0 - close_location_threshold
            ):
                signals.append(
                    wave.Signal(
                        strategy_id,
                        "long",
                        row,
                        f"{symbol} prior-day-low sweep reversal",
                    ),
                )
                break
    return signals


def _gap_fade_signals(
    contexts: dict[date, DayContext],
    *,
    strategy_id: str,
    gap_points: float,
    opening_minutes: int,
    reversal_points: float,
    delta_threshold: float,
    close_location_threshold: float,
    entry_end: time,
    symbol: str,
) -> list[wave.Signal]:
    signals: list[wave.Signal] = []
    for context in contexts.values():
        if context.previous_close is None or abs(context.gap) < gap_points:
            continue
        opening = context.opening_15 if opening_minutes == 15 else context.opening_30
        if context.gap > 0.0:
            direction = "short"
            if opening.close > context.day_open - reversal_points:
                continue
            if opening.close_location > 1.0 - close_location_threshold:
                continue
        else:
            direction = "long"
            if opening.close < context.day_open + reversal_points:
                continue
            if opening.close_location < close_location_threshold:
                continue
        for row in context.rows:
            row_time = row.timestamp.time()
            if row_time < opening.end_time:
                continue
            if row_time > entry_end:
                break
            if direction == "short":
                trigger = (
                    row.close < opening.low
                    and row.close <= row.vwap
                    and row.delta <= -delta_threshold
                    and row.close_location <= 1.0 - close_location_threshold
                )
            else:
                trigger = (
                    row.close > opening.high
                    and row.close >= row.vwap
                    and row.delta >= delta_threshold
                    and row.close_location >= close_location_threshold
                )
            if trigger:
                signals.append(
                    wave.Signal(
                        strategy_id, direction, row, f"{symbol} gap-fade acceptance"
                    ),
                )
                break
    return signals


def _vwap_trend_pullback_signals(
    contexts: dict[date, DayContext],
    *,
    strategy_id: str,
    trend_points: float,
    slope_points: float,
    touch_points: float,
    delta_threshold: float,
    close_location_threshold: float,
    entry_end: time,
    symbol: str,
) -> list[wave.Signal]:
    signals: list[wave.Signal] = []
    for context in contexts.values():
        rows = list(context.rows)
        pullback_long = False
        pullback_short = False
        for index, row in enumerate(rows):
            row_time = row.timestamp.time()
            if row_time < time(10, 0):
                continue
            if row_time > entry_end:
                break
            if index < 10:
                continue
            vwap_slope = row.vwap - rows[index - 10].vwap
            day_move = row.close - context.day_open
            if (
                day_move >= trend_points
                and vwap_slope >= slope_points
                and row.low <= row.vwap + touch_points
                and row.close >= row.vwap
            ):
                pullback_long = True
            if (
                day_move <= -trend_points
                and vwap_slope <= -slope_points
                and row.high >= row.vwap - touch_points
                and row.close <= row.vwap
            ):
                pullback_short = True
            previous = rows[index - 1]
            if (
                pullback_long
                and day_move >= trend_points * 0.5
                and vwap_slope >= slope_points
                and row.close > previous.high
                and row.close >= row.vwap
                and row.delta >= delta_threshold
                and row.close_location >= close_location_threshold
            ):
                signals.append(
                    wave.Signal(
                        strategy_id, "long", row, f"{symbol} VWAP trend pullback"
                    ),
                )
                break
            if (
                pullback_short
                and day_move <= -trend_points * 0.5
                and vwap_slope <= -slope_points
                and row.close < previous.low
                and row.close <= row.vwap
                and row.delta <= -delta_threshold
                and row.close_location <= 1.0 - close_location_threshold
            ):
                signals.append(
                    wave.Signal(
                        strategy_id, "short", row, f"{symbol} VWAP trend pullback"
                    ),
                )
                break
    return signals


def _exit_profiles() -> list[ExitProfile]:
    pairs = (
        (20.0, 30.0),
        (25.0, 40.0),
        (30.0, 20.0),
        (30.0, 40.0),
        (30.0, 50.0),
        (40.0, 20.0),
        (40.0, 30.0),
        (40.0, 50.0),
        (40.0, 60.0),
        (50.0, 30.0),
        (60.0, 30.0),
        (60.0, 40.0),
        (80.0, 40.0),
        (80.0, 60.0),
        (100.0, 50.0),
        (120.0, 60.0),
    )
    return [ExitProfile(target, stop) for target, stop in pairs]


def _evaluate_signals(
    signals: list[wave.Signal],
    bars_by_date: dict[date, list[wave.Bar]],
    exit_profile: ExitProfile,
    *,
    family: str,
) -> list[PathOutcome]:
    local_index = {
        row.index: index
        for rows in bars_by_date.values()
        for index, row in enumerate(rows)
    }
    outcomes: list[PathOutcome] = []
    traded_dates: set[date] = set()
    for signal in sorted(signals, key=lambda item: item.bar.timestamp):
        if signal.bar.trade_date in traded_dates:
            continue
        rows = bars_by_date[signal.bar.trade_date]
        following_rows = [
            row
            for row in rows[local_index[signal.bar.index] + 1 :]
            if row.timestamp.time() <= FLATTEN_TIME
        ]
        outcomes.append(
            _evaluate_signal(signal, following_rows, exit_profile, family=family),
        )
        traded_dates.add(signal.bar.trade_date)
    return outcomes


def _evaluate_signal(
    signal: wave.Signal,
    following_rows: list[wave.Bar],
    exit_profile: ExitProfile,
    *,
    family: str,
) -> PathOutcome:
    is_long = signal.direction == "long"
    entry_price = signal.bar.close
    target_price = (
        entry_price + exit_profile.target_points
        if is_long
        else entry_price - exit_profile.target_points
    )
    stop_price = (
        entry_price - exit_profile.stop_points
        if is_long
        else entry_price + exit_profile.stop_points
    )
    exit_bar = following_rows[-1] if following_rows else signal.bar
    exit_price = exit_bar.close
    exit_reason = "end_of_session" if following_rows else "no_following_bar"
    for row in following_rows:
        stop_hit = row.low <= stop_price if is_long else row.high >= stop_price
        target_hit = row.high >= target_price if is_long else row.low <= target_price
        if stop_hit:
            exit_bar = row
            exit_price = stop_price
            exit_reason = "stop_hit"
            break
        if target_hit:
            exit_bar = row
            exit_price = target_price
            exit_reason = "target_hit"
            break
    gross_points = exit_price - entry_price if is_long else entry_price - exit_price
    return PathOutcome(
        strategy_id=signal.strategy_id,
        family=family,
        direction=signal.direction,
        entry_time=signal.bar.timestamp,
        exit_time=exit_bar.timestamp,
        entry_bar_index=signal.bar.index,
        exit_bar_index=exit_bar.index,
        entry_price=entry_price,
        exit_price=exit_price,
        target_price=target_price,
        stop_price=stop_price,
        exit_reason=exit_reason,
        holding_minutes=(exit_bar.timestamp - signal.bar.timestamp).total_seconds()
        / 60.0,
        gross_points=gross_points,
        notes=signal.notes,
    )


def _metrics(
    outcomes: list[PathOutcome],
    *,
    quantity: int,
    total_slippage_ticks: int,
) -> PeriodMetrics:
    values = [
        _mnq_net(outcome, quantity, total_slippage_ticks=total_slippage_ticks)
        for outcome in outcomes
    ]
    positives = [value for value in values if value > 0.0]
    negatives = [value for value in values if value < 0.0]
    daily: dict[date, float] = defaultdict(float)
    for outcome, value in zip(outcomes, values, strict=True):
        daily[outcome.entry_time.date()] += value
    net = sum(values)
    drawdown = _max_drawdown(values)
    return PeriodMetrics(
        trades=len(outcomes),
        trade_dates=len(daily),
        net_usd=net,
        average_trade_usd=statistics.mean(values) if values else 0.0,
        profit_factor=(sum(positives) / abs(sum(negatives)) if negatives else 999.0),
        win_rate=(len(positives) / len(values) if values else 0.0),
        max_drawdown_usd=drawdown,
        net_to_drawdown=(net / abs(drawdown) if drawdown < 0.0 else 999.0),
        worst_day_usd=min(daily.values()) if daily else 0.0,
        max_loss_streak=_max_loss_streak(values),
        average_holding_minutes=(
            statistics.mean(outcome.holding_minutes for outcome in outcomes)
            if outcomes
            else 0.0
        ),
        median_holding_minutes=(
            statistics.median(outcome.holding_minutes for outcome in outcomes)
            if outcomes
            else 0.0
        ),
    )


def _sweep_row(
    strategy_id: str,
    family: str,
    exit_profile: ExitProfile,
    metrics: dict[str, PeriodMetrics],
    *,
    sample_weeks: float,
) -> dict[str, object]:
    train = metrics["train"]
    validation = metrics["validation"]
    development = metrics["development"]
    holdout = metrics["holdout"]
    full = metrics["full"]
    eligible = (
        train.trades >= 50
        and validation.trades >= 20
        and development.trades >= 80
        and train.net_usd > 0.0
        and validation.net_usd > 0.0
        and train.profit_factor >= 1.20
        and validation.profit_factor >= 1.20
        and development.profit_factor >= 1.30
        and train.max_drawdown_usd > -600.0
        and validation.max_drawdown_usd > -450.0
    )
    return {
        "schema_version": 1,
        "strategy_id": strategy_id,
        "family": family,
        "target_points": _fmt(exit_profile.target_points),
        "stop_points": _fmt(exit_profile.stop_points),
        "full_trades": full.trades,
        "trades_per_week": _fmt(full.trades / sample_weeks),
        "train_trades": train.trades,
        "train_net_usd": _fmt(train.net_usd),
        "train_profit_factor": _fmt(train.profit_factor),
        "train_win_rate": _fmt(train.win_rate),
        "train_max_drawdown_usd": _fmt(train.max_drawdown_usd),
        "validation_trades": validation.trades,
        "validation_net_usd": _fmt(validation.net_usd),
        "validation_profit_factor": _fmt(validation.profit_factor),
        "validation_win_rate": _fmt(validation.win_rate),
        "validation_max_drawdown_usd": _fmt(validation.max_drawdown_usd),
        "development_net_usd": _fmt(development.net_usd),
        "development_profit_factor": _fmt(development.profit_factor),
        "development_max_drawdown_usd": _fmt(development.max_drawdown_usd),
        "holdout_trades": holdout.trades,
        "holdout_net_usd": _fmt(holdout.net_usd),
        "holdout_profit_factor": _fmt(holdout.profit_factor),
        "holdout_win_rate": _fmt(holdout.win_rate),
        "holdout_max_drawdown_usd": _fmt(holdout.max_drawdown_usd),
        "full_net_usd": _fmt(full.net_usd),
        "full_profit_factor": _fmt(full.profit_factor),
        "full_win_rate": _fmt(full.win_rate),
        "full_max_drawdown_usd": _fmt(full.max_drawdown_usd),
        "full_worst_day_usd": _fmt(full.worst_day_usd),
        "selection_eligible": eligible,
        "selection_rank": "",
    }


def _selection_key(row: dict[str, object]) -> tuple[float, ...]:
    train_pf = min(float(row["train_profit_factor"]), 4.0)
    validation_pf = min(float(row["validation_profit_factor"]), 4.0)
    minimum_pf = min(train_pf, validation_pf)
    train_drawdown = abs(float(row["train_max_drawdown_usd"]))
    validation_drawdown = abs(float(row["validation_max_drawdown_usd"]))
    minimum_net_to_dd = min(
        float(row["train_net_usd"]) / train_drawdown if train_drawdown else 999.0,
        (
            float(row["validation_net_usd"]) / validation_drawdown
            if validation_drawdown
            else 999.0
        ),
    )
    return (
        -minimum_pf,
        -minimum_net_to_dd,
        -min(float(row["development_profit_factor"]), 4.0),
        -min(float(row["trades_per_week"]), 5.0),
        -float(row["development_net_usd"]),
        abs(float(row["development_max_drawdown_usd"])),
    )


def _report_sort_key(row: dict[str, object]) -> tuple[float, ...]:
    rank = row.get("selection_rank")
    return (
        0.0 if rank != "" else 1.0,
        float(rank) if rank != "" else 999999.0,
        -float(row["development_profit_factor"]),
        -float(row["development_net_usd"]),
    )


def _family_leaders(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    by_family: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        by_family[str(row["family"])].append(row)
    leaders = []
    for family, family_rows in sorted(by_family.items()):
        eligible = [row for row in family_rows if bool(row["selection_eligible"])]
        pool = eligible or family_rows
        leaders.append(min(pool, key=_selection_key))
    return leaders


def _size_candidate(
    outcomes: list[PathOutcome],
    trade_dates: list[date],
    *,
    stop_points: float,
    target_points: float,
    seed: int,
) -> list[dict[str, object]]:
    rows = []
    for quantity in range(1, MAX_FUNDED_STARTING_MICROS + 1):
        stop_loss = stop_points * MNQ_POINT_VALUE_USD * quantity + _mnq_cost(
            quantity,
            BASE_TOTAL_SLIPPAGE_TICKS,
        )
        target_profit = target_points * MNQ_POINT_VALUE_USD * quantity - _mnq_cost(
            quantity,
            BASE_TOTAL_SLIPPAGE_TICKS,
        )
        metrics = _metrics(
            outcomes,
            quantity=quantity,
            total_slippage_ticks=BASE_TOTAL_SLIPPAGE_TICKS,
        )
        attempts = _historical_attempts(outcomes, trade_dates, quantity=quantity)
        monte_carlo = _monte_carlo_attempts(
            outcomes,
            trade_dates,
            quantity=quantity,
            seed=seed + quantity,
        )
        funded_lock = _historical_attempts(
            outcomes,
            trade_dates,
            quantity=quantity,
            profit_target_usd=FUNDED_LOCK_TARGET_USD,
            consistency_fraction=1.0,
        )
        risk_eligible = (
            stop_loss <= INTERNAL_MAX_STOP_LOSS_USD
            and target_profit <= INTERNAL_MAX_TARGET_PROFIT_USD
            and metrics.max_drawdown_usd > -1500.0
            and attempts.pass_rate >= 0.25
            and monte_carlo.pass_rate >= 0.25
            and monte_carlo.fail_rate <= 0.20
        )
        rows.append(
            {
                "quantity": quantity,
                "stop_loss_usd": _fmt(-stop_loss),
                "target_profit_usd": _fmt(target_profit),
                "net_usd": _fmt(metrics.net_usd),
                "max_drawdown_usd": _fmt(metrics.max_drawdown_usd),
                "historical_pass_rate": _fmt(attempts.pass_rate),
                "historical_fail_rate": _fmt(attempts.fail_rate),
                "historical_timeout_rate": _fmt(attempts.timeout_rate),
                "historical_median_calendar_days": _fmt(
                    attempts.median_calendar_days_to_pass,
                ),
                "historical_median_trade_days": _fmt(
                    attempts.median_trade_days_to_pass
                ),
                "monte_carlo_pass_rate": _fmt(monte_carlo.pass_rate),
                "monte_carlo_fail_rate": _fmt(monte_carlo.fail_rate),
                "monte_carlo_timeout_rate": _fmt(monte_carlo.timeout_rate),
                "funded_lock_rate": _fmt(funded_lock.pass_rate),
                "funded_lock_fail_rate": _fmt(funded_lock.fail_rate),
                "risk_eligible": risk_eligible,
            },
        )
    return rows


def _historical_attempts(
    outcomes: list[PathOutcome],
    trade_dates: list[date],
    *,
    quantity: int,
    profit_target_usd: float = TRADEIFY_PROFIT_TARGET_USD,
    consistency_fraction: float = TRADEIFY_CONSISTENCY_FRACTION,
    horizon_calendar_days: int = 90,
) -> AttemptSummary:
    value_by_date = {
        outcome.entry_time.date(): _mnq_net(
            outcome,
            quantity,
            total_slippage_ticks=BASE_TOTAL_SLIPPAGE_TICKS,
        )
        for outcome in outcomes
    }
    results = []
    for start_index, start_date in enumerate(trade_dates):
        end_date = start_date + timedelta(days=horizon_calendar_days)
        attempt_dates = [
            value for value in trade_dates[start_index:] if value <= end_date
        ]
        daily_values = [
            (value, value_by_date.get(value, 0.0)) for value in attempt_dates
        ]
        results.append(
            _simulate_attempt(
                daily_values,
                profit_target_usd=profit_target_usd,
                consistency_fraction=consistency_fraction,
            ),
        )
    return _summarize_attempts(results)


def _monte_carlo_attempts(
    outcomes: list[PathOutcome],
    trade_dates: list[date],
    *,
    quantity: int,
    seed: int,
) -> AttemptSummary:
    value_by_date = {
        outcome.entry_time.date(): _mnq_net(
            outcome,
            quantity,
            total_slippage_ticks=STRESS_TOTAL_SLIPPAGE_TICKS,
        )
        for outcome in outcomes
    }
    source = [value_by_date.get(trade_date, 0.0) for trade_date in trade_dates]
    blocks = [
        source[index : index + MONTE_CARLO_BLOCK_DAYS]
        for index in range(0, len(source) - MONTE_CARLO_BLOCK_DAYS + 1)
    ]
    rng = random.Random(seed)
    results = []
    synthetic_start = date(2030, 1, 1)
    for _ in range(MONTE_CARLO_RUNS):
        values: list[float] = []
        while len(values) < MONTE_CARLO_DAYS:
            values.extend(rng.choice(blocks))
        daily_values = [
            (synthetic_start + timedelta(days=index), value)
            for index, value in enumerate(values[:MONTE_CARLO_DAYS])
        ]
        results.append(_simulate_attempt(daily_values))
    return _summarize_attempts(results)


def _simulate_attempt(
    daily_values: list[tuple[date, float]],
    *,
    profit_target_usd: float = TRADEIFY_PROFIT_TARGET_USD,
    consistency_fraction: float = TRADEIFY_CONSISTENCY_FRACTION,
) -> tuple[str, float, int]:
    equity = 0.0
    high_water = 0.0
    floor = -TRADEIFY_MAX_DRAWDOWN_USD
    largest_winning_day = 0.0
    trade_days = 0
    start_date = daily_values[0][0] if daily_values else date.min
    for trade_date, value in daily_values:
        if value != 0.0:
            trade_days += 1
        equity += value
        largest_winning_day = max(largest_winning_day, value)
        if equity <= floor + 0.01:
            return "fail", float((trade_date - start_date).days + 1), trade_days
        high_water = max(high_water, equity)
        floor = max(floor, high_water - TRADEIFY_MAX_DRAWDOWN_USD)
        consistency_ok = (
            largest_winning_day <= max(equity, 0.01) * consistency_fraction + 0.01
        )
        if equity >= profit_target_usd - 0.01 and consistency_ok:
            return "pass", float((trade_date - start_date).days + 1), trade_days
    return "timeout", 0.0, trade_days


def _summarize_attempts(results: list[tuple[str, float, int]]) -> AttemptSummary:
    passes = [result for result in results if result[0] == "pass"]
    attempts = len(results)
    return AttemptSummary(
        attempts=attempts,
        pass_rate=len(passes) / attempts if attempts else 0.0,
        fail_rate=sum(result[0] == "fail" for result in results) / attempts
        if attempts
        else 0.0,
        timeout_rate=(
            sum(result[0] == "timeout" for result in results) / attempts
            if attempts
            else 0.0
        ),
        median_calendar_days_to_pass=(
            statistics.median(result[1] for result in passes) if passes else 0.0
        ),
        median_trade_days_to_pass=(
            statistics.median(result[2] for result in passes) if passes else 0.0
        ),
    )


def _stress_summary(
    outcomes: list[PathOutcome],
    date_sets: dict[str, set[date]],
    sizing_rows: list[dict[str, object]],
    *,
    seed: int,
) -> dict[str, object]:
    eligible_sizes = [row for row in sizing_rows if bool(row["risk_eligible"])]
    if not eligible_sizes:
        return {"selected_quantity": 0}
    selected_size = max(
        eligible_sizes,
        key=lambda row: (
            float(row["historical_pass_rate"]),
            -float(row["monte_carlo_fail_rate"]),
            int(row["quantity"]),
        ),
    )
    quantity = int(selected_size["quantity"])
    base = _metrics(
        outcomes,
        quantity=quantity,
        total_slippage_ticks=BASE_TOTAL_SLIPPAGE_TICKS,
    )
    stress = _metrics(
        outcomes,
        quantity=quantity,
        total_slippage_ticks=STRESS_TOTAL_SLIPPAGE_TICKS,
    )
    holdout = _metrics(
        _outcomes_for_dates(outcomes, date_sets["holdout"]),
        quantity=quantity,
        total_slippage_ticks=STRESS_TOTAL_SLIPPAGE_TICKS,
    )
    drawdowns = _shuffled_drawdowns(
        outcomes,
        quantity=quantity,
        runs=MONTE_CARLO_RUNS,
        seed=seed + 5000,
    )
    yearly = _period_net(
        outcomes,
        quantity=quantity,
        total_slippage_ticks=STRESS_TOTAL_SLIPPAGE_TICKS,
        period="year",
    )
    quarterly = _period_net(
        outcomes,
        quantity=quantity,
        total_slippage_ticks=STRESS_TOTAL_SLIPPAGE_TICKS,
        period="quarter",
    )
    return {
        "selected_quantity": quantity,
        "base_metrics": base,
        "stress_metrics": stress,
        "holdout_stress_metrics": holdout,
        "monte_carlo_median_drawdown": statistics.median(drawdowns),
        "monte_carlo_p95_drawdown": _percentile(drawdowns, 0.05),
        "monte_carlo_p99_drawdown": _percentile(drawdowns, 0.01),
        "worst_year_net": min(yearly.values()) if yearly else 0.0,
        "worst_quarter_net": min(quarterly.values()) if quarterly else 0.0,
        "all_years_positive": bool(yearly) and min(yearly.values()) > 0.0,
    }


def _shuffled_drawdowns(
    outcomes: list[PathOutcome],
    *,
    quantity: int,
    runs: int,
    seed: int,
) -> list[float]:
    values = [
        _mnq_net(
            outcome,
            quantity,
            total_slippage_ticks=STRESS_TOTAL_SLIPPAGE_TICKS,
        )
        for outcome in outcomes
    ]
    rng = random.Random(seed)
    drawdowns = []
    for _ in range(runs):
        shuffled = list(values)
        rng.shuffle(shuffled)
        drawdowns.append(_max_drawdown(shuffled))
    return sorted(drawdowns)


def _period_net(
    outcomes: list[PathOutcome],
    *,
    quantity: int,
    total_slippage_ticks: int,
    period: str,
) -> dict[object, float]:
    values: dict[object, float] = defaultdict(float)
    for outcome in outcomes:
        if period == "year":
            key: object = outcome.entry_time.year
        elif period == "quarter":
            key = (outcome.entry_time.year, (outcome.entry_time.month - 1) // 3 + 1)
        else:
            raise ValueError(f"unsupported period: {period}")
        values[key] += _mnq_net(
            outcome,
            quantity,
            total_slippage_ticks=total_slippage_ticks,
        )
    return dict(values)


def _write_report(
    path: str,
    *,
    bars: list[wave.Bar],
    trade_dates: list[date],
    train_dates: list[date],
    validation_dates: list[date],
    holdout_dates: list[date],
    signal_sets: dict[str, list[wave.Signal]],
    rows: list[dict[str, object]],
    family_leaders: list[dict[str, object]],
    selected_row: dict[str, object] | None,
    selected_outcomes: list[PathOutcome],
    sizing_rows: list[dict[str, object]],
    stress: dict[str, object],
) -> None:
    lines = [
        "# Tradeify 50K MNQ Strategy Research",
        "",
        "Status: fresh strategy discovery for Tradeify Select and a future NinjaTrader implementation. No NinjaTrader code is included.",
        "",
        "## Research Contract",
        "",
        "- account: Tradeify Select 50K evaluation;",
        "- objective: `$3000` net profit with `$2000` EOD trailing drawdown and `40%` consistency;",
        "- execution limit used for sizing: at most `20 MNQ`, matching funded day-one size rather than the looser `40 MNQ` evaluation limit;",
        "- frequency: at most one completed trade per session;",
        "- base costs: Tradeify `$1.82` MNQ round trip plus `2` total slippage ticks per contract;",
        "- stress costs: Tradeify `$1.82` MNQ round trip plus `6` total slippage ticks per contract;",
        "- ambiguous target/stop bar: stop first;",
        "- all positions flattened by `15:45 America/New_York`;",
        "- final holdout is not used by the selection ranking.",
        "",
        "## Data And Split",
        "",
        f"- source rows: `{len(bars)}`;",
        f"- dates: `{trade_dates[0]}` through `{trade_dates[-1]}`;",
        f"- unique dates: `{len(trade_dates)}`;",
        f"- training: `{train_dates[0]}` through `{train_dates[-1]}` (`{len(train_dates)}` dates);",
        f"- validation: `{validation_dates[0]}` through `{validation_dates[-1]}` (`{len(validation_dates)}` dates);",
        f"- untouched final holdout: `{holdout_dates[0]}` through `{holdout_dates[-1]}` (`{len(holdout_dates)}` dates).",
        "",
        "## Fresh Families",
        "",
        "The pass tests opening-drive pullbacks, prior-session liquidity sweeps, gap-fade acceptance, and VWAP trend pullbacks. These are separate from the frozen legacy MNQ bot rules.",
        "",
        f"Generated signal sets: `{len(signal_sets)}`.",
        f"Evaluated strategy/exit rows: `{len(rows)}`.",
        "",
        "| Family | Trades | /Wk | Dev Net | Dev PF | Dev DD | Holdout Net | Holdout PF | Holdout DD | Exit | Eligible |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in family_leaders:
        lines.append(
            "| "
            f"`{row['family']}` | {row['full_trades']} | {row['trades_per_week']} | "
            f"{row['development_net_usd']} | {row['development_profit_factor']} | "
            f"{row['development_max_drawdown_usd']} | {row['holdout_net_usd']} | "
            f"{row['holdout_profit_factor']} | {row['holdout_max_drawdown_usd']} | "
            f"`{row['target_points']}/{row['stop_points']}` | "
            f"{'yes' if row['selection_eligible'] else 'no'} |",
        )

    lines.extend(["", "## Frozen Selection", ""])
    if selected_row is None:
        lines.extend(
            [
                "No row passed the predeclared development eligibility screen. Nothing is promoted.",
                "",
                "This is a valid rejection, not a NinjaTrader build candidate.",
            ],
        )
        Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    lines.extend(
        [
            f"Frozen rule: `{selected_row['strategy_id']}` with `{selected_row['target_points']}/{selected_row['stop_points']}` target/stop points.",
            "",
            "The ranking used training and validation only. Holdout metrics below are the first-read result for the selected row.",
            "",
            "| Period | Trades | Net 1 MNQ | PF | Win | DD |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
            f"| Training | {selected_row['train_trades']} | {selected_row['train_net_usd']} | {selected_row['train_profit_factor']} | {float(selected_row['train_win_rate']) * 100:.1f}% | {selected_row['train_max_drawdown_usd']} |",
            f"| Validation | {selected_row['validation_trades']} | {selected_row['validation_net_usd']} | {selected_row['validation_profit_factor']} | {float(selected_row['validation_win_rate']) * 100:.1f}% | {selected_row['validation_max_drawdown_usd']} |",
            f"| Final holdout | {selected_row['holdout_trades']} | {selected_row['holdout_net_usd']} | {selected_row['holdout_profit_factor']} | {float(selected_row['holdout_win_rate']) * 100:.1f}% | {selected_row['holdout_max_drawdown_usd']} |",
            f"| Full sample | {selected_row['full_trades']} | {selected_row['full_net_usd']} | {selected_row['full_profit_factor']} | {float(selected_row['full_win_rate']) * 100:.1f}% | {selected_row['full_max_drawdown_usd']} |",
            "",
            f"Average hold: `{_fmt(statistics.mean(outcome.holding_minutes for outcome in selected_outcomes))}` minutes; median hold: `{_fmt(statistics.median(outcome.holding_minutes for outcome in selected_outcomes))}` minutes.",
            "",
            "## Tradeify Sizing",
            "",
            "Sizing is restricted to the funded day-one maximum and rejects a nominal stop above `$450`, a nominal target above `$1100`, full-sample DD below `-$1500`, or stress Monte Carlo eval-fail rate above `20%`.",
            "",
            "| MNQ | Stop | Target | Net | DD | Hist Pass | Hist Fail | Median Days | MC Pass | MC Fail | Funded Lock | Risk |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ],
    )
    for row in sizing_rows:
        lines.append(
            "| "
            f"{row['quantity']} | {row['stop_loss_usd']} | {row['target_profit_usd']} | "
            f"{row['net_usd']} | {row['max_drawdown_usd']} | "
            f"{float(row['historical_pass_rate']) * 100:.1f}% | "
            f"{float(row['historical_fail_rate']) * 100:.1f}% | "
            f"{row['historical_median_calendar_days']} | "
            f"{float(row['monte_carlo_pass_rate']) * 100:.1f}% | "
            f"{float(row['monte_carlo_fail_rate']) * 100:.1f}% | "
            f"{float(row['funded_lock_rate']) * 100:.1f}% | "
            f"{'eligible' if row['risk_eligible'] else 'reject'} |",
        )

    lines.extend(["", "## Stress Decision", ""])
    selected_quantity = int(stress.get("selected_quantity", 0))
    if selected_quantity == 0:
        lines.append(
            "No quantity passed the account-risk sizing screen. The strategy is rejected."
        )
    else:
        base = stress["base_metrics"]
        stressed = stress["stress_metrics"]
        holdout_stressed = stress["holdout_stress_metrics"]
        assert isinstance(base, PeriodMetrics)
        assert isinstance(stressed, PeriodMetrics)
        assert isinstance(holdout_stressed, PeriodMetrics)
        promoted = (
            float(selected_row["holdout_net_usd"]) > 0.0
            and float(selected_row["holdout_profit_factor"]) >= 1.30
            and selected_row["holdout_trades"] >= 20
            and stressed.profit_factor >= 1.45
            and holdout_stressed.net_usd > 0.0
            and holdout_stressed.profit_factor >= 1.20
            and float(stress["monte_carlo_p95_drawdown"]) > -TRADEIFY_MAX_DRAWDOWN_USD
            and bool(stress["all_years_positive"])
        )
        lines.extend(
            [
                f"Selected research size: `{selected_quantity} MNQ`.",
                "",
                "| Test | Net | PF | Win | DD |",
                "| --- | ---: | ---: | ---: | ---: |",
                f"| Base full sample | {_fmt(base.net_usd)} | {_fmt(base.profit_factor)} | {base.win_rate * 100:.1f}% | {_fmt(base.max_drawdown_usd)} |",
                f"| Six-tick stress full sample | {_fmt(stressed.net_usd)} | {_fmt(stressed.profit_factor)} | {stressed.win_rate * 100:.1f}% | {_fmt(stressed.max_drawdown_usd)} |",
                f"| Six-tick stress holdout | {_fmt(holdout_stressed.net_usd)} | {_fmt(holdout_stressed.profit_factor)} | {holdout_stressed.win_rate * 100:.1f}% | {_fmt(holdout_stressed.max_drawdown_usd)} |",
                f"| Shuffled median DD | {_fmt(float(stress['monte_carlo_median_drawdown']))} |  |  |  |",
                f"| Shuffled P95 DD | {_fmt(float(stress['monte_carlo_p95_drawdown']))} |  |  |  |",
                f"| Shuffled P99 DD | {_fmt(float(stress['monte_carlo_p99_drawdown']))} |  |  |  |",
                "",
                f"Research verdict: `{'PROMOTE_TO_DEEP_VALIDATION' if promoted else 'REJECT_OR_REFINE'}`.",
            ],
        )
        if promoted:
            lines.extend(
                [
                    "",
                    "This is a non-rejected strategy research candidate, not permission to trade it. Before NinjaTrader implementation it still needs nearby-parameter sensitivity, rolling walk-forward selection, news/regime attribution, and fresh-platform replay.",
                ],
            )
        else:
            lines.extend(
                [
                    "",
                    "The frozen row did not clear every final gate. Do not build it in NinjaTrader as the production bot.",
                ],
            )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _split_dates(trade_dates: list[date]) -> tuple[list[date], list[date], list[date]]:
    train_end = max(1, int(len(trade_dates) * 0.50))
    validation_end = max(train_end + 1, int(len(trade_dates) * 0.75))
    return (
        trade_dates[:train_end],
        trade_dates[train_end:validation_end],
        trade_dates[validation_end:],
    )


def _outcomes_for_dates(
    outcomes: list[PathOutcome],
    dates: set[date],
) -> list[PathOutcome]:
    return [outcome for outcome in outcomes if outcome.entry_time.date() in dates]


def _mnq_net(
    outcome: PathOutcome,
    quantity: int,
    *,
    total_slippage_ticks: int,
) -> float:
    return outcome.gross_points * MNQ_POINT_VALUE_USD * quantity - _mnq_cost(
        quantity, total_slippage_ticks
    )


def _mnq_cost(quantity: int, total_slippage_ticks: int) -> float:
    return quantity * (
        MNQ_ROUND_TURN_FEE_USD + total_slippage_ticks * MNQ_TICK_VALUE_USD
    )


def _max_drawdown(values: Iterable[float]) -> float:
    equity = 0.0
    peak = 0.0
    drawdown = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = min(drawdown, equity - peak)
    return drawdown


def _max_loss_streak(values: Iterable[float]) -> int:
    longest = 0
    current = 0
    for value in values:
        if value < 0.0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _close_location(low: float, high: float, close: float) -> float:
    return (close - low) / (high - low) if high > low else 0.5


def _row_key(row: dict[str, object]) -> tuple[str, float, float]:
    return (
        str(row["strategy_id"]),
        float(row["target_points"]),
        float(row["stop_points"]),
    )


def _time_id(value: time) -> str:
    return value.strftime("%H%M")


def _percentile(sorted_values: list[float], fraction: float) -> float:
    if not sorted_values:
        return 0.0
    index = min(max(int(len(sorted_values) * fraction), 0), len(sorted_values) - 1)
    return sorted_values[index]


def _fmt(value: float) -> str:
    if not math.isfinite(value):
        return str(value)
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.8f}".rstrip("0").rstrip(".")


def _write_csv(path: str, header: list[str], rows: list[dict[str, object]]) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def _write_audit(path: str, outcomes: list[PathOutcome]) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUDIT_HEADER)
        writer.writeheader()
        for outcome in outcomes:
            writer.writerow(
                {
                    "schema_version": 1,
                    "strategy_id": outcome.strategy_id,
                    "family": outcome.family,
                    "direction": outcome.direction,
                    "entry_time": outcome.entry_time.isoformat(sep=" "),
                    "exit_time": outcome.exit_time.isoformat(sep=" "),
                    "entry_bar_index": outcome.entry_bar_index,
                    "exit_bar_index": outcome.exit_bar_index,
                    "entry_price": _fmt(outcome.entry_price),
                    "exit_price": _fmt(outcome.exit_price),
                    "target_price": _fmt(outcome.target_price),
                    "stop_price": _fmt(outcome.stop_price),
                    "exit_reason": outcome.exit_reason,
                    "holding_minutes": _fmt(outcome.holding_minutes),
                    "gross_points": _fmt(outcome.gross_points),
                    "base_net_1_mnq_usd": _fmt(
                        _mnq_net(
                            outcome,
                            1,
                            total_slippage_ticks=BASE_TOTAL_SLIPPAGE_TICKS,
                        ),
                    ),
                    "notes": outcome.notes,
                },
            )


if __name__ == "__main__":
    raise SystemExit(main())
