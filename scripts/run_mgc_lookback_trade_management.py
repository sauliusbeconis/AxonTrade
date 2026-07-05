#!/usr/bin/env python3
"""Trade-management research for the promoted MGC lookback-breakout signal."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import math
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any


DEFAULT_OUTPUT = "reports/mgc-lookback-trade-management.csv"
DEFAULT_REPORT_OUTPUT = "reports/mgc-lookback-trade-management.md"
DEFAULT_TRAIN_DATE_COUNTS = "120,180,240"
DEFAULT_HOLDOUT_DATE_COUNTS = "40,40,60"

HEADER = [
    "schema_version",
    "management_id",
    "signal_id",
    "slippage_ticks_per_contract",
    "target_points",
    "stop_points",
    "management",
    "clock_exit",
    "trigger_points",
    "trail_points",
    "trades",
    "net_usd",
    "average_trade_usd",
    "profit_factor",
    "max_drawdown_usd",
    "latest_year_net_usd",
    "recent_120_trade_days_net_usd",
    "worst_quarter_net_usd",
    "target_hits",
    "stop_hits",
    "managed_stop_hits",
    "clock_exits",
    "eod_exits",
    "holdout_windows",
    "holdout_net_usd",
    "holdout_profit_factor",
    "holdout_positive_windows",
    "holdout_negative_windows",
    "holdout_worst_window_usd",
]


@dataclass(frozen=True)
class SignalSpec:
    signal_id: str
    delta_cap: float
    close_location_threshold: float
    weekdays: frozenset[int]


@dataclass(frozen=True)
class ManagementSpec:
    management_id: str
    target_points: float
    stop_points: float
    management: str
    clock_exit: time
    trigger_points: float
    trail_points: float


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run MGC lookback breakout trade-management research.",
    )
    parser.add_argument("input", nargs="?", default=None)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--symbol", default="MGC")
    parser.add_argument("--train-date-counts", default=DEFAULT_TRAIN_DATE_COUNTS)
    parser.add_argument("--holdout-date-counts", default=DEFAULT_HOLDOUT_DATE_COUNTS)
    args = parser.parse_args()

    normal = _load_module("run_mgc_normal_bot_research.py", "mgc_normal_bot_research")
    mgc_eval = _load_module("run_mgc_eval_pass_initial_scan.py", "mgc_eval_pass_initial")
    comp = _load_module("run_mgc_comprehensive_normal_search.py", "mgc_comprehensive_normal_search")
    refine = _load_module("run_mgc_lookback_breakout_refine.py", "mgc_lookback_breakout_refine")
    review = _load_module("run_mgc_lookback_breakout_candidate_review.py", "mgc_lookback_breakout_candidate_review")
    core = mgc_eval._load_mnq_core()
    mgc_eval._patch_core_for_mgc(core)

    input_path = args.input or normal.DEFAULT_INPUT
    bars = core._load_feature_bars(input_path)
    bars_by_date = mgc_eval._active_bars_by_date(core._bars_by_date(bars))
    rows_by_index = core._rows_by_global_index(bars_by_date)
    trade_dates = sorted(bars_by_date)
    configs = _parse_configs(args.train_date_counts, args.holdout_date_counts)

    rows = []
    for signal_spec in _signal_specs():
        signals = _signals_for_spec(
            core,
            comp,
            refine,
            bars_by_date,
            rows_by_index,
            signal_spec,
            symbol=args.symbol,
        )
        for management_spec in _management_specs():
            for slippage_ticks in (1.0, 6.0):
                risk = review._risk(
                    core,
                    normal,
                    target_points=management_spec.target_points,
                    stop_points=management_spec.stop_points,
                    slippage_ticks=slippage_ticks,
                )
                outcomes = _evaluate_sequence(
                    core,
                    signals,
                    bars_by_date,
                    rows_by_index,
                    risk,
                    management_spec,
                )
                if len(outcomes) < 120:
                    continue
                summary = _summary(core, outcomes, bars_by_date)
                holdout = _holdout_summary(core, outcomes, trade_dates, configs)
                rows.append(
                    {
                        "schema_version": 1,
                        "management_id": management_spec.management_id,
                        "signal_id": signal_spec.signal_id,
                        "slippage_ticks_per_contract": _format_number(slippage_ticks),
                        "target_points": _format_number(management_spec.target_points),
                        "stop_points": _format_number(management_spec.stop_points),
                        "management": management_spec.management,
                        "clock_exit": _time_id(management_spec.clock_exit),
                        "trigger_points": _format_number(management_spec.trigger_points),
                        "trail_points": _format_number(management_spec.trail_points),
                        **summary,
                        **holdout,
                    },
                )

    rows.sort(key=_ranking_key)
    _write_csv(args.output, rows)
    _write_report(args.report_output, bars, rows, configs)
    best = rows[0] if rows else None
    best_summary = "none"
    if best is not None:
        best_summary = (
            f"{best['management_id']} signal={best['signal_id']} "
            f"slip={best['slippage_ticks_per_contract']} trades={best['trades']} "
            f"net={best['net_usd']} pf={best['profit_factor']} "
            f"holdout={best['holdout_net_usd']} holdout_pf={best['holdout_profit_factor']}"
        )
    print(
        f"wrote {len(rows)} MGC trade-management rows to {args.output}; best={best_summary}",
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


def _signal_specs() -> list[SignalSpec]:
    return [
        SignalSpec("delta100_mtf", 100.0, 0.50, frozenset({0, 1, 4})),
        SignalSpec("delta150_mtf", 150.0, 0.50, frozenset({0, 1, 4})),
        SignalSpec("delta100_mf", 100.0, 0.50, frozenset({0, 4})),
    ]


def _management_specs() -> list[ManagementSpec]:
    specs = []
    for target_points, stop_points in (
        (20.0, 10.0),
        (20.0, 12.0),
        (25.0, 12.0),
        (25.0, 15.0),
        (30.0, 15.0),
        (35.0, 15.0),
        (40.0, 15.0),
        (40.0, 20.0),
    ):
        for clock_exit in (time(12, 30), time(14, 0), time(16, 30)):
            specs.append(
                ManagementSpec(
                    f"fixed:t{target_points:g}:s{stop_points:g}:clock{_time_id(clock_exit)}",
                    target_points,
                    stop_points,
                    "fixed",
                    clock_exit,
                    0.0,
                    0.0,
                ),
            )
        if target_points >= 25.0:
            for trigger_points in (10.0, 15.0, 20.0):
                if trigger_points >= target_points:
                    continue
                specs.append(
                    ManagementSpec(
                        f"breakeven:t{target_points:g}:s{stop_points:g}:trig{trigger_points:g}",
                        target_points,
                        stop_points,
                        "breakeven",
                        time(16, 30),
                        trigger_points,
                        0.0,
                    ),
                )
            for trigger_points, trail_points in ((15.0, 10.0), (20.0, 12.0), (25.0, 15.0)):
                if trigger_points >= target_points:
                    continue
                specs.append(
                    ManagementSpec(
                        f"trail:t{target_points:g}:s{stop_points:g}:trig{trigger_points:g}:trail{trail_points:g}",
                        target_points,
                        stop_points,
                        "trail",
                        time(16, 30),
                        trigger_points,
                        trail_points,
                    ),
                )
    return specs


def _signals_for_spec(
    core: ModuleType,
    comp: ModuleType,
    refine: ModuleType,
    bars_by_date: dict[date, list[Any]],
    rows_by_index: dict[int, int],
    spec: SignalSpec,
    *,
    symbol: str,
) -> list[Any]:
    raw_signals = comp._all_lookback_breakouts(
        core,
        bars_by_date,
        strategy_id=f"mgc_management:{spec.signal_id}",
        lookback_bars=10,
        buffer_points=0.0,
        delta_threshold=0.0,
        close_location_threshold=spec.close_location_threshold,
        entry_end=time(10, 30),
        symbol=symbol,
    )
    signals = []
    for signal in sorted(raw_signals, key=lambda item: item.bar.timestamp):
        features = refine._features(signal, bars_by_date, rows_by_index)
        if int(features["weekday"]) not in spec.weekdays:
            continue
        if float(features["abs_delta"]) > spec.delta_cap:
            continue
        signals.append(signal)
    return signals


def _evaluate_sequence(
    core: ModuleType,
    signals: list[Any],
    bars_by_date: dict[date, list[Any]],
    rows_by_index: dict[int, int],
    risk: Any,
    management: ManagementSpec,
) -> list[Any]:
    outcomes = []
    trades_by_date: Counter[date] = Counter()
    busy_until = datetime.min
    for signal in signals:
        signal_date = signal.bar.trade_date
        if trades_by_date[signal_date] >= 1:
            continue
        if signal.bar.timestamp <= busy_until:
            continue
        rows = bars_by_date[signal_date]
        local_index = rows_by_index[signal.bar.index]
        following_rows = [
            row for row in rows[local_index + 1:]
            if row.timestamp.time() <= management.clock_exit
        ]
        outcome = _evaluate_managed_signal(core, signal, following_rows, risk, management)
        outcomes.append(outcome)
        trades_by_date[signal_date] += 1
        busy_until = outcome.exit_time
    return outcomes


def _evaluate_managed_signal(
    core: ModuleType,
    signal: Any,
    following_rows: list[Any],
    risk: Any,
    management: ManagementSpec,
) -> Any:
    is_long = signal.direction == "long"
    entry_price = signal.bar.close
    target_price = entry_price + risk.target_points if is_long else entry_price - risk.target_points
    initial_stop = entry_price - risk.stop_points if is_long else entry_price + risk.stop_points
    active_stop = initial_stop
    best_favorable = entry_price
    exit_bar = following_rows[-1] if following_rows else signal.bar
    exit_price = exit_bar.close
    exit_reason = "clock_exit" if following_rows else "no_following_bar"

    for row in following_rows:
        stop_hit = row.low <= active_stop if is_long else row.high >= active_stop
        target_hit = row.high >= target_price if is_long else row.low <= target_price
        if stop_hit:
            exit_bar = row
            exit_price = active_stop
            exit_reason = "managed_stop_hit" if active_stop != initial_stop else "stop_hit"
            break
        if target_hit:
            exit_bar = row
            exit_price = target_price
            exit_reason = "target_hit"
            break

        if is_long:
            best_favorable = max(best_favorable, row.high)
            favorable_move = best_favorable - entry_price
            if management.management == "breakeven" and favorable_move >= management.trigger_points:
                active_stop = max(active_stop, entry_price)
            elif management.management == "trail" and favorable_move >= management.trigger_points:
                active_stop = max(active_stop, best_favorable - management.trail_points)
        else:
            best_favorable = min(best_favorable, row.low)
            favorable_move = entry_price - best_favorable
            if management.management == "breakeven" and favorable_move >= management.trigger_points:
                active_stop = min(active_stop, entry_price)
            elif management.management == "trail" and favorable_move >= management.trigger_points:
                active_stop = min(active_stop, best_favorable + management.trail_points)

    if exit_reason == "clock_exit" and management.clock_exit == time(16, 30):
        exit_reason = "end_of_session"
    gross_points = exit_price - entry_price if is_long else entry_price - exit_price
    net_usd = gross_points * risk.quantity * 10.0 - risk.round_turn_cost_usd
    return core.TradeOutcome(
        strategy_id=signal.strategy_id,
        direction=signal.direction,
        entry_time=signal.bar.timestamp,
        exit_time=exit_bar.timestamp,
        entry_bar_index=signal.bar.index,
        exit_bar_index=exit_bar.index,
        entry_price=entry_price,
        exit_price=exit_price,
        target_price=target_price,
        stop_price=active_stop,
        exit_reason=exit_reason,
        holding_minutes=(exit_bar.timestamp - signal.bar.timestamp).total_seconds() / 60.0,
        gross_points=gross_points,
        net_usd=net_usd,
        notes=f"{signal.notes}; management={management.management_id}",
    )


def _summary(
    core: ModuleType,
    outcomes: list[Any],
    bars_by_date: dict[date, list[Any]],
) -> dict[str, object]:
    values = [outcome.net_usd for outcome in outcomes]
    positive = [value for value in values if value > 0.0]
    negative = [value for value in values if value < 0.0]
    latest_year = max(bars_by_date).year if bars_by_date else 0
    recent_dates = set(sorted(bars_by_date)[-120:])
    quarterly: dict[tuple[int, int], float] = defaultdict(float)
    latest_values = []
    recent_values = []
    for outcome in outcomes:
        entry_date = outcome.entry_time.date()
        quarter = (outcome.entry_time.month - 1) // 3 + 1
        quarterly[(outcome.entry_time.year, quarter)] += outcome.net_usd
        if outcome.entry_time.year == latest_year:
            latest_values.append(outcome.net_usd)
        if entry_date in recent_dates:
            recent_values.append(outcome.net_usd)
    return {
        "trades": len(outcomes),
        "net_usd": _format_number(sum(values)),
        "average_trade_usd": _format_number(statistics.mean(values) if values else 0.0),
        "profit_factor": _format_number(sum(positive) / abs(sum(negative)) if negative else 999.0),
        "max_drawdown_usd": _format_number(core._max_drawdown(values)),
        "latest_year_net_usd": _format_number(sum(latest_values)),
        "recent_120_trade_days_net_usd": _format_number(sum(recent_values)),
        "worst_quarter_net_usd": _format_number(min(quarterly.values()) if quarterly else 0.0),
        "target_hits": sum(outcome.exit_reason == "target_hit" for outcome in outcomes),
        "stop_hits": sum(outcome.exit_reason == "stop_hit" for outcome in outcomes),
        "managed_stop_hits": sum(outcome.exit_reason == "managed_stop_hit" for outcome in outcomes),
        "clock_exits": sum(outcome.exit_reason == "clock_exit" for outcome in outcomes),
        "eod_exits": sum(outcome.exit_reason == "end_of_session" for outcome in outcomes),
    }


def _holdout_summary(
    core: ModuleType,
    outcomes: list[Any],
    trade_dates: list[date],
    configs: list[tuple[int, int]],
) -> dict[str, object]:
    windows = []
    holdout_outcomes = []
    for train_count, holdout_count in configs:
        max_start = len(trade_dates) - train_count - holdout_count
        for start_index in range(0, max_start + 1, holdout_count):
            window_dates = set(
                trade_dates[
                    start_index + train_count:
                    start_index + train_count + holdout_count
                ],
            )
            window_outcomes = [
                outcome for outcome in outcomes
                if outcome.entry_time.date() in window_dates
            ]
            windows.append(sum(outcome.net_usd for outcome in window_outcomes))
            holdout_outcomes.extend(window_outcomes)
    values = [outcome.net_usd for outcome in holdout_outcomes]
    positive = [value for value in values if value > 0.0]
    negative = [value for value in values if value < 0.0]
    return {
        "holdout_windows": len(windows),
        "holdout_net_usd": _format_number(sum(values)),
        "holdout_profit_factor": _format_number(sum(positive) / abs(sum(negative)) if negative else 999.0),
        "holdout_positive_windows": sum(value > 0.0 for value in windows),
        "holdout_negative_windows": sum(value < 0.0 for value in windows),
        "holdout_worst_window_usd": _format_number(min(windows) if windows else 0.0),
    }


def _ranking_key(row: dict[str, object]) -> tuple[float, ...]:
    return (
        0.0 if float(row["slippage_ticks_per_contract"]) == 1.0 else 1.0,
        0.0 if int(row["trades"]) >= 250 else 1.0,
        int(row["holdout_negative_windows"]),
        -float(row["holdout_profit_factor"]),
        -float(row["profit_factor"]),
        -float(row["holdout_net_usd"]),
        abs(float(row["max_drawdown_usd"])),
        -float(row["net_usd"]),
    )


def _write_csv(path: str, rows: list[dict[str, object]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADER, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_report(
    path: str,
    bars: list[Any],
    rows: list[dict[str, object]],
    configs: list[tuple[int, int]],
) -> None:
    lines = [
        "# MGC Lookback Trade Management",
        "",
        "Status: trade-management research on the fixed promoted MGC lookback-breakout signal.",
        "",
        "## Source",
        "",
        f"- rows: `{len(bars)}`",
        f"- dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        f"- holdout windows: `{', '.join(f'{a}x{b}' for a, b in configs)}`",
        "",
        "## Top Base-Cost Rows",
        "",
        "| Rank | Signal | Management | Trades | Net | PF | DD | Latest | Recent120 | Worst Q | Holdout Net | Holdout PF | Pos/Windows | Worst Window |",
        "| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    base_rows = [row for row in rows if row["slippage_ticks_per_contract"] == "1"]
    for rank, row in enumerate(base_rows[:30], start=1):
        lines.append(_table_row(rank, row))

    lines.extend(
        [
            "",
            "## Top Stress Rows",
            "",
            "| Rank | Signal | Management | Trades | Net | PF | DD | Latest | Recent120 | Worst Q | Holdout Net | Holdout PF | Pos/Windows | Worst Window |",
            "| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    stress_rows = [row for row in rows if row["slippage_ticks_per_contract"] == "6"]
    for rank, row in enumerate(stress_rows[:30], start=1):
        lines.append(_table_row(rank, row))

    baseline_rows = [
        row for row in rows
        if row["signal_id"] == "delta100_mtf"
        and row["management_id"] == "fixed:t25:s15:clock1630"
    ]
    lines.extend(
        [
            "",
            "## Baseline Rows",
            "",
            "| Slip | Trades | Net | PF | DD | Latest | Recent120 | Holdout Net | Holdout PF | Pos/Windows |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    for row in baseline_rows:
        lines.append(
            "| "
            f"{row['slippage_ticks_per_contract']} | {row['trades']} | "
            f"{row['net_usd']} | {row['profit_factor']} | {row['max_drawdown_usd']} | "
            f"{row['latest_year_net_usd']} | {row['recent_120_trade_days_net_usd']} | "
            f"{row['holdout_net_usd']} | {row['holdout_profit_factor']} | "
            f"{row['holdout_positive_windows']}/{row['holdout_windows']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This pass searches exits and simple stop management while holding the signal "
            "family fixed. Rows that use fewer trades through a narrower signal spec "
            "can have prettier PF, so the baseline remains important unless a new row "
            "improves base cost, stressed cost, and holdout without shrinking the sample "
            "too far.",
            "",
        ],
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def _table_row(rank: int, row: dict[str, object]) -> str:
    return (
        "| "
        f"{rank} | `{row['signal_id']}` | `{row['management_id']}` | "
        f"{row['trades']} | {row['net_usd']} | {row['profit_factor']} | "
        f"{row['max_drawdown_usd']} | {row['latest_year_net_usd']} | "
        f"{row['recent_120_trade_days_net_usd']} | {row['worst_quarter_net_usd']} | "
        f"{row['holdout_net_usd']} | {row['holdout_profit_factor']} | "
        f"{row['holdout_positive_windows']}/{row['holdout_windows']} | "
        f"{row['holdout_worst_window_usd']} |"
    )


def _parse_configs(train_counts: str, holdout_counts: str) -> list[tuple[int, int]]:
    train_values = _parse_int_list(train_counts)
    holdout_values = _parse_int_list(holdout_counts)
    if len(train_values) != len(holdout_values):
        raise ValueError("train-date-counts and holdout-date-counts lengths must match")
    return list(zip(train_values, holdout_values))


def _parse_int_list(value: str) -> list[int]:
    values = [int(part.strip()) for part in value.split(",") if part.strip()]
    if not values or any(item <= 0 for item in values):
        raise ValueError("date-count lists must contain positive integers")
    return values


def _time_id(value: time) -> str:
    return f"{value.hour:02d}{value.minute:02d}"


def _format_number(value: float) -> str:
    if not math.isfinite(value):
        return "999"
    formatted = f"{value:.8f}".rstrip("0").rstrip(".")
    return formatted if formatted else "0"


if __name__ == "__main__":
    raise SystemExit(main())
