#!/usr/bin/env python3
"""Fresh MNQ strategy-family research outside the current bot direction."""

from __future__ import annotations

import argparse
import csv
import math
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


DEFAULT_OUTPUT = "reports/mnq-fresh-strategy-research.csv"
DEFAULT_REPORT = "reports/mnq-fresh-strategy-research.md"
DEFAULT_TRADE_AUDIT = "reports/mnq-fresh-strategy-research-best-trade-audit.csv"
POINT_VALUE_USD = wave.POINT_VALUE_USD
TICK_VALUE_USD = wave.TICK_VALUE_USD
COMMISSION_PER_SIDE_USD = wave.COMMISSION_PER_SIDE_USD
SLIPPAGE_TICKS_PER_CONTRACT = wave.SLIPPAGE_TICKS_PER_CONTRACT
ROUND_TURN_COST_PER_CONTRACT = (
    2.0 * COMMISSION_PER_SIDE_USD + SLIPPAGE_TICKS_PER_CONTRACT * TICK_VALUE_USD
)
FLATTEN_TIME = wave.FLATTEN_TIME
NY_OPEN = time(9, 30)


@dataclass(frozen=True)
class RiskProfile:
    quantity: int
    target_points: float
    stop_points: float
    round_turn_cost_usd: float


@dataclass(frozen=True)
class Outcome:
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
    net_usd: float
    notes: str


@dataclass(frozen=True)
class SampleInfo:
    weeks: float
    latest_year: int


SUMMARY_HEADER = [
    "schema_version",
    "strategy_id",
    "family",
    "quantity",
    "target_points",
    "stop_points",
    "raw_signals",
    "trades",
    "trades_per_week",
    "win_rate",
    "target_rate",
    "stop_rate",
    "eod_rate",
    "net_usd",
    "average_trade_usd",
    "profit_factor",
    "max_drawdown_usd",
    "net_to_drawdown",
    "latest_year",
    "latest_year_trades",
    "latest_year_net_usd",
    "worst_year_net_usd",
    "worst_quarter_net_usd",
    "worst_month_net_usd",
    "worst_day_usd",
    "max_loss_streak",
    "average_holding_minutes",
    "median_holding_minutes",
    "max_trades_per_day",
    "promotion_lens",
]


TRADE_AUDIT_HEADER = [
    "schema_version",
    "strategy_id",
    "family",
    "quantity",
    "target_points",
    "stop_points",
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
    "net_usd",
    "notes",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run fresh MNQ research across ORB, noise-area momentum, compression, "
            "VWAP reclaim, and failed-breakout families."
        ),
    )
    parser.add_argument("input", nargs="?", default=wave.DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT)
    parser.add_argument("--trade-audit-output", default=DEFAULT_TRADE_AUDIT)
    parser.add_argument("--symbol", default="MNQU26-CME")
    parser.add_argument("--minimum-raw-signals", type=int, default=120)
    parser.add_argument("--minimum-trades", type=int, default=120)
    args = parser.parse_args()

    bars = wave._load_feature_bars(args.input)
    bars_by_date = wave._bars_by_date(bars)
    rows_by_index = _rows_by_global_index(bars_by_date)
    sample_info = _sample_info(bars)
    signal_sets = _generate_signal_sets(bars_by_date, symbol=args.symbol)
    print(
        "generated "
        f"{len(signal_sets)} fresh MNQ signal sets with "
        f"{sum(len(signals) for signals in signal_sets.values())} raw signals",
        flush=True,
    )
    risks = _risk_profiles()

    rows: list[dict[str, object]] = []
    best_row: dict[str, object] | None = None
    best_outcomes: list[Outcome] = []
    for strategy_id, signals in signal_sets.items():
        if len(signals) < args.minimum_raw_signals:
            continue
        family = strategy_id.split(":", 1)[0]
        for max_trades_per_day in (1, 2):
            for risk in risks:
                outcomes = _evaluate_signals(
                    signals,
                    bars_by_date,
                    rows_by_index,
                    risk,
                    family=family,
                    max_trades_per_day=max_trades_per_day,
                )
                if len(outcomes) < args.minimum_trades:
                    continue
                row = _summary_row(
                    strategy_id,
                    family,
                    len(signals),
                    outcomes,
                    risk,
                    sample_info,
                    max_trades_per_day=max_trades_per_day,
                )
                rows.append(row)
                if _is_better(row, best_row):
                    best_row = row
                    best_outcomes = outcomes

    rows.sort(key=_ranking_key)
    _write_csv(args.output, SUMMARY_HEADER, rows)
    if best_row is not None:
        _write_trade_audit(args.trade_audit_output, best_row, best_outcomes)
    _write_report(args.report_output, bars, signal_sets, rows, best_row)
    best_summary = "none"
    if best_row is not None:
        best_summary = (
            f"{best_row['strategy_id']} q={best_row['quantity']} "
            f"t={best_row['target_points']} s={best_row['stop_points']} "
            f"trades={best_row['trades']} net={best_row['net_usd']} "
            f"pf={best_row['profit_factor']} dd={best_row['max_drawdown_usd']}"
        )
    print(
        f"wrote {len(rows)} fresh MNQ research rows to {args.output}; "
        f"best={best_summary}",
    )
    return 0


def _generate_signal_sets(
    bars_by_date: dict[date, list[wave.Bar]],
    *,
    symbol: str,
) -> dict[str, list[wave.Signal]]:
    signal_sets: dict[str, list[wave.Signal]] = {}
    for skip_friday in (False, True):
        for spacing_minutes in (30, 60):
            for entry_end in (time(12, 30), time(14, 30)):
                for or_minutes in (15, 30):
                    for min_width in (20.0, 40.0):
                        for buffer_points in (0.0, 5.0):
                            for delta_threshold in (0.0, 600.0):
                                for close_location_threshold in (0.55,):
                                    strategy_id = (
                                        "fresh_orb_continuation:"
                                        f"or{or_minutes}:minw{min_width:g}:"
                                        f"buf{buffer_points:g}:delta{delta_threshold:g}:"
                                        f"cl{close_location_threshold:g}:"
                                        f"end{_time_id(entry_end)}:"
                                        f"space{spacing_minutes}:skipfri{int(skip_friday)}"
                                    )
                                    signal_sets[strategy_id] = _orb_continuation_signals(
                                        bars_by_date,
                                        strategy_id=strategy_id,
                                        or_minutes=or_minutes,
                                        min_width=min_width,
                                        buffer_points=buffer_points,
                                        delta_threshold=delta_threshold,
                                        close_location_threshold=close_location_threshold,
                                        entry_end=entry_end,
                                        spacing_minutes=spacing_minutes,
                                        skip_friday=skip_friday,
                                        symbol=symbol,
                                    )

                    for max_width in (30.0, 50.0):
                        for buffer_points in (0.0, 5.0):
                            for delta_threshold in (0.0, 600.0):
                                for close_location_threshold in (0.55,):
                                    strategy_id = (
                                        "fresh_compression_breakout:"
                                        f"or{or_minutes}:maxw{max_width:g}:"
                                        f"buf{buffer_points:g}:delta{delta_threshold:g}:"
                                        f"cl{close_location_threshold:g}:"
                                        f"end{_time_id(entry_end)}:"
                                        f"space{spacing_minutes}:skipfri{int(skip_friday)}"
                                    )
                                    signal_sets[strategy_id] = _orb_continuation_signals(
                                        bars_by_date,
                                        strategy_id=strategy_id,
                                        or_minutes=or_minutes,
                                        min_width=0.0,
                                        max_width=max_width,
                                        buffer_points=buffer_points,
                                        delta_threshold=delta_threshold,
                                        close_location_threshold=close_location_threshold,
                                        entry_end=entry_end,
                                        spacing_minutes=spacing_minutes,
                                        skip_friday=skip_friday,
                                        symbol=symbol,
                                    )

                    for reclaim_mode in ("edge", "mid"):
                        for buffer_points in (5.0,):
                            for delta_threshold in (0.0, 600.0):
                                strategy_id = (
                                    "fresh_failed_or_reversal:"
                                    f"or{or_minutes}:mode{reclaim_mode}:"
                                    f"buf{buffer_points:g}:delta{delta_threshold:g}:"
                                    f"end{_time_id(entry_end)}:"
                                    f"space{spacing_minutes}:skipfri{int(skip_friday)}"
                                )
                                signal_sets[strategy_id] = _failed_or_reversal_signals(
                                    bars_by_date,
                                    strategy_id=strategy_id,
                                    or_minutes=or_minutes,
                                    reclaim_mode=reclaim_mode,
                                    buffer_points=buffer_points,
                                    delta_threshold=delta_threshold,
                                    entry_end=entry_end,
                                    spacing_minutes=spacing_minutes,
                                    skip_friday=skip_friday,
                                    symbol=symbol,
                                )

                for lookback_days in (10, 20):
                    for noise_multiple in (1.0, 1.25):
                        for entry_start in (time(9, 45), time(10, 0)):
                            for delta_threshold in (0.0, 600.0):
                                for close_location_threshold in (0.55,):
                                    strategy_id = (
                                        "fresh_noise_area_momentum:"
                                        f"lb{lookback_days}:mult{noise_multiple:g}:"
                                        f"delta{delta_threshold:g}:"
                                        f"cl{close_location_threshold:g}:"
                                        f"start{_time_id(entry_start)}:"
                                        f"end{_time_id(entry_end)}:"
                                        f"space{spacing_minutes}:skipfri{int(skip_friday)}"
                                    )
                                    signal_sets[strategy_id] = _noise_area_signals(
                                        bars_by_date,
                                        strategy_id=strategy_id,
                                        lookback_days=lookback_days,
                                        noise_multiple=noise_multiple,
                                        delta_threshold=delta_threshold,
                                        close_location_threshold=close_location_threshold,
                                        entry_start=entry_start,
                                        entry_end=entry_end,
                                        spacing_minutes=spacing_minutes,
                                        skip_friday=skip_friday,
                                        symbol=symbol,
                                    )

                for stretch_points in (50.0, 80.0):
                    for reclaim_points in (0.0, 10.0):
                        for delta_threshold in (0.0, 600.0):
                            for close_location_threshold in (0.45,):
                                strategy_id = (
                                    "fresh_vwap_reclaim_reversal:"
                                    f"stretch{stretch_points:g}:"
                                    f"reclaim{reclaim_points:g}:"
                                    f"delta{delta_threshold:g}:"
                                    f"cl{close_location_threshold:g}:"
                                    f"end{_time_id(entry_end)}:"
                                    f"space{spacing_minutes}:skipfri{int(skip_friday)}"
                                )
                                signal_sets[strategy_id] = _vwap_reclaim_reversal_signals(
                                    bars_by_date,
                                    strategy_id=strategy_id,
                                    stretch_points=stretch_points,
                                    reclaim_points=reclaim_points,
                                    delta_threshold=delta_threshold,
                                    close_location_threshold=close_location_threshold,
                                    entry_end=entry_end,
                                    spacing_minutes=spacing_minutes,
                                    skip_friday=skip_friday,
                                    symbol=symbol,
                                )

                for min_range in (25.0, 40.0):
                    for delta_threshold in (1500.0, 2200.0):
                        for failed_close_location in (0.35, 0.45):
                            strategy_id = (
                                "fresh_delta_exhaustion_reversal:"
                                f"range{min_range:g}:delta{delta_threshold:g}:"
                                f"failcl{failed_close_location:g}:"
                                f"end{_time_id(entry_end)}:"
                                f"space{spacing_minutes}:skipfri{int(skip_friday)}"
                            )
                            signal_sets[strategy_id] = _delta_exhaustion_reversal_signals(
                                bars_by_date,
                                strategy_id=strategy_id,
                                min_range=min_range,
                                delta_threshold=delta_threshold,
                                failed_close_location=failed_close_location,
                                entry_end=entry_end,
                                spacing_minutes=spacing_minutes,
                                skip_friday=skip_friday,
                                symbol=symbol,
                            )
    return signal_sets


def _orb_continuation_signals(
    bars_by_date: dict[date, list[wave.Bar]],
    *,
    strategy_id: str,
    or_minutes: int,
    min_width: float,
    buffer_points: float,
    delta_threshold: float,
    close_location_threshold: float,
    entry_end: time,
    spacing_minutes: int,
    skip_friday: bool,
    symbol: str,
    max_width: float | None = None,
) -> list[wave.Signal]:
    signals = []
    for rows in bars_by_date.values():
        if _skip_day(rows, skip_friday=skip_friday):
            continue
        opening_range = _opening_range(rows, or_minutes)
        if opening_range is None:
            continue
        or_high, or_low, or_end = opening_range
        width = or_high - or_low
        if width < min_width:
            continue
        if max_width is not None and width > max_width:
            continue
        high_break = or_high + buffer_points
        low_break = or_low - buffer_points
        previous_close = None
        last_signal_time = datetime.min
        for row in rows:
            row_time = row.timestamp.time()
            if row_time <= or_end or row_time > entry_end:
                previous_close = row.close
                continue
            if not _spacing_ok(row, last_signal_time, spacing_minutes):
                previous_close = row.close
                continue
            if previous_close is not None:
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
                            f"{symbol} fresh OR continuation long width={width:g}",
                        ),
                    )
                    last_signal_time = row.timestamp
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
                            f"{symbol} fresh OR continuation short width={width:g}",
                        ),
                    )
                    last_signal_time = row.timestamp
            previous_close = row.close
    return signals


def _failed_or_reversal_signals(
    bars_by_date: dict[date, list[wave.Bar]],
    *,
    strategy_id: str,
    or_minutes: int,
    reclaim_mode: str,
    buffer_points: float,
    delta_threshold: float,
    entry_end: time,
    spacing_minutes: int,
    skip_friday: bool,
    symbol: str,
) -> list[wave.Signal]:
    signals = []
    for rows in bars_by_date.values():
        if _skip_day(rows, skip_friday=skip_friday):
            continue
        opening_range = _opening_range(rows, or_minutes)
        if opening_range is None:
            continue
        or_high, or_low, or_end = opening_range
        midpoint = (or_high + or_low) / 2.0
        high_break = or_high + buffer_points
        low_break = or_low - buffer_points
        high_reclaim = midpoint if reclaim_mode == "mid" else or_high
        low_reclaim = midpoint if reclaim_mode == "mid" else or_low
        broke_high = False
        broke_low = False
        last_signal_time = datetime.min
        for row in rows:
            row_time = row.timestamp.time()
            if row_time <= or_end or row_time > entry_end:
                continue
            if row.high >= high_break:
                broke_high = True
            if row.low <= low_break:
                broke_low = True
            if not _spacing_ok(row, last_signal_time, spacing_minutes):
                continue
            if (
                broke_high
                and row.close < high_reclaim
                and row.delta <= -delta_threshold
                and row.close_location <= 0.45
            ):
                signals.append(
                    wave.Signal(
                        strategy_id,
                        "short",
                        row,
                        f"{symbol} failed OR high reversal mode={reclaim_mode}",
                    ),
                )
                broke_high = False
                last_signal_time = row.timestamp
            elif (
                broke_low
                and row.close > low_reclaim
                and row.delta >= delta_threshold
                and row.close_location >= 0.55
            ):
                signals.append(
                    wave.Signal(
                        strategy_id,
                        "long",
                        row,
                        f"{symbol} failed OR low reversal mode={reclaim_mode}",
                    ),
                )
                broke_low = False
                last_signal_time = row.timestamp
    return signals


def _noise_area_signals(
    bars_by_date: dict[date, list[wave.Bar]],
    *,
    strategy_id: str,
    lookback_days: int,
    noise_multiple: float,
    delta_threshold: float,
    close_location_threshold: float,
    entry_start: time,
    entry_end: time,
    spacing_minutes: int,
    skip_friday: bool,
    symbol: str,
) -> list[wave.Signal]:
    signals = []
    history_by_time: dict[time, list[float]] = defaultdict(list)
    for trade_date in sorted(bars_by_date):
        rows = bars_by_date[trade_date]
        if not rows:
            continue
        day_open = _day_open(rows)
        last_signal_time = datetime.min
        if not _skip_day(rows, skip_friday=skip_friday):
            for row in rows:
                row_time = row.timestamp.time()
                if row_time < entry_start or row_time > entry_end:
                    continue
                history = history_by_time[row_time]
                if len(history) < max(5, lookback_days // 2):
                    continue
                recent_noise = history[-lookback_days:]
                noise = statistics.mean(recent_noise) * noise_multiple
                if not _spacing_ok(row, last_signal_time, spacing_minutes):
                    continue
                move = row.close - day_open
                if (
                    move >= noise
                    and row.close >= row.vwap
                    and row.delta >= delta_threshold
                    and row.close_location >= close_location_threshold
                ):
                    signals.append(
                        wave.Signal(
                            strategy_id,
                            "long",
                            row,
                            f"{symbol} noise-area momentum long noise={noise:g}",
                        ),
                    )
                    last_signal_time = row.timestamp
                elif (
                    move <= -noise
                    and row.close <= row.vwap
                    and row.delta <= -delta_threshold
                    and row.close_location <= 1.0 - close_location_threshold
                ):
                    signals.append(
                        wave.Signal(
                            strategy_id,
                            "short",
                            row,
                            f"{symbol} noise-area momentum short noise={noise:g}",
                        ),
                    )
                    last_signal_time = row.timestamp
        for row in rows:
            history_by_time[row.timestamp.time()].append(abs(row.close - day_open))
    return signals


def _vwap_reclaim_reversal_signals(
    bars_by_date: dict[date, list[wave.Bar]],
    *,
    strategy_id: str,
    stretch_points: float,
    reclaim_points: float,
    delta_threshold: float,
    close_location_threshold: float,
    entry_end: time,
    spacing_minutes: int,
    skip_friday: bool,
    symbol: str,
) -> list[wave.Signal]:
    signals = []
    for rows in bars_by_date.values():
        if _skip_day(rows, skip_friday=skip_friday):
            continue
        stretched_high = False
        stretched_low = False
        last_signal_time = datetime.min
        for row in rows:
            row_time = row.timestamp.time()
            dist = row.close - row.vwap
            if dist >= stretch_points:
                stretched_high = True
            if dist <= -stretch_points:
                stretched_low = True
            if row_time < time(9, 45) or row_time > entry_end:
                continue
            if not _spacing_ok(row, last_signal_time, spacing_minutes):
                continue
            if (
                stretched_high
                and row.close <= row.vwap + reclaim_points
                and row.delta <= -delta_threshold
                and row.close_location <= close_location_threshold
            ):
                signals.append(
                    wave.Signal(
                        strategy_id,
                        "short",
                        row,
                        f"{symbol} VWAP reclaim short stretch={stretch_points:g}",
                    ),
                )
                stretched_high = False
                last_signal_time = row.timestamp
            elif (
                stretched_low
                and row.close >= row.vwap - reclaim_points
                and row.delta >= delta_threshold
                and row.close_location >= 1.0 - close_location_threshold
            ):
                signals.append(
                    wave.Signal(
                        strategy_id,
                        "long",
                        row,
                        f"{symbol} VWAP reclaim long stretch={stretch_points:g}",
                    ),
                )
                stretched_low = False
                last_signal_time = row.timestamp
    return signals


def _delta_exhaustion_reversal_signals(
    bars_by_date: dict[date, list[wave.Bar]],
    *,
    strategy_id: str,
    min_range: float,
    delta_threshold: float,
    failed_close_location: float,
    entry_end: time,
    spacing_minutes: int,
    skip_friday: bool,
    symbol: str,
) -> list[wave.Signal]:
    signals = []
    for rows in bars_by_date.values():
        if _skip_day(rows, skip_friday=skip_friday):
            continue
        last_signal_time = datetime.min
        for row in rows:
            row_time = row.timestamp.time()
            if row_time < time(9, 45) or row_time > entry_end:
                continue
            if not _spacing_ok(row, last_signal_time, spacing_minutes):
                continue
            bar_range = row.high - row.low
            if bar_range < min_range:
                continue
            if (
                row.delta >= delta_threshold
                and row.close_location <= failed_close_location
                and row.close >= row.vwap
            ):
                signals.append(
                    wave.Signal(
                        strategy_id,
                        "short",
                        row,
                        f"{symbol} delta exhaustion short range={bar_range:g}",
                    ),
                )
                last_signal_time = row.timestamp
            elif (
                row.delta <= -delta_threshold
                and row.close_location >= 1.0 - failed_close_location
                and row.close <= row.vwap
            ):
                signals.append(
                    wave.Signal(
                        strategy_id,
                        "long",
                        row,
                        f"{symbol} delta exhaustion long range={bar_range:g}",
                    ),
                )
                last_signal_time = row.timestamp
    return signals


def _risk_profiles() -> list[RiskProfile]:
    profiles = []
    quantity = 2
    round_turn_cost = quantity * ROUND_TURN_COST_PER_CONTRACT
    for target_points, stop_points in (
        (20.0, 15.0),
        (30.0, 20.0),
        (40.0, 20.0),
        (40.0, 30.0),
        (60.0, 30.0),
        (60.0, 40.0),
        (80.0, 40.0),
        (80.0, 60.0),
        (120.0, 60.0),
    ):
        profiles.append(
            RiskProfile(
                quantity=quantity,
                target_points=target_points,
                stop_points=stop_points,
                round_turn_cost_usd=round_turn_cost,
            ),
        )
    return profiles


def _evaluate_signals(
    signals: list[wave.Signal],
    bars_by_date: dict[date, list[wave.Bar]],
    rows_by_index: dict[int, int],
    risk: RiskProfile,
    *,
    family: str,
    max_trades_per_day: int,
) -> list[Outcome]:
    outcomes = []
    next_available_time = datetime.min
    trades_by_date: dict[date, int] = defaultdict(int)
    for signal in sorted(signals, key=lambda value: value.bar.timestamp):
        signal_date = signal.bar.trade_date
        if signal.bar.timestamp <= next_available_time:
            continue
        if trades_by_date[signal_date] >= max_trades_per_day:
            continue
        day_rows = bars_by_date[signal_date]
        local_index = rows_by_index[signal.bar.index]
        following_rows = [
            row
            for row in day_rows[local_index + 1:]
            if row.timestamp.time() <= FLATTEN_TIME
        ]
        outcome = _evaluate_signal(signal, following_rows, risk, family=family)
        outcomes.append(outcome)
        trades_by_date[signal_date] += 1
        next_available_time = outcome.exit_time
    return outcomes


def _evaluate_signal(
    signal: wave.Signal,
    following_rows: list[wave.Bar],
    risk: RiskProfile,
    *,
    family: str,
) -> Outcome:
    is_long = signal.direction == "long"
    entry_price = signal.bar.close
    target_price = entry_price + risk.target_points if is_long else entry_price - risk.target_points
    stop_price = entry_price - risk.stop_points if is_long else entry_price + risk.stop_points
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
    net_usd = gross_points * POINT_VALUE_USD * risk.quantity - risk.round_turn_cost_usd
    return Outcome(
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
        holding_minutes=(exit_bar.timestamp - signal.bar.timestamp).total_seconds() / 60.0,
        gross_points=gross_points,
        net_usd=net_usd,
        notes=signal.notes,
    )


def _summary_row(
    strategy_id: str,
    family: str,
    raw_signals: int,
    outcomes: list[Outcome],
    risk: RiskProfile,
    sample: SampleInfo,
    *,
    max_trades_per_day: int,
) -> dict[str, object]:
    net_values = [outcome.net_usd for outcome in outcomes]
    positives = [value for value in net_values if value > 0.0]
    negatives = [value for value in net_values if value < 0.0]
    yearly: dict[int, float] = defaultdict(float)
    quarterly: dict[tuple[int, int], float] = defaultdict(float)
    monthly: dict[tuple[int, int], float] = defaultdict(float)
    daily: dict[date, float] = defaultdict(float)
    latest_year_trades = 0
    for outcome in outcomes:
        entry_date = outcome.entry_time.date()
        yearly[outcome.entry_time.year] += outcome.net_usd
        quarterly[(outcome.entry_time.year, (outcome.entry_time.month - 1) // 3 + 1)] += (
            outcome.net_usd
        )
        monthly[(outcome.entry_time.year, outcome.entry_time.month)] += outcome.net_usd
        daily[entry_date] += outcome.net_usd
        if outcome.entry_time.year == sample.latest_year:
            latest_year_trades += 1
    drawdown = _max_drawdown(net_values)
    net = sum(net_values)
    pf = sum(positives) / abs(sum(negatives)) if negatives else 999.0
    trades_per_week = len(outcomes) / sample.weeks if sample.weeks else 0.0
    promotion = _promotion_lens(
        trades=len(outcomes),
        trades_per_week=trades_per_week,
        net=net,
        pf=pf,
        drawdown=drawdown,
        latest_year_net=yearly.get(sample.latest_year, 0.0),
        worst_quarter=min(quarterly.values()) if quarterly else 0.0,
    )
    return {
        "schema_version": 1,
        "strategy_id": strategy_id,
        "family": family,
        "quantity": risk.quantity,
        "target_points": _fmt(risk.target_points),
        "stop_points": _fmt(risk.stop_points),
        "raw_signals": raw_signals,
        "trades": len(outcomes),
        "trades_per_week": _fmt(trades_per_week),
        "win_rate": _fmt(len(positives) / len(outcomes) if outcomes else 0.0),
        "target_rate": _fmt(
            sum(outcome.exit_reason == "target_hit" for outcome in outcomes) / len(outcomes)
            if outcomes
            else 0.0,
        ),
        "stop_rate": _fmt(
            sum(outcome.exit_reason == "stop_hit" for outcome in outcomes) / len(outcomes)
            if outcomes
            else 0.0,
        ),
        "eod_rate": _fmt(
            sum(
                outcome.exit_reason in {"end_of_session", "no_following_bar"}
                for outcome in outcomes
            )
            / len(outcomes)
            if outcomes
            else 0.0,
        ),
        "net_usd": _fmt(net),
        "average_trade_usd": _fmt(statistics.mean(net_values) if net_values else 0.0),
        "profit_factor": _fmt(pf),
        "max_drawdown_usd": _fmt(drawdown),
        "net_to_drawdown": _fmt(net / abs(drawdown) if drawdown < 0 else 999.0),
        "latest_year": sample.latest_year,
        "latest_year_trades": latest_year_trades,
        "latest_year_net_usd": _fmt(yearly.get(sample.latest_year, 0.0)),
        "worst_year_net_usd": _fmt(min(yearly.values()) if yearly else 0.0),
        "worst_quarter_net_usd": _fmt(min(quarterly.values()) if quarterly else 0.0),
        "worst_month_net_usd": _fmt(min(monthly.values()) if monthly else 0.0),
        "worst_day_usd": _fmt(min(daily.values()) if daily else 0.0),
        "max_loss_streak": _max_loss_streak(net_values),
        "average_holding_minutes": _fmt(
            statistics.mean(outcome.holding_minutes for outcome in outcomes)
            if outcomes
            else 0.0,
        ),
        "median_holding_minutes": _fmt(
            statistics.median(outcome.holding_minutes for outcome in outcomes)
            if outcomes
            else 0.0,
        ),
        "max_trades_per_day": max_trades_per_day,
        "promotion_lens": promotion,
    }


def _promotion_lens(
    *,
    trades: int,
    trades_per_week: float,
    net: float,
    pf: float,
    drawdown: float,
    latest_year_net: float,
    worst_quarter: float,
) -> str:
    failures = []
    if trades < 200:
        failures.append("trades<200")
    if trades_per_week < 2.0:
        failures.append("freq<2/wk")
    if net <= 0:
        failures.append("net<=0")
    if pf < 1.6:
        failures.append("pf<1.6")
    if drawdown < -1000:
        failures.append("dd<-1000")
    if latest_year_net <= 0:
        failures.append("latest<=0")
    if worst_quarter < -750:
        failures.append("worstQ<-750")
    return "promote" if not failures else "reject:" + ",".join(failures)


def _write_report(
    path: str,
    bars: list[wave.Bar],
    signal_sets: dict[str, list[wave.Signal]],
    rows: list[dict[str, object]],
    best_row: dict[str, object] | None,
) -> None:
    promoted = [row for row in rows if row["promotion_lens"] == "promote"]
    top_rows = rows[:25]
    family_rows: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        family_rows[str(row["family"])].append(row)
    lines = [
        "# MNQ Fresh Strategy Research",
        "",
        "Status: first fresh-angle MNQ strategy-family sweep, deliberately not bound by the prior bot families.",
        "",
        "## Objective",
        "",
        "Find a candidate family with all of the following qualities:",
        "",
        "- stable profitability;",
        "- high trade frequency;",
        "- low chronological drawdown;",
        "- high profit factor;",
        "- simple enough to implement safely in Sierra Chart.",
        "",
        "The first-pass promotion lens is intentionally strict: at least `200` trades, at least `2` trades/week, positive full-sample and latest-year net, PF `>= 1.6`, drawdown better than `-$1000`, and worst quarter better than `-$750`.",
        "",
        "## Online Research Input",
        "",
        "The fresh sweep is built around strategy families supported by external market/research evidence:",
        "",
        "- CME describes NQ/MNQ as liquid Nasdaq-100 futures products with nearly 24-hour access and tight-spread/deep-liquidity characteristics.",
        "- Opening-range breakout and timely opening-range breakout research motivates testing NY cash-open breakout and failed-breakout families.",
        "- Intraday momentum/noise-area research motivates testing a rolling time-of-day noise band instead of fixed price thresholds.",
        "- Order-flow imbalance literature motivates keeping delta/close-location confirmations in the family tests.",
        "",
        "Primary online sources are listed in `docs/online-instrument-focus.md`; this report uses them only to choose strategy families, not to claim profitability.",
        "",
        "Specific source URLs used for this pass:",
        "",
        "- CME NQ overview: `https://www.cmegroup.com/markets/equities/nasdaq/e-mini-nasdaq-100.html`",
        "- CME MNQ overview: `https://www.cmegroup.com/markets/equities/nasdaq/micro-e-mini-nasdaq-100.html`",
        "- CME Nasdaq futures page: `https://www.cmegroup.com/markets/equities/nasdaq.html`",
        "- Opening-range breakout paper index: `https://ideas.repec.org/p/hhs/umnees/0845.html`",
        "- Intraday momentum paper: `https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4824172`",
        "- Market intraday momentum futures paper: `https://academicweb.nd.edu/~zda/intramom.pdf`",
        "- Order-flow imbalance / price impact: `https://arxiv.org/abs/1011.6402`",
        "",
        "## Source",
        "",
        f"- rows: `{len(bars)}`",
        f"- dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        f"- unique trading dates: `{len({bar.trade_date for bar in bars})}`",
        "- instrument: `MNQ`, point value `$2`, tick value `$0.50`",
        "- base cost model: `$0.50/side` commission plus `1` total slippage tick per contract",
        "",
        "## Families Tested",
        "",
        "| Family | Raw Strategy Sets | Raw Signals | Best Net | Best PF | Best DD | Best Trades/Wk | Promotion Rows |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for family in sorted(family_rows):
        rows_for_family = family_rows[family]
        best_family = min(rows_for_family, key=_ranking_key)
        raw_strategy_sets = sum(1 for key in signal_sets if key.startswith(family + ":"))
        raw_signals = sum(len(value) for key, value in signal_sets.items() if key.startswith(family + ":"))
        promotion_count = sum(row["promotion_lens"] == "promote" for row in rows_for_family)
        lines.append(
            "| "
            f"`{family}` | {raw_strategy_sets} | {raw_signals} | "
            f"{best_family['net_usd']} | {best_family['profit_factor']} | "
            f"{best_family['max_drawdown_usd']} | {best_family['trades_per_week']} | "
            f"{promotion_count} |",
        )
    lines.extend(["", "## Result", ""])
    if best_row is None:
        lines.append("No rows reached the minimum trade threshold.")
    else:
        lines.extend(
            [
                f"Rows generated after minimum thresholds: `{len(rows)}`",
                f"Rows promoted by the strict first-pass lens: `{len(promoted)}`",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Strategy | `{best_row['strategy_id']}` |",
                f"| Family | `{best_row['family']}` |",
                f"| Quantity | `{best_row['quantity']}` |",
                f"| Target / Stop | `{best_row['target_points']} / {best_row['stop_points']}` points |",
                f"| Trades | `{best_row['trades']}` |",
                f"| Trades/week | `{best_row['trades_per_week']}` |",
                f"| Net | `${best_row['net_usd']}` |",
                f"| PF | `{best_row['profit_factor']}` |",
                f"| Win rate | `{float(best_row['win_rate']) * 100:.1f}%` |",
                f"| Drawdown | `${best_row['max_drawdown_usd']}` |",
                f"| Net/DD | `{best_row['net_to_drawdown']}` |",
                f"| Latest-year net | `${best_row['latest_year_net_usd']}` |",
                f"| Worst quarter | `${best_row['worst_quarter_net_usd']}` |",
                f"| Worst month | `${best_row['worst_month_net_usd']}` |",
                f"| Average hold | `{best_row['average_holding_minutes']}` min |",
                f"| Lens | `{best_row['promotion_lens']}` |",
            ],
        )
    lines.extend(
        [
            "",
            "## Top Rows",
            "",
            "| Rank | Lens | Family | Qty | Target | Stop | Trades | /Wk | Net | PF | DD | Latest | Worst Q | Strategy |",
            "| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ],
    )
    for rank, row in enumerate(top_rows, start=1):
        lines.append(
            "| "
            f"{rank} | `{row['promotion_lens']}` | `{row['family']}` | "
            f"{row['quantity']} | {row['target_points']} | {row['stop_points']} | "
            f"{row['trades']} | {row['trades_per_week']} | {row['net_usd']} | "
            f"{row['profit_factor']} | {row['max_drawdown_usd']} | "
            f"{row['latest_year_net_usd']} | {row['worst_quarter_net_usd']} | "
            f"`{row['strategy_id']}` |",
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
        ],
    )
    if promoted:
        lines.extend(
            [
                "This first pass found rows that clear the strict promotion lens. The next step is deep validation on the promoted family only:",
                "",
                "- slippage stress through at least `12` ticks;",
                "- rolling holdouts;",
                "- period attribution;",
                "- Monte Carlo trade-order risk;",
                "- overlap check against existing MNQ bots;",
                "- Sierra implementation complexity review.",
            ],
        )
    else:
        lines.extend(
            [
                "No family cleared the strict first-pass lens. The correct next step is not to loosen the lens immediately; it is to inspect near-miss families and decide whether a second data representation is required.",
                "",
                "Most likely second representations:",
                "",
                "- tick/range bars from MNQ, because the 3-minute export can blur high-frequency order-flow timing;",
                "- depth/order-book imbalance if Sierra market depth history is available;",
                "- daily online context labels for CPI/FOMC/NFP/large tech earnings days.",
            ],
        )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _opening_range(rows: list[wave.Bar], minutes: int) -> tuple[float, float, time] | None:
    end_dt = datetime.combine(rows[0].trade_date, NY_OPEN) + timedelta(minutes=minutes)
    end_time = end_dt.time()
    range_rows = [row for row in rows if NY_OPEN <= row.timestamp.time() < end_time]
    if not range_rows:
        return None
    return max(row.high for row in range_rows), min(row.low for row in range_rows), end_time


def _day_open(rows: list[wave.Bar]) -> float:
    for row in rows:
        if row.timestamp.time() >= NY_OPEN:
            return row.open
    return rows[0].open


def _skip_day(rows: list[wave.Bar], *, skip_friday: bool) -> bool:
    return bool(skip_friday and rows and rows[0].trade_date.weekday() == 4)


def _spacing_ok(row: wave.Bar, last_signal_time: datetime, spacing_minutes: int) -> bool:
    return (row.timestamp - last_signal_time).total_seconds() >= spacing_minutes * 60


def _rows_by_global_index(
    bars_by_date: dict[date, list[wave.Bar]],
) -> dict[int, int]:
    return {
        row.index: local_index
        for rows in bars_by_date.values()
        for local_index, row in enumerate(rows)
    }


def _sample_info(bars: list[wave.Bar]) -> SampleInfo:
    first = bars[0].trade_date
    last = bars[-1].trade_date
    weeks = max((last - first).days / 7.0, 1.0)
    return SampleInfo(weeks=weeks, latest_year=last.year)


def _max_drawdown(values: list[float]) -> float:
    peak = 0.0
    equity = 0.0
    drawdown = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        drawdown = min(drawdown, equity - peak)
    return drawdown


def _max_loss_streak(values: list[float]) -> int:
    longest = 0
    current = 0
    for value in values:
        if value < 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _ranking_key(row: dict[str, object]) -> tuple[float, float, float, float, float]:
    promoted = 0 if row["promotion_lens"] == "promote" else 1
    pf = float(row["profit_factor"])
    net_to_dd = float(row["net_to_drawdown"])
    trades_per_week = float(row["trades_per_week"])
    net = float(row["net_usd"])
    drawdown = float(row["max_drawdown_usd"])
    return (
        promoted,
        -min(pf, 4.0),
        -net_to_dd,
        -min(trades_per_week, 6.0),
        -net,
        drawdown,
    )


def _is_better(row: dict[str, object], best: dict[str, object] | None) -> bool:
    if best is None:
        return True
    return _ranking_key(row) < _ranking_key(best)


def _write_csv(path: str, header: list[str], rows: list[dict[str, object]]) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def _write_trade_audit(
    path: str,
    row: dict[str, object],
    outcomes: list[Outcome],
) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TRADE_AUDIT_HEADER)
        writer.writeheader()
        for outcome in outcomes:
            writer.writerow(
                {
                    "schema_version": 1,
                    "strategy_id": outcome.strategy_id,
                    "family": outcome.family,
                    "quantity": row["quantity"],
                    "target_points": row["target_points"],
                    "stop_points": row["stop_points"],
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
                    "net_usd": _fmt(outcome.net_usd),
                    "notes": outcome.notes,
                },
            )


def _time_id(value: time) -> str:
    return value.strftime("%H%M")


def _fmt(value: float) -> str:
    if math.isfinite(value) and abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.8f}".rstrip("0").rstrip(".")


if __name__ == "__main__":
    raise SystemExit(main())
