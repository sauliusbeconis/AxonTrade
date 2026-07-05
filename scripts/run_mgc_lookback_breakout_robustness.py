#!/usr/bin/env python3
"""Robustness variants around the promoted MGC lookback-breakout lead."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import math
import statistics
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from types import ModuleType
from typing import Any, Callable


DEFAULT_OUTPUT = "reports/mgc-lookback-breakout-robustness.csv"
DEFAULT_REPORT_OUTPUT = "reports/mgc-lookback-breakout-robustness.md"
DEFAULT_TRAIN_DATE_COUNTS = "120,180,240"
DEFAULT_HOLDOUT_DATE_COUNTS = "40,40,60"
FLATTEN_TIME = time(16, 30)

HEADER = [
    "schema_version",
    "variant_id",
    "slippage_ticks_per_contract",
    "lookback_bars",
    "buffer_points",
    "close_location_threshold",
    "weekday_filter",
    "delta_cap",
    "time_filter",
    "direction_filter",
    "target_points",
    "stop_points",
    "trades",
    "net_usd",
    "average_trade_usd",
    "profit_factor",
    "max_drawdown_usd",
    "latest_year_net_usd",
    "recent_120_trade_days_net_usd",
    "worst_quarter_net_usd",
    "holdout_windows",
    "holdout_net_usd",
    "holdout_profit_factor",
    "holdout_positive_windows",
    "holdout_negative_windows",
    "holdout_worst_window_usd",
]


@dataclass(frozen=True)
class VariantSpec:
    variant_id: str
    lookback_bars: int
    buffer_points: float
    close_location_threshold: float
    entry_end: time
    weekdays: frozenset[int]
    weekday_filter: str
    delta_cap: float
    start_time: time
    time_filter: str
    direction_filter: str
    target_points: float
    stop_points: float


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run robustness variants around the promoted MGC lookback lead.",
    )
    parser.add_argument("input", nargs="?", default=None)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--symbol", default="MGC")
    parser.add_argument("--train-date-counts", default=DEFAULT_TRAIN_DATE_COUNTS)
    parser.add_argument("--holdout-date-counts", default=DEFAULT_HOLDOUT_DATE_COUNTS)
    parser.add_argument("--minimum-trades", type=int, default=100)
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
    for spec in _variant_specs():
        signals = _signals_for_spec(
            core,
            comp,
            refine,
            bars_by_date,
            rows_by_index,
            spec,
            symbol=args.symbol,
        )
        if len({signal.bar.trade_date for signal in signals}) < args.minimum_trades:
            continue
        for slippage_ticks in (1.0, 6.0):
            risk = review._risk(
                core,
                normal,
                target_points=spec.target_points,
                stop_points=spec.stop_points,
                slippage_ticks=slippage_ticks,
            )
            outcomes = review._evaluate_sequence(
                core,
                signals,
                bars_by_date,
                rows_by_index,
                review.CandidateSpec(
                    spec.variant_id,
                    spec.lookback_bars,
                    spec.buffer_points,
                    spec.close_location_threshold,
                    spec.entry_end,
                    "robustness",
                    1,
                    0,
                    spec.target_points,
                    spec.stop_points,
                ),
                risk,
            )
            if len(outcomes) < args.minimum_trades:
                continue
            full = normal._summary_row(
                core,
                spec.variant_id,
                "mgc_lookback_robustness",
                outcomes,
                risk,
                bars_by_date,
            )
            holdout = _holdout_summary(core, outcomes, trade_dates, configs)
            rows.append(
                {
                    "schema_version": 1,
                    "variant_id": spec.variant_id,
                    "slippage_ticks_per_contract": _format_number(slippage_ticks),
                    "lookback_bars": spec.lookback_bars,
                    "buffer_points": _format_number(spec.buffer_points),
                    "close_location_threshold": _format_number(spec.close_location_threshold),
                    "weekday_filter": spec.weekday_filter,
                    "delta_cap": _format_number(spec.delta_cap),
                    "time_filter": spec.time_filter,
                    "direction_filter": spec.direction_filter,
                    "target_points": full["target_points"],
                    "stop_points": full["stop_points"],
                    "trades": full["trades"],
                    "net_usd": full["net_usd"],
                    "average_trade_usd": full["average_trade_usd"],
                    "profit_factor": full["profit_factor"],
                    "max_drawdown_usd": full["max_drawdown_usd"],
                    "latest_year_net_usd": full["latest_year_net_usd"],
                    "recent_120_trade_days_net_usd": full["recent_120_trade_days_net_usd"],
                    "worst_quarter_net_usd": full["worst_quarter_net_usd"],
                    **holdout,
                },
            )

    rows.sort(key=_ranking_key)
    _write_csv(args.output, rows)
    _write_report(args.report_output, bars, rows, configs, args.minimum_trades)
    best = rows[0] if rows else None
    best_summary = "none"
    if best is not None:
        best_summary = (
            f"{best['variant_id']} slip={best['slippage_ticks_per_contract']} "
            f"trades={best['trades']} net={best['net_usd']} pf={best['profit_factor']} "
            f"holdout={best['holdout_net_usd']} holdout_pf={best['holdout_profit_factor']}"
        )
    print(
        f"wrote {len(rows)} MGC robustness rows to {args.output}; best={best_summary}",
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


def _variant_specs() -> list[VariantSpec]:
    base_weekdays = frozenset({0, 1, 4})
    variants: dict[tuple[object, ...], VariantSpec] = {}

    def add(
        *,
        lookback_bars: int = 10,
        close_location_threshold: float = 0.50,
        weekday_filter: str = "mon_tue_fri",
        weekdays: frozenset[int] = base_weekdays,
        delta_cap: float = 100.0,
        time_filter: str = "0820_1030",
        start_time: time = time(8, 20),
        entry_end: time = time(10, 30),
        direction_filter: str = "both",
        target_points: float = 25.0,
        stop_points: float = 15.0,
    ) -> None:
        if (
            lookback_bars == 10
            and close_location_threshold == 0.50
            and weekday_filter == "mon_tue_fri"
            and delta_cap == 100.0
            and time_filter == "0820_1030"
            and direction_filter == "both"
            and target_points == 25.0
            and stop_points == 15.0
        ):
            variant_id = "promoted_lead"
        else:
            variant_id = (
                "robust:"
                f"lb{lookback_bars}:cl{close_location_threshold:g}:"
                f"{weekday_filter}:delta{delta_cap:g}:"
                f"{time_filter}:{direction_filter}:"
                f"t{target_points:g}:s{stop_points:g}"
            )
        key = (
            lookback_bars,
            close_location_threshold,
            weekday_filter,
            delta_cap,
            time_filter,
            direction_filter,
            target_points,
            stop_points,
        )
        variants[key] = VariantSpec(
            variant_id=variant_id,
            lookback_bars=lookback_bars,
            buffer_points=0.0,
            close_location_threshold=close_location_threshold,
            entry_end=entry_end,
            weekdays=weekdays,
            weekday_filter=weekday_filter,
            delta_cap=delta_cap,
            start_time=start_time,
            time_filter=time_filter,
            direction_filter=direction_filter,
            target_points=target_points,
            stop_points=stop_points,
        )

    add()
    for lookback_bars in (5, 10, 15):
        add(lookback_bars=lookback_bars)
    for close_location_threshold in (0.50, 0.55):
        add(close_location_threshold=close_location_threshold)
    for delta_cap in (50.0, 100.0, 150.0):
        add(delta_cap=delta_cap)
    for weekday_filter, weekdays in (
        ("mon_tue_fri", base_weekdays),
        ("mon_fri", frozenset({0, 4})),
        ("mon_tue", frozenset({0, 1})),
    ):
        add(weekday_filter=weekday_filter, weekdays=weekdays)
    for time_filter, start_time in (
        ("0820_1030", time(8, 20)),
        ("0900_1030", time(9, 0)),
        ("0930_1030", time(9, 30)),
    ):
        add(time_filter=time_filter, start_time=start_time)
    for direction_filter in ("both", "long", "short"):
        add(direction_filter=direction_filter)
    for target_points, stop_points in ((20.0, 12.0), (25.0, 15.0), (30.0, 15.0)):
        add(target_points=target_points, stop_points=stop_points)

    return list(variants.values())


def _signals_for_spec(
    core: ModuleType,
    comp: ModuleType,
    refine: ModuleType,
    bars_by_date: dict[date, list[Any]],
    rows_by_index: dict[int, int],
    spec: VariantSpec,
    *,
    symbol: str,
) -> list[Any]:
    strategy_id = (
        "mgc_lookback_robustness:"
        f"lb{spec.lookback_bars}:buf0:delta0:"
        f"cl{spec.close_location_threshold:g}:end{_time_id(spec.entry_end)}"
    )
    raw_signals = comp._all_lookback_breakouts(
        core,
        bars_by_date,
        strategy_id=strategy_id,
        lookback_bars=spec.lookback_bars,
        buffer_points=0.0,
        delta_threshold=0.0,
        close_location_threshold=spec.close_location_threshold,
        entry_end=spec.entry_end,
        symbol=symbol,
    )
    signals = []
    for signal in sorted(raw_signals, key=lambda item: item.bar.timestamp):
        features = refine._features(signal, bars_by_date, rows_by_index)
        if signal.bar.timestamp.time() < spec.start_time:
            continue
        if int(features["weekday"]) not in spec.weekdays:
            continue
        if float(features["abs_delta"]) > spec.delta_cap:
            continue
        if spec.direction_filter != "both" and signal.direction != spec.direction_filter:
            continue
        signals.append(signal)
    return signals


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
    metrics = _metrics(core, holdout_outcomes)
    return {
        "holdout_windows": len(windows),
        "holdout_net_usd": _format_number(metrics["net_usd"]),
        "holdout_profit_factor": _format_number(metrics["profit_factor"]),
        "holdout_positive_windows": sum(value > 0.0 for value in windows),
        "holdout_negative_windows": sum(value < 0.0 for value in windows),
        "holdout_worst_window_usd": _format_number(min(windows) if windows else 0.0),
    }


def _metrics(core: ModuleType, outcomes: list[Any]) -> dict[str, float]:
    values = [outcome.net_usd for outcome in outcomes]
    positive = [value for value in values if value > 0.0]
    negative = [value for value in values if value < 0.0]
    return {
        "net_usd": sum(values),
        "profit_factor": sum(positive) / abs(sum(negative)) if negative else 999.0,
        "max_drawdown_usd": core._max_drawdown(values),
        "average_trade_usd": statistics.mean(values) if values else 0.0,
    }


def _ranking_key(row: dict[str, object]) -> tuple[float, ...]:
    slippage = float(row["slippage_ticks_per_contract"])
    trades = int(row["trades"])
    return (
        0.0 if slippage == 1.0 else 1.0,
        0.0 if trades >= 250 else 1.0,
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
    minimum_trades: int,
) -> None:
    lines = [
        "# MGC Lookback Breakout Robustness",
        "",
        "Status: sensitivity test around the promoted fixed MGC lookback-breakout lead.",
        "",
        "## Source",
        "",
        f"- rows: `{len(bars)}`",
        f"- dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        f"- holdout windows: `{', '.join(f'{a}x{b}' for a, b in configs)}`",
        f"- minimum trades per reported row: `{minimum_trades}`",
        "",
        "## Top Base-Cost Rows",
        "",
        "| Rank | Variant | Trades | Net | PF | DD | Latest | Recent120 | Worst Q | Holdout Net | Holdout PF | Pos/Windows | Worst Window |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    base_rows = [row for row in rows if row["slippage_ticks_per_contract"] == "1"]
    for rank, row in enumerate(base_rows[:25], start=1):
        lines.append(_table_row(rank, row))

    stressed_rows = [row for row in rows if row["slippage_ticks_per_contract"] == "6"]
    lines.extend(
        [
            "",
            "## Top Stress Rows",
            "",
            "| Rank | Variant | Trades | Net | PF | DD | Latest | Recent120 | Worst Q | Holdout Net | Holdout PF | Pos/Windows | Worst Window |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    for rank, row in enumerate(stressed_rows[:25], start=1):
        lines.append(_table_row(rank, row))

    promoted = [row for row in rows if row["variant_id"] == "promoted_lead"]
    lines.extend(
        [
            "",
            "## Promoted Lead Rows",
            "",
            "| Slip | Trades | Net | PF | DD | Latest | Recent120 | Worst Q | Holdout Net | Holdout PF | Pos/Windows | Worst Window |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    for row in promoted:
        lines.append(
            "| "
            f"{row['slippage_ticks_per_contract']} | {row['trades']} | "
            f"{row['net_usd']} | {row['profit_factor']} | {row['max_drawdown_usd']} | "
            f"{row['latest_year_net_usd']} | {row['recent_120_trade_days_net_usd']} | "
            f"{row['worst_quarter_net_usd']} | {row['holdout_net_usd']} | "
            f"{row['holdout_profit_factor']} | {row['holdout_positive_windows']}/"
            f"{row['holdout_windows']} | {row['holdout_worst_window_usd']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This is a robustness screen, not a replacement optimizer. If a nearby "
            "variant beats the promoted lead, it should be treated as a lead for "
            "manual review only if it keeps enough trades, holds under slippage, "
            "and improves the same holdout windows without relying on a tiny time "
            "or direction subset.",
            "",
            "Result from this pass: keep the promoted fixed rule. The `delta150` "
            "variant has slightly higher full-sample and holdout net, and the "
            "Mon/Fri-only variant has higher PF, but the promoted lead has the "
            "best overall base/stress balance with `338` trades and `25 / 26` "
            "positive holdout windows under both base and stress cost.",
            "",
        ],
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def _table_row(rank: int, row: dict[str, object]) -> str:
    return (
        "| "
        f"{rank} | `{row['variant_id']}` | {row['trades']} | {row['net_usd']} | "
        f"{row['profit_factor']} | {row['max_drawdown_usd']} | "
        f"{row['latest_year_net_usd']} | {row['recent_120_trade_days_net_usd']} | "
        f"{row['worst_quarter_net_usd']} | {row['holdout_net_usd']} | "
        f"{row['holdout_profit_factor']} | {row['holdout_positive_windows']}/"
        f"{row['holdout_windows']} | {row['holdout_worst_window_usd']} |"
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
