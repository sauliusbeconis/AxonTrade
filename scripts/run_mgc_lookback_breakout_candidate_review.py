#!/usr/bin/env python3
"""Focused review of fixed MGC lookback-breakout candidates."""

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
from typing import Any


DEFAULT_OUTPUT = "reports/mgc-lookback-breakout-candidate-review.csv"
DEFAULT_REPORT_OUTPUT = "reports/mgc-lookback-breakout-candidate-review.md"
DEFAULT_TRAIN_DATE_COUNTS = "120,180,240"
DEFAULT_HOLDOUT_DATE_COUNTS = "40,40,60"
FLATTEN_TIME = time(16, 30)

HEADER = [
    "schema_version",
    "candidate",
    "slippage_ticks_per_contract",
    "target_points",
    "stop_points",
    "target_net_usd",
    "stop_net_usd",
    "full_trades",
    "full_net_usd",
    "full_average_trade_usd",
    "full_profit_factor",
    "full_max_drawdown_usd",
    "full_latest_year_net_usd",
    "full_recent_120_trade_days_net_usd",
    "full_worst_quarter_net_usd",
    "holdout_windows",
    "holdout_trades",
    "holdout_net_usd",
    "holdout_average_trade_usd",
    "holdout_profit_factor",
    "holdout_max_drawdown_usd",
    "holdout_positive_windows",
    "holdout_negative_windows",
    "holdout_worst_window_usd",
]


@dataclass(frozen=True)
class CandidateSpec:
    candidate_id: str
    lookback_bars: int
    buffer_points: float
    close_location_threshold: float
    entry_end: time
    filter_id: str
    max_trades_per_day: int
    reentry_gap_minutes: int
    target_points: float
    stop_points: float


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Review fixed MGC lookback-breakout candidates.",
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
    core = mgc_eval._load_mnq_core()
    mgc_eval._patch_core_for_mgc(core)

    input_path = args.input or normal.DEFAULT_INPUT
    bars = core._load_feature_bars(input_path)
    bars_by_date = mgc_eval._active_bars_by_date(core._bars_by_date(bars))
    rows_by_index = core._rows_by_global_index(bars_by_date)
    trade_dates = sorted(bars_by_date)
    configs = _parse_configs(args.train_date_counts, args.holdout_date_counts)

    rows = []
    for spec in _candidate_specs():
        signals = _candidate_signals(
            core,
            comp,
            refine,
            bars_by_date,
            rows_by_index,
            spec,
            symbol=args.symbol,
        )
        for slippage_ticks in (1.0, 3.0, 6.0):
            risk = _risk(
                core,
                normal,
                target_points=spec.target_points,
                stop_points=spec.stop_points,
                slippage_ticks=slippage_ticks,
            )
            outcomes = _evaluate_sequence(core, signals, bars_by_date, rows_by_index, spec, risk)
            full = normal._summary_row(
                core,
                spec.candidate_id,
                "mgc_lookback_candidate_review",
                outcomes,
                risk,
                bars_by_date,
            )
            holdout = _holdout_summary(core, outcomes, trade_dates, configs)
            rows.append(
                {
                    "schema_version": 1,
                    "candidate": spec.candidate_id,
                    "slippage_ticks_per_contract": _format_number(slippage_ticks),
                    "target_points": _format_number(risk.target_points),
                    "stop_points": _format_number(risk.stop_points),
                    "target_net_usd": _format_number(risk.target_net_usd),
                    "stop_net_usd": _format_number(risk.stop_net_usd),
                    "full_trades": full["trades"],
                    "full_net_usd": full["net_usd"],
                    "full_average_trade_usd": full["average_trade_usd"],
                    "full_profit_factor": full["profit_factor"],
                    "full_max_drawdown_usd": full["max_drawdown_usd"],
                    "full_latest_year_net_usd": full["latest_year_net_usd"],
                    "full_recent_120_trade_days_net_usd": full["recent_120_trade_days_net_usd"],
                    "full_worst_quarter_net_usd": full["worst_quarter_net_usd"],
                    **holdout,
                },
            )

    rows.sort(key=_ranking_key)
    _write_csv(args.output, rows)
    _write_report(args.report_output, bars, rows, configs)
    best = rows[0]
    print(
        f"wrote {len(rows)} MGC candidate review rows to {args.output}; "
        f"best={best['candidate']} slip={best['slippage_ticks_per_contract']} "
        f"full_net={best['full_net_usd']} holdout_net={best['holdout_net_usd']} "
        f"holdout_pf={best['holdout_profit_factor']}",
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


def _candidate_specs() -> list[CandidateSpec]:
    return [
        CandidateSpec("bar8_25_15_current", 10, 0.0, 0.50, time(10, 30), "bar8", 1, 0, 25.0, 15.0),
        CandidateSpec("absdelta100_25_15_holdout_lead", 10, 0.0, 0.50, time(10, 30), "absdelta100", 1, 0, 25.0, 15.0),
        CandidateSpec("absdelta100_30_15_recent", 10, 0.0, 0.50, time(10, 30), "absdelta100", 1, 0, 30.0, 15.0),
        CandidateSpec("absdelta100_no_wed_thu_25_15", 10, 0.0, 0.50, time(10, 30), "absdelta100_no_wed_thu", 1, 0, 25.0, 15.0),
        CandidateSpec("absdelta100_no_wed_25_15", 10, 0.0, 0.50, time(10, 30), "absdelta100_no_wed", 1, 0, 25.0, 15.0),
        CandidateSpec("absdelta100_no_thu_25_15", 10, 0.0, 0.50, time(10, 30), "absdelta100_no_thu", 1, 0, 25.0, 15.0),
        CandidateSpec("absdelta100_no_wed_thu_30_15", 10, 0.0, 0.50, time(10, 30), "absdelta100_no_wed_thu", 1, 0, 30.0, 15.0),
        CandidateSpec("vwapdist20_25_15_lb5", 5, 0.0, 0.50, time(10, 30), "vwapdist20", 1, 0, 25.0, 15.0),
        CandidateSpec("nofri_bar8_20_12_lb5", 5, 0.0, 0.50, time(10, 30), "nofri_bar8", 1, 0, 20.0, 12.0),
    ]


def _candidate_signals(
    core: ModuleType,
    comp: ModuleType,
    refine: ModuleType,
    bars_by_date: dict[date, list[Any]],
    rows_by_index: dict[int, int],
    spec: CandidateSpec,
    *,
    symbol: str,
) -> list[Any]:
    strategy_id = (
        "mgc_lookback_candidate_review:"
        f"lb{spec.lookback_bars}:buf{spec.buffer_points:g}:delta0:"
        f"cl{spec.close_location_threshold:g}:end{_time_id(spec.entry_end)}"
    )
    raw_signals = comp._all_lookback_breakouts(
        core,
        bars_by_date,
        strategy_id=strategy_id,
        lookback_bars=spec.lookback_bars,
        buffer_points=spec.buffer_points,
        delta_threshold=0.0,
        close_location_threshold=spec.close_location_threshold,
        entry_end=spec.entry_end,
        symbol=symbol,
    )
    filter_keep = _filter_keep(spec.filter_id)
    return [
        signal for signal in sorted(raw_signals, key=lambda item: item.bar.timestamp)
        if filter_keep(signal, refine._features(signal, bars_by_date, rows_by_index))
    ]


def _filter_keep(filter_id: str):
    filters = {
        "bar8": lambda _signal, features: float(features["bar_range"]) <= 8.0,
        "absdelta100": lambda _signal, features: float(features["abs_delta"]) <= 100.0,
        "vwapdist20": lambda _signal, features: float(features["abs_vwap_distance"]) <= 20.0,
        "nofri_bar8": lambda _signal, features: (
            int(features["weekday"]) in {0, 1, 2, 3}
            and float(features["bar_range"]) <= 8.0
        ),
        "absdelta100_no_wed_thu": lambda _signal, features: (
            float(features["abs_delta"]) <= 100.0
            and int(features["weekday"]) in {0, 1, 4}
        ),
        "absdelta100_no_wed": lambda _signal, features: (
            float(features["abs_delta"]) <= 100.0
            and int(features["weekday"]) != 2
        ),
        "absdelta100_no_thu": lambda _signal, features: (
            float(features["abs_delta"]) <= 100.0
            and int(features["weekday"]) != 3
        ),
    }
    return filters[filter_id]


def _risk(
    core: ModuleType,
    normal: ModuleType,
    *,
    target_points: float,
    stop_points: float,
    slippage_ticks: float,
) -> Any:
    round_turn_cost = 2.0 * normal.COMMISSION_PER_SIDE_USD + slippage_ticks * normal.TICK_VALUE_USD
    return core.RiskProfile(
        quantity=1,
        target_net_usd=target_points * normal.POINT_VALUE_USD - round_turn_cost,
        stop_net_usd=stop_points * normal.POINT_VALUE_USD + round_turn_cost,
        target_points=core._round_up_to_tick(target_points),
        stop_points=core._round_up_to_tick(stop_points),
        round_turn_cost_usd=round_turn_cost,
    )


def _evaluate_sequence(
    core: ModuleType,
    signals: list[Any],
    bars_by_date: dict[date, list[Any]],
    rows_by_index: dict[int, int],
    spec: CandidateSpec,
    risk: Any,
) -> list[Any]:
    outcomes = []
    trades_by_date: Counter[date] = Counter()
    busy_until = datetime.min
    for signal in signals:
        signal_date = signal.bar.trade_date
        if trades_by_date[signal_date] >= spec.max_trades_per_day:
            continue
        if signal.bar.timestamp <= busy_until:
            continue
        rows = bars_by_date[signal_date]
        local_index = rows_by_index[signal.bar.index]
        following_rows = [
            row for row in rows[local_index + 1:]
            if row.timestamp.time() <= FLATTEN_TIME
        ]
        outcome = core._evaluate_signal(signal, following_rows, risk)
        outcomes.append(outcome)
        trades_by_date[signal_date] += 1
        busy_until = outcome.exit_time
    return outcomes


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
        "holdout_trades": len(holdout_outcomes),
        "holdout_net_usd": _format_number(metrics["net_usd"]),
        "holdout_average_trade_usd": _format_number(metrics["average_trade_usd"]),
        "holdout_profit_factor": _format_number(metrics["profit_factor"]),
        "holdout_max_drawdown_usd": _format_number(metrics["max_drawdown_usd"]),
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
        "average_trade_usd": statistics.mean(values) if values else 0.0,
        "profit_factor": sum(positive) / abs(sum(negative)) if negative else 999.0,
        "max_drawdown_usd": core._max_drawdown(values),
    }


def _ranking_key(row: dict[str, object]) -> tuple[float, ...]:
    return (
        0.0 if float(row["slippage_ticks_per_contract"]) == 1.0 else 1.0,
        int(row["holdout_negative_windows"]),
        -float(row["holdout_net_usd"]),
        -float(row["holdout_profit_factor"]),
        abs(float(row["holdout_max_drawdown_usd"])),
        -float(row["full_net_usd"]),
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
        "# MGC Lookback Breakout Candidate Review",
        "",
        "Status: focused fixed-candidate review after walk-forward identified a stronger nearby filter.",
        "",
        "## Source",
        "",
        f"- rows: `{len(bars)}`",
        f"- dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        f"- holdout windows: `{', '.join(f'{a}x{b}' for a, b in configs)}`",
        "",
        "## Candidate Rows",
        "",
        "| Candidate | Slip | Target | Stop | Full Trades | Full Net | Full PF | Latest | Recent120 | Worst Q | Holdout Net | Holdout PF | Pos/Windows | Worst Window |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| "
            f"`{row['candidate']}` | {row['slippage_ticks_per_contract']} | "
            f"{row['target_points']} | {row['stop_points']} | {row['full_trades']} | "
            f"{row['full_net_usd']} | {row['full_profit_factor']} | "
            f"{row['full_latest_year_net_usd']} | {row['full_recent_120_trade_days_net_usd']} | "
            f"{row['full_worst_quarter_net_usd']} | {row['holdout_net_usd']} | "
            f"{row['holdout_profit_factor']} | {row['holdout_positive_windows']}/"
            f"{row['holdout_windows']} | {row['holdout_worst_window_usd']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The `absdelta100_no_wed_thu_25_15` candidate is the cleanest next "
            "MGC lead in this pass. It uses the same base signal as the previous "
            "`bar8` lead, filters out high absolute-delta entry bars, and trades "
            "only Monday, Tuesday, and Friday. Treat the weekday rule as a fixed "
            "research hypothesis that still needs replay/mechanics validation.",
            "",
        ],
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


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
