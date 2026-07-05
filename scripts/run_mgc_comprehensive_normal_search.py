#!/usr/bin/env python3
"""Comprehensive MGC normal-profitability strategy search."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import math
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable


DEFAULT_OUTPUT = "reports/mgc-comprehensive-normal-search.csv"
DEFAULT_REPORT_OUTPUT = "reports/mgc-comprehensive-normal-search.md"
DEFAULT_TRADE_AUDIT_OUTPUT = "reports/mgc-comprehensive-normal-search-best-trade-audit.csv"

SETUP_START = time(8, 20)
OPENING_RANGE_START = time(8, 20)
OPENING_RANGE_END = time(8, 50)
FLATTEN_TIME = time(16, 30)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a broad MGC normal-profitability search across strategy families.",
    )
    parser.add_argument("input", nargs="?", default=None)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--trade-audit-output", default=DEFAULT_TRADE_AUDIT_OUTPUT)
    parser.add_argument("--symbol", default="MGC")
    parser.add_argument("--minimum-trades", type=int, default=180)
    parser.add_argument("--deep", action="store_true", help="Use the larger slower parameter grid.")
    args = parser.parse_args()

    normal = _load_module("run_mgc_normal_bot_research.py", "mgc_normal_bot_research")
    mgc_eval = _load_module("run_mgc_eval_pass_initial_scan.py", "mgc_eval_pass_initial")
    core = mgc_eval._load_mnq_core()
    mgc_eval._patch_core_for_mgc(core)

    input_path = args.input or normal.DEFAULT_INPUT
    bars = core._load_feature_bars(input_path)
    bars_by_date = mgc_eval._active_bars_by_date(core._bars_by_date(bars))
    rows_by_index = core._rows_by_global_index(bars_by_date)
    signals_by_strategy = _generate_signals(core, bars_by_date, symbol=args.symbol, deep=args.deep)
    risk_profiles = _risk_profiles(core, normal, deep=args.deep)
    policies = _policies(deep=args.deep)

    rows = []
    best_row: dict[str, object] | None = None
    best_outcomes: list[Any] = []
    for strategy_id, signals in signals_by_strategy.items():
        if not signals:
            continue
        family = strategy_id.split(":", 1)[0]
        ordered_signals = sorted(signals, key=lambda signal: signal.bar.timestamp)
        for risk in risk_profiles:
            outcomes_by_signal_index = _outcomes_by_signal_index(
                core,
                ordered_signals,
                bars_by_date,
                rows_by_index,
                risk,
            )
            for policy in policies:
                outcomes = _evaluate_sequence(
                    ordered_signals,
                    outcomes_by_signal_index,
                    max_trades_per_day=policy["max_trades_per_day"],
                    reentry_gap_minutes=policy["reentry_gap_minutes"],
                )
                if len(outcomes) < args.minimum_trades:
                    continue
                policy_strategy_id = (
                    f"{strategy_id}:maxday{policy['max_trades_per_day']}"
                    f":gap{policy['reentry_gap_minutes']}"
                )
                row = normal._summary_row(
                    core,
                    policy_strategy_id,
                    family,
                    outcomes,
                    risk,
                    bars_by_date,
                )
                row["notes"] = (
                    "comprehensive MGC normal search; event-based signals; "
                    f"max_trades_per_day={policy['max_trades_per_day']}; "
                    f"reentry_gap_minutes={policy['reentry_gap_minutes']}"
                )
                rows.append(row)
                if _is_better_row(row, best_row):
                    best_row = row
                    best_outcomes = outcomes

    rows.sort(key=_ranking_key)
    _write_csv(args.output, normal.SUMMARY_HEADER, rows)
    if best_row is not None:
        core._write_trade_audit(args.trade_audit_output, best_outcomes, best_row)
    _write_report(args.report_output, bars, signals_by_strategy, rows, best_row)

    best_summary = "none"
    if best_row is not None:
        best_summary = (
            f"{best_row['strategy_id']} trades={best_row['trades']} "
            f"target={best_row['target_points']} stop={best_row['stop_points']} "
            f"pf={best_row['profit_factor']} net={best_row['net_usd']} "
            f"latest={best_row['latest_year_net_usd']} recent={best_row['recent_120_trade_days_net_usd']}"
        )
    print(
        f"wrote {len(rows)} MGC comprehensive normal rows to {args.output}; "
        f"best={best_summary}",
    )
    return 0


def _load_module(filename: str, module_name: str) -> ModuleType:
    module_path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _risk_profiles(core: ModuleType, normal: ModuleType, *, deep: bool) -> list[Any]:
    profiles = []
    round_turn_cost = 2.0 * normal.COMMISSION_PER_SIDE_USD + normal.SLIPPAGE_TICKS_PER_CONTRACT * normal.TICK_VALUE_USD
    point_pairs = (
        (3.0, 2.0),
        (4.0, 3.0),
        (5.0, 3.0),
        (6.0, 4.0),
        (8.0, 5.0),
        (10.0, 6.0),
        (12.0, 8.0),
        (15.0, 10.0),
        (20.0, 12.0),
        (25.0, 15.0),
        (30.0, 15.0),
        (30.0, 20.0),
    )
    if not deep:
        point_pairs = (
            (4.0, 3.0),
            (6.0, 4.0),
            (8.0, 5.0),
            (10.0, 6.0),
            (12.0, 8.0),
            (15.0, 10.0),
            (20.0, 12.0),
            (30.0, 15.0),
        )
    for target_points, stop_points in point_pairs:
        target_points = core._round_up_to_tick(target_points)
        stop_points = core._round_up_to_tick(stop_points)
        profiles.append(
            core.RiskProfile(
                quantity=1,
                target_net_usd=target_points * normal.POINT_VALUE_USD - round_turn_cost,
                stop_net_usd=stop_points * normal.POINT_VALUE_USD + round_turn_cost,
                target_points=target_points,
                stop_points=stop_points,
                round_turn_cost_usd=round_turn_cost,
            ),
        )
    return profiles


def _policies(*, deep: bool) -> list[dict[str, int]]:
    policies = [
        {"max_trades_per_day": 1, "reentry_gap_minutes": 0},
        {"max_trades_per_day": 2, "reentry_gap_minutes": 15},
    ]
    if deep:
        policies.append({"max_trades_per_day": 4, "reentry_gap_minutes": 30})
    return policies


def _generate_signals(
    core: ModuleType,
    bars_by_date: dict[date, list[Any]],
    *,
    symbol: str,
    deep: bool,
) -> dict[str, list[Any]]:
    signals_by_strategy: dict[str, list[Any]] = {}
    entry_ends = (time(10, 30), time(13, 30), time(16, 0)) if deep else (time(10, 30), time(13, 30))
    or_widths = (4.0, 6.0, 10.0, 15.0) if deep else (4.0, 6.0)
    buffers = (0.0, 0.5, 1.0) if deep else (0.0, 0.5)
    deltas = (0.0, 50.0, 100.0, 200.0) if deep else (0.0, 100.0)
    small_deltas = (0.0, 50.0, 100.0) if deep else (0.0, 100.0)
    close_locations = (0.50, 0.55, 0.60) if deep else (0.50, 0.55)

    for entry_end in entry_ends:
        for min_or_width in or_widths:
            for buffer_points in buffers:
                for delta_threshold in small_deltas:
                    for close_location_threshold in close_locations:
                        strategy_id = (
                            "mgc_or_breakout_all:"
                            f"min_or{min_or_width:g}:buf{buffer_points:g}:"
                            f"delta{delta_threshold:g}:cl{close_location_threshold:g}:"
                            f"end{_time_id(entry_end)}"
                        )
                        signals_by_strategy[strategy_id] = _all_opening_range_breakouts(
                            core,
                            bars_by_date,
                            strategy_id=strategy_id,
                            min_or_width=min_or_width,
                            buffer_points=buffer_points,
                            delta_threshold=delta_threshold,
                            close_location_threshold=close_location_threshold,
                            entry_end=entry_end,
                            symbol=symbol,
                        )

        for min_or_width in ((4.0, 6.0, 10.0) if deep else (4.0, 6.0)):
            for buffer_points in ((0.0, 0.5) if deep else (0.0,)):
                for retest_points in ((1.0, 2.0, 5.0) if deep else (2.0, 5.0)):
                    for delta_threshold in ((0.0, 50.0) if deep else (0.0, )):
                        strategy_id = (
                            "mgc_or_retest_all:"
                            f"min_or{min_or_width:g}:buf{buffer_points:g}:"
                            f"retest{retest_points:g}:delta{delta_threshold:g}:"
                            f"end{_time_id(entry_end)}"
                        )
                        signals_by_strategy[strategy_id] = _all_opening_range_retests(
                            core,
                            bars_by_date,
                            strategy_id=strategy_id,
                            min_or_width=min_or_width,
                            buffer_points=buffer_points,
                            retest_points=retest_points,
                            delta_threshold=delta_threshold,
                            entry_end=entry_end,
                            symbol=symbol,
                        )

        for lookback_bars in ((10, 20, 40, 60) if deep else (10, 20, 40)):
            for buffer_points in buffers:
                for delta_threshold in deltas:
                    for close_location_threshold in close_locations:
                        strategy_id = (
                            "mgc_lookback_breakout_all:"
                            f"lb{lookback_bars}:buf{buffer_points:g}:"
                            f"delta{delta_threshold:g}:cl{close_location_threshold:g}:"
                            f"end{_time_id(entry_end)}"
                        )
                        signals_by_strategy[strategy_id] = _all_lookback_breakouts(
                            core,
                            bars_by_date,
                            strategy_id=strategy_id,
                            lookback_bars=lookback_bars,
                            buffer_points=buffer_points,
                            delta_threshold=delta_threshold,
                            close_location_threshold=close_location_threshold,
                            entry_end=entry_end,
                            symbol=symbol,
                        )

        for stretch_points in ((8.0, 12.0, 15.0, 20.0, 25.0) if deep else (8.0, 15.0, 25.0)):
            for pullback_points in ((2.0, 5.0, 8.0) if deep else (2.0, 5.0)):
                for delta_threshold in small_deltas:
                    for close_location_threshold in (0.50, 0.55):
                        strategy_id = (
                            "mgc_vwap_pullback_all:"
                            f"stretch{stretch_points:g}:pb{pullback_points:g}:"
                            f"delta{delta_threshold:g}:cl{close_location_threshold:g}:"
                            f"end{_time_id(entry_end)}"
                        )
                        signals_by_strategy[strategy_id] = _all_vwap_pullbacks(
                            core,
                            bars_by_date,
                            strategy_id=strategy_id,
                            stretch_points=stretch_points,
                            pullback_points=pullback_points,
                            delta_threshold=delta_threshold,
                            close_location_threshold=close_location_threshold,
                            entry_end=entry_end,
                            symbol=symbol,
                        )

        for extension_points in ((8.0, 12.0, 15.0, 20.0, 25.0) if deep else (8.0, 15.0, 25.0)):
            for delta_threshold in deltas:
                for close_location_threshold in (0.35, 0.45):
                    strategy_id = (
                        "mgc_vwap_fade:"
                        f"ext{extension_points:g}:delta{delta_threshold:g}:"
                        f"cl{close_location_threshold:g}:end{_time_id(entry_end)}"
                    )
                    signals_by_strategy[strategy_id] = _all_vwap_fades(
                        core,
                        bars_by_date,
                        strategy_id=strategy_id,
                        extension_points=extension_points,
                        delta_threshold=delta_threshold,
                        close_location_threshold=close_location_threshold,
                        entry_end=entry_end,
                        symbol=symbol,
                    )

        for stretch_points in ((5.0, 8.0, 12.0) if deep else (5.0, 12.0)):
            for delta_threshold in small_deltas:
                for close_location_threshold in (0.50, 0.55):
                    strategy_id = (
                        "mgc_vwap_reclaim:"
                        f"stretch{stretch_points:g}:delta{delta_threshold:g}:"
                        f"cl{close_location_threshold:g}:end{_time_id(entry_end)}"
                    )
                    signals_by_strategy[strategy_id] = _all_vwap_reclaims(
                        core,
                        bars_by_date,
                        strategy_id=strategy_id,
                        stretch_points=stretch_points,
                        delta_threshold=delta_threshold,
                        close_location_threshold=close_location_threshold,
                        entry_end=entry_end,
                        symbol=symbol,
                    )

        for delta_threshold in ((100.0, 200.0, 300.0, 500.0) if deep else (100.0, 300.0)):
            for close_location_threshold in (0.55, 0.60):
                for require_vwap_alignment in (False, True):
                    strategy_id = (
                        "mgc_delta_impulse:"
                        f"delta{delta_threshold:g}:cl{close_location_threshold:g}:"
                        f"vwap{int(require_vwap_alignment)}:end{_time_id(entry_end)}"
                    )
                    signals_by_strategy[strategy_id] = _all_delta_impulses(
                        core,
                        bars_by_date,
                        strategy_id=strategy_id,
                        delta_threshold=delta_threshold,
                        close_location_threshold=close_location_threshold,
                        require_vwap_alignment=require_vwap_alignment,
                        entry_end=entry_end,
                        symbol=symbol,
                    )

    return {
        strategy_id: signals
        for strategy_id, signals in signals_by_strategy.items()
        if signals
    }


def _all_opening_range_breakouts(
    core: ModuleType,
    bars_by_date: dict[date, list[Any]],
    *,
    strategy_id: str,
    min_or_width: float,
    buffer_points: float,
    delta_threshold: float,
    close_location_threshold: float,
    entry_end: time,
    symbol: str,
) -> list[Any]:
    signals = []
    for rows in bars_by_date.values():
        opening_range = _opening_range(rows)
        if opening_range is None:
            continue
        or_high, or_low = opening_range
        if or_high - or_low < min_or_width:
            continue
        high_break = or_high + buffer_points
        low_break = or_low - buffer_points
        previous_close = None
        for row in rows:
            if not _in_entry_window(row.timestamp.time(), entry_end):
                previous_close = row.close
                continue
            if previous_close is not None:
                if (
                    previous_close <= high_break < row.close
                    and row.close >= row.vwap
                    and row.delta >= delta_threshold
                    and row.close_location >= close_location_threshold
                ):
                    signals.append(core.Signal(strategy_id, "long", row, f"{symbol} OR high breakout"))
                elif (
                    previous_close >= low_break > row.close
                    and row.close <= row.vwap
                    and row.delta <= -delta_threshold
                    and row.close_location <= 1.0 - close_location_threshold
                ):
                    signals.append(core.Signal(strategy_id, "short", row, f"{symbol} OR low breakout"))
            previous_close = row.close
    return signals


def _all_opening_range_retests(
    core: ModuleType,
    bars_by_date: dict[date, list[Any]],
    *,
    strategy_id: str,
    min_or_width: float,
    buffer_points: float,
    retest_points: float,
    delta_threshold: float,
    entry_end: time,
    symbol: str,
) -> list[Any]:
    signals = []
    for rows in bars_by_date.values():
        opening_range = _opening_range(rows)
        if opening_range is None:
            continue
        or_high, or_low = opening_range
        if or_high - or_low < min_or_width:
            continue
        high_break = or_high + buffer_points
        low_break = or_low - buffer_points
        broke_high = False
        broke_low = False
        last_signal_index = -100000
        for local_index, row in enumerate(rows):
            row_time = row.timestamp.time()
            if row.close > high_break:
                broke_high = True
            if row.close < low_break:
                broke_low = True
            if not _in_entry_window(row_time, entry_end):
                continue
            if local_index - last_signal_index < 15:
                continue
            if (
                broke_high
                and row.low <= high_break + retest_points
                and row.close > high_break
                and row.close >= row.vwap
                and row.delta >= delta_threshold
                and row.close_location >= 0.50
            ):
                signals.append(core.Signal(strategy_id, "long", row, f"{symbol} OR high retest"))
                last_signal_index = local_index
            elif (
                broke_low
                and row.high >= low_break - retest_points
                and row.close < low_break
                and row.close <= row.vwap
                and row.delta <= -delta_threshold
                and row.close_location <= 0.50
            ):
                signals.append(core.Signal(strategy_id, "short", row, f"{symbol} OR low retest"))
                last_signal_index = local_index
    return signals


def _all_lookback_breakouts(
    core: ModuleType,
    bars_by_date: dict[date, list[Any]],
    *,
    strategy_id: str,
    lookback_bars: int,
    buffer_points: float,
    delta_threshold: float,
    close_location_threshold: float,
    entry_end: time,
    symbol: str,
) -> list[Any]:
    signals = []
    for rows in bars_by_date.values():
        for index in range(lookback_bars, len(rows)):
            row = rows[index]
            if not _in_entry_window(row.timestamp.time(), entry_end):
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
                signals.append(core.Signal(strategy_id, "long", row, f"{symbol} lookback high breakout"))
            elif (
                previous_close >= low_break > row.close
                and row.close <= row.vwap
                and row.delta <= -delta_threshold
                and row.close_location <= 1.0 - close_location_threshold
            ):
                signals.append(core.Signal(strategy_id, "short", row, f"{symbol} lookback low breakout"))
    return signals


def _all_vwap_pullbacks(
    core: ModuleType,
    bars_by_date: dict[date, list[Any]],
    *,
    strategy_id: str,
    stretch_points: float,
    pullback_points: float,
    delta_threshold: float,
    close_location_threshold: float,
    entry_end: time,
    symbol: str,
) -> list[Any]:
    signals = []
    for rows in bars_by_date.values():
        stretched_high = False
        stretched_low = False
        last_signal_index = -100000
        for local_index, row in enumerate(rows):
            distance_from_vwap = row.close - row.vwap
            if distance_from_vwap >= stretch_points:
                stretched_high = True
            if distance_from_vwap <= -stretch_points:
                stretched_low = True
            if not _in_entry_window(row.timestamp.time(), entry_end):
                continue
            if local_index - last_signal_index < 30:
                continue
            if (
                stretched_high
                and row.low <= row.vwap + pullback_points
                and row.close > row.vwap + pullback_points
                and row.delta >= delta_threshold
                and row.close_location >= close_location_threshold
            ):
                signals.append(core.Signal(strategy_id, "long", row, f"{symbol} VWAP pullback continuation"))
                stretched_high = False
                last_signal_index = local_index
            elif (
                stretched_low
                and row.high >= row.vwap - pullback_points
                and row.close < row.vwap - pullback_points
                and row.delta <= -delta_threshold
                and row.close_location <= 1.0 - close_location_threshold
            ):
                signals.append(core.Signal(strategy_id, "short", row, f"{symbol} VWAP pullback continuation"))
                stretched_low = False
                last_signal_index = local_index
    return signals


def _all_vwap_fades(
    core: ModuleType,
    bars_by_date: dict[date, list[Any]],
    *,
    strategy_id: str,
    extension_points: float,
    delta_threshold: float,
    close_location_threshold: float,
    entry_end: time,
    symbol: str,
) -> list[Any]:
    signals = []
    for rows in bars_by_date.values():
        last_signal_index = -100000
        for local_index, row in enumerate(rows):
            if not _in_entry_window(row.timestamp.time(), entry_end):
                continue
            if local_index - last_signal_index < 15:
                continue
            distance_from_vwap = row.close - row.vwap
            if (
                distance_from_vwap >= extension_points
                and row.delta >= delta_threshold
                and row.close_location <= close_location_threshold
            ):
                signals.append(core.Signal(strategy_id, "short", row, f"{symbol} VWAP upper fade"))
                last_signal_index = local_index
            elif (
                distance_from_vwap <= -extension_points
                and row.delta <= -delta_threshold
                and row.close_location >= 1.0 - close_location_threshold
            ):
                signals.append(core.Signal(strategy_id, "long", row, f"{symbol} VWAP lower fade"))
                last_signal_index = local_index
    return signals


def _all_vwap_reclaims(
    core: ModuleType,
    bars_by_date: dict[date, list[Any]],
    *,
    strategy_id: str,
    stretch_points: float,
    delta_threshold: float,
    close_location_threshold: float,
    entry_end: time,
    symbol: str,
) -> list[Any]:
    signals = []
    for rows in bars_by_date.values():
        stretched_high = False
        stretched_low = False
        last_signal_index = -100000
        previous_row = None
        for local_index, row in enumerate(rows):
            if row.close - row.vwap >= stretch_points:
                stretched_high = True
            if row.close - row.vwap <= -stretch_points:
                stretched_low = True
            if previous_row is None:
                previous_row = row
                continue
            if not _in_entry_window(row.timestamp.time(), entry_end):
                previous_row = row
                continue
            if local_index - last_signal_index < 30:
                previous_row = row
                continue
            if (
                stretched_low
                and previous_row.close <= previous_row.vwap
                and row.close > row.vwap
                and row.delta >= delta_threshold
                and row.close_location >= close_location_threshold
            ):
                signals.append(core.Signal(strategy_id, "long", row, f"{symbol} VWAP reclaim long"))
                stretched_low = False
                last_signal_index = local_index
            elif (
                stretched_high
                and previous_row.close >= previous_row.vwap
                and row.close < row.vwap
                and row.delta <= -delta_threshold
                and row.close_location <= 1.0 - close_location_threshold
            ):
                signals.append(core.Signal(strategy_id, "short", row, f"{symbol} VWAP reclaim short"))
                stretched_high = False
                last_signal_index = local_index
            previous_row = row
    return signals


def _all_delta_impulses(
    core: ModuleType,
    bars_by_date: dict[date, list[Any]],
    *,
    strategy_id: str,
    delta_threshold: float,
    close_location_threshold: float,
    require_vwap_alignment: bool,
    entry_end: time,
    symbol: str,
) -> list[Any]:
    signals = []
    for rows in bars_by_date.values():
        last_signal_index = -100000
        for local_index, row in enumerate(rows):
            if not _in_entry_window(row.timestamp.time(), entry_end):
                continue
            if local_index - last_signal_index < 15:
                continue
            if (
                row.delta >= delta_threshold
                and row.close_location >= close_location_threshold
                and (not require_vwap_alignment or row.close >= row.vwap)
            ):
                signals.append(core.Signal(strategy_id, "long", row, f"{symbol} delta impulse long"))
                last_signal_index = local_index
            elif (
                row.delta <= -delta_threshold
                and row.close_location <= 1.0 - close_location_threshold
                and (not require_vwap_alignment or row.close <= row.vwap)
            ):
                signals.append(core.Signal(strategy_id, "short", row, f"{symbol} delta impulse short"))
                last_signal_index = local_index
    return signals


def _outcomes_by_signal_index(
    core: ModuleType,
    signals: list[Any],
    bars_by_date: dict[date, list[Any]],
    rows_by_index: dict[int, int],
    risk: Any,
) -> dict[int, Any]:
    outcomes = {}
    for signal in signals:
        rows = bars_by_date[signal.bar.trade_date]
        local_index = rows_by_index[signal.bar.index]
        following_rows = [
            row for row in rows[local_index + 1:]
            if row.timestamp.time() <= FLATTEN_TIME
        ]
        outcomes[signal.bar.index] = core._evaluate_signal(signal, following_rows, risk)
    return outcomes


def _evaluate_sequence(
    signals: list[Any],
    outcomes_by_signal_index: dict[int, Any],
    *,
    max_trades_per_day: int,
    reentry_gap_minutes: int,
) -> list[Any]:
    outcomes = []
    trades_by_date: Counter[date] = Counter()
    busy_until = datetime.min
    reentry_gap = timedelta(minutes=reentry_gap_minutes)
    for signal in signals:
        signal_date = signal.bar.trade_date
        if trades_by_date[signal_date] >= max_trades_per_day:
            continue
        if signal.bar.timestamp <= busy_until:
            continue
        outcome = outcomes_by_signal_index[signal.bar.index]
        outcomes.append(outcome)
        trades_by_date[signal_date] += 1
        busy_until = outcome.exit_time + reentry_gap
    return outcomes


def _ranking_key(row: dict[str, object]) -> tuple[float, ...]:
    trades = int(row["trades"])
    net = float(row["net_usd"])
    latest_net = float(row["latest_year_net_usd"])
    recent_net = float(row["recent_120_trade_days_net_usd"])
    profit_factor = float(row["profit_factor"])
    drawdown_to_net = float(row["drawdown_to_net"])
    worst_year = float(row["worst_year_net_usd"])
    worst_quarter = float(row["worst_quarter_net_usd"])
    return (
        0.0 if trades >= 300 else 1.0,
        0.0 if net > 0.0 and latest_net > 0.0 and recent_net > 0.0 else 1.0,
        0.0 if profit_factor >= 1.18 else 1.0,
        0.0 if worst_year >= -abs(net) * 0.25 else 1.0,
        0.0 if worst_quarter >= -abs(net) * 0.20 else 1.0,
        drawdown_to_net,
        -profit_factor,
        -latest_net,
        -net,
    )


def _is_better_row(row: dict[str, object], current_best: dict[str, object] | None) -> bool:
    if current_best is None:
        return True
    return _ranking_key(row) < _ranking_key(current_best)


def _accepted_rows(rows: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    return [
        row for row in rows
        if int(row["trades"]) >= 300
        and float(row["net_usd"]) > 0.0
        and float(row["latest_year_net_usd"]) > 0.0
        and float(row["recent_120_trade_days_net_usd"]) > 0.0
        and float(row["profit_factor"]) >= 1.18
        and float(row["latest_year_profit_factor"]) >= 1.05
        and float(row["drawdown_to_net"]) <= 0.75
        and float(row["worst_quarter_net_usd"]) >= -abs(float(row["net_usd"])) * 0.20
    ]


def _write_report(
    path: str,
    bars: list[Any],
    signals_by_strategy: dict[str, list[Any]],
    rows: list[dict[str, object]],
    best_row: dict[str, object] | None,
) -> None:
    accepted = _accepted_rows(rows)
    family_counts: Counter[str] = Counter()
    for strategy_id, signals in signals_by_strategy.items():
        family_counts[strategy_id.split(":", 1)[0]] += len(signals)

    lines = [
        "# MGC Comprehensive Normal Search",
        "",
        "Status: broad event-based MGC normal-profitability research. Not an ACSIL candidate yet.",
        "",
        "## Source",
        "",
        f"- rows: `{len(bars)}`",
        f"- dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        f"- unique dates: `{len({bar.trade_date for bar in bars})}`",
        "- instrument: `MGC`, one-minute Sierra order-flow export",
        "- simulation: non-overlapping trades, configurable max trades/day, fixed target/stop exits, flatten by `16:30`",
        "",
        "## Search Families",
        "",
    ]
    for family, count in family_counts.most_common():
        lines.append(f"- `{family}` raw signals: `{count}`")

    lines.extend(
        [
            "",
            "## Result",
            "",
        ],
    )
    if best_row is None:
        lines.append("No rows met the minimum-trade requirement.")
    else:
        lines.extend(
            [
                "Best row by broad normal-profitability ranking:",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Strategy | `{best_row['strategy_id']}` |",
                f"| Family | `{best_row['family']}` |",
                f"| Target / stop points | `{best_row['target_points']} / {best_row['stop_points']}` |",
                f"| Target / stop net | `${best_row['target_net_usd']} / ${best_row['stop_net_usd']}` |",
                f"| Trades | `{best_row['trades']}` |",
                f"| Signal days | `{best_row['signal_days']}` |",
                f"| Net | `${best_row['net_usd']}` |",
                f"| Average trade | `${best_row['average_trade_usd']}` |",
                f"| Win rate | `{float(best_row['win_rate']) * 100:.1f}%` |",
                f"| Profit factor | `{best_row['profit_factor']}` |",
                f"| Max trade-sequence drawdown | `${best_row['max_drawdown_usd']}` |",
                f"| Drawdown / net | `{float(best_row['drawdown_to_net']) * 100:.1f}%` |",
                f"| Latest-year trades | `{best_row['latest_year_trades']}` |",
                f"| Latest-year net | `${best_row['latest_year_net_usd']}` |",
                f"| Recent 120 trade-day net | `${best_row['recent_120_trade_days_net_usd']}` |",
                f"| Worst year | `${best_row['worst_year_net_usd']}` |",
                f"| Worst quarter | `${best_row['worst_quarter_net_usd']}` |",
                "",
            ],
        )
        if accepted:
            lines.append(f"Rows passing the broad first-pass lens: `{len(accepted)}`.")
        else:
            lines.append("No row passed the broad first-pass lens.")

    lines.extend(
        [
            "",
            "## Top Rows",
            "",
            "| Rank | Family | Target | Stop | Trades | Net | PF | DD/Net | Latest | Recent120 | Worst Q | Strategy |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ],
    )
    for rank, row in enumerate(rows[:25], start=1):
        lines.append(
            "| "
            f"{rank} | {row['family']} | {row['target_points']} | {row['stop_points']} | "
            f"{row['trades']} | {row['net_usd']} | {row['profit_factor']} | "
            f"{float(row['drawdown_to_net']) * 100:.1f}% | "
            f"{row['latest_year_net_usd']} | {row['recent_120_trade_days_net_usd']} | "
            f"{row['worst_quarter_net_usd']} | `{row['strategy_id']}` |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This pass directly addresses the sparse-sample problem by allowing repeated "
            "intraday signals and testing multiple families. A candidate still needs "
            "holdout/walk-forward validation and slippage stress before implementation.",
            "",
        ],
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def _write_csv(path: str, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _opening_range(rows: list[Any]) -> tuple[float, float] | None:
    opening_rows = [
        row for row in rows
        if OPENING_RANGE_START <= row.timestamp.time() < OPENING_RANGE_END
    ]
    if not opening_rows:
        return None
    return max(row.high for row in opening_rows), min(row.low for row in opening_rows)


def _in_entry_window(value: time, entry_end: time) -> bool:
    return SETUP_START <= value <= entry_end


def _time_id(value: time) -> str:
    return f"{value.hour:02d}{value.minute:02d}"


if __name__ == "__main__":
    raise SystemExit(main())
