#!/usr/bin/env python3
"""Research MNQ wave-rider candidates against a 25K eval pass objective."""

from __future__ import annotations

import argparse
import csv
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Iterable

from axontrade.data import load_sierra_bar_study_rows


DEFAULT_INPUT = (
    "/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/"
    "AxonTrade_MNQ_OrderflowExport_Expanded.txt"
)
DEFAULT_SWEEP_OUTPUT = "reports/mnq-eval-pass-wave-rider-sweep.csv"
DEFAULT_TRADE_AUDIT_OUTPUT = "reports/mnq-eval-pass-wave-rider-best-trade-audit.csv"
DEFAULT_REPORT_OUTPUT = "reports/mnq-eval-pass-wave-rider-research.md"
POINT_VALUE_USD = 2.0
TICK_SIZE_POINTS = 0.25
TICK_VALUE_USD = 0.50
COMMISSION_PER_SIDE_USD = 0.50
SLIPPAGE_TICKS_PER_CONTRACT = 1.0
PROFIT_TARGET_USD = 1250.0
MAX_LOSS_USD = 1000.0
CONSISTENCY_FRACTION = 0.50
EPSILON_USD = 0.01
MAX_EVAL_CALENDAR_DAYS = 30
MAX_EVAL_TRADE_DAYS = 12
SETUP_START = time(10, 0)
OPENING_RANGE_START = time(9, 30)
OPENING_RANGE_END = time(10, 0)
FLATTEN_TIME = time(15, 45)


@dataclass(frozen=True)
class Bar:
    index: int
    timestamp: datetime
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: float
    trades: float
    bid_volume: float
    ask_volume: float
    delta: float
    vwap: float
    close_location: float


@dataclass(frozen=True)
class Signal:
    strategy_id: str
    direction: str
    bar: Bar
    notes: str


@dataclass(frozen=True)
class SignalFeatures:
    abs_delta: float
    bar_range: float
    directional_vwap_dist: float
    lookback_move: float
    day_range_so_far: float


@dataclass(frozen=True)
class RiskProfile:
    quantity: int
    target_net_usd: float
    stop_net_usd: float
    target_points: float
    stop_points: float
    round_turn_cost_usd: float


@dataclass(frozen=True)
class TradeOutcome:
    strategy_id: str
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


SWEEP_HEADER = [
    "schema_version",
    "strategy_id",
    "family",
    "quantity",
    "target_net_usd",
    "stop_net_usd",
    "target_points",
    "stop_points",
    "signal_days",
    "evaluated_trades",
    "win_rate",
    "net_usd",
    "average_trade_usd",
    "profit_factor",
    "max_trade_sequence_drawdown_usd",
    "latest_year",
    "latest_year_trades",
    "latest_year_win_rate",
    "latest_year_net_usd",
    "worst_quarter_net_usd",
    "worst_trade_usd",
    "worst_day_usd",
    "average_holding_minutes",
    "target_hits",
    "stop_hits",
    "eod_exits",
    "eval_attempts",
    "pass_rate",
    "two_trade_day_pass_rate",
    "fail_rate",
    "timeout_rate",
    "median_calendar_days_to_pass",
    "median_trade_days_to_pass",
    "signal_start_attempts",
    "signal_start_pass_rate",
    "signal_start_two_trade_day_pass_rate",
    "signal_start_fail_rate",
    "signal_start_timeout_rate",
    "signal_start_median_calendar_days_to_pass",
    "signal_start_median_trade_days_to_pass",
    "average_pass_net_usd",
    "best_eval_net_usd",
    "worst_eval_net_usd",
    "notes",
]

TRADE_AUDIT_HEADER = [
    "schema_version",
    "strategy_id",
    "quantity",
    "target_net_usd",
    "stop_net_usd",
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
        description="Sweep MNQ one-trade-per-day wave-rider candidates for LucidFlex-style eval passing.",
    )
    parser.add_argument("input", nargs="?", default=DEFAULT_INPUT)
    parser.add_argument("--sweep-output", default=DEFAULT_SWEEP_OUTPUT)
    parser.add_argument("--trade-audit-output", default=DEFAULT_TRADE_AUDIT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--symbol", default="MNQU26-CME")
    parser.add_argument("--minimum-signal-days", type=int, default=40)
    args = parser.parse_args()

    bars = _load_feature_bars(args.input)
    bars_by_date = _bars_by_date(bars)
    signals_by_strategy = _generate_strategy_signals(bars_by_date, symbol=args.symbol)
    signals_by_strategy = _with_filtered_signal_variants(signals_by_strategy, bars_by_date)
    risk_profiles = _risk_profiles()

    sweep_rows = []
    best_trades: list[TradeOutcome] = []
    best_row: dict[str, object] | None = None
    for strategy_id, signals in signals_by_strategy.items():
        if len(signals) < args.minimum_signal_days:
            continue
        family = strategy_id.split(":", 1)[0]
        for risk in risk_profiles:
            outcomes = _evaluate_signals(signals, bars_by_date, risk)
            row = _sweep_row(strategy_id, family, outcomes, risk, bars_by_date)
            sweep_rows.append(row)
            if _is_better_row(row, best_row):
                best_row = row
                best_trades = outcomes

    sweep_rows.sort(key=_ranking_key)
    _write_csv(args.sweep_output, SWEEP_HEADER, sweep_rows)
    if best_row is not None:
        _write_trade_audit(args.trade_audit_output, best_trades, best_row)
    _write_report(args.report_output, bars, sweep_rows, best_row)

    best_summary = "none"
    if best_row is not None:
        best_summary = (
            f"{best_row['strategy_id']} qty={best_row['quantity']} "
            f"target={best_row['target_net_usd']} stop={best_row['stop_net_usd']} "
            f"signal_pass={float(best_row['signal_start_pass_rate']):.3f} "
            f"signal_two_day={float(best_row['signal_start_two_trade_day_pass_rate']):.3f} "
            f"signal_fail={float(best_row['signal_start_fail_rate']):.3f}"
        )
    print(
        f"wrote {len(sweep_rows)} MNQ eval-pass wave-rider sweep rows to "
        f"{args.sweep_output}; best={best_summary}",
    )
    return 0


def _load_feature_bars(path: str) -> list[Bar]:
    raw_rows = load_sierra_bar_study_rows(path)
    cumulative_price_volume_by_date: dict[date, float] = defaultdict(float)
    cumulative_volume_by_date: dict[date, float] = defaultdict(float)
    bars = []
    for index, row in enumerate(raw_rows):
        timestamp = _parse_sierra_timestamp(row)
        high = _to_float(row.get("High"))
        low = _to_float(row.get("Low"))
        close = _to_float(row.get("Last") or row.get("Close"))
        volume = _to_float(row.get("Volume"), default=0.0)
        exported_vwap = _optional_float(row.get("VWAP"))
        vwap = exported_vwap
        if vwap is None:
            typical_price = _to_float(row.get("HLC Avg"), default=(high + low + close) / 3.0)
            if volume > 0:
                cumulative_price_volume_by_date[timestamp.date()] += typical_price * volume
                cumulative_volume_by_date[timestamp.date()] += volume
            cumulative_volume = cumulative_volume_by_date[timestamp.date()]
            vwap = (
                cumulative_price_volume_by_date[timestamp.date()] / cumulative_volume
                if cumulative_volume > 0
                else close
            )
        bars.append(
            Bar(
                index=index,
                timestamp=timestamp,
                trade_date=timestamp.date(),
                open=_to_float(row.get("Open")),
                high=high,
                low=low,
                close=close,
                volume=volume,
                trades=_to_float(row.get("# of Trades"), default=0.0),
                bid_volume=_to_float(row.get("Bid Volume"), default=0.0),
                ask_volume=_to_float(row.get("Ask Volume"), default=0.0),
                delta=_to_float(row.get("Ask Volume Bid Volume Difference"), default=0.0),
                vwap=vwap,
                close_location=_close_location(low=low, high=high, close=close),
            ),
        )
    return bars


def _generate_strategy_signals(
    bars_by_date: dict[date, list[Bar]],
    *,
    symbol: str,
) -> dict[str, list[Signal]]:
    signals_by_strategy: dict[str, list[Signal]] = defaultdict(list)
    for skip_friday in (False, True):
        for entry_end in (time(12, 30),):
            for min_or_width in (20.0, 40.0):
                for buffer_points in (0.0, 10.0):
                    for delta_threshold in (0.0, 600.0):
                        for close_location_threshold in (0.55,):
                            strategy_id = (
                                "or_breakout:"
                                f"min_or{min_or_width:g}:buf{buffer_points:g}:"
                                f"delta{delta_threshold:g}:cl{close_location_threshold:g}:"
                                f"end{_time_id(entry_end)}:skipfri{int(skip_friday)}"
                            )
                            for trade_date, rows in bars_by_date.items():
                                signal = _opening_range_breakout_signal(
                                    rows,
                                    strategy_id=strategy_id,
                                    min_or_width=min_or_width,
                                    buffer_points=buffer_points,
                                    delta_threshold=delta_threshold,
                                    close_location_threshold=close_location_threshold,
                                    entry_end=entry_end,
                                    skip_friday=skip_friday,
                                    symbol=symbol,
                                )
                                if signal is not None:
                                    signals_by_strategy[strategy_id].append(signal)

            for min_or_width in (20.0, 40.0):
                for buffer_points in (0.0, 10.0):
                    for retest_points in (5.0, 15.0):
                        for delta_threshold in (0.0,):
                            for close_location_threshold in (0.55,):
                                strategy_id = (
                                    "or_retest:"
                                    f"min_or{min_or_width:g}:buf{buffer_points:g}:"
                                    f"retest{retest_points:g}:delta{delta_threshold:g}:"
                                    f"cl{close_location_threshold:g}:end{_time_id(entry_end)}:"
                                    f"skipfri{int(skip_friday)}"
                                )
                                for rows in bars_by_date.values():
                                    signal = _opening_range_retest_signal(
                                        rows,
                                        strategy_id=strategy_id,
                                        min_or_width=min_or_width,
                                        buffer_points=buffer_points,
                                        retest_points=retest_points,
                                        delta_threshold=delta_threshold,
                                        close_location_threshold=close_location_threshold,
                                        entry_end=entry_end,
                                        skip_friday=skip_friday,
                                        symbol=symbol,
                                    )
                                    if signal is not None:
                                        signals_by_strategy[strategy_id].append(signal)

            for lookback_bars in (10, 20, 40):
                for buffer_points in (0.0,):
                    for delta_threshold in (0.0, 600.0):
                        for close_location_threshold in (0.55,):
                            strategy_id = (
                                "lookback_breakout:"
                                f"lb{lookback_bars}:buf{buffer_points:g}:"
                                f"delta{delta_threshold:g}:cl{close_location_threshold:g}:"
                                f"end{_time_id(entry_end)}:skipfri{int(skip_friday)}"
                            )
                            for rows in bars_by_date.values():
                                signal = _lookback_breakout_signal(
                                    rows,
                                    strategy_id=strategy_id,
                                    lookback_bars=lookback_bars,
                                    buffer_points=buffer_points,
                                    delta_threshold=delta_threshold,
                                    close_location_threshold=close_location_threshold,
                                    entry_end=entry_end,
                                    skip_friday=skip_friday,
                                    symbol=symbol,
                                )
                                if signal is not None:
                                    signals_by_strategy[strategy_id].append(signal)

            for stretch_points in (30.0, 60.0):
                for pullback_points in (10.0, 20.0):
                    for delta_threshold in (0.0,):
                        for close_location_threshold in (0.55,):
                            strategy_id = (
                                "vwap_pullback:"
                                f"stretch{stretch_points:g}:pb{pullback_points:g}:"
                                f"delta{delta_threshold:g}:cl{close_location_threshold:g}:"
                                f"end{_time_id(entry_end)}:skipfri{int(skip_friday)}"
                            )
                            for rows in bars_by_date.values():
                                signal = _vwap_pullback_signal(
                                    rows,
                                    strategy_id=strategy_id,
                                    stretch_points=stretch_points,
                                    pullback_points=pullback_points,
                                    delta_threshold=delta_threshold,
                                    close_location_threshold=close_location_threshold,
                                    entry_end=entry_end,
                                    skip_friday=skip_friday,
                                    symbol=symbol,
                                )
                                if signal is not None:
                                    signals_by_strategy[strategy_id].append(signal)
    return dict(signals_by_strategy)


def _opening_range_breakout_signal(
    rows: list[Bar],
    *,
    strategy_id: str,
    min_or_width: float,
    buffer_points: float,
    delta_threshold: float,
    close_location_threshold: float,
    entry_end: time,
    skip_friday: bool,
    symbol: str,
) -> Signal | None:
    if _skip_day(rows, skip_friday=skip_friday):
        return None
    opening_range = _opening_range(rows)
    if opening_range is None:
        return None
    or_high, or_low = opening_range
    if or_high - or_low < min_or_width:
        return None
    high_break = or_high + buffer_points
    low_break = or_low - buffer_points
    previous_close = None
    for row in rows:
        if not _entry_time_allowed(row.timestamp.time(), entry_end):
            previous_close = row.close
            continue
        if previous_close is not None:
            if (
                previous_close <= high_break < row.close
                and row.close >= row.vwap
                and row.delta >= delta_threshold
                and row.close_location >= close_location_threshold
            ):
                return Signal(strategy_id, "long", row, f"{symbol} OR high breakout")
            if (
                previous_close >= low_break > row.close
                and row.close <= row.vwap
                and row.delta <= -delta_threshold
                and row.close_location <= 1.0 - close_location_threshold
            ):
                return Signal(strategy_id, "short", row, f"{symbol} OR low breakout")
        previous_close = row.close
    return None


def _opening_range_retest_signal(
    rows: list[Bar],
    *,
    strategy_id: str,
    min_or_width: float,
    buffer_points: float,
    retest_points: float,
    delta_threshold: float,
    close_location_threshold: float,
    entry_end: time,
    skip_friday: bool,
    symbol: str,
) -> Signal | None:
    if _skip_day(rows, skip_friday=skip_friday):
        return None
    opening_range = _opening_range(rows)
    if opening_range is None:
        return None
    or_high, or_low = opening_range
    if or_high - or_low < min_or_width:
        return None
    high_break = or_high + buffer_points
    low_break = or_low - buffer_points
    broke_high = False
    broke_low = False
    for row in rows:
        row_time = row.timestamp.time()
        if row_time < SETUP_START:
            continue
        if row.close > high_break:
            broke_high = True
        if row.close < low_break:
            broke_low = True
        if not _entry_time_allowed(row_time, entry_end):
            continue
        if (
            broke_high
            and row.low <= high_break + retest_points
            and row.close > high_break
            and row.close >= row.vwap
            and row.delta >= delta_threshold
            and row.close_location >= close_location_threshold
        ):
            return Signal(strategy_id, "long", row, f"{symbol} OR high retest continuation")
        if (
            broke_low
            and row.high >= low_break - retest_points
            and row.close < low_break
            and row.close <= row.vwap
            and row.delta <= -delta_threshold
            and row.close_location <= 1.0 - close_location_threshold
        ):
            return Signal(strategy_id, "short", row, f"{symbol} OR low retest continuation")
    return None


def _lookback_breakout_signal(
    rows: list[Bar],
    *,
    strategy_id: str,
    lookback_bars: int,
    buffer_points: float,
    delta_threshold: float,
    close_location_threshold: float,
    entry_end: time,
    skip_friday: bool,
    symbol: str,
) -> Signal | None:
    if _skip_day(rows, skip_friday=skip_friday):
        return None
    for index in range(lookback_bars, len(rows)):
        row = rows[index]
        if not _entry_time_allowed(row.timestamp.time(), entry_end):
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
            return Signal(strategy_id, "long", row, f"{symbol} lookback high breakout")
        if (
            previous_close >= low_break > row.close
            and row.close <= row.vwap
            and row.delta <= -delta_threshold
            and row.close_location <= 1.0 - close_location_threshold
        ):
            return Signal(strategy_id, "short", row, f"{symbol} lookback low breakout")
    return None


def _vwap_pullback_signal(
    rows: list[Bar],
    *,
    strategy_id: str,
    stretch_points: float,
    pullback_points: float,
    delta_threshold: float,
    close_location_threshold: float,
    entry_end: time,
    skip_friday: bool,
    symbol: str,
) -> Signal | None:
    if _skip_day(rows, skip_friday=skip_friday):
        return None
    stretched_high = False
    stretched_low = False
    for row in rows:
        row_time = row.timestamp.time()
        distance_from_vwap = row.close - row.vwap
        if row_time < SETUP_START:
            if distance_from_vwap >= stretch_points:
                stretched_high = True
            if distance_from_vwap <= -stretch_points:
                stretched_low = True
            continue
        if distance_from_vwap >= stretch_points:
            stretched_high = True
        if distance_from_vwap <= -stretch_points:
            stretched_low = True
        if not _entry_time_allowed(row_time, entry_end):
            continue
        if (
            stretched_high
            and row.low <= row.vwap + pullback_points
            and row.close > row.vwap + pullback_points
            and row.delta >= delta_threshold
            and row.close_location >= close_location_threshold
        ):
            return Signal(strategy_id, "long", row, f"{symbol} VWAP pullback continuation")
        if (
            stretched_low
            and row.high >= row.vwap - pullback_points
            and row.close < row.vwap - pullback_points
            and row.delta <= -delta_threshold
            and row.close_location <= 1.0 - close_location_threshold
        ):
            return Signal(strategy_id, "short", row, f"{symbol} VWAP pullback continuation")
    return None


def _risk_profiles() -> list[RiskProfile]:
    profiles = []
    for quantity in (5, 6, 8, 10, 12, 15, 20):
        round_turn_cost = quantity * (
            2.0 * COMMISSION_PER_SIDE_USD + SLIPPAGE_TICKS_PER_CONTRACT * TICK_VALUE_USD
        )
        for target_usd in (625.0, 650.0, 700.0):
            target_points = _round_up_to_tick(
                (target_usd + round_turn_cost) / (quantity * POINT_VALUE_USD),
            )
            actual_target_usd = target_points * quantity * POINT_VALUE_USD - round_turn_cost
            for stop_usd in (350.0, 500.0, 650.0, 800.0):
                if stop_usd <= round_turn_cost:
                    continue
                stop_points = _round_down_to_tick(
                    (stop_usd - round_turn_cost) / (quantity * POINT_VALUE_USD),
                )
                if stop_points <= 0:
                    continue
                actual_stop_usd = stop_points * quantity * POINT_VALUE_USD + round_turn_cost
                profiles.append(
                    RiskProfile(
                        quantity=quantity,
                        target_net_usd=actual_target_usd,
                        stop_net_usd=actual_stop_usd,
                        target_points=target_points,
                        stop_points=stop_points,
                        round_turn_cost_usd=round_turn_cost,
                    ),
                )
    return profiles


def _evaluate_signals(
    signals: list[Signal],
    bars_by_date: dict[date, list[Bar]],
    risk: RiskProfile,
) -> list[TradeOutcome]:
    outcomes = []
    for signal in signals:
        day_rows = bars_by_date[signal.bar.trade_date]
        following_rows = [
            row
            for row in day_rows
            if row.index > signal.bar.index and row.timestamp.time() <= FLATTEN_TIME
        ]
        outcomes.append(_evaluate_signal(signal, following_rows, risk))
    return outcomes


def _evaluate_signal(
    signal: Signal,
    following_rows: list[Bar],
    risk: RiskProfile,
) -> TradeOutcome:
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
    gross_usd = gross_points * POINT_VALUE_USD * risk.quantity
    net_usd = gross_usd - risk.round_turn_cost_usd
    return TradeOutcome(
        strategy_id=signal.strategy_id,
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


def _sweep_row(
    strategy_id: str,
    family: str,
    outcomes: list[TradeOutcome],
    risk: RiskProfile,
    bars_by_date: dict[date, list[Bar]],
) -> dict[str, object]:
    net_values = [outcome.net_usd for outcome in outcomes]
    positive = [value for value in net_values if value > 0]
    negative = [value for value in net_values if value < 0]
    daily_net: dict[date, float] = defaultdict(float)
    for outcome in outcomes:
        daily_net[outcome.entry_time.date()] += outcome.net_usd
    latest_year = max(bars_by_date).year if bars_by_date else 0
    latest_year_values = [
        outcome.net_usd
        for outcome in outcomes
        if outcome.entry_time.year == latest_year
    ]
    latest_year_wins = [value for value in latest_year_values if value > 0.0]
    quarterly_net: dict[tuple[int, int], float] = defaultdict(float)
    for outcome in outcomes:
        quarter = (outcome.entry_time.month - 1) // 3 + 1
        quarterly_net[(outcome.entry_time.year, quarter)] += outcome.net_usd
    eval_metrics = _simulate_eval_attempt_metrics(outcomes, sorted(bars_by_date))
    signal_eval_metrics = _simulate_signal_start_eval_attempt_metrics(outcomes)
    return {
        "schema_version": 1,
        "strategy_id": strategy_id,
        "family": family,
        "quantity": risk.quantity,
        "target_net_usd": _format_number(risk.target_net_usd),
        "stop_net_usd": _format_number(risk.stop_net_usd),
        "target_points": _format_number(risk.target_points),
        "stop_points": _format_number(risk.stop_points),
        "signal_days": len({outcome.entry_time.date() for outcome in outcomes}),
        "evaluated_trades": len(outcomes),
        "win_rate": _format_number(len(positive) / len(outcomes) if outcomes else 0.0),
        "net_usd": _format_number(sum(net_values)),
        "average_trade_usd": _format_number(statistics.mean(net_values) if net_values else 0.0),
        "profit_factor": _format_number(sum(positive) / abs(sum(negative)) if negative else 999.0),
        "max_trade_sequence_drawdown_usd": _format_number(_max_drawdown(net_values)),
        "latest_year": latest_year,
        "latest_year_trades": len(latest_year_values),
        "latest_year_win_rate": _format_number(
            len(latest_year_wins) / len(latest_year_values)
            if latest_year_values
            else 0.0,
        ),
        "latest_year_net_usd": _format_number(sum(latest_year_values)),
        "worst_quarter_net_usd": _format_number(
            min(quarterly_net.values()) if quarterly_net else 0.0,
        ),
        "worst_trade_usd": _format_number(min(net_values) if net_values else 0.0),
        "worst_day_usd": _format_number(min(daily_net.values()) if daily_net else 0.0),
        "average_holding_minutes": _format_number(
            statistics.mean(outcome.holding_minutes for outcome in outcomes)
            if outcomes
            else 0.0,
        ),
        "target_hits": sum(outcome.exit_reason == "target_hit" for outcome in outcomes),
        "stop_hits": sum(outcome.exit_reason == "stop_hit" for outcome in outcomes),
        "eod_exits": sum(
            outcome.exit_reason in {"end_of_session", "no_following_bar"}
            for outcome in outcomes
        ),
        "eval_attempts": eval_metrics["attempts"],
        "pass_rate": _format_number(eval_metrics["pass_rate"]),
        "two_trade_day_pass_rate": _format_number(eval_metrics["two_trade_day_pass_rate"]),
        "fail_rate": _format_number(eval_metrics["fail_rate"]),
        "timeout_rate": _format_number(eval_metrics["timeout_rate"]),
        "median_calendar_days_to_pass": _format_number(
            eval_metrics["median_calendar_days_to_pass"],
        ),
        "median_trade_days_to_pass": _format_number(eval_metrics["median_trade_days_to_pass"]),
        "signal_start_attempts": signal_eval_metrics["attempts"],
        "signal_start_pass_rate": _format_number(signal_eval_metrics["pass_rate"]),
        "signal_start_two_trade_day_pass_rate": _format_number(
            signal_eval_metrics["two_trade_day_pass_rate"],
        ),
        "signal_start_fail_rate": _format_number(signal_eval_metrics["fail_rate"]),
        "signal_start_timeout_rate": _format_number(signal_eval_metrics["timeout_rate"]),
        "signal_start_median_calendar_days_to_pass": _format_number(
            signal_eval_metrics["median_calendar_days_to_pass"],
        ),
        "signal_start_median_trade_days_to_pass": _format_number(
            signal_eval_metrics["median_trade_days_to_pass"],
        ),
        "average_pass_net_usd": _format_number(eval_metrics["average_pass_net_usd"]),
        "best_eval_net_usd": _format_number(eval_metrics["best_eval_net_usd"]),
        "worst_eval_net_usd": _format_number(eval_metrics["worst_eval_net_usd"]),
        "notes": "one trade per signal day; eval simulated from each rolling calendar start",
    }


def _simulate_eval_attempt_metrics(
    outcomes: list[TradeOutcome],
    trade_dates: list[date],
) -> dict[str, float]:
    outcomes_by_date = {outcome.entry_time.date(): outcome for outcome in outcomes}
    attempts = 0
    passed = 0
    failed = 0
    timed_out = 0
    two_trade_day_passes = 0
    pass_calendar_days: list[float] = []
    pass_trade_days: list[float] = []
    pass_net_values: list[float] = []
    best_net = -math.inf
    worst_net = math.inf
    for start_index, start_date in enumerate(trade_dates):
        attempts += 1
        equity = 0.0
        largest_day = 0.0
        trade_days = 0
        status = "timeout"
        end_date = start_date
        for current_date in trade_dates[start_index:]:
            if (current_date - start_date).days > MAX_EVAL_CALENDAR_DAYS:
                end_date = current_date
                break
            outcome = outcomes_by_date.get(current_date)
            if outcome is None:
                end_date = current_date
                continue
            trade_days += 1
            equity += outcome.net_usd
            largest_day = max(largest_day, outcome.net_usd)
            end_date = current_date
            if equity <= -MAX_LOSS_USD - EPSILON_USD:
                status = "failed"
                break
            if (
                trade_days >= 2
                and equity >= PROFIT_TARGET_USD - EPSILON_USD
                and largest_day <= equity * CONSISTENCY_FRACTION + EPSILON_USD
            ):
                status = "passed"
                break
            if trade_days >= MAX_EVAL_TRADE_DAYS:
                break
        best_net = max(best_net, equity)
        worst_net = min(worst_net, equity)
        if status == "passed":
            passed += 1
            if trade_days <= 2:
                two_trade_day_passes += 1
            pass_calendar_days.append(float((end_date - start_date).days + 1))
            pass_trade_days.append(float(trade_days))
            pass_net_values.append(equity)
        elif status == "failed":
            failed += 1
        else:
            timed_out += 1
    if attempts == 0:
        return {
            "attempts": 0,
            "pass_rate": 0.0,
            "two_trade_day_pass_rate": 0.0,
            "fail_rate": 0.0,
            "timeout_rate": 0.0,
            "median_calendar_days_to_pass": 0.0,
            "median_trade_days_to_pass": 0.0,
            "average_pass_net_usd": 0.0,
            "best_eval_net_usd": 0.0,
            "worst_eval_net_usd": 0.0,
        }
    return {
        "attempts": attempts,
        "pass_rate": passed / attempts,
        "two_trade_day_pass_rate": two_trade_day_passes / attempts,
        "fail_rate": failed / attempts,
        "timeout_rate": timed_out / attempts,
        "median_calendar_days_to_pass": (
            statistics.median(pass_calendar_days) if pass_calendar_days else 0.0
        ),
        "median_trade_days_to_pass": (
            statistics.median(pass_trade_days) if pass_trade_days else 0.0
        ),
        "average_pass_net_usd": statistics.mean(pass_net_values) if pass_net_values else 0.0,
        "best_eval_net_usd": best_net if math.isfinite(best_net) else 0.0,
        "worst_eval_net_usd": worst_net if math.isfinite(worst_net) else 0.0,
    }


def _simulate_signal_start_eval_attempt_metrics(
    outcomes: list[TradeOutcome],
) -> dict[str, float]:
    ordered_outcomes = sorted(outcomes, key=lambda outcome: outcome.entry_time)
    attempts = 0
    passed = 0
    failed = 0
    timed_out = 0
    two_trade_day_passes = 0
    pass_calendar_days: list[float] = []
    pass_trade_days: list[float] = []
    for start_index, start_outcome in enumerate(ordered_outcomes):
        attempts += 1
        equity = 0.0
        largest_day = 0.0
        trade_days = 0
        status = "timeout"
        end_date = start_outcome.entry_time.date()
        for outcome in ordered_outcomes[start_index:start_index + MAX_EVAL_TRADE_DAYS]:
            trade_days += 1
            equity += outcome.net_usd
            largest_day = max(largest_day, outcome.net_usd)
            end_date = outcome.entry_time.date()
            if equity <= -MAX_LOSS_USD - EPSILON_USD:
                status = "failed"
                break
            if (
                trade_days >= 2
                and equity >= PROFIT_TARGET_USD - EPSILON_USD
                and largest_day <= equity * CONSISTENCY_FRACTION + EPSILON_USD
            ):
                status = "passed"
                break
        if status == "passed":
            passed += 1
            if trade_days <= 2:
                two_trade_day_passes += 1
            pass_calendar_days.append(
                float((end_date - start_outcome.entry_time.date()).days + 1),
            )
            pass_trade_days.append(float(trade_days))
        elif status == "failed":
            failed += 1
        else:
            timed_out += 1
    if attempts == 0:
        return {
            "attempts": 0,
            "pass_rate": 0.0,
            "two_trade_day_pass_rate": 0.0,
            "fail_rate": 0.0,
            "timeout_rate": 0.0,
            "median_calendar_days_to_pass": 0.0,
            "median_trade_days_to_pass": 0.0,
        }
    return {
        "attempts": attempts,
        "pass_rate": passed / attempts,
        "two_trade_day_pass_rate": two_trade_day_passes / attempts,
        "fail_rate": failed / attempts,
        "timeout_rate": timed_out / attempts,
        "median_calendar_days_to_pass": (
            statistics.median(pass_calendar_days) if pass_calendar_days else 0.0
        ),
        "median_trade_days_to_pass": (
            statistics.median(pass_trade_days) if pass_trade_days else 0.0
        ),
    }


def _write_report(
    report_output: str,
    bars: list[Bar],
    sweep_rows: list[dict[str, object]],
    best_row: dict[str, object] | None,
) -> None:
    accepted = [
        row for row in sweep_rows
        if float(row["signal_start_pass_rate"]) >= 0.65
        and float(row["signal_start_fail_rate"]) <= 0.25
        and float(row["net_usd"]) > 0.0
        and float(row["latest_year_net_usd"]) > 0.0
        and int(row["latest_year_trades"]) >= 8
        and int(row["evaluated_trades"]) >= 40
    ]
    top_rows = sweep_rows[:10]
    lines = [
        "# MNQ Eval-Pass Wave Rider Research",
        "",
        "Status: second-pass MNQ-only research for a LucidFlex-style 25K evaluation objective.",
        "",
        "## Objective",
        "",
        "- profit target: `$1250`",
        "- max loss: `-$1000`",
        "- consistency: largest winning day must be `<= 50%` of total profit",
        "- desired path: about `$625-$700` on each of two traded days",
        "",
        "## Source",
        "",
        f"- rows: `{len(bars)}`",
        f"- dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        f"- unique dates: `{len({bar.trade_date for bar in bars})}`",
        "- instrument: `MNQ`, point value `$2`, tick value `$0.50`",
        "- cost model: `$0.50/side` commission plus `1` total slippage tick per contract",
        "",
        "## Search Space",
        "",
        "- entry families: opening-range breakout, opening-range retest, lookback breakout, VWAP pullback continuation",
        "- grid: continuation filters plus second-pass clean-breakout filters",
        "- one trade per strategy per day",
        "- quantities: `5`, `6`, `8`, `10`, `12`, `15`, `20` MNQ",
        "- target net/trade: around `$625`, `$650`, `$700`, tick-rounded",
        "- stop net/trade: around `$350`, `$500`, `$650`, `$800`, tick-rounded",
        "- eval attempts: simulated from each rolling calendar start date and from each valid signal date",
        "",
        "## Result",
        "",
    ]
    if best_row is None:
        lines.append("No rows were generated.")
    else:
        lines.extend(
            [
                "Best second-pass row by eval-pass ranking:",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Strategy | `{best_row['strategy_id']}` |",
                f"| Quantity | `{best_row['quantity']}` |",
                f"| Target net/trade | `${best_row['target_net_usd']}` |",
                f"| Stop net/trade | `${best_row['stop_net_usd']}` |",
                f"| Signals/trades | `{best_row['evaluated_trades']}` |",
                f"| Win rate | `{float(best_row['win_rate']) * 100:.1f}%` |",
                f"| Avg trade | `${best_row['average_trade_usd']}` |",
                f"| Full-sample net | `${best_row['net_usd']}` |",
                f"| Trade-sequence max DD | `${best_row['max_trade_sequence_drawdown_usd']}` |",
                f"| Latest-year trades | `{best_row['latest_year_trades']}` |",
                f"| Latest-year net | `${best_row['latest_year_net_usd']}` |",
                f"| Worst quarter net | `${best_row['worst_quarter_net_usd']}` |",
                f"| Signal-start pass rate | `{float(best_row['signal_start_pass_rate']) * 100:.1f}%` |",
                f"| Signal-start two-trade-day pass rate | `{float(best_row['signal_start_two_trade_day_pass_rate']) * 100:.1f}%` |",
                f"| Signal-start fail rate | `{float(best_row['signal_start_fail_rate']) * 100:.1f}%` |",
                f"| Signal-start timeout rate | `{float(best_row['signal_start_timeout_rate']) * 100:.1f}%` |",
                f"| Signal-start median calendar days to pass | `{best_row['signal_start_median_calendar_days_to_pass']}` |",
                f"| Signal-start median traded days to pass | `{best_row['signal_start_median_trade_days_to_pass']}` |",
                f"| Calendar-start pass rate | `{float(best_row['pass_rate']) * 100:.1f}%` |",
                f"| Calendar-start fail rate | `{float(best_row['fail_rate']) * 100:.1f}%` |",
                "",
            ],
        )
        if accepted:
            lines.append(
                f"Rows meeting the rough second-pass acceptance lens: `{len(accepted)}`.",
            )
        else:
            lines.append(
                "No row met the rough second-pass acceptance lens of signal-start pass rate "
                "`>= 65%`, signal-start fail rate `<= 25%`, positive full-sample and latest-year "
                "net, at least `8` latest-year trades, and at least `40` total trades.",
            )
    lines.extend(
        [
            "",
            "## Top Rows",
            "",
            "| Rank | Family | Qty | Target | Stop | Trades | Latest-Year Net | Signal Pass | 2-Day | Signal Fail | Avg Trade | Strategy |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ],
    )
    for rank, row in enumerate(top_rows, start=1):
        lines.append(
            "| "
            f"{rank} | {row['family']} | {row['quantity']} | "
            f"{row['target_net_usd']} | {row['stop_net_usd']} | "
            f"{row['evaluated_trades']} | "
            f"{row['latest_year_net_usd']} | "
            f"{float(row['signal_start_pass_rate']) * 100:.1f}% | "
            f"{float(row['signal_start_two_trade_day_pass_rate']) * 100:.1f}% | "
            f"{float(row['signal_start_fail_rate']) * 100:.1f}% | "
            f"{row['average_trade_usd']} | `{row['strategy_id']}` |"
        )
    fast_rows = [
        row for row in sweep_rows
        if int(row["evaluated_trades"]) >= 40
        and float(row["signal_start_fail_rate"]) <= 0.30
        and float(row["latest_year_net_usd"]) > 0.0
        and int(row["latest_year_trades"]) >= 8
    ]
    fast_rows.sort(
        key=lambda row: (
            -float(row["signal_start_two_trade_day_pass_rate"]),
            -float(row["signal_start_pass_rate"]),
            float(row["signal_start_fail_rate"]),
        ),
    )
    lines.extend(
        [
            "",
            "## Fastest Two-Day Leads",
            "",
            "| Rank | Qty | Target | Stop | Trades | Latest-Year Net | Signal Pass | 2-Day | Signal Fail | Median Calendar Days | Strategy |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ],
    )
    for rank, row in enumerate(fast_rows[:8], start=1):
        lines.append(
            "| "
            f"{rank} | {row['quantity']} | {row['target_net_usd']} | "
            f"{row['stop_net_usd']} | {row['evaluated_trades']} | "
            f"{row['latest_year_net_usd']} | "
            f"{float(row['signal_start_pass_rate']) * 100:.1f}% | "
            f"{float(row['signal_start_two_trade_day_pass_rate']) * 100:.1f}% | "
            f"{float(row['signal_start_fail_rate']) * 100:.1f}% | "
            f"{row['signal_start_median_calendar_days_to_pass']} | "
            f"`{row['strategy_id']}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This is research for eval-passing geometry, not a deployment candidate by itself. "
            "A true candidate still needs slippage stress, walk-forward selection, and "
            "replay/mechanics validation.",
            "",
            "Signal-start metrics assume the account is only exposed after a valid setup appears. "
            "Calendar-start metrics are harsher because they also penalize waiting time after a random "
            "start date.",
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
    trades: list[TradeOutcome],
    row: dict[str, object],
) -> None:
    rows = [
        {
            "schema_version": 1,
            "strategy_id": trade.strategy_id,
            "quantity": row["quantity"],
            "target_net_usd": row["target_net_usd"],
            "stop_net_usd": row["stop_net_usd"],
            "direction": trade.direction,
            "entry_time": trade.entry_time.isoformat(sep=" "),
            "exit_time": trade.exit_time.isoformat(sep=" "),
            "entry_bar_index": trade.entry_bar_index,
            "exit_bar_index": trade.exit_bar_index,
            "entry_price": _format_number(trade.entry_price),
            "exit_price": _format_number(trade.exit_price),
            "target_price": _format_number(trade.target_price),
            "stop_price": _format_number(trade.stop_price),
            "exit_reason": trade.exit_reason,
            "holding_minutes": _format_number(trade.holding_minutes),
            "gross_points": _format_number(trade.gross_points),
            "net_usd": _format_number(trade.net_usd),
            "notes": trade.notes,
        }
        for trade in trades
    ]
    _write_csv(path, TRADE_AUDIT_HEADER, rows)


def _bars_by_date(bars: list[Bar]) -> dict[date, list[Bar]]:
    rows_by_date: dict[date, list[Bar]] = defaultdict(list)
    for bar in bars:
        rows_by_date[bar.trade_date].append(bar)
    return dict(sorted(rows_by_date.items()))


def _with_filtered_signal_variants(
    signals_by_strategy: dict[str, list[Signal]],
    bars_by_date: dict[date, list[Bar]],
) -> dict[str, list[Signal]]:
    expanded: dict[str, list[Signal]] = {
        strategy_id: list(signals)
        for strategy_id, signals in signals_by_strategy.items()
    }
    lookback_signals = {
        strategy_id: signals
        for strategy_id, signals in signals_by_strategy.items()
        if strategy_id.startswith("lookback_breakout:")
    }
    filters = [
        (
            "absdelta1000",
            lambda features: features.abs_delta <= 1000.0,
        ),
        (
            "absdelta1172",
            lambda features: features.abs_delta <= 1172.0,
        ),
        (
            "barrange24_75",
            lambda features: features.bar_range <= 24.75,
        ),
        (
            "absdelta1000_lbmove103_75",
            lambda features: (
                features.abs_delta <= 1000.0
                and features.lookback_move <= 103.75
            ),
        ),
        (
            "absdelta1172_lbmove103_75",
            lambda features: (
                features.abs_delta <= 1172.0
                and features.lookback_move <= 103.75
            ),
        ),
        (
            "absdelta1172_barrange24_75",
            lambda features: (
                features.abs_delta <= 1172.0
                and features.bar_range <= 24.75
            ),
        ),
        (
            "barrange24_75_vwapdist103_45",
            lambda features: (
                features.bar_range <= 24.75
                and features.directional_vwap_dist <= 103.45
            ),
        ),
    ]
    rows_by_index = _rows_by_global_index(bars_by_date)
    for strategy_id, signals in lookback_signals.items():
        lookback_bars = _strategy_lookback_bars(strategy_id)
        if lookback_bars is None:
            continue
        for filter_id, keep_signal in filters:
            filtered_strategy_id = f"{strategy_id}:filter{filter_id}"
            filtered_signals = []
            for signal in signals:
                features = _signal_features(
                    signal,
                    bars_by_date=bars_by_date,
                    rows_by_index=rows_by_index,
                    lookback_bars=lookback_bars,
                )
                if keep_signal(features):
                    filtered_signals.append(
                        Signal(
                            strategy_id=filtered_strategy_id,
                            direction=signal.direction,
                            bar=signal.bar,
                            notes=f"{signal.notes}; filter {filter_id}",
                        ),
                    )
            expanded[filtered_strategy_id] = filtered_signals
    return expanded


def _signal_features(
    signal: Signal,
    *,
    bars_by_date: dict[date, list[Bar]],
    rows_by_index: dict[int, int],
    lookback_bars: int,
) -> SignalFeatures:
    rows = bars_by_date[signal.bar.trade_date]
    local_index = rows_by_index[signal.bar.index]
    lookback = rows[max(0, local_index - lookback_bars):local_index]
    direction = 1.0 if signal.direction == "long" else -1.0
    lookback_move = (
        (signal.bar.close - lookback[0].close) * direction
        if lookback
        else 0.0
    )
    day_rows = rows[: local_index + 1]
    return SignalFeatures(
        abs_delta=abs(signal.bar.delta),
        bar_range=signal.bar.high - signal.bar.low,
        directional_vwap_dist=(signal.bar.close - signal.bar.vwap) * direction,
        lookback_move=lookback_move,
        day_range_so_far=max(row.high for row in day_rows) - min(row.low for row in day_rows),
    )


def _rows_by_global_index(bars_by_date: dict[date, list[Bar]]) -> dict[int, int]:
    rows_by_index = {}
    for rows in bars_by_date.values():
        for local_index, bar in enumerate(rows):
            rows_by_index[bar.index] = local_index
    return rows_by_index


def _strategy_lookback_bars(strategy_id: str) -> int | None:
    for token in strategy_id.split(":"):
        if token.startswith("lb") and token[2:].isdigit():
            return int(token[2:])
    return None


def _opening_range(rows: list[Bar]) -> tuple[float, float] | None:
    opening_rows = [
        row for row in rows
        if OPENING_RANGE_START <= row.timestamp.time() < OPENING_RANGE_END
    ]
    if not opening_rows:
        return None
    return max(row.high for row in opening_rows), min(row.low for row in opening_rows)


def _entry_time_allowed(value: time, entry_end: time) -> bool:
    return SETUP_START <= value <= entry_end


def _skip_day(rows: list[Bar], *, skip_friday: bool) -> bool:
    return not rows or (skip_friday and rows[0].timestamp.weekday() == 4)


def _parse_sierra_timestamp(row: dict[str, str]) -> datetime:
    value = row.get("Date Time") or row.get("DateTime") or row.get("Timestamp")
    if value:
        return _parse_timestamp(value)
    date_value = row.get("Date", "")
    time_value = row.get("Time", "00:00:00")
    return _parse_timestamp(f"{date_value} {time_value}")


def _parse_timestamp(value: str) -> datetime:
    value = value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    # Sierra sometimes exports non-zero-padded month/day.
    date_part, time_part = value.split(" ", 1)
    year, month, day = (int(part) for part in date_part.split("-"))
    hour, minute, second = time_part.split(".")[0].split(":")
    return datetime(year, month, day, int(hour), int(minute), int(second))


def _to_float(value: str | None, *, default: float | None = None) -> float:
    if value is None or str(value).strip() == "":
        if default is None:
            raise ValueError("missing required numeric value")
        return default
    return float(value)


def _optional_float(value: str | None) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    return float(value)


def _close_location(*, low: float, high: float, close: float) -> float:
    if high <= low:
        return 0.5
    return (close - low) / (high - low)


def _max_drawdown(values: Iterable[float]) -> float:
    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_drawdown = min(max_drawdown, equity - peak)
    return max_drawdown


def _round_up_to_tick(value: float) -> float:
    return math.ceil((value - 1e-12) / TICK_SIZE_POINTS) * TICK_SIZE_POINTS


def _round_down_to_tick(value: float) -> float:
    return math.floor((value + 1e-12) / TICK_SIZE_POINTS) * TICK_SIZE_POINTS


def _ranking_key(row: dict[str, object]) -> tuple[float, float, float, float, float, float, float]:
    sample_penalty = 0.0 if int(row["evaluated_trades"]) >= 40 else 1.0
    latest_year_penalty = (
        0.0
        if float(row["latest_year_net_usd"]) > 0.0 and int(row["latest_year_trades"]) >= 8
        else 1.0
    )
    return (
        sample_penalty,
        latest_year_penalty,
        -float(row["signal_start_pass_rate"]),
        float(row["signal_start_fail_rate"]),
        -float(row["signal_start_two_trade_day_pass_rate"]),
        float(row["signal_start_median_calendar_days_to_pass"]) or 999.0,
        -float(row["average_trade_usd"]),
    )


def _is_better_row(
    row: dict[str, object],
    current_best: dict[str, object] | None,
) -> bool:
    if current_best is None:
        return True
    return _ranking_key(row) < _ranking_key(current_best)


def _time_id(value: time) -> str:
    return f"{value.hour:02d}{value.minute:02d}"


def _format_number(value: float) -> str:
    if not math.isfinite(value):
        return "0"
    formatted = f"{value:.8f}".rstrip("0").rstrip(".")
    return formatted if formatted else "0"


if __name__ == "__main__":
    raise SystemExit(main())
