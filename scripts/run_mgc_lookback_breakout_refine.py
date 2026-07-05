#!/usr/bin/env python3
"""Refine the MGC high-frequency lookback-breakout lead."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import sys
from collections import namedtuple
from datetime import date, datetime, time, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any, Callable


DEFAULT_OUTPUT = "reports/mgc-lookback-breakout-refine.csv"
DEFAULT_REPORT_OUTPUT = "reports/mgc-lookback-breakout-refine.md"
DEFAULT_TRADE_AUDIT_OUTPUT = "reports/mgc-lookback-breakout-refine-best-trade-audit.csv"

FLATTEN_TIME = time(16, 30)
FilterSpec = namedtuple("FilterSpec", "filter_id keep")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refine the high-frequency MGC lookback-breakout normal lead.",
    )
    parser.add_argument("input", nargs="?", default=None)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--trade-audit-output", default=DEFAULT_TRADE_AUDIT_OUTPUT)
    parser.add_argument("--minimum-trades", type=int, default=250)
    parser.add_argument("--symbol", default="MGC")
    args = parser.parse_args()

    normal = _load_module("run_mgc_normal_bot_research.py", "mgc_normal_bot_research")
    mgc_eval = _load_module("run_mgc_eval_pass_initial_scan.py", "mgc_eval_pass_initial")
    comp = _load_module("run_mgc_comprehensive_normal_search.py", "mgc_comprehensive_normal_search")
    core = mgc_eval._load_mnq_core()
    mgc_eval._patch_core_for_mgc(core)

    input_path = args.input or normal.DEFAULT_INPUT
    bars = core._load_feature_bars(input_path)
    bars_by_date = mgc_eval._active_bars_by_date(core._bars_by_date(bars))
    rows_by_index = core._rows_by_global_index(bars_by_date)
    filters = _filter_specs()
    policies = [
        {"policy_id": "maxday1_gap0", "max_trades_per_day": 1, "reentry_gap_minutes": 0},
        {"policy_id": "maxday2_gap15", "max_trades_per_day": 2, "reentry_gap_minutes": 15},
    ]
    risk_profiles = _risk_profiles(core, normal)

    rows = []
    best_row: dict[str, object] | None = None
    best_outcomes: list[Any] = []
    base_count = 0
    signal_count_by_base: dict[str, int] = {}
    for base_strategy_id, base_signals in _base_signal_sets(comp, core, bars_by_date, args.symbol):
        base_count += 1
        if not base_signals:
            continue
        signal_count_by_base[base_strategy_id] = len(base_signals)
        feature_by_index = {
            signal.bar.index: _features(signal, bars_by_date, rows_by_index)
            for signal in base_signals
        }
        ordered_signals = sorted(base_signals, key=lambda signal: signal.bar.timestamp)
        filtered_by_id = []
        for filter_spec in filters:
            filtered_signals = [
                signal for signal in ordered_signals
                if filter_spec.keep(signal, feature_by_index[signal.bar.index])
            ]
            if len({signal.bar.trade_date for signal in filtered_signals}) >= args.minimum_trades:
                filtered_by_id.append((filter_spec.filter_id, filtered_signals))
        if not filtered_by_id:
            continue

        for risk in risk_profiles:
            outcomes_by_signal_index = _outcomes_by_signal_index(
                core,
                ordered_signals,
                bars_by_date,
                rows_by_index,
                risk,
            )
            for filter_id, filtered_signals in filtered_by_id:
                for policy in policies:
                    outcomes = _evaluate_sequence(
                        filtered_signals,
                        outcomes_by_signal_index,
                        max_trades_per_day=policy["max_trades_per_day"],
                        reentry_gap_minutes=policy["reentry_gap_minutes"],
                    )
                    if len(outcomes) < args.minimum_trades:
                        continue
                    strategy_id = f"{base_strategy_id}:filter{filter_id}:{policy['policy_id']}"
                    row = normal._summary_row(
                        core,
                        strategy_id,
                        "mgc_lookback_breakout_refine",
                        outcomes,
                        risk,
                        bars_by_date,
                    )
                    row["notes"] = (
                        "MGC lookback-breakout refinement; "
                        f"filter={filter_id}; policy={policy['policy_id']}"
                    )
                    rows.append(row)
                    if _is_better_row(row, best_row):
                        best_row = row
                        best_outcomes = outcomes

    rows.sort(key=_ranking_key)
    _write_csv(args.output, normal.SUMMARY_HEADER, rows)
    if best_row is not None:
        core._write_trade_audit(args.trade_audit_output, best_outcomes, best_row)
    _write_report(args.report_output, bars, base_count, signal_count_by_base, rows, best_row)

    best_summary = "none"
    if best_row is not None:
        best_summary = (
            f"{best_row['strategy_id']} trades={best_row['trades']} "
            f"target={best_row['target_points']} stop={best_row['stop_points']} "
            f"pf={best_row['profit_factor']} net={best_row['net_usd']} "
            f"latest={best_row['latest_year_net_usd']} recent={best_row['recent_120_trade_days_net_usd']}"
        )
    print(
        f"wrote {len(rows)} MGC lookback-refine rows to {args.output}; "
        f"base_sets={base_count}; best={best_summary}",
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


def _base_signal_sets(
    comp: ModuleType,
    core: ModuleType,
    bars_by_date: dict[date, list[Any]],
    symbol: str,
) -> list[tuple[str, list[Any]]]:
    signal_sets = []
    for entry_end in (time(10, 30), time(13, 30)):
        for lookback_bars in (5, 10, 15, 20):
            for buffer_points in (0.0, 0.5):
                for delta_threshold in (0.0, 50.0):
                    for close_location_threshold in (0.50, 0.55):
                        strategy_id = (
                            "mgc_lookback_breakout_refine_base:"
                            f"lb{lookback_bars}:buf{buffer_points:g}:"
                            f"delta{delta_threshold:g}:cl{close_location_threshold:g}:"
                            f"end{_time_id(entry_end)}"
                        )
                        signals = comp._all_lookback_breakouts(
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
                        signal_sets.append((strategy_id, signals))
    return signal_sets


def _features(
    signal: Any,
    bars_by_date: dict[date, list[Any]],
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
    }


def _filter_specs() -> list[FilterSpec]:
    def keep_all(_signal: Any, _features: dict[str, float | int | str]) -> bool:
        return True

    def start_after(minute: int) -> Callable[[Any, dict[str, float | int | str]], bool]:
        return lambda _signal, features: int(features["time_minutes"]) >= minute

    def before_or_equal(minute: int) -> Callable[[Any, dict[str, float | int | str]], bool]:
        return lambda _signal, features: int(features["time_minutes"]) <= minute

    def direction(value: str) -> Callable[[Any, dict[str, float | int | str]], bool]:
        return lambda signal, _features: signal.direction == value

    def weekday_in(values: set[int]) -> Callable[[Any, dict[str, float | int | str]], bool]:
        return lambda _signal, features: int(features["weekday"]) in values

    def cap(key: str, value: float) -> Callable[[Any, dict[str, float | int | str]], bool]:
        return lambda _signal, features: float(features[key]) <= value

    def both(*checks: Callable[[Any, dict[str, float | int | str]], bool]) -> Callable[[Any, dict[str, float | int | str]], bool]:
        return lambda signal, features: all(check(signal, features) for check in checks)

    return [
        FilterSpec("none", keep_all),
        FilterSpec("nofri", weekday_in({0, 1, 2, 3})),
        FilterSpec("tuewedthu", weekday_in({1, 2, 3})),
        FilterSpec("long", direction("long")),
        FilterSpec("short", direction("short")),
        FilterSpec("start0900", start_after(9 * 60)),
        FilterSpec("start0930", start_after(9 * 60 + 30)),
        FilterSpec("end1030", before_or_equal(10 * 60 + 30)),
        FilterSpec("bar8", cap("bar_range", 8.0)),
        FilterSpec("bar6", cap("bar_range", 6.0)),
        FilterSpec("vwapdist20", cap("abs_vwap_distance", 20.0)),
        FilterSpec("absdelta100", cap("abs_delta", 100.0)),
        FilterSpec("start0900_bar8", both(start_after(9 * 60), cap("bar_range", 8.0))),
        FilterSpec("nofri_bar8", both(weekday_in({0, 1, 2, 3}), cap("bar_range", 8.0))),
        FilterSpec("start0900_nofri", both(start_after(9 * 60), weekday_in({0, 1, 2, 3}))),
    ]


def _risk_profiles(core: ModuleType, normal: ModuleType) -> list[Any]:
    profiles = []
    round_turn_cost = 2.0 * normal.COMMISSION_PER_SIDE_USD + normal.SLIPPAGE_TICKS_PER_CONTRACT * normal.TICK_VALUE_USD
    for target_points, stop_points in (
        (15.0, 10.0),
        (20.0, 12.0),
        (25.0, 15.0),
        (30.0, 15.0),
        (40.0, 20.0),
    ):
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
    trades_by_date: dict[date, int] = {}
    busy_until = datetime.min
    reentry_gap = timedelta(minutes=reentry_gap_minutes)
    for signal in signals:
        signal_date = signal.bar.trade_date
        if trades_by_date.get(signal_date, 0) >= max_trades_per_day:
            continue
        if signal.bar.timestamp <= busy_until:
            continue
        outcome = outcomes_by_signal_index[signal.bar.index]
        outcomes.append(outcome)
        trades_by_date[signal_date] = trades_by_date.get(signal_date, 0) + 1
        busy_until = outcome.exit_time + reentry_gap
    return outcomes


def _ranking_key(row: dict[str, object]) -> tuple[float, ...]:
    trades = int(row["trades"])
    net = float(row["net_usd"])
    latest_net = float(row["latest_year_net_usd"])
    recent_net = float(row["recent_120_trade_days_net_usd"])
    profit_factor = float(row["profit_factor"])
    drawdown_to_net = float(row["drawdown_to_net"])
    worst_quarter = float(row["worst_quarter_net_usd"])
    return (
        0.0 if trades >= 300 else 1.0,
        0.0 if net > 0.0 and latest_net > 0.0 and recent_net > 0.0 else 1.0,
        0.0 if profit_factor >= 1.20 else 1.0,
        0.0 if worst_quarter >= -abs(net) * 0.20 else 1.0,
        drawdown_to_net,
        -profit_factor,
        -latest_net,
        -recent_net,
        -net,
    )


def _is_better_row(row: dict[str, object], current_best: dict[str, object] | None) -> bool:
    if current_best is None:
        return True
    return _ranking_key(row) < _ranking_key(current_best)


def _accepted_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        row for row in rows
        if int(row["trades"]) >= 300
        and float(row["net_usd"]) > 0.0
        and float(row["latest_year_net_usd"]) > 0.0
        and float(row["recent_120_trade_days_net_usd"]) > 0.0
        and float(row["profit_factor"]) >= 1.20
        and float(row["latest_year_profit_factor"]) >= 1.05
        and float(row["drawdown_to_net"]) <= 0.75
        and float(row["worst_quarter_net_usd"]) >= -abs(float(row["net_usd"])) * 0.20
    ]


def _write_csv(path: str, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_report(
    path: str,
    bars: list[Any],
    base_count: int,
    signal_count_by_base: dict[str, int],
    rows: list[dict[str, object]],
    best_row: dict[str, object] | None,
) -> None:
    accepted = _accepted_rows(rows)
    lines = [
        "# MGC Lookback Breakout Refinement",
        "",
        "Status: focused refinement of the high-frequency MGC lookback-breakout lead. Not an ACSIL candidate yet.",
        "",
        "## Source",
        "",
        f"- rows: `{len(bars)}`",
        f"- dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        f"- base parameter sets: `{base_count}`",
        f"- base parameter sets with signals: `{len(signal_count_by_base)}`",
        "- instrument: `MGC`, one-minute Sierra order-flow export",
        "- cost model: `$0.50/side` commission plus `1` total slippage tick per contract",
        "",
        "## Search Space",
        "",
        "- family: lookback breakout continuation",
        "- lookbacks: `5`, `10`, `15`, `20` bars",
        "- buffers: `0`, `0.5` points",
        "- delta thresholds: `0`, `50`",
        "- close-location thresholds: `0.50`, `0.55`",
        "- entry ends: `10:30`, `13:30`",
        "- policies: max `1` trade/day and max `2` trades/day with `15` minute re-entry gap",
        "- filters: direction, weekday, time, bar range, day range, VWAP distance, and absolute delta caps",
        "",
        "## Result",
        "",
    ]
    if best_row is None:
        lines.append("No rows met the minimum-trade requirement.")
    else:
        lines.extend(
            [
                "Best row by focused normal-profitability ranking:",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Strategy | `{best_row['strategy_id']}` |",
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
            lines.append(f"Rows passing the focused first-pass lens: `{len(accepted)}`.")
        else:
            lines.append("No row passed the focused first-pass lens.")
    lines.extend(
        [
            "",
            "## Top Rows",
            "",
            "| Rank | Target | Stop | Trades | Net | PF | DD/Net | Latest | Recent120 | Worst Q | Strategy |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ],
    )
    for rank, row in enumerate(rows[:25], start=1):
        lines.append(
            "| "
            f"{rank} | {row['target_points']} | {row['stop_points']} | {row['trades']} | "
            f"{row['net_usd']} | {row['profit_factor']} | "
            f"{float(row['drawdown_to_net']) * 100:.1f}% | "
            f"{row['latest_year_net_usd']} | {row['recent_120_trade_days_net_usd']} | "
            f"{row['worst_quarter_net_usd']} | `{row['strategy_id']}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The refinement found whether the high-frequency lookback lead can be improved "
            "without making it sparse. Rows that pass this lens still need slippage "
            "stress and chronological holdout testing before implementation.",
            "",
        ],
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def _time_id(value: time) -> str:
    return f"{value.hour:02d}{value.minute:02d}"


if __name__ == "__main__":
    raise SystemExit(main())
