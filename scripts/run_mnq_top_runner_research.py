#!/usr/bin/env python3
"""Research MNQ top-runner candidates for normal profitability."""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_mnq_eval_pass_wave_rider as wave  # noqa: E402


DEFAULT_SWEEP_OUTPUT = "reports/mnq-top-runner-research.csv"
DEFAULT_TRADE_AUDIT_OUTPUT = "reports/mnq-top-runner-best-trade-audit.csv"
DEFAULT_REPORT_OUTPUT = "reports/mnq-top-runner-research.md"
ROUND_TURN_COST_PER_CONTRACT_USD = (
    2.0 * wave.COMMISSION_PER_SIDE_USD
    + wave.SLIPPAGE_TICKS_PER_CONTRACT * wave.TICK_VALUE_USD
)


@dataclass(frozen=True)
class RunnerRisk:
    quantity: int
    target_points: float
    stop_points: float
    round_turn_cost_usd: float


@dataclass(frozen=True)
class RunnerOutcome:
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
    trading_dates: tuple[date, ...]
    weeks: float
    latest_year: int


SWEEP_HEADER = [
    "schema_version",
    "strategy_id",
    "family",
    "quantity",
    "target_points",
    "stop_points",
    "raw_signals",
    "evaluated_trades",
    "signal_days",
    "trades_per_week",
    "win_rate",
    "target_hit_rate",
    "stop_hit_rate",
    "end_of_session_rate",
    "net_usd",
    "average_trade_usd",
    "profit_factor",
    "payoff_ratio",
    "max_trade_sequence_drawdown_usd",
    "net_to_drawdown",
    "latest_year",
    "latest_year_trades",
    "latest_year_net_usd",
    "worst_quarter_net_usd",
    "worst_day_usd",
    "worst_trade_usd",
    "average_holding_minutes",
    "median_holding_minutes",
    "notes",
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
        description="Sweep MNQ runner-style entry families for normal profitability.",
    )
    parser.add_argument("input", nargs="?", default=wave.DEFAULT_INPUT)
    parser.add_argument("--sweep-output", default=DEFAULT_SWEEP_OUTPUT)
    parser.add_argument("--trade-audit-output", default=DEFAULT_TRADE_AUDIT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--symbol", default="MNQU26-CME")
    parser.add_argument("--minimum-raw-signals", type=int, default=60)
    parser.add_argument("--minimum-trades", type=int, default=60)
    args = parser.parse_args()

    bars = wave._load_feature_bars(args.input)
    bars_by_date = wave._bars_by_date(bars)
    rows_by_index = wave._rows_by_global_index(bars_by_date)
    flatten_index_by_date = _flatten_index_by_date(bars_by_date)
    sample_info = _sample_info(bars)
    signals_by_strategy = _generate_signals_by_strategy(bars_by_date, symbol=args.symbol)
    risk_profiles = _risk_profiles()

    sweep_rows: list[dict[str, object]] = []
    best_row: dict[str, object] | None = None
    best_outcomes: list[RunnerOutcome] = []
    for strategy_id, signals in signals_by_strategy.items():
        if len(signals) < args.minimum_raw_signals:
            continue
        family = strategy_id.split(":", 1)[0]
        for risk in risk_profiles:
            outcomes = _evaluate_signals(
                signals,
                bars_by_date,
                rows_by_index,
                flatten_index_by_date,
                risk,
                family=family,
            )
            if len(outcomes) < args.minimum_trades:
                continue
            row = _sweep_row(strategy_id, family, len(signals), outcomes, risk, sample_info)
            sweep_rows.append(row)
            if _is_better_row(row, best_row):
                best_row = row
                best_outcomes = outcomes

    sweep_rows.sort(key=_ranking_key)
    _write_csv(args.sweep_output, SWEEP_HEADER, sweep_rows)
    if best_row is not None:
        _write_trade_audit(args.trade_audit_output, best_outcomes, best_row)
    _write_report(args.report_output, bars, sweep_rows, best_row)

    best_summary = "none"
    if best_row is not None:
        best_summary = (
            f"{best_row['strategy_id']} q={best_row['quantity']} "
            f"target={best_row['target_points']} stop={best_row['stop_points']} "
            f"trades={best_row['evaluated_trades']} net={best_row['net_usd']} "
            f"pf={best_row['profit_factor']} dd={best_row['max_trade_sequence_drawdown_usd']}"
        )
    print(
        f"wrote {len(sweep_rows)} MNQ top-runner rows to {args.sweep_output}; "
        f"best={best_summary}",
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
            for lookback_bars in (20, 40, 60):
                for buffer_points in (0.0, 2.5, 5.0):
                    for delta_threshold in (0.0, 600.0, 1000.0):
                        for close_location_threshold in (0.55, 0.65):
                            strategy_id = (
                                "runner_lookback_breakout:"
                                f"lb{lookback_bars}:buf{buffer_points:g}:"
                                f"delta{delta_threshold:g}:cl{close_location_threshold:g}:"
                                f"end{wave._time_id(entry_end)}:skipfri{int(skip_friday)}"
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
                                        symbol=symbol,
                                    ),
                                )
                            signals_by_strategy[strategy_id] = signals

            for min_or_width in (20.0, 40.0, 60.0):
                for buffer_points in (0.0, 5.0, 10.0):
                    for delta_threshold in (0.0, 600.0, 1000.0):
                        for close_location_threshold in (0.55, 0.65):
                            strategy_id = (
                                "runner_opening_range_breakout:"
                                f"or{min_or_width:g}:buf{buffer_points:g}:"
                                f"delta{delta_threshold:g}:cl{close_location_threshold:g}:"
                                f"end{wave._time_id(entry_end)}:skipfri{int(skip_friday)}"
                            )
                            signals = []
                            for rows in bars_by_date.values():
                                signals.extend(
                                    _opening_range_breakout_signals(
                                        rows,
                                        strategy_id=strategy_id,
                                        min_or_width=min_or_width,
                                        buffer_points=buffer_points,
                                        delta_threshold=delta_threshold,
                                        close_location_threshold=close_location_threshold,
                                        entry_end=entry_end,
                                        skip_friday=skip_friday,
                                        symbol=symbol,
                                    ),
                                )
                            signals_by_strategy[strategy_id] = signals

            for stretch_points in (40.0, 80.0, 120.0):
                for pullback_points in (10.0, 20.0, 30.0):
                    for delta_threshold in (0.0, 600.0):
                        for close_location_threshold in (0.55, 0.65):
                            strategy_id = (
                                "runner_vwap_pullback:"
                                f"stretch{stretch_points:g}:pb{pullback_points:g}:"
                                f"delta{delta_threshold:g}:cl{close_location_threshold:g}:"
                                f"end{wave._time_id(entry_end)}:skipfri{int(skip_friday)}"
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
                                        symbol=symbol,
                                    ),
                                )
                            signals_by_strategy[strategy_id] = signals

            for min_bar_range in (10.0, 20.0, 30.0):
                for delta_threshold in (800.0, 1200.0, 1600.0):
                    for close_location_threshold in (0.65, 0.75):
                        for min_vwap_dist in (0.0, 20.0, 40.0):
                            strategy_id = (
                                "runner_delta_impulse:"
                                f"range{min_bar_range:g}:delta{delta_threshold:g}:"
                                f"cl{close_location_threshold:g}:vwap{min_vwap_dist:g}:"
                                f"end{wave._time_id(entry_end)}:skipfri{int(skip_friday)}"
                            )
                            signals = []
                            for rows in bars_by_date.values():
                                signals.extend(
                                    _delta_impulse_signals(
                                        rows,
                                        strategy_id=strategy_id,
                                        min_bar_range=min_bar_range,
                                        delta_threshold=delta_threshold,
                                        close_location_threshold=close_location_threshold,
                                        min_vwap_dist=min_vwap_dist,
                                        entry_end=entry_end,
                                        skip_friday=skip_friday,
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
    symbol: str,
) -> list[wave.Signal]:
    if wave._skip_day(rows, skip_friday=skip_friday):
        return []
    signals = []
    last_signal_time = datetime.min
    for index in range(lookback_bars, len(rows)):
        row = rows[index]
        if not _entry_allowed(row, entry_end, last_signal_time):
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
                wave.Signal(strategy_id, "long", row, f"{symbol} runner lookback high"),
            )
            last_signal_time = row.timestamp
        elif (
            previous_close >= low_break > row.close
            and row.close <= row.vwap
            and row.delta <= -delta_threshold
            and row.close_location <= 1.0 - close_location_threshold
        ):
            signals.append(
                wave.Signal(strategy_id, "short", row, f"{symbol} runner lookback low"),
            )
            last_signal_time = row.timestamp
    return signals


def _opening_range_breakout_signals(
    rows: list[wave.Bar],
    *,
    strategy_id: str,
    min_or_width: float,
    buffer_points: float,
    delta_threshold: float,
    close_location_threshold: float,
    entry_end: time,
    skip_friday: bool,
    symbol: str,
) -> list[wave.Signal]:
    if wave._skip_day(rows, skip_friday=skip_friday):
        return []
    opening_range = wave._opening_range(rows)
    if opening_range is None:
        return []
    or_high, or_low = opening_range
    if or_high - or_low < min_or_width:
        return []
    high_break = or_high + buffer_points
    low_break = or_low - buffer_points
    signals = []
    last_signal_time = datetime.min
    previous_close = None
    for row in rows:
        if not _entry_allowed(row, entry_end, last_signal_time):
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
                    wave.Signal(strategy_id, "long", row, f"{symbol} runner OR high"),
                )
                last_signal_time = row.timestamp
            elif (
                previous_close >= low_break > row.close
                and row.close <= row.vwap
                and row.delta <= -delta_threshold
                and row.close_location <= 1.0 - close_location_threshold
            ):
                signals.append(
                    wave.Signal(strategy_id, "short", row, f"{symbol} runner OR low"),
                )
                last_signal_time = row.timestamp
        previous_close = row.close
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
    symbol: str,
) -> list[wave.Signal]:
    if wave._skip_day(rows, skip_friday=skip_friday):
        return []
    signals = []
    last_signal_time = datetime.min
    stretched_high = False
    stretched_low = False
    for row in rows:
        distance_from_vwap = row.close - row.vwap
        if distance_from_vwap >= stretch_points:
            stretched_high = True
        if distance_from_vwap <= -stretch_points:
            stretched_low = True
        if not _entry_allowed(row, entry_end, last_signal_time):
            continue
        if (
            stretched_high
            and row.low <= row.vwap + pullback_points
            and row.close > row.vwap + pullback_points
            and row.delta >= delta_threshold
            and row.close_location >= close_location_threshold
        ):
            signals.append(
                wave.Signal(strategy_id, "long", row, f"{symbol} runner VWAP pullback"),
            )
            stretched_high = False
            last_signal_time = row.timestamp
        elif (
            stretched_low
            and row.high >= row.vwap - pullback_points
            and row.close < row.vwap - pullback_points
            and row.delta <= -delta_threshold
            and row.close_location <= 1.0 - close_location_threshold
        ):
            signals.append(
                wave.Signal(strategy_id, "short", row, f"{symbol} runner VWAP pullback"),
            )
            stretched_low = False
            last_signal_time = row.timestamp
    return signals


def _delta_impulse_signals(
    rows: list[wave.Bar],
    *,
    strategy_id: str,
    min_bar_range: float,
    delta_threshold: float,
    close_location_threshold: float,
    min_vwap_dist: float,
    entry_end: time,
    skip_friday: bool,
    symbol: str,
) -> list[wave.Signal]:
    if wave._skip_day(rows, skip_friday=skip_friday):
        return []
    signals = []
    last_signal_time = datetime.min
    for row in rows:
        if not _entry_allowed(row, entry_end, last_signal_time):
            continue
        bar_range = row.high - row.low
        directional_vwap_dist = row.close - row.vwap
        if (
            bar_range >= min_bar_range
            and row.delta >= delta_threshold
            and row.close_location >= close_location_threshold
            and directional_vwap_dist >= min_vwap_dist
        ):
            signals.append(
                wave.Signal(strategy_id, "long", row, f"{symbol} runner long impulse"),
            )
            last_signal_time = row.timestamp
        elif (
            bar_range >= min_bar_range
            and row.delta <= -delta_threshold
            and row.close_location <= 1.0 - close_location_threshold
            and directional_vwap_dist <= -min_vwap_dist
        ):
            signals.append(
                wave.Signal(strategy_id, "short", row, f"{symbol} runner short impulse"),
            )
            last_signal_time = row.timestamp
    return signals


def _entry_allowed(row: wave.Bar, entry_end: time, last_signal_time: datetime) -> bool:
    if not wave._entry_time_allowed(row.timestamp.time(), entry_end):
        return False
    elapsed = (row.timestamp - last_signal_time).total_seconds()
    return elapsed >= 60 * 60


def _risk_profiles() -> list[RunnerRisk]:
    profiles = []
    for quantity in (2,):
        round_turn_cost = quantity * ROUND_TURN_COST_PER_CONTRACT_USD
        for target_points in (60.0, 80.0, 100.0, 120.0, 160.0, 200.0, 260.0, 320.0):
            for stop_points in (25.0, 35.0, 50.0, 70.0, 90.0, 120.0):
                if target_points < stop_points:
                    continue
                profiles.append(
                    RunnerRisk(
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
    flatten_index_by_date: dict[date, int],
    risk: RunnerRisk,
    *,
    family: str,
) -> list[RunnerOutcome]:
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
        outcome = _evaluate_signal(signal, following_rows, risk, family=family)
        outcomes.append(outcome)
        next_available_time = outcome.exit_time
    return outcomes


def _evaluate_signal(
    signal: wave.Signal,
    following_rows: list[wave.Bar],
    risk: RunnerRisk,
    *,
    family: str,
) -> RunnerOutcome:
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
    net_usd = gross_points * wave.POINT_VALUE_USD * risk.quantity - risk.round_turn_cost_usd
    return RunnerOutcome(
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


def _sweep_row(
    strategy_id: str,
    family: str,
    raw_signal_count: int,
    outcomes: list[RunnerOutcome],
    risk: RunnerRisk,
    sample_info: SampleInfo,
) -> dict[str, object]:
    net_values = [outcome.net_usd for outcome in outcomes]
    positive = [value for value in net_values if value > 0.0]
    negative = [value for value in net_values if value < 0.0]
    wins = len(positive)
    target_hits = sum(outcome.exit_reason == "target_hit" for outcome in outcomes)
    stop_hits = sum(outcome.exit_reason == "stop_hit" for outcome in outcomes)
    eod_exits = sum(
        outcome.exit_reason in {"end_of_session", "no_following_bar"}
        for outcome in outcomes
    )
    latest_year_values = [
        outcome.net_usd
        for outcome in outcomes
        if outcome.entry_time.year == sample_info.latest_year
    ]
    quarterly_net: dict[tuple[int, int], float] = defaultdict(float)
    daily_net: dict[date, float] = defaultdict(float)
    for outcome in outcomes:
        quarter = (outcome.entry_time.month - 1) // 3 + 1
        quarterly_net[(outcome.entry_time.year, quarter)] += outcome.net_usd
        daily_net[outcome.entry_time.date()] += outcome.net_usd
    max_drawdown = wave._max_drawdown(net_values)
    profit_factor = sum(positive) / abs(sum(negative)) if negative else 999.0
    average_win = statistics.mean(positive) if positive else 0.0
    average_loss = abs(statistics.mean(negative)) if negative else 0.0
    payoff_ratio = average_win / average_loss if average_loss > 0.0 else 999.0
    net_to_drawdown = sum(net_values) / abs(max_drawdown) if max_drawdown < 0.0 else 999.0
    return {
        "schema_version": 1,
        "strategy_id": strategy_id,
        "family": family,
        "quantity": risk.quantity,
        "target_points": wave._format_number(risk.target_points),
        "stop_points": wave._format_number(risk.stop_points),
        "raw_signals": raw_signal_count,
        "evaluated_trades": len(outcomes),
        "signal_days": len({outcome.entry_time.date() for outcome in outcomes}),
        "trades_per_week": wave._format_number(len(outcomes) / sample_info.weeks),
        "win_rate": wave._format_number(wins / len(outcomes)),
        "target_hit_rate": wave._format_number(target_hits / len(outcomes)),
        "stop_hit_rate": wave._format_number(stop_hits / len(outcomes)),
        "end_of_session_rate": wave._format_number(eod_exits / len(outcomes)),
        "net_usd": wave._format_number(sum(net_values)),
        "average_trade_usd": wave._format_number(statistics.mean(net_values)),
        "profit_factor": wave._format_number(profit_factor),
        "payoff_ratio": wave._format_number(payoff_ratio),
        "max_trade_sequence_drawdown_usd": wave._format_number(max_drawdown),
        "net_to_drawdown": wave._format_number(net_to_drawdown),
        "latest_year": sample_info.latest_year,
        "latest_year_trades": len(latest_year_values),
        "latest_year_net_usd": wave._format_number(sum(latest_year_values)),
        "worst_quarter_net_usd": wave._format_number(
            min(quarterly_net.values()) if quarterly_net else 0.0,
        ),
        "worst_day_usd": wave._format_number(min(daily_net.values()) if daily_net else 0.0),
        "worst_trade_usd": wave._format_number(min(net_values)),
        "average_holding_minutes": wave._format_number(
            statistics.mean(outcome.holding_minutes for outcome in outcomes),
        ),
        "median_holding_minutes": wave._format_number(
            statistics.median(outcome.holding_minutes for outcome in outcomes),
        ),
        "notes": (
            "runner scan; fixed target/stop; stop-first same-bar handling; "
            "one-hour signal spacing; one open trade per strategy"
        ),
    }


def _write_report(
    report_output: str,
    bars: list[wave.Bar],
    sweep_rows: list[dict[str, object]],
    best_row: dict[str, object] | None,
) -> None:
    accepted = [
        row for row in sweep_rows
        if int(row["evaluated_trades"]) >= 80
        and float(row["trades_per_week"]) >= 0.6
        and float(row["net_usd"]) > 0.0
        and float(row["latest_year_net_usd"]) > 0.0
        and float(row["profit_factor"]) >= 1.55
        and float(row["max_trade_sequence_drawdown_usd"]) > -2000.0
        and float(row["worst_quarter_net_usd"]) > -1500.0
        and float(row["net_to_drawdown"]) >= 2.0
    ]
    family_best = _best_by_family(sweep_rows)
    top_rows = sweep_rows[:15]
    lines = [
        "# MNQ Top-Runner Research",
        "",
        "Status: first-pass normal-profitability runner scan for MNQ.",
        "",
        "## Objective",
        "",
        "This pass skips the breakeven-frequency idea and searches for stronger "
        "runner-style bots: high profit factor, high net, and low trade-sequence "
        "drawdown. It is not eval-pass geometry.",
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
        "- entry families: lookback breakout, opening-range breakout, VWAP pullback, delta impulse",
        "- exit: fixed runner target/stop with session flatten",
        "- quantity: fixed `2 MNQ` for comparable PF/net/DD",
        "- target grid: `60,80,100,120,160,200,260,320` MNQ points",
        "- stop grid: `25,35,50,70,90,120` MNQ points",
        "- one-hour signal spacing and one open trade per strategy",
        "",
        "## Result",
        "",
    ]
    if best_row is None:
        lines.append("No rows were generated.")
    else:
        lines.extend(
            [
                f"Accepted rows by runner lens: `{len(accepted)}`.",
                "",
                "Top ranked row:",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Strategy | `{best_row['strategy_id']}` |",
                f"| Family | `{best_row['family']}` |",
                f"| Target / Stop | `{best_row['target_points']} / {best_row['stop_points']}` |",
                f"| Trades | `{best_row['evaluated_trades']}` |",
                f"| Trades/week | `{best_row['trades_per_week']}` |",
                f"| Net | `${best_row['net_usd']}` |",
                f"| PF | `{best_row['profit_factor']}` |",
                f"| Net/DD | `{best_row['net_to_drawdown']}` |",
                f"| Max trade-sequence DD | `${best_row['max_trade_sequence_drawdown_usd']}` |",
                f"| Latest-year net | `${best_row['latest_year_net_usd']}` |",
                f"| Worst quarter | `${best_row['worst_quarter_net_usd']}` |",
                f"| Win rate | `{float(best_row['win_rate']) * 100:.1f}%` |",
                f"| Target hit rate | `{float(best_row['target_hit_rate']) * 100:.1f}%` |",
                f"| Stop hit rate | `{float(best_row['stop_hit_rate']) * 100:.1f}%` |",
            ],
        )
    lines.extend(
        [
            "",
            "## Top Rows",
            "",
            "| Rank | Family | Target / Stop | Trades | /Wk | Net | PF | Net/DD | DD | Latest | Worst Q | Strategy |",
            "| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ],
    )
    for rank, row in enumerate(top_rows, start=1):
        lines.append(
            "| "
            f"{rank} | {row['family']} | {row['target_points']} / {row['stop_points']} | "
            f"{row['evaluated_trades']} | {row['trades_per_week']} | "
            f"{row['net_usd']} | {row['profit_factor']} | {row['net_to_drawdown']} | "
            f"{row['max_trade_sequence_drawdown_usd']} | {row['latest_year_net_usd']} | "
            f"{row['worst_quarter_net_usd']} | `{row['strategy_id']}` |"
        )
    lines.extend(
        [
            "",
            "## Best By Family",
            "",
            "| Family | Target / Stop | Trades | Net | PF | DD | Latest | Worst Q | Strategy |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ],
    )
    for row in family_best:
        lines.append(
            "| "
            f"{row['family']} | {row['target_points']} / {row['stop_points']} | "
            f"{row['evaluated_trades']} | {row['net_usd']} | {row['profit_factor']} | "
            f"{row['max_trade_sequence_drawdown_usd']} | {row['latest_year_net_usd']} | "
            f"{row['worst_quarter_net_usd']} | `{row['strategy_id']}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Rows from this scan are research leads only. A candidate must still pass "
            "slippage stress and fixed holdout validation before replay/mechanics.",
            "",
        ],
    )
    Path(report_output).write_text("\n".join(lines), encoding="utf-8")


def _best_by_family(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    best: dict[str, dict[str, object]] = {}
    for row in rows:
        family = str(row["family"])
        current = best.get(family)
        if current is None or _ranking_key(row) < _ranking_key(current):
            best[family] = row
    return sorted(best.values(), key=_ranking_key)


def _write_trade_audit(
    path: str,
    outcomes: list[RunnerOutcome],
    row: dict[str, object],
) -> None:
    rows = [
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
            "entry_price": wave._format_number(outcome.entry_price),
            "exit_price": wave._format_number(outcome.exit_price),
            "target_price": wave._format_number(outcome.target_price),
            "stop_price": wave._format_number(outcome.stop_price),
            "exit_reason": outcome.exit_reason,
            "holding_minutes": wave._format_number(outcome.holding_minutes),
            "gross_points": wave._format_number(outcome.gross_points),
            "net_usd": wave._format_number(outcome.net_usd),
            "notes": outcome.notes,
        }
        for outcome in outcomes
    ]
    _write_csv(path, TRADE_AUDIT_HEADER, rows)


def _write_csv(path: str, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


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


def _sample_info(bars: list[wave.Bar]) -> SampleInfo:
    trading_dates = tuple(sorted({bar.trade_date for bar in bars}))
    weeks = max(1.0, (trading_dates[-1] - trading_dates[0]).days / 7.0)
    return SampleInfo(
        trading_dates=trading_dates,
        weeks=weeks,
        latest_year=trading_dates[-1].year,
    )


def _ranking_key(row: dict[str, object]) -> tuple[float, ...]:
    trades = int(row["evaluated_trades"])
    net = float(row["net_usd"])
    latest = float(row["latest_year_net_usd"])
    pf = float(row["profit_factor"])
    max_drawdown = float(row["max_trade_sequence_drawdown_usd"])
    worst_quarter = float(row["worst_quarter_net_usd"])
    net_to_drawdown = float(row["net_to_drawdown"])
    accepted_penalty = (
        0.0
        if (
            trades >= 80
            and float(row["trades_per_week"]) >= 0.6
            and net > 0.0
            and latest > 0.0
            and pf >= 1.55
            and max_drawdown > -2000.0
            and worst_quarter > -1500.0
            and net_to_drawdown >= 2.0
        )
        else 1.0
    )
    return (
        accepted_penalty,
        0.0 if net > 0.0 else 1.0,
        0.0 if latest > 0.0 else 1.0,
        0.0 if worst_quarter > -1500.0 else 1.0,
        0.0 if max_drawdown > -2000.0 else 1.0,
        -pf,
        -net_to_drawdown,
        -net,
        max_drawdown,
        -trades,
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
