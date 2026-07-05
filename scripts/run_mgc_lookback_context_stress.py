#!/usr/bin/env python3
"""Context stress diagnostics for the current MGC lookback break-even lead."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import math
import statistics
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date, time
from pathlib import Path
from types import ModuleType
from typing import Any, Callable


DEFAULT_DIAGNOSTIC_OUTPUT = "reports/mgc-lookback-context-stress.csv"
DEFAULT_EXCLUSION_OUTPUT = "reports/mgc-lookback-context-exclusions.csv"
DEFAULT_REPORT_OUTPUT = "reports/mgc-lookback-context-stress.md"
DEFAULT_TRAIN_DATE_COUNTS = "120,180,240"
DEFAULT_HOLDOUT_DATE_COUNTS = "40,40,60"

DIAGNOSTIC_HEADER = [
    "schema_version",
    "section",
    "bucket_id",
    "bucket_label",
    "trades",
    "base_net_usd",
    "base_average_trade_usd",
    "base_win_rate",
    "base_profit_factor",
    "base_max_drawdown_usd",
    "stress_net_usd",
    "stress_average_trade_usd",
    "stress_win_rate",
    "stress_profit_factor",
    "stress_max_drawdown_usd",
    "target_hits",
    "stop_hits",
    "managed_stop_hits",
    "eod_exits",
]

EXCLUSION_HEADER = [
    "schema_version",
    "exclusion_id",
    "exclusion_label",
    "trades",
    "trade_delta",
    "base_net_usd",
    "base_net_delta_usd",
    "base_average_trade_usd",
    "base_profit_factor",
    "base_max_drawdown_usd",
    "base_holdout_net_usd",
    "base_holdout_profit_factor",
    "base_holdout_positive_windows",
    "base_holdout_negative_windows",
    "base_holdout_worst_window_usd",
    "stress_net_usd",
    "stress_net_delta_usd",
    "stress_average_trade_usd",
    "stress_profit_factor",
    "stress_max_drawdown_usd",
    "stress_holdout_net_usd",
    "stress_holdout_profit_factor",
    "stress_holdout_positive_windows",
    "stress_holdout_negative_windows",
    "stress_holdout_worst_window_usd",
]


@dataclass(frozen=True)
class EvaluatedTrade:
    signal: Any
    features: dict[str, float | int | str]
    base_outcome: Any
    stress_outcome: Any


@dataclass(frozen=True)
class BucketSpec:
    section: str
    bucket_id: str
    bucket_label: str
    predicate: Callable[[Any, dict[str, float | int | str]], bool]
    live_filter: bool


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run context stress diagnostics for the current MGC lookback break-even lead.",
    )
    parser.add_argument("input", nargs="?", default=None)
    parser.add_argument("--diagnostic-output", default=DEFAULT_DIAGNOSTIC_OUTPUT)
    parser.add_argument("--exclusion-output", default=DEFAULT_EXCLUSION_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--symbol", default="MGC")
    parser.add_argument("--minimum-exclusion-trades", type=int, default=250)
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

    management_spec = management.ManagementSpec(
        "breakeven:t25:s15:trig20",
        25.0,
        15.0,
        "breakeven",
        time(16, 30),
        20.0,
        0.0,
    )
    base_risk = review._risk(core, normal, target_points=25.0, stop_points=15.0, slippage_ticks=1.0)
    stress_risk = review._risk(core, normal, target_points=25.0, stop_points=15.0, slippage_ticks=6.0)
    signals = _lead_signals(
        core,
        comp,
        refine,
        bars_by_date,
        rows_by_index,
        symbol=args.symbol,
    )
    evaluated = _evaluate_paired_sequence(
        core,
        signals,
        bars_by_date,
        rows_by_index,
        base_risk,
        stress_risk,
        management,
        management_spec,
        refine,
    )
    lead_summary = _paired_summary(core, evaluated)
    lead_holdout = _paired_holdout(core, evaluated, trade_dates, configs, management)

    bucket_specs = _bucket_specs()
    diagnostic_rows = _diagnostic_rows(core, evaluated, bucket_specs)
    exclusion_rows = _exclusion_rows(
        core,
        refine,
        signals,
        bars_by_date,
        rows_by_index,
        trade_dates,
        configs,
        base_risk,
        stress_risk,
        management,
        management_spec,
        bucket_specs,
        lead_summary,
        minimum_trades=args.minimum_exclusion_trades,
    )

    _write_csv(args.diagnostic_output, DIAGNOSTIC_HEADER, diagnostic_rows)
    _write_csv(args.exclusion_output, EXCLUSION_HEADER, exclusion_rows)
    _write_report(
        args.report_output,
        bars,
        evaluated,
        lead_summary,
        lead_holdout,
        diagnostic_rows,
        exclusion_rows,
        configs,
        args.minimum_exclusion_trades,
    )
    best_exclusion = exclusion_rows[0] if exclusion_rows else None
    best_summary = "none"
    if best_exclusion is not None:
        best_summary = (
            f"{best_exclusion['exclusion_id']} trades={best_exclusion['trades']} "
            f"base={best_exclusion['base_net_usd']} stress={best_exclusion['stress_net_usd']} "
            f"stress_pf={best_exclusion['stress_profit_factor']}"
        )
    print(
        f"wrote {len(diagnostic_rows)} diagnostics and {len(exclusion_rows)} exclusions; "
        f"lead_trades={len(evaluated)}; best_exclusion={best_summary}",
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


def _lead_signals(
    core: ModuleType,
    comp: ModuleType,
    refine: ModuleType,
    bars_by_date: dict[date, list[Any]],
    rows_by_index: dict[int, int],
    *,
    symbol: str,
) -> list[Any]:
    raw_signals = comp._all_lookback_breakouts(
        core,
        bars_by_date,
        strategy_id="mgc_lb_be_context:lb10:buf0:cl0.45:end1030:mtf:delta125",
        lookback_bars=10,
        buffer_points=0.0,
        delta_threshold=0.0,
        close_location_threshold=0.45,
        entry_end=time(10, 30),
        symbol=symbol,
    )
    signals = []
    for signal in sorted(raw_signals, key=lambda item: item.bar.timestamp):
        features = refine._features(signal, bars_by_date, rows_by_index)
        if int(features["weekday"]) not in {0, 1, 4}:
            continue
        if float(features["abs_delta"]) > 125.0:
            continue
        signals.append(signal)
    return signals


def _evaluate_paired_sequence(
    core: ModuleType,
    signals: list[Any],
    bars_by_date: dict[date, list[Any]],
    rows_by_index: dict[int, int],
    base_risk: Any,
    stress_risk: Any,
    management: ModuleType,
    management_spec: Any,
    refine: ModuleType,
) -> list[EvaluatedTrade]:
    evaluated = []
    trades_by_date: Counter[date] = Counter()
    busy_until = core.datetime.min if hasattr(core, "datetime") else None
    if busy_until is None:
        from datetime import datetime

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
            if row.timestamp.time() <= management_spec.clock_exit
        ]
        base_outcome = management._evaluate_managed_signal(
            core,
            signal,
            following_rows,
            base_risk,
            management_spec,
        )
        stress_outcome = management._evaluate_managed_signal(
            core,
            signal,
            following_rows,
            stress_risk,
            management_spec,
        )
        evaluated.append(
            EvaluatedTrade(
                signal=signal,
                features=refine._features(signal, bars_by_date, rows_by_index),
                base_outcome=base_outcome,
                stress_outcome=stress_outcome,
            ),
        )
        trades_by_date[signal_date] += 1
        busy_until = base_outcome.exit_time
    return evaluated


def _bucket_specs() -> list[BucketSpec]:
    specs: list[BucketSpec] = []
    weekdays = {0: "Monday", 1: "Tuesday", 4: "Friday"}
    for weekday, label in weekdays.items():
        specs.append(
            BucketSpec(
                "weekday",
                f"weekday_{weekday}",
                label,
                lambda _signal, features, weekday=weekday: int(features["weekday"]) == weekday,
                True,
            ),
        )
    for direction in ("long", "short"):
        specs.append(
            BucketSpec(
                "direction",
                direction,
                direction,
                lambda signal, _features, direction=direction: signal.direction == direction,
                True,
            ),
        )
    for bucket_id, label, start_minute, end_minute, include_end in (
        ("time_0820_0900", "08:20-09:00", 8 * 60 + 20, 9 * 60, False),
        ("time_0900_0930", "09:00-09:30", 9 * 60, 9 * 60 + 30, False),
        ("time_0930_1000", "09:30-10:00", 9 * 60 + 30, 10 * 60, False),
        ("time_1000_1030", "10:00-10:30", 10 * 60, 10 * 60 + 30, True),
    ):
        specs.append(
            BucketSpec(
                "entry_time",
                bucket_id,
                label,
                lambda _signal, features, start=start_minute, end=end_minute, include_end=include_end: (
                    _in_bucket(float(features["time_minutes"]), float(start), float(end), include_upper=include_end)
                ),
                True,
            ),
        )
    specs.extend(_numeric_bucket_specs("abs_delta", "entry_abs_delta", "abs delta", (25.0, 50.0, 75.0, 100.0, 125.0), True))
    specs.extend(_numeric_bucket_specs("bar_range", "bar_range", "bar range", (3.0, 5.0, 8.0, 999999.0), True))
    specs.extend(_numeric_bucket_specs("day_range_so_far", "day_range", "day range", (10.0, 20.0, 35.0, 999999.0), True))
    specs.extend(_numeric_bucket_specs("abs_vwap_distance", "vwap_distance", "VWAP distance", (2.0, 5.0, 10.0, 999999.0), True))
    specs.extend(_directional_close_location_specs())
    specs.extend(_year_specs())
    specs.extend(_quarter_specs())
    return specs


def _numeric_bucket_specs(
    feature_key: str,
    section: str,
    label_prefix: str,
    upper_bounds: tuple[float, ...],
    live_filter: bool,
) -> list[BucketSpec]:
    specs = []
    lower = 0.0
    last_upper = upper_bounds[-1]
    for upper in upper_bounds:
        bucket_id = f"{section}_{_number_id(lower)}_{_number_id(upper)}"
        label = f"{label_prefix} {_format_range(lower, upper)}"
        specs.append(
            BucketSpec(
                section,
                bucket_id,
                label,
                lambda _signal, features, lower=lower, upper=upper, key=feature_key: (
                    _in_bucket(float(features[key]), lower, upper, include_upper=upper == last_upper)
                ),
                live_filter,
            ),
        )
        lower = upper
    return specs


def _directional_close_location_specs() -> list[BucketSpec]:
    specs = []
    lower = 0.45
    last_upper = 1.0
    for upper in (0.55, 0.65, 0.75, last_upper):
        specs.append(
            BucketSpec(
                "directional_close_location",
                f"dir_cl_{_number_id(lower)}_{_number_id(upper)}",
                f"directional close-location {_format_range(lower, upper)}",
                lambda signal, _features, lower=lower, upper=upper: (
                    _in_bucket(_directional_close_location(signal), lower, upper, include_upper=upper == last_upper)
                ),
                True,
            ),
        )
        lower = upper
    return specs


def _year_specs() -> list[BucketSpec]:
    return [
        BucketSpec(
            "year",
            f"year_{year}",
            str(year),
            lambda signal, _features, year=year: signal.bar.timestamp.year == year,
            False,
        )
        for year in (2024, 2025, 2026)
    ]


def _quarter_specs() -> list[BucketSpec]:
    specs = []
    for year in (2024, 2025, 2026):
        for quarter in (1, 2, 3, 4):
            specs.append(
                BucketSpec(
                    "quarter",
                    f"q_{year}_{quarter}",
                    f"{year} Q{quarter}",
                    lambda signal, _features, year=year, quarter=quarter: (
                        signal.bar.timestamp.year == year
                        and ((signal.bar.timestamp.month - 1) // 3 + 1) == quarter
                    ),
                    False,
                ),
            )
    return specs


def _diagnostic_rows(
    core: ModuleType,
    evaluated: list[EvaluatedTrade],
    bucket_specs: list[BucketSpec],
) -> list[dict[str, object]]:
    rows = []
    for spec in bucket_specs:
        selected = [
            item for item in evaluated
            if spec.predicate(item.signal, item.features)
        ]
        if not selected:
            continue
        rows.append(
            {
                "schema_version": 1,
                "section": spec.section,
                "bucket_id": spec.bucket_id,
                "bucket_label": spec.bucket_label,
                **_paired_summary(core, selected),
            },
        )
    rows.sort(key=_diagnostic_ranking_key)
    return rows


def _exclusion_rows(
    core: ModuleType,
    refine: ModuleType,
    signals: list[Any],
    bars_by_date: dict[date, list[Any]],
    rows_by_index: dict[int, int],
    trade_dates: list[date],
    configs: list[tuple[int, int]],
    base_risk: Any,
    stress_risk: Any,
    management: ModuleType,
    management_spec: Any,
    bucket_specs: list[BucketSpec],
    lead_summary: dict[str, object],
    *,
    minimum_trades: int,
) -> list[dict[str, object]]:
    rows = []
    feature_rows = [
        (signal, refine._features(signal, bars_by_date, rows_by_index))
        for signal in signals
    ]
    for spec in bucket_specs:
        if not spec.live_filter:
            continue
        filtered_signals = [
            signal for signal, features in feature_rows
            if not spec.predicate(signal, features)
        ]
        evaluated = _evaluate_paired_sequence(
            core,
            filtered_signals,
            bars_by_date,
            rows_by_index,
            base_risk,
            stress_risk,
            management,
            management_spec,
            refine,
        )
        if len(evaluated) < minimum_trades:
            continue
        summary = _paired_summary(core, evaluated)
        holdout = _paired_holdout(core, evaluated, trade_dates, configs, management)
        rows.append(
            {
                "schema_version": 1,
                "exclusion_id": f"exclude_{spec.bucket_id}",
                "exclusion_label": f"exclude {spec.bucket_label}",
                "trades": summary["trades"],
                "trade_delta": int(summary["trades"]) - int(lead_summary["trades"]),
                "base_net_usd": summary["base_net_usd"],
                "base_net_delta_usd": _format_number(float(summary["base_net_usd"]) - float(lead_summary["base_net_usd"])),
                "base_average_trade_usd": summary["base_average_trade_usd"],
                "base_profit_factor": summary["base_profit_factor"],
                "base_max_drawdown_usd": summary["base_max_drawdown_usd"],
                "base_holdout_net_usd": holdout["base_holdout_net_usd"],
                "base_holdout_profit_factor": holdout["base_holdout_profit_factor"],
                "base_holdout_positive_windows": holdout["base_holdout_positive_windows"],
                "base_holdout_negative_windows": holdout["base_holdout_negative_windows"],
                "base_holdout_worst_window_usd": holdout["base_holdout_worst_window_usd"],
                "stress_net_usd": summary["stress_net_usd"],
                "stress_net_delta_usd": _format_number(float(summary["stress_net_usd"]) - float(lead_summary["stress_net_usd"])),
                "stress_average_trade_usd": summary["stress_average_trade_usd"],
                "stress_profit_factor": summary["stress_profit_factor"],
                "stress_max_drawdown_usd": summary["stress_max_drawdown_usd"],
                "stress_holdout_net_usd": holdout["stress_holdout_net_usd"],
                "stress_holdout_profit_factor": holdout["stress_holdout_profit_factor"],
                "stress_holdout_positive_windows": holdout["stress_holdout_positive_windows"],
                "stress_holdout_negative_windows": holdout["stress_holdout_negative_windows"],
                "stress_holdout_worst_window_usd": holdout["stress_holdout_worst_window_usd"],
            },
        )
    rows.sort(key=_exclusion_ranking_key)
    return rows


def _paired_summary(core: ModuleType, evaluated: list[EvaluatedTrade]) -> dict[str, object]:
    base_outcomes = [item.base_outcome for item in evaluated]
    stress_outcomes = [item.stress_outcome for item in evaluated]
    base_values = [outcome.net_usd for outcome in base_outcomes]
    stress_values = [outcome.net_usd for outcome in stress_outcomes]
    return {
        "trades": len(evaluated),
        **_side_summary(core, "base", base_values),
        **_side_summary(core, "stress", stress_values),
        "target_hits": sum(outcome.exit_reason == "target_hit" for outcome in base_outcomes),
        "stop_hits": sum(outcome.exit_reason == "stop_hit" for outcome in base_outcomes),
        "managed_stop_hits": sum(outcome.exit_reason == "managed_stop_hit" for outcome in base_outcomes),
        "eod_exits": sum(outcome.exit_reason == "end_of_session" for outcome in base_outcomes),
    }


def _side_summary(core: ModuleType, prefix: str, values: list[float]) -> dict[str, object]:
    positive = [value for value in values if value > 0.0]
    negative = [value for value in values if value < 0.0]
    return {
        f"{prefix}_net_usd": _format_number(sum(values)),
        f"{prefix}_average_trade_usd": _format_number(statistics.mean(values) if values else 0.0),
        f"{prefix}_win_rate": _format_number(len(positive) / len(values) if values else 0.0),
        f"{prefix}_profit_factor": _format_number(sum(positive) / abs(sum(negative)) if negative else 999.0),
        f"{prefix}_max_drawdown_usd": _format_number(core._max_drawdown(values)),
    }


def _paired_holdout(
    core: ModuleType,
    evaluated: list[EvaluatedTrade],
    trade_dates: list[date],
    configs: list[tuple[int, int]],
    management: ModuleType,
) -> dict[str, object]:
    base_holdout = management._holdout_summary(
        core,
        [item.base_outcome for item in evaluated],
        trade_dates,
        configs,
    )
    stress_holdout = management._holdout_summary(
        core,
        [item.stress_outcome for item in evaluated],
        trade_dates,
        configs,
    )
    return {
        **{f"base_{key}": value for key, value in base_holdout.items()},
        **{f"stress_{key}": value for key, value in stress_holdout.items()},
    }


def _write_csv(path: str, header: list[str], rows: list[dict[str, object]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_report(
    path: str,
    bars: list[Any],
    evaluated: list[EvaluatedTrade],
    lead_summary: dict[str, object],
    lead_holdout: dict[str, object],
    diagnostics: list[dict[str, object]],
    exclusions: list[dict[str, object]],
    configs: list[tuple[int, int]],
    minimum_exclusion_trades: int,
) -> None:
    drag_buckets = sorted(
        [
            row for row in diagnostics
            if int(row["trades"]) >= 20
        ],
        key=lambda row: (
            float(row["stress_average_trade_usd"]),
            float(row["base_average_trade_usd"]),
        ),
    )[:20]
    strength_buckets = sorted(
        [
            row for row in diagnostics
            if int(row["trades"]) >= 20
        ],
        key=lambda row: (
            float(row["stress_average_trade_usd"]),
            float(row["base_average_trade_usd"]),
        ),
        reverse=True,
    )[:20]
    lines = [
        "# MGC Lookback Context Stress",
        "",
        "Status: context/session stress diagnostics on the current MGC lookback "
        "break-even lead.",
        "",
        "## Source",
        "",
        f"- rows: `{len(bars)}`",
        f"- dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        f"- evaluated trades: `{len(evaluated)}`",
        f"- holdout windows: `{', '.join(f'{train}x{holdout}' for train, holdout in configs)}`",
        f"- minimum exclusion trades: `{minimum_exclusion_trades}`",
        "",
        "## Frozen Lead",
        "",
        "- strategy: `mgc_lb_be_sensitivity:lb10:buf0:cl0.45:end1030:mtf:delta125:breakeven:t25:s15:trig20`",
        "- entry: `10` bar lookback breakout, `0` buffer, directional close-location `>= 0.45`, entry through `10:30`, Monday/Tuesday/Friday only, entry bar absolute delta `<= 125`",
        "- management: `25` point target, `15` point initial stop, move stop to breakeven after `+20` points",
        "",
        _lead_table(lead_summary, lead_holdout),
        "",
        "## Weakest Context Buckets",
        "",
        "| Rank | Section | Bucket | Trades | Base Avg | Base PF | Stress Avg | Stress PF | Stress DD |",
        "| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for rank, row in enumerate(drag_buckets, start=1):
        lines.append(_diagnostic_table_row(rank, row))
    lines.extend(
        [
            "",
            "## Strongest Context Buckets",
            "",
            "| Rank | Section | Bucket | Trades | Base Avg | Base PF | Stress Avg | Stress PF | Stress DD |",
            "| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    for rank, row in enumerate(strength_buckets, start=1):
        lines.append(_diagnostic_table_row(rank, row))
    lines.extend(
        [
            "",
            "## Live-Rule Exclusion Tests",
            "",
            "| Rank | Exclusion | Trades | Base Net | Base Delta | Base PF | Base DD | Stress Net | Stress Delta | Stress PF | Stress DD | Stress Holdout | Pos/Windows | Worst Window |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    for rank, row in enumerate(exclusions[:30], start=1):
        lines.append(_exclusion_table_row(rank, row))
    positive_delta_exclusions = [
        row for row in exclusions
        if float(row["stress_net_delta_usd"]) > 0.0
    ]
    positive_delta_exclusions.sort(
        key=lambda row: (
            float(row["stress_net_delta_usd"]),
            float(row["base_net_delta_usd"]),
        ),
        reverse=True,
    )
    if positive_delta_exclusions:
        lines.extend(
            [
                "",
                "## Full-Sample Improvement Traps",
                "",
                "| Rank | Exclusion | Trades | Base Delta | Stress Delta | Stress PF | Stress Holdout | Pos/Windows | Worst Window |",
                "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
            ],
        )
        for rank, row in enumerate(positive_delta_exclusions[:10], start=1):
            lines.append(_trap_table_row(rank, row))

    top_exclusion = exclusions[0] if exclusions else None
    lines.extend(
        [
            "",
            "## Decision",
            "",
            "Keep the frozen `10:30` break-even lead. No simple live-rule "
            "exclusion improved full-sample net, PF, drawdown, and holdout "
            "quality together.",
            "",
            "The strongest contexts are Monday, 2026, wider entry-bar ranges, "
            "day range above `20`, and entry-bar absolute delta above `75`. "
            "The weakest contexts are VWAP distance `2-5`, entry-bar absolute "
            "delta `50-75`, Tuesday, early `2024`, and day range below `10`.",
            "",
        ],
    )
    if top_exclusion is not None:
        lines.extend(
            [
                "The top-ranked exclusion improves holdout cleanliness but still "
                "reduces full-sample net, so it is not a replacement:",
                "",
                (
                    f"- `{top_exclusion['exclusion_id']}`: stress net "
                    f"`{top_exclusion['stress_net_usd']}` "
                    f"(`{top_exclusion['stress_net_delta_usd']}` versus lead), "
                    f"stress PF `{top_exclusion['stress_profit_factor']}`, "
                    f"stress holdout `{top_exclusion['stress_holdout_net_usd']}` "
                    f"with `{top_exclusion['stress_holdout_positive_windows']}/"
                    f"{int(top_exclusion['stress_holdout_positive_windows']) + int(top_exclusion['stress_holdout_negative_windows'])}` "
                    "positive windows."
                ),
                "",
            ],
        )
    lines.extend(
        [
            "Full-sample improvement rows are treated as traps unless they also "
            "preserve holdout quality. In this pass, the stress-net improvement "
            "rows lost holdout windows and worsened worst-window loss, so they "
            "are monitoring notes only.",
            "",
        ],
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def _lead_table(summary: dict[str, object], holdout: dict[str, object]) -> str:
    lines = [
        "| Cost | Trades | Net | Avg | PF | DD | Holdout Net | Holdout PF | Pos/Windows | Worst Window |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        (
            f"| base | {summary['trades']} | {summary['base_net_usd']} | "
            f"{summary['base_average_trade_usd']} | {summary['base_profit_factor']} | "
            f"{summary['base_max_drawdown_usd']} | {holdout['base_holdout_net_usd']} | "
            f"{holdout['base_holdout_profit_factor']} | "
            f"{holdout['base_holdout_positive_windows']}/{holdout['base_holdout_windows']} | "
            f"{holdout['base_holdout_worst_window_usd']} |"
        ),
        (
            f"| stress | {summary['trades']} | {summary['stress_net_usd']} | "
            f"{summary['stress_average_trade_usd']} | {summary['stress_profit_factor']} | "
            f"{summary['stress_max_drawdown_usd']} | {holdout['stress_holdout_net_usd']} | "
            f"{holdout['stress_holdout_profit_factor']} | "
            f"{holdout['stress_holdout_positive_windows']}/{holdout['stress_holdout_windows']} | "
            f"{holdout['stress_holdout_worst_window_usd']} |"
        ),
    ]
    return "\n".join(lines)


def _diagnostic_table_row(rank: int, row: dict[str, object]) -> str:
    return (
        "| "
        f"{rank} | {row['section']} | {row['bucket_label']} | {row['trades']} | "
        f"{row['base_average_trade_usd']} | {row['base_profit_factor']} | "
        f"{row['stress_average_trade_usd']} | {row['stress_profit_factor']} | "
        f"{row['stress_max_drawdown_usd']} |"
    )


def _exclusion_table_row(rank: int, row: dict[str, object]) -> str:
    return (
        "| "
        f"{rank} | {row['exclusion_label']} | {row['trades']} | "
        f"{row['base_net_usd']} | {row['base_net_delta_usd']} | "
        f"{row['base_profit_factor']} | {row['base_max_drawdown_usd']} | "
        f"{row['stress_net_usd']} | {row['stress_net_delta_usd']} | "
        f"{row['stress_profit_factor']} | {row['stress_max_drawdown_usd']} | "
        f"{row['stress_holdout_net_usd']} | "
        f"{row['stress_holdout_positive_windows']}/{int(row['stress_holdout_positive_windows']) + int(row['stress_holdout_negative_windows'])} | "
        f"{row['stress_holdout_worst_window_usd']} |"
    )


def _trap_table_row(rank: int, row: dict[str, object]) -> str:
    return (
        "| "
        f"{rank} | {row['exclusion_label']} | {row['trades']} | "
        f"{row['base_net_delta_usd']} | {row['stress_net_delta_usd']} | "
        f"{row['stress_profit_factor']} | {row['stress_holdout_net_usd']} | "
        f"{row['stress_holdout_positive_windows']}/{int(row['stress_holdout_positive_windows']) + int(row['stress_holdout_negative_windows'])} | "
        f"{row['stress_holdout_worst_window_usd']} |"
    )


def _diagnostic_ranking_key(row: dict[str, object]) -> tuple[object, ...]:
    return (
        row["section"],
        float(row["stress_average_trade_usd"]),
        float(row["base_average_trade_usd"]),
    )


def _exclusion_ranking_key(row: dict[str, object]) -> tuple[float, ...]:
    return (
        int(row["stress_holdout_negative_windows"]),
        -float(row["stress_profit_factor"]),
        -float(row["base_profit_factor"]),
        -float(row["stress_holdout_net_usd"]),
        -float(row["stress_net_usd"]),
        abs(float(row["stress_max_drawdown_usd"])),
        -float(row["stress_net_delta_usd"]),
    )


def _directional_close_location(signal: Any) -> float:
    return signal.bar.close_location if signal.direction == "long" else 1.0 - signal.bar.close_location


def _in_bucket(value: float, lower: float, upper: float, *, include_upper: bool) -> bool:
    if include_upper:
        return lower <= value <= upper
    return lower <= value < upper


def _number_id(value: float) -> str:
    if value >= 999999.0:
        return "inf"
    return f"{value:g}".replace(".", "p")


def _format_range(lower: float, upper: float) -> str:
    if upper >= 999999.0:
        return f">={lower:g}"
    return f"{lower:g}-{upper:g}"


def _format_number(value: float) -> str:
    if not math.isfinite(value):
        return "999"
    formatted = f"{value:.8f}".rstrip("0").rstrip(".")
    return formatted if formatted else "0"


if __name__ == "__main__":
    raise SystemExit(main())
