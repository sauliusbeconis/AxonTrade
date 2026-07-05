#!/usr/bin/env python3
"""Refine the first MGC normal-profitability VWAP pullback lead."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import sys
from collections import namedtuple
from datetime import time
from pathlib import Path
from types import ModuleType
from typing import Any, Callable


DEFAULT_OUTPUT = "reports/mgc-normal-bot-refine.csv"
DEFAULT_REPORT_OUTPUT = "reports/mgc-normal-bot-refine.md"
DEFAULT_TRADE_AUDIT_OUTPUT = "reports/mgc-normal-bot-refine-best-trade-audit.csv"

FilterSpec = namedtuple("FilterSpec", "filter_id keep")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refine the first MGC normal-profitability VWAP pullback lead.",
    )
    parser.add_argument("input", nargs="?", default=None)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--trade-audit-output", default=DEFAULT_TRADE_AUDIT_OUTPUT)
    parser.add_argument("--minimum-trades", type=int, default=50)
    parser.add_argument("--symbol", default="MGC")
    args = parser.parse_args()

    normal = _load_module("run_mgc_normal_bot_research.py", "mgc_normal_bot_research")
    mgc_eval = _load_module("run_mgc_eval_pass_initial_scan.py", "mgc_eval_pass_initial")
    core = mgc_eval._load_mnq_core()
    mgc_eval._patch_core_for_mgc(core)

    input_path = args.input or normal.DEFAULT_INPUT
    bars = core._load_feature_bars(input_path)
    bars_by_date = mgc_eval._active_bars_by_date(core._bars_by_date(bars))
    rows_by_index = core._rows_by_global_index(bars_by_date)
    base_signals = _base_vwap_pullback_signals(core, bars_by_date, symbol=args.symbol)
    features_by_index = {
        signal.bar.index: _features(core, signal, bars_by_date, rows_by_index)
        for signal in base_signals
    }

    risk_profiles = _refined_risk_profiles(core, normal)
    filters = _filter_specs()
    rows = []
    best_row: dict[str, object] | None = None
    best_outcomes = []
    for filter_spec in filters:
        filtered = [
            signal for signal in base_signals
            if filter_spec.keep(signal, features_by_index[signal.bar.index])
        ]
        if len(filtered) < args.minimum_trades:
            continue
        for risk in risk_profiles:
            strategy_id = f"{_base_strategy_id()}:filter{filter_spec.filter_id}"
            outcomes = core._evaluate_signals(filtered, bars_by_date, risk)
            row = normal._summary_row(
                core,
                strategy_id,
                "mgc_vwap_pullback_refined",
                outcomes,
                risk,
                bars_by_date,
            )
            row["notes"] = f"refined from base MGC VWAP pullback; filter={filter_spec.filter_id}"
            rows.append(row)
            if normal._is_better_row(row, best_row):
                best_row = row
                best_outcomes = outcomes

    rows.sort(key=normal._ranking_key)
    _write_csv(args.output, normal.SUMMARY_HEADER, rows)
    if best_row is not None:
        core._write_trade_audit(args.trade_audit_output, best_outcomes, best_row)
    _write_report(args.report_output, normal, bars, base_signals, rows, best_row)

    best_summary = "none"
    if best_row is not None:
        best_summary = (
            f"{best_row['strategy_id']} qty={best_row['quantity']} "
            f"target={best_row['target_points']} stop={best_row['stop_points']} "
            f"pf={best_row['profit_factor']} net={best_row['net_usd']} "
            f"latest={best_row['latest_year_net_usd']}"
        )
    print(
        f"wrote {len(rows)} MGC normal refine rows to {args.output}; "
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


def _base_strategy_id() -> str:
    return "mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri0"


def _base_vwap_pullback_signals(
    core: ModuleType,
    bars_by_date: dict[Any, list[Any]],
    *,
    symbol: str,
) -> list[Any]:
    signals = []
    strategy_id = _base_strategy_id()
    for rows in bars_by_date.values():
        signal = core._vwap_pullback_signal(
            rows,
            strategy_id=strategy_id,
            stretch_points=15.0,
            pullback_points=5.0,
            delta_threshold=0.0,
            close_location_threshold=0.55,
            entry_end=time(10, 30),
            skip_friday=False,
            symbol=symbol,
        )
        if signal is not None:
            signals.append(signal)
    return signals


def _features(
    core: ModuleType,
    signal: Any,
    bars_by_date: dict[Any, list[Any]],
    rows_by_index: dict[int, int],
) -> dict[str, float | int | str]:
    rows = bars_by_date[signal.bar.trade_date]
    local_index = rows_by_index[signal.bar.index]
    day_rows = rows[: local_index + 1]
    return {
        "weekday": signal.bar.timestamp.weekday(),
        "time_minutes": signal.bar.timestamp.hour * 60 + signal.bar.timestamp.minute,
        "direction": signal.direction,
        "abs_delta": abs(signal.bar.delta),
        "bar_range": signal.bar.high - signal.bar.low,
        "abs_vwap_distance": abs(signal.bar.close - signal.bar.vwap),
        "day_range_so_far": max(row.high for row in day_rows) - min(row.low for row in day_rows),
        "close_location": signal.bar.close_location,
    }


def _refined_risk_profiles(core: ModuleType, normal: ModuleType) -> list[Any]:
    profiles = []
    for quantity in (1, 2, 3, 5):
        round_turn_cost = quantity * (
            2.0 * normal.COMMISSION_PER_SIDE_USD
            + normal.SLIPPAGE_TICKS_PER_CONTRACT * normal.TICK_VALUE_USD
        )
        for target_points, stop_points in (
            (20.0, 12.0),
            (25.0, 12.0),
            (25.0, 15.0),
            (30.0, 15.0),
            (30.0, 18.0),
            (35.0, 20.0),
            (25.0, 20.0),
            (30.0, 20.0),
        ):
            target_points = core._round_up_to_tick(target_points)
            stop_points = core._round_up_to_tick(stop_points)
            profiles.append(
                core.RiskProfile(
                    quantity=quantity,
                    target_net_usd=target_points * quantity * normal.POINT_VALUE_USD - round_turn_cost,
                    stop_net_usd=stop_points * quantity * normal.POINT_VALUE_USD + round_turn_cost,
                    target_points=target_points,
                    stop_points=stop_points,
                    round_turn_cost_usd=round_turn_cost,
                ),
            )
    return profiles


def _filter_specs() -> list[FilterSpec]:
    direction_sets: dict[str, Callable[[str], bool]] = {
        "both": lambda direction: True,
        "long": lambda direction: direction == "long",
        "short": lambda direction: direction == "short",
    }
    weekday_sets: dict[str, set[int]] = {
        "allweek": {0, 1, 2, 3, 4},
        "nofri": {0, 1, 2, 3},
        "montuewed": {0, 1, 2},
        "tuewedthu": {1, 2, 3},
        "tuewed": {1, 2},
        "wedthu": {2, 3},
    }
    time_windows: dict[str, tuple[int, int]] = {
        "0820_1030": (8 * 60 + 20, 10 * 60 + 30),
        "0820_0930": (8 * 60 + 20, 9 * 60 + 30),
        "0900_1030": (9 * 60, 10 * 60 + 30),
        "0930_1030": (9 * 60 + 30, 10 * 60 + 30),
        "0820_1000": (8 * 60 + 20, 10 * 60),
    }
    context_filters: dict[str, Callable[[dict[str, float | int | str]], bool]] = {
        "none": lambda f: True,
        "absdelta100": lambda f: float(f["abs_delta"]) <= 100.0,
        "absdelta200": lambda f: float(f["abs_delta"]) <= 200.0,
        "barrange5": lambda f: float(f["bar_range"]) <= 5.0,
        "barrange8": lambda f: float(f["bar_range"]) <= 8.0,
        "dayrange40": lambda f: float(f["day_range_so_far"]) <= 40.0,
        "dayrange60": lambda f: float(f["day_range_so_far"]) <= 60.0,
        "vwapdist20": lambda f: float(f["abs_vwap_distance"]) <= 20.0,
        "vwapdist30": lambda f: float(f["abs_vwap_distance"]) <= 30.0,
        "bar8_day60": lambda f: float(f["bar_range"]) <= 8.0 and float(f["day_range_so_far"]) <= 60.0,
        "abs200_day60": lambda f: float(f["abs_delta"]) <= 200.0 and float(f["day_range_so_far"]) <= 60.0,
    }

    specs = []
    for direction_id, direction_keep in direction_sets.items():
        for weekday_id, weekdays in weekday_sets.items():
            for time_id, (start_minute, end_minute) in time_windows.items():
                for context_id, context_keep in context_filters.items():
                    filter_id = f"{direction_id}:{weekday_id}:{time_id}:{context_id}"

                    def keep(
                        signal: Any,
                        features: dict[str, float | int | str],
                        *,
                        direction_keep: Callable[[str], bool] = direction_keep,
                        weekdays: set[int] = weekdays,
                        start_minute: int = start_minute,
                        end_minute: int = end_minute,
                        context_keep: Callable[[dict[str, float | int | str]], bool] = context_keep,
                    ) -> bool:
                        return (
                            direction_keep(signal.direction)
                            and int(features["weekday"]) in weekdays
                            and start_minute <= int(features["time_minutes"]) <= end_minute
                            and context_keep(features)
                        )

                    specs.append(FilterSpec(filter_id, keep))
    return specs


def _write_csv(path: str, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_report(
    path: str,
    normal: ModuleType,
    bars: list[Any],
    base_signals: list[Any],
    rows: list[dict[str, object]],
    best_row: dict[str, object] | None,
) -> None:
    accepted = normal._accepted_rows(rows)
    lines = [
        "# MGC Normal Bot Refinement",
        "",
        "Status: refinement of the first MGC normal-profitability VWAP pullback lead.",
        "",
        "## Source",
        "",
        f"- rows: `{len(bars)}`",
        f"- dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        f"- base strategy: `{_base_strategy_id()}`",
        f"- base signals: `{len(base_signals)}`",
        "",
        "## Filter Search",
        "",
        "- direction: both, long-only, short-only",
        "- weekdays: all week, no Friday, Monday-Wednesday, Tuesday-Thursday, Tuesday-Wednesday, Wednesday-Thursday",
        "- entry windows: `08:20-10:30`, `08:20-09:30`, `09:00-10:30`, `09:30-10:30`, `08:20-10:00`",
        "- context: absolute delta caps, bar-range caps, day-range caps, VWAP-distance caps, simple combinations",
        "- risk points: `20/12`, `25/12`, `25/15`, `30/15`, `30/18`, `35/20`, `25/20`, `30/20`",
        "",
        "## Result",
        "",
    ]
    if best_row is None:
        lines.append("No rows were generated.")
    else:
        lines.extend(
            [
                "Best refined row by normal-profitability ranking:",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Strategy | `{best_row['strategy_id']}` |",
                f"| Quantity | `{best_row['quantity']}` |",
                f"| Target / stop points | `{best_row['target_points']} / {best_row['stop_points']}` |",
                f"| Target / stop net | `${best_row['target_net_usd']} / ${best_row['stop_net_usd']}` |",
                f"| Trades | `{best_row['trades']}` |",
                f"| Net | `${best_row['net_usd']}` |",
                f"| Average trade | `${best_row['average_trade_usd']}` |",
                f"| Win rate | `{float(best_row['win_rate']) * 100:.1f}%` |",
                f"| Profit factor | `{best_row['profit_factor']}` |",
                f"| Max drawdown | `${best_row['max_drawdown_usd']}` |",
                f"| Drawdown / net | `{float(best_row['drawdown_to_net']) * 100:.1f}%` |",
                f"| Latest-year net | `${best_row['latest_year_net_usd']}` |",
                f"| Recent 120 trade-day net | `${best_row['recent_120_trade_days_net_usd']}` |",
                f"| Worst year | `${best_row['worst_year_net_usd']}` |",
                f"| Worst quarter | `${best_row['worst_quarter_net_usd']}` |",
                "",
            ],
        )
        if accepted:
            lines.append(f"Rows passing the normal-profitability lens: `{len(accepted)}`.")
        else:
            lines.append("No refined row passed the normal-profitability lens.")
    lines.extend(
        [
            "",
            "## Top Rows",
            "",
            "| Rank | Qty | Target | Stop | Trades | Net | PF | DD/Net | Latest | Recent120 | Worst Q | Strategy |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ],
    )
    for rank, row in enumerate(rows[:20], start=1):
        lines.append(
            "| "
            f"{rank} | {row['quantity']} | {row['target_points']} | "
            f"{row['stop_points']} | {row['trades']} | {row['net_usd']} | "
            f"{row['profit_factor']} | {float(row['drawdown_to_net']) * 100:.1f}% | "
            f"{row['latest_year_net_usd']} | {row['recent_120_trade_days_net_usd']} | "
            f"{row['worst_quarter_net_usd']} | `{row['strategy_id']}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The refinement is still offline research. Prefer candidates that improve "
            "recent performance and reduce bad-quarter behavior without becoming too sparse.",
            "",
        ],
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
