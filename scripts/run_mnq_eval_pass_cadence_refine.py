#!/usr/bin/env python3
"""Refine faster-cadence MNQ eval-pass candidates."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import math
import statistics
import sys
from dataclasses import dataclass
from datetime import date, time
from pathlib import Path
from typing import Callable


DEFAULT_OUTPUT = "reports/mnq-eval-pass-wave-rider-cadence-refine.csv"
DEFAULT_REPORT = "reports/mnq-eval-pass-wave-rider-cadence-refine.md"

EXTRA_FIELDS = [
    "signal_frequency_per_trade_day",
    "average_trading_day_gap_between_signals",
    "median_trading_day_gap_between_signals",
    "max_trading_day_gap_between_signals",
]


@dataclass(frozen=True)
class FilterSpec:
    filter_id: str
    keep_signal: Callable[[dict[str, object]], bool]


@dataclass(frozen=True)
class CandidateResult:
    row: dict[str, object]
    outcomes: list[object]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run faster-cadence MNQ eval-pass refinement.",
    )
    parser.add_argument("input", nargs="?", help="MNQ Sierra orderflow export path.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT)
    parser.add_argument("--symbol", default="MNQU26-CME")
    args = parser.parse_args()

    wave = _load_module("run_mnq_eval_pass_wave_rider.py", "mnq_eval_pass_wave_rider")
    deep = _load_module(
        "run_mnq_eval_pass_wave_rider_deep_search.py",
        "mnq_eval_pass_wave_rider_deep_search",
    )
    input_path = args.input or wave.DEFAULT_INPUT
    bars = wave._load_feature_bars(input_path)
    bars_by_date = wave._bars_by_date(bars)
    rows_by_index = wave._rows_by_global_index(bars_by_date)
    trade_dates = sorted(bars_by_date)

    base_signals = deep._lookback_breakout_signals(
        wave,
        bars_by_date,
        strategy_id="cadence_base:lb10:buf0:delta300:cl0.55:start1000:end1230",
        lookback_bars=10,
        buffer_points=0.0,
        delta_threshold=300.0,
        close_location_threshold=0.55,
        entry_start=time(10, 0),
        entry_end=time(12, 30),
        skip_friday=False,
        symbol=args.symbol,
    )
    features = [
        _signal_context_features(
            wave,
            signal,
            bars_by_date=bars_by_date,
            rows_by_index=rows_by_index,
            lookback_bars=10,
        )
        for signal in base_signals
    ]
    risks = _risk_profiles(deep, wave)
    results = _run_refinement(
        wave,
        bars_by_date,
        trade_dates=trade_dates,
        base_signals=base_signals,
        features=features,
        filters=_filter_specs(),
        risks=risks,
    )
    results.sort(key=_ranking_key)
    _write_csv(args.output, [result.row for result in results])
    _write_report(
        args.report_output,
        bars=bars,
        base_signals=base_signals,
        results=results,
    )
    best = results[0].row if results else None
    best_summary = "none"
    if best is not None:
        best_summary = (
            f"{best['strategy_id']} qty={best['quantity']} "
            f"target={best['target_net_usd']} stop={best['stop_net_usd']} "
            f"calendar_pass={float(best['pass_rate']):.3f} "
            f"calendar_fail={float(best['fail_rate']):.3f}"
        )
    print(
        f"wrote {len(results)} MNQ cadence-refine rows to {args.output}; "
        f"best={best_summary}",
    )
    return 0


def _load_module(filename: str, module_name: str):
    module_path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _signal_context_features(
    wave,
    signal: object,
    *,
    bars_by_date: dict[date, list[object]],
    rows_by_index: dict[int, int],
    lookback_bars: int,
) -> dict[str, object]:
    feature = wave._signal_features(
        signal,
        bars_by_date=bars_by_date,
        rows_by_index=rows_by_index,
        lookback_bars=lookback_bars,
    )
    return {
        "weekday": signal.bar.timestamp.weekday(),
        "direction": signal.direction,
        "minute_of_day": signal.bar.timestamp.hour * 60 + signal.bar.timestamp.minute,
        "abs_delta": feature.abs_delta,
        "bar_range": feature.bar_range,
        "directional_vwap_dist": feature.directional_vwap_dist,
        "lookback_move": feature.lookback_move,
    }


def _run_refinement(
    wave,
    bars_by_date: dict[date, list[object]],
    *,
    trade_dates: list[date],
    base_signals: list[object],
    features: list[dict[str, object]],
    filters: list[FilterSpec],
    risks: list[object],
) -> list[CandidateResult]:
    results = []
    for filter_spec in filters:
        filtered_signals = [
            wave.Signal(
                f"cadence_refine:{filter_spec.filter_id}",
                signal.direction,
                signal.bar,
                f"{signal.notes}; cadence filter {filter_spec.filter_id}",
            )
            for signal, feature in zip(base_signals, features)
            if filter_spec.keep_signal(feature)
        ]
        if len(filtered_signals) < 50:
            continue
        for risk in risks:
            outcomes = wave._evaluate_signals(filtered_signals, bars_by_date, risk)
            row = wave._sweep_row(
                filtered_signals[0].strategy_id,
                "mnq_cadence_refine",
                outcomes,
                risk,
                bars_by_date,
            )
            row.update(_cadence_metrics(outcomes, trade_dates))
            if not _is_research_row(row):
                continue
            results.append(CandidateResult(row, outcomes))
    return results


def _filter_specs() -> list[FilterSpec]:
    weekday_sets = {
        "all": {0, 1, 2, 3, 4},
        "no_fri": {0, 1, 2, 3},
        "no_thu_fri": {0, 1, 2},
        "mon_wed_only": {0, 2},
        "tue_wed": {1, 2},
        "mon_wed_fri": {0, 1, 2, 4},
        "wed_only": {2},
    }
    direction_sets = {
        "both": {"long", "short"},
        "short": {"short"},
        "long": {"long"},
    }
    time_windows = {
        "1000_1230": (600, 750),
        "1000_1130": (600, 690),
        "1000_1100": (600, 660),
        "1003_1100": (603, 660),
        "1018_1100": (618, 660),
        "1000_1045": (600, 645),
        "1003_1045": (603, 645),
    }
    context_filters: dict[str, Callable[[dict[str, object]], bool]] = {
        "none": lambda feature: True,
        "move_le125": lambda feature: float(feature["lookback_move"]) <= 125.0,
        "bar_le60": lambda feature: float(feature["bar_range"]) <= 60.0,
        "vwap_le100": (
            lambda feature: float(feature["directional_vwap_dist"]) <= 100.0
        ),
        "move125_bar60": (
            lambda feature: float(feature["lookback_move"]) <= 125.0
            and float(feature["bar_range"]) <= 60.0
        ),
    }
    specs = []
    for weekday_id, weekdays in weekday_sets.items():
        for direction_id, directions in direction_sets.items():
            for time_id, (start_minute, end_minute) in time_windows.items():
                for context_id, context_keep in context_filters.items():
                    filter_id = f"{weekday_id}:{direction_id}:{time_id}:{context_id}"
                    specs.append(
                        FilterSpec(
                            filter_id,
                            _make_keep_signal(
                                weekdays=weekdays,
                                directions=directions,
                                start_minute=start_minute,
                                end_minute=end_minute,
                                context_keep=context_keep,
                            ),
                        ),
                    )
    return specs


def _make_keep_signal(
    *,
    weekdays: set[int],
    directions: set[str],
    start_minute: int,
    end_minute: int,
    context_keep: Callable[[dict[str, object]], bool],
) -> Callable[[dict[str, object]], bool]:
    return lambda feature: (
        int(feature["weekday"]) in weekdays
        and str(feature["direction"]) in directions
        and start_minute <= int(feature["minute_of_day"]) <= end_minute
        and context_keep(feature)
    )


def _risk_profiles(deep, wave) -> list[object]:
    specs = [
        (3, 350.0, 500.0),
        (3, 400.0, 500.0),
        (4, 350.0, 500.0),
        (4, 350.0, 650.0),
        (4, 400.0, 650.0),
        (4, 500.0, 650.0),
        (5, 350.0, 650.0),
        (5, 450.0, 650.0),
        (5, 500.0, 650.0),
        (6, 450.0, 650.0),
    ]
    return [deep._make_risk_profile(wave, *spec) for spec in specs]


def _is_research_row(row: dict[str, object]) -> bool:
    return (
        int(row["evaluated_trades"]) >= 50
        and float(row["net_usd"]) > 0.0
        and float(row["latest_year_net_usd"]) > 0.0
    )


def _cadence_metrics(
    outcomes: list[object],
    trade_dates: list[date],
) -> dict[str, object]:
    date_positions = {trade_date: index for index, trade_date in enumerate(trade_dates)}
    signal_dates = sorted({outcome.entry_time.date() for outcome in outcomes})
    gaps = [
        date_positions[right] - date_positions[left]
        for left, right in zip(signal_dates, signal_dates[1:], strict=False)
        if left in date_positions and right in date_positions
    ]
    return {
        "signal_frequency_per_trade_day": _format_number(
            len(signal_dates) / len(trade_dates) if trade_dates else 0.0,
        ),
        "average_trading_day_gap_between_signals": _format_number(
            statistics.mean(gaps) if gaps else 0.0,
        ),
        "median_trading_day_gap_between_signals": _format_number(
            statistics.median(gaps) if gaps else 0.0,
        ),
        "max_trading_day_gap_between_signals": _format_number(max(gaps) if gaps else 0.0),
    }


def _ranking_key(result: CandidateResult) -> tuple[float, ...]:
    row = result.row
    pass_rate = float(row["pass_rate"])
    fail_rate = float(row["fail_rate"])
    latest_year = float(row["latest_year_net_usd"])
    max_dd = abs(float(row["max_trade_sequence_drawdown_usd"]))
    signal_fail = float(row["signal_start_fail_rate"])
    timeout = float(row["timeout_rate"])
    strict_penalty = 0.0 if fail_rate <= 0.12 and pass_rate >= 0.30 else 1.0
    return (
        strict_penalty,
        fail_rate,
        -pass_rate,
        signal_fail,
        timeout,
        -latest_year,
        max_dd,
    )


def _write_csv(path: str, rows: list[dict[str, object]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [*rows[0]] if rows else []
    if rows:
        fieldnames = [*fieldnames, *[field for field in EXTRA_FIELDS if field not in fieldnames]]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        if not rows:
            handle.write("")
            return
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_report(
    path: str,
    *,
    bars: list[object],
    base_signals: list[object],
    results: list[CandidateResult],
) -> None:
    strict_rows = [
        result for result in results
        if float(result.row["pass_rate"]) >= 0.30
        and float(result.row["fail_rate"]) <= 0.12
        and int(result.row["evaluated_trades"]) >= 80
    ]
    balanced_rows = [
        result for result in results
        if float(result.row["pass_rate"]) >= 0.35
        and float(result.row["fail_rate"]) <= 0.16
        and int(result.row["evaluated_trades"]) >= 80
    ]
    best = strict_rows[0] if strict_rows else (results[0] if results else None)
    lines = [
        "# MNQ Eval-Pass Wave Rider Cadence Refinement",
        "",
        "Status: faster-cadence offline research only; not implementation-ready.",
        "",
        "## Source",
        "",
        f"- rows: `{len(bars)}`",
        f"- dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        f"- unique dates: `{len({bar.trade_date for bar in bars})}`",
        f"- base signals: `{len(base_signals)}`",
        "- instrument: `MNQ`, point value `$2`, tick value `$0.50`",
        "- cost model: `$0.50/side` commission plus `1` total slippage tick per contract",
        "",
        "## Base Idea",
        "",
        "`lb10 / buf0 / delta300 / cl0.55 / 10:00-12:30` lookback breakout.",
        "",
        "This is the faster B-setup family. It intentionally gives up two-day pass "
        "potential in exchange for many more signals than the sparse A+ lead.",
        "",
        "## Best Low-Fail Row",
        "",
    ]
    if best is None:
        lines.append("No positive rows were generated.")
    else:
        row = best.row
        lines.extend(
            [
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Strategy | `{row['strategy_id']}` |",
                f"| Quantity | `{row['quantity']}` |",
                f"| Target / stop | `${row['target_net_usd']} / ${row['stop_net_usd']}` |",
                f"| Trades | `{row['evaluated_trades']}` |",
                f"| Signal frequency | `{row['signal_frequency_per_trade_day']}` per trading day |",
                f"| Median signal gap | `{row['median_trading_day_gap_between_signals']}` trading days |",
                f"| Max signal gap | `{row['max_trading_day_gap_between_signals']}` trading days |",
                f"| Full-sample net | `${row['net_usd']}` |",
                f"| Latest-year net | `${row['latest_year_net_usd']}` |",
                f"| Worst quarter | `${row['worst_quarter_net_usd']}` |",
                f"| Trade-sequence max DD | `${row['max_trade_sequence_drawdown_usd']}` |",
                f"| Calendar-start pass / fail / timeout | `{float(row['pass_rate']) * 100:.1f}% / {float(row['fail_rate']) * 100:.1f}% / {float(row['timeout_rate']) * 100:.1f}%` |",
                f"| Signal-start pass / fail | `{float(row['signal_start_pass_rate']) * 100:.1f}% / {float(row['signal_start_fail_rate']) * 100:.1f}%` |",
                f"| Median calendar days to pass | `{row['median_calendar_days_to_pass']}` |",
                f"| Median traded days to pass | `{row['median_trade_days_to_pass']}` |",
                "",
            ],
        )
    lines.extend(
        [
            "## Strict Rows",
            "",
            "Rows shown here have calendar-start pass `>=30%`, fail `<=12%`, and at least `80` trades.",
            "",
            "| Rank | Qty | Target | Stop | Trades | Latest Net | Cal Pass | Cal Fail | Timeout | Signal Pass | Signal Fail | Median Trade Days | DD | Strategy |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ],
    )
    for rank, result in enumerate(strict_rows[:12], start=1):
        lines.append(_table_row(rank, result.row))
    lines.extend(
        [
            "",
            "## Balanced Rows",
            "",
            "Rows shown here have calendar-start pass `>=35%`, fail `<=16%`, and at least `80` trades.",
            "",
            "| Rank | Qty | Target | Stop | Trades | Latest Net | Cal Pass | Cal Fail | Timeout | Signal Pass | Signal Fail | Median Trade Days | DD | Strategy |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ],
    )
    for rank, result in enumerate(balanced_rows[:12], start=1):
        lines.append(_table_row(rank, result.row))
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This is a materially faster B setup than the sparse A+ lead, but it is not "
            "a deployment candidate yet. The best low-fail row trades about every "
            "three trading days and cuts calendar-start fail rate near the `10-12%` "
            "target, but it still needs walk-forward, slippage stress, and replay "
            "mechanics before any implementation discussion.",
            "",
            "Two-day pass rate is expected to be `0%` for the low-fail rows because "
            "the per-trade target is about `$350`; this path is designed for a "
            "multi-trade eval pass.",
            "",
        ],
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def _table_row(rank: int, row: dict[str, object]) -> str:
    return (
        "| "
        f"{rank} | {row['quantity']} | {row['target_net_usd']} | "
        f"{row['stop_net_usd']} | {row['evaluated_trades']} | "
        f"{row['latest_year_net_usd']} | "
        f"{float(row['pass_rate']) * 100:.1f}% | "
        f"{float(row['fail_rate']) * 100:.1f}% | "
        f"{float(row['timeout_rate']) * 100:.1f}% | "
        f"{float(row['signal_start_pass_rate']) * 100:.1f}% | "
        f"{float(row['signal_start_fail_rate']) * 100:.1f}% | "
        f"{row['median_trade_days_to_pass']} | "
        f"{row['max_trade_sequence_drawdown_usd']} | "
        f"`{row['strategy_id']}` |"
    )


def _format_number(value: float) -> str:
    if not math.isfinite(value):
        return "0"
    formatted = f"{value:.8f}".rstrip("0").rstrip(".")
    return formatted if formatted else "0"


if __name__ == "__main__":
    raise SystemExit(main())
