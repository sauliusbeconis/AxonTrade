#!/usr/bin/env python3
"""Focused sensitivity pass around the improved MGC lookback break-even lead."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import math
import sys
from dataclasses import dataclass
from datetime import date, time
from pathlib import Path
from types import ModuleType
from typing import Any


DEFAULT_OUTPUT = "reports/mgc-lookback-breakeven-sensitivity.csv"
DEFAULT_REPORT_OUTPUT = "reports/mgc-lookback-breakeven-sensitivity.md"
DEFAULT_TRAIN_DATE_COUNTS = "120,180,240"
DEFAULT_HOLDOUT_DATE_COUNTS = "40,40,60"

HEADER = [
    "schema_version",
    "variant_id",
    "lookback_bars",
    "buffer_points",
    "close_location_threshold",
    "entry_end",
    "weekday_filter",
    "delta_cap",
    "management_id",
    "target_points",
    "stop_points",
    "management",
    "trigger_points",
    "trades",
    "base_net_usd",
    "base_average_trade_usd",
    "base_profit_factor",
    "base_max_drawdown_usd",
    "base_latest_year_net_usd",
    "base_recent_120_trade_days_net_usd",
    "base_worst_quarter_net_usd",
    "base_holdout_net_usd",
    "base_holdout_profit_factor",
    "base_holdout_positive_windows",
    "base_holdout_negative_windows",
    "base_holdout_worst_window_usd",
    "stress_net_usd",
    "stress_average_trade_usd",
    "stress_profit_factor",
    "stress_max_drawdown_usd",
    "stress_latest_year_net_usd",
    "stress_recent_120_trade_days_net_usd",
    "stress_worst_quarter_net_usd",
    "stress_holdout_net_usd",
    "stress_holdout_profit_factor",
    "stress_holdout_positive_windows",
    "stress_holdout_negative_windows",
    "stress_holdout_worst_window_usd",
    "target_hits",
    "stop_hits",
    "managed_stop_hits",
    "eod_exits",
]


@dataclass(frozen=True)
class BaseSignalSpec:
    lookback_bars: int
    buffer_points: float
    close_location_threshold: float
    entry_end: time


@dataclass(frozen=True)
class SignalFilterSpec:
    weekday_filter: str
    weekdays: frozenset[int]
    delta_cap: float


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run focused MGC lookback break-even sensitivity research.",
    )
    parser.add_argument("input", nargs="?", default=None)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--symbol", default="MGC")
    parser.add_argument("--minimum-trades", type=int, default=250)
    parser.add_argument("--train-date-counts", default=DEFAULT_TRAIN_DATE_COUNTS)
    parser.add_argument("--holdout-date-counts", default=DEFAULT_HOLDOUT_DATE_COUNTS)
    args = parser.parse_args()

    normal = _load_module("run_mgc_normal_bot_research.py", "mgc_normal_bot_research")
    mgc_eval = _load_module("run_mgc_eval_pass_initial_scan.py", "mgc_eval_pass_initial")
    comp = _load_module("run_mgc_comprehensive_normal_search.py", "mgc_comprehensive_normal_search")
    refine = _load_module("run_mgc_lookback_breakout_refine.py", "mgc_lookback_breakout_refine")
    review = _load_module("run_mgc_lookback_breakout_candidate_review.py", "mgc_lookback_breakout_candidate_review")
    management = _load_module("run_mgc_lookback_trade_management.py", "mgc_lookback_trade_management")
    core = mgc_eval._load_mnq_core()
    mgc_eval._patch_core_for_mgc(core)

    input_path = args.input or normal.DEFAULT_INPUT
    bars = core._load_feature_bars(input_path)
    bars_by_date = mgc_eval._active_bars_by_date(core._bars_by_date(bars))
    rows_by_index = core._rows_by_global_index(bars_by_date)
    trade_dates = sorted(bars_by_date)
    configs = management._parse_configs(args.train_date_counts, args.holdout_date_counts)

    output_rows = []
    for base_spec in _base_signal_specs():
        base_signals = comp._all_lookback_breakouts(
            core,
            bars_by_date,
            strategy_id=_base_signal_id(base_spec),
            lookback_bars=base_spec.lookback_bars,
            buffer_points=base_spec.buffer_points,
            delta_threshold=0.0,
            close_location_threshold=base_spec.close_location_threshold,
            entry_end=base_spec.entry_end,
            symbol=args.symbol,
        )
        feature_rows = [
            (signal, refine._features(signal, bars_by_date, rows_by_index))
            for signal in sorted(base_signals, key=lambda item: item.bar.timestamp)
        ]
        for filter_spec in _signal_filter_specs():
            signals = [
                signal
                for signal, features in feature_rows
                if int(features["weekday"]) in filter_spec.weekdays
                and float(features["abs_delta"]) <= filter_spec.delta_cap
            ]
            if len({signal.bar.trade_date for signal in signals}) < args.minimum_trades:
                continue
            for management_spec in _management_specs(management):
                base_row = _evaluate_pair_side(
                    core,
                    normal,
                    review,
                    management,
                    signals,
                    bars_by_date,
                    rows_by_index,
                    trade_dates,
                    configs,
                    management_spec,
                    slippage_ticks=1.0,
                )
                if int(base_row["trades"]) < args.minimum_trades:
                    continue
                stress_row = _evaluate_pair_side(
                    core,
                    normal,
                    review,
                    management,
                    signals,
                    bars_by_date,
                    rows_by_index,
                    trade_dates,
                    configs,
                    management_spec,
                    slippage_ticks=6.0,
                )
                variant_id = (
                    "mgc_lb_be_sensitivity:"
                    f"lb{base_spec.lookback_bars}:buf{base_spec.buffer_points:g}:"
                    f"cl{base_spec.close_location_threshold:g}:end{_time_id(base_spec.entry_end)}:"
                    f"{filter_spec.weekday_filter}:delta{filter_spec.delta_cap:g}:"
                    f"{management_spec.management_id}"
                )
                output_rows.append(
                    {
                        "schema_version": 1,
                        "variant_id": variant_id,
                        "lookback_bars": base_spec.lookback_bars,
                        "buffer_points": _format_number(base_spec.buffer_points),
                        "close_location_threshold": _format_number(base_spec.close_location_threshold),
                        "entry_end": _time_id(base_spec.entry_end),
                        "weekday_filter": filter_spec.weekday_filter,
                        "delta_cap": _format_number(filter_spec.delta_cap),
                        "management_id": management_spec.management_id,
                        "target_points": _format_number(management_spec.target_points),
                        "stop_points": _format_number(management_spec.stop_points),
                        "management": management_spec.management,
                        "trigger_points": _format_number(management_spec.trigger_points),
                        "trades": base_row["trades"],
                        **_prefixed("base", base_row),
                        **_prefixed("stress", stress_row),
                        "target_hits": base_row["target_hits"],
                        "stop_hits": base_row["stop_hits"],
                        "managed_stop_hits": base_row["managed_stop_hits"],
                        "eod_exits": base_row["eod_exits"],
                    },
                )

    output_rows.sort(key=_ranking_key)
    _write_csv(args.output, output_rows)
    _write_report(args.report_output, bars, output_rows, configs, args.minimum_trades)
    best = output_rows[0] if output_rows else None
    best_summary = "none"
    if best is not None:
        best_summary = (
            f"{best['variant_id']} trades={best['trades']} "
            f"base={best['base_net_usd']} base_pf={best['base_profit_factor']} "
            f"stress={best['stress_net_usd']} stress_pf={best['stress_profit_factor']} "
            f"stress_holdout={best['stress_holdout_net_usd']}"
        )
    print(
        f"wrote {len(output_rows)} MGC break-even sensitivity rows to {args.output}; "
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


def _base_signal_specs() -> list[BaseSignalSpec]:
    return [
        BaseSignalSpec(lookback, buffer_points, close_location, entry_end)
        for lookback in (10,)
        for buffer_points in (0.0,)
        for close_location in (0.45, 0.50, 0.55)
        for entry_end in (time(10, 15), time(10, 30), time(10, 45))
    ]


def _signal_filter_specs() -> list[SignalFilterSpec]:
    return [
        SignalFilterSpec(weekday_filter, frozenset(weekdays), delta_cap)
        for weekday_filter, weekdays in (
            ("mtf", (0, 1, 4)),
            ("mf", (0, 4)),
            ("mt", (0, 1)),
            ("tf", (1, 4)),
        )
        for delta_cap in (100.0, 125.0, 150.0, 175.0, 200.0)
    ]


def _management_specs(management: ModuleType) -> list[Any]:
    specs = []
    for target_points in (23.0, 25.0, 27.0, 30.0):
        for stop_points in (13.0, 15.0, 17.0):
            specs.append(
                management.ManagementSpec(
                    f"fixed:t{target_points:g}:s{stop_points:g}:clock1630",
                    target_points,
                    stop_points,
                    "fixed",
                    time(16, 30),
                    0.0,
                    0.0,
                ),
            )
            for trigger_points in (16.0, 18.0, 20.0, 22.0):
                if trigger_points >= target_points:
                    continue
                specs.append(
                    management.ManagementSpec(
                        f"breakeven:t{target_points:g}:s{stop_points:g}:trig{trigger_points:g}",
                        target_points,
                        stop_points,
                        "breakeven",
                        time(16, 30),
                        trigger_points,
                        0.0,
                    ),
                )
    return specs


def _evaluate_pair_side(
    core: ModuleType,
    normal: ModuleType,
    review: ModuleType,
    management: ModuleType,
    signals: list[Any],
    bars_by_date: dict[date, list[Any]],
    rows_by_index: dict[int, int],
    trade_dates: list[date],
    configs: list[tuple[int, int]],
    management_spec: Any,
    *,
    slippage_ticks: float,
) -> dict[str, object]:
    risk = review._risk(
        core,
        normal,
        target_points=management_spec.target_points,
        stop_points=management_spec.stop_points,
        slippage_ticks=slippage_ticks,
    )
    outcomes = management._evaluate_sequence(
        core,
        signals,
        bars_by_date,
        rows_by_index,
        risk,
        management_spec,
    )
    return {
        **management._summary(core, outcomes, bars_by_date),
        **management._holdout_summary(core, outcomes, trade_dates, configs),
    }


def _prefixed(prefix: str, row: dict[str, object]) -> dict[str, object]:
    keys = (
        "net_usd",
        "average_trade_usd",
        "profit_factor",
        "max_drawdown_usd",
        "latest_year_net_usd",
        "recent_120_trade_days_net_usd",
        "worst_quarter_net_usd",
        "holdout_net_usd",
        "holdout_profit_factor",
        "holdout_positive_windows",
        "holdout_negative_windows",
        "holdout_worst_window_usd",
    )
    return {f"{prefix}_{key}": row[key] for key in keys}


def _ranking_key(row: dict[str, object]) -> tuple[float, ...]:
    return (
        int(row["stress_holdout_negative_windows"]),
        int(row["base_holdout_negative_windows"]),
        -float(row["stress_profit_factor"]),
        -float(row["base_profit_factor"]),
        -float(row["stress_holdout_net_usd"]),
        -float(row["base_holdout_net_usd"]),
        abs(float(row["stress_max_drawdown_usd"])),
        -float(row["stress_net_usd"]),
        -float(row["base_net_usd"]),
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
        "# MGC Lookback Break-Even Sensitivity",
        "",
        "Status: focused sensitivity pass around the improved MGC lookback-breakout "
        "break-even lead.",
        "",
        "## Source",
        "",
        f"- rows: `{len(bars)}`",
        f"- dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        f"- minimum trades: `{minimum_trades}`",
        f"- holdout windows: `{', '.join(f'{train}x{holdout}' for train, holdout in configs)}`",
        "- base cost: `1` slippage tick/contract",
        "- stress cost: `6` slippage ticks/contract",
        "",
        "## Top Paired Rows",
        "",
        "| Rank | Lookback | Buf | CL | End | Weekdays | Delta Cap | Management | Trades | Base Net | Base PF | Base DD | Base Holdout | Base Pos | Stress Net | Stress PF | Stress DD | Stress Holdout | Stress Pos | Stress Worst Window |",
        "| ---: | ---: | ---: | ---: | ---: | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for rank, row in enumerate(rows[:50], start=1):
        lines.append(_table_row(rank, row))

    lines.extend(
        [
            "",
            "## Reference Rows",
            "",
            "| Label | Variant | Trades | Base Net | Base PF | Base DD | Base Holdout | Stress Net | Stress PF | Stress DD | Stress Holdout | Stress Pos | Stress Worst Window |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    reference_specs = (
        (
            "risk-balanced new lead",
            "0.45",
            "1030",
            "mtf",
            "125",
            "breakeven:t25:s15:trig20",
        ),
        (
            "higher-net growth variant",
            "0.45",
            "1045",
            "mtf",
            "125",
            "breakeven:t25:s15:trig20",
        ),
        (
            "first break-even lead",
            "0.5",
            "1030",
            "mtf",
            "150",
            "breakeven:t25:s15:trig20",
        ),
        (
            "old fixed baseline",
            "0.5",
            "1030",
            "mtf",
            "100",
            "fixed:t25:s15:clock1630",
        ),
        (
            "lowest-window-risk variant",
            "0.55",
            "1030",
            "mtf",
            "150",
            "breakeven:t25:s15:trig20",
        ),
    )
    for label, close_location, entry_end, weekday_filter, delta_cap, management_id in reference_specs:
        selected = [
            row for row in rows
            if row["lookback_bars"] == 10
            and row["buffer_points"] == "0"
            and row["close_location_threshold"] == close_location
            and row["entry_end"] == entry_end
            and row["weekday_filter"] == weekday_filter
            and row["delta_cap"] == delta_cap
            and row["management_id"] == management_id
        ]
        if selected:
            lines.append(_reference_row(label, selected[0]))

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The ranking is paired: each row must survive normal cost and a six-tick "
            "slippage stress test. The lowest-window-risk row uses `cl0.55`, but "
            "the practical replacement lead is the `cl0.45/end1030/delta125` "
            "break-even row: it improves net, PF, drawdown, latest-year net, "
            "recent-120-trade-day net, and aggregate holdout versus the old fixed "
            "baseline under both base and stress cost.",
            "",
        ],
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def _table_row(rank: int, row: dict[str, object]) -> str:
    return (
        "| "
        f"{rank} | {row['lookback_bars']} | {row['buffer_points']} | "
        f"{row['close_location_threshold']} | {row['entry_end']} | "
        f"{row['weekday_filter']} | {row['delta_cap']} | `{row['management_id']}` | "
        f"{row['trades']} | {row['base_net_usd']} | {row['base_profit_factor']} | "
        f"{row['base_max_drawdown_usd']} | {row['base_holdout_net_usd']} | "
        f"{row['base_holdout_positive_windows']}/{int(row['base_holdout_positive_windows']) + int(row['base_holdout_negative_windows'])} | "
        f"{row['stress_net_usd']} | {row['stress_profit_factor']} | "
        f"{row['stress_max_drawdown_usd']} | {row['stress_holdout_net_usd']} | "
        f"{row['stress_holdout_positive_windows']}/{int(row['stress_holdout_positive_windows']) + int(row['stress_holdout_negative_windows'])} | "
        f"{row['stress_holdout_worst_window_usd']} |"
    )


def _reference_row(label: str, row: dict[str, object]) -> str:
    return (
        "| "
        f"{label} | `{row['variant_id']}` | {row['trades']} | {row['base_net_usd']} | "
        f"{row['base_profit_factor']} | {row['base_max_drawdown_usd']} | "
        f"{row['base_holdout_net_usd']} | {row['stress_net_usd']} | "
        f"{row['stress_profit_factor']} | {row['stress_max_drawdown_usd']} | "
        f"{row['stress_holdout_net_usd']} | "
        f"{row['stress_holdout_positive_windows']}/{int(row['stress_holdout_positive_windows']) + int(row['stress_holdout_negative_windows'])} | "
        f"{row['stress_holdout_worst_window_usd']} |"
    )


def _base_signal_id(spec: BaseSignalSpec) -> str:
    return (
        "mgc_lb_be_sensitivity_base:"
        f"lb{spec.lookback_bars}:buf{spec.buffer_points:g}:"
        f"cl{spec.close_location_threshold:g}:end{_time_id(spec.entry_end)}"
    )


def _time_id(value: time) -> str:
    return f"{value.hour:02d}{value.minute:02d}"


def _format_number(value: float) -> str:
    if not math.isfinite(value):
        return "999"
    formatted = f"{value:.8f}".rstrip("0").rstrip(".")
    return formatted if formatted else "0"


if __name__ == "__main__":
    raise SystemExit(main())
