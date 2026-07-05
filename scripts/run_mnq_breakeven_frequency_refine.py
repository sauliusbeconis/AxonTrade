#!/usr/bin/env python3
"""Refine the only weak-positive MNQ breakeven-frequency lead."""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, time
from pathlib import Path
from typing import Callable, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_mnq_breakeven_frequency_research as be  # noqa: E402
import run_mnq_eval_pass_wave_rider as wave  # noqa: E402


DEFAULT_OUTPUT = "reports/mnq-breakeven-frequency-refine.csv"
DEFAULT_REPORT_OUTPUT = "reports/mnq-breakeven-frequency-refine.md"
BASE_STRATEGY_ID = (
    "lookback_be_frequency:lb20:buf2.5:delta600:cl0.55:"
    "end1230:skipfri1:maxday1:space30"
)
LOOKBACK_BARS = 20
BUFFER_POINTS = 2.5
DELTA_THRESHOLD = 600.0
CLOSE_LOCATION_THRESHOLD = 0.55
ENTRY_END = time(12, 30)
SKIP_FRIDAY = True
MAX_PER_DAY = 1
MIN_SPACING_SECONDS = 30 * 60


@dataclass(frozen=True)
class FilterSpec:
    filter_id: str
    label: str
    keep: Callable[[be.ManagedOutcome, dict[str, float | int | str]], bool]


HEADER = [
    "schema_version",
    "filter_id",
    "filter_label",
    "strategy_id",
    "quantity",
    "split",
    "first_target_points",
    "initial_stop_points",
    "runner_target_points",
    "evaluated_trades",
    "signal_days",
    "trades_per_week",
    "first_target_rate",
    "full_stop_rate",
    "runner_breakeven_rate",
    "runner_target_rate",
    "net_usd",
    "average_trade_usd",
    "profit_factor",
    "max_trade_sequence_drawdown_usd",
    "latest_year_trades",
    "latest_year_net_usd",
    "worst_quarter_net_usd",
    "worst_day_usd",
    "average_holding_minutes",
    "median_holding_minutes",
    "direction_mix",
    "weekday_mix",
    "notes",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refine the weak-positive MNQ breakeven-frequency lead.",
    )
    parser.add_argument("input", nargs="?", default=wave.DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--symbol", default="MNQU26-CME")
    parser.add_argument("--minimum-trades", type=int, default=80)
    args = parser.parse_args()

    bars = wave._load_feature_bars(args.input)
    bars_by_date = wave._bars_by_date(bars)
    rows_by_index = wave._rows_by_global_index(bars_by_date)
    flatten_index_by_date = be._flatten_index_by_date(bars_by_date)
    sample_info = be._sample_info(bars)
    signals = _base_signals(bars_by_date, symbol=args.symbol)
    path_risk = be.ManagedRisk(
        quantity=2,
        first_leg_quantity=1,
        runner_quantity=1,
        first_target_points=25.0,
        initial_stop_points=40.0,
        runner_target_points=80.0,
        round_turn_cost_usd=2 * be.ROUND_TURN_COST_PER_CONTRACT_USD,
    )
    priced_risk = be.ManagedRisk(
        quantity=4,
        first_leg_quantity=3,
        runner_quantity=1,
        first_target_points=25.0,
        initial_stop_points=40.0,
        runner_target_points=80.0,
        round_turn_cost_usd=4 * be.ROUND_TURN_COST_PER_CONTRACT_USD,
    )
    outcomes = be._evaluate_signals(
        signals,
        bars_by_date,
        rows_by_index,
        flatten_index_by_date,
        path_risk,
    )
    features_by_index = _features_by_index(signals, bars_by_date, rows_by_index)
    filters = _filter_specs()
    rows: list[dict[str, object]] = []
    for spec in filters:
        filtered = [
            outcome
            for outcome in outcomes
            if spec.keep(outcome, features_by_index[outcome.entry_bar_index])
        ]
        if len(filtered) < args.minimum_trades:
            continue
        row = _summary_row(spec, filtered, priced_risk, sample_info)
        rows.append(row)

    rows.sort(key=_ranking_key)
    _write_csv(args.output, HEADER, rows)
    _write_report(args.report_output, bars, outcomes, rows, priced_risk)
    best = rows[0] if rows else None
    best_summary = "none"
    if best is not None:
        best_summary = (
            f"{best['filter_id']} trades={best['evaluated_trades']} "
            f"net={best['net_usd']} pf={best['profit_factor']} "
            f"latest={best['latest_year_net_usd']} worstq={best['worst_quarter_net_usd']}"
        )
    print(
        f"wrote {len(rows)} MNQ breakeven refinement rows to {args.output}; "
        f"base_trades={len(outcomes)}; best={best_summary}",
    )
    return 0


def _base_signals(
    bars_by_date: dict[date, list[wave.Bar]],
    *,
    symbol: str,
) -> list[wave.Signal]:
    signals = []
    for rows in bars_by_date.values():
        signals.extend(
            be._lookback_breakout_signals(
                rows,
                strategy_id=BASE_STRATEGY_ID,
                lookback_bars=LOOKBACK_BARS,
                buffer_points=BUFFER_POINTS,
                delta_threshold=DELTA_THRESHOLD,
                close_location_threshold=CLOSE_LOCATION_THRESHOLD,
                entry_end=ENTRY_END,
                skip_friday=SKIP_FRIDAY,
                max_per_day=MAX_PER_DAY,
                min_spacing_seconds=MIN_SPACING_SECONDS,
                symbol=symbol,
            ),
        )
    return signals


def _features_by_index(
    signals: list[wave.Signal],
    bars_by_date: dict[date, list[wave.Bar]],
    rows_by_index: dict[int, int],
) -> dict[int, dict[str, float | int | str]]:
    features = {}
    for signal in signals:
        row = signal.bar
        rows = bars_by_date[row.trade_date]
        local_index = rows_by_index[row.index]
        lookback = rows[max(0, local_index - LOOKBACK_BARS):local_index]
        day_rows = rows[: local_index + 1]
        direction = 1.0 if signal.direction == "long" else -1.0
        lookback_move = (row.close - lookback[0].close) * direction if lookback else 0.0
        prev5 = rows[max(0, local_index - 5):local_index]
        prev5_move = (row.close - prev5[0].close) * direction if prev5 else 0.0
        open_move = (row.close - day_rows[0].open) * direction if day_rows else 0.0
        features[row.index] = {
            "weekday": row.timestamp.weekday(),
            "minute": row.timestamp.hour * 60 + row.timestamp.minute,
            "direction": signal.direction,
            "bar_range": row.high - row.low,
            "abs_delta": abs(row.delta),
            "directional_delta": row.delta * direction,
            "directional_close_location": (
                row.close_location if signal.direction == "long" else 1.0 - row.close_location
            ),
            "directional_vwap_dist": (row.close - row.vwap) * direction,
            "lookback_move": lookback_move,
            "prev5_move": prev5_move,
            "open_move": open_move,
            "day_range_so_far": max(day.high for day in day_rows) - min(day.low for day in day_rows),
            "volume": row.volume,
            "trades": row.trades,
        }
    return features


def _filter_specs() -> list[FilterSpec]:
    specs: list[FilterSpec] = [
        FilterSpec("all", "baseline, no additional filter", lambda _outcome, _f: True),
    ]
    specs.extend(_direction_specs())
    specs.extend(_weekday_specs())
    specs.extend(_time_window_specs())
    specs.extend(_numeric_specs())
    specs.extend(_combo_specs())
    return specs


def _direction_specs() -> list[FilterSpec]:
    return [
        FilterSpec("long_only", "long entries only", lambda _o, f: f["direction"] == "long"),
        FilterSpec("short_only", "short entries only", lambda _o, f: f["direction"] == "short"),
    ]


def _weekday_specs() -> list[FilterSpec]:
    weekday_groups = {
        "mon": (0,),
        "tue": (1,),
        "wed": (2,),
        "thu": (3,),
        "mon_tue": (0, 1),
        "wed_thu": (2, 3),
        "mon_wed": (0, 2),
        "tue_thu": (1, 3),
        "mon_tue_wed": (0, 1, 2),
        "tue_wed_thu": (1, 2, 3),
        "not_mon": (1, 2, 3),
        "not_tue": (0, 2, 3),
        "not_wed": (0, 1, 3),
        "not_thu": (0, 1, 2),
    }
    return [
        FilterSpec(
            f"weekday_{name}",
            f"weekday group {name}",
            lambda _o, f, allowed=set(days): int(f["weekday"]) in allowed,
        )
        for name, days in weekday_groups.items()
    ]


def _time_window_specs() -> list[FilterSpec]:
    windows = (
        ("1000_1030", 10 * 60, 10 * 60 + 30),
        ("1000_1100", 10 * 60, 11 * 60),
        ("1000_1130", 10 * 60, 11 * 60 + 30),
        ("1000_1200", 10 * 60, 12 * 60),
        ("1030_1200", 10 * 60 + 30, 12 * 60),
        ("1030_1230", 10 * 60 + 30, 12 * 60 + 30),
        ("1100_1230", 11 * 60, 12 * 60 + 30),
    )
    return [
        FilterSpec(
            f"time_{name}",
            f"entry time {name}",
            lambda _o, f, start=start, end=end: start <= int(f["minute"]) <= end,
        )
        for name, start, end in windows
    ]


def _numeric_specs() -> list[FilterSpec]:
    specs: list[FilterSpec] = []
    specs.extend(_numeric_cap_specs("bar_range", "bar", (10.0, 15.0, 20.0, 25.0, 30.0)))
    specs.extend(_numeric_cap_specs("abs_delta", "absdelta", (800.0, 1000.0, 1200.0, 1600.0)))
    specs.extend(_numeric_cap_specs("directional_vwap_dist", "vwapdist", (20.0, 40.0, 60.0, 80.0, 120.0)))
    specs.extend(_numeric_cap_specs("lookback_move", "lbmove", (20.0, 40.0, 60.0, 80.0, 120.0)))
    specs.extend(_numeric_cap_specs("prev5_move", "prev5", (10.0, 20.0, 30.0, 40.0, 60.0)))
    specs.extend(_numeric_cap_specs("open_move", "openmove", (30.0, 60.0, 90.0, 120.0, 180.0)))
    specs.extend(_numeric_cap_specs("day_range_so_far", "dayrange", (40.0, 60.0, 80.0, 120.0, 160.0)))
    specs.extend(_numeric_floor_specs("directional_vwap_dist", "vwapdistmin", (0.0, 10.0, 20.0, 40.0)))
    specs.extend(_numeric_floor_specs("lookback_move", "lbmovemin", (0.0, 10.0, 20.0, 40.0)))
    specs.extend(_numeric_floor_specs("directional_close_location", "clmin", (0.6, 0.7, 0.8)))
    return specs


def _numeric_cap_specs(
    feature_name: str,
    prefix: str,
    thresholds: Iterable[float],
) -> list[FilterSpec]:
    return [
        FilterSpec(
            f"{prefix}_lte{_value_id(threshold)}",
            f"{feature_name} <= {threshold:g}",
            lambda _o, f, name=feature_name, limit=threshold: float(f[name]) <= limit,
        )
        for threshold in thresholds
    ]


def _numeric_floor_specs(
    feature_name: str,
    prefix: str,
    thresholds: Iterable[float],
) -> list[FilterSpec]:
    return [
        FilterSpec(
            f"{prefix}_gte{_value_id(threshold)}",
            f"{feature_name} >= {threshold:g}",
            lambda _o, f, name=feature_name, floor=threshold: float(f[name]) >= floor,
        )
        for threshold in thresholds
    ]


def _combo_specs() -> list[FilterSpec]:
    specs: list[FilterSpec] = []
    time_specs = _time_window_specs()
    numeric_specs = [
        spec for spec in _numeric_specs()
        if spec.filter_id.startswith(
            (
                "bar_lte",
                "absdelta_lte",
                "vwapdist_lte",
                "lbmove_lte",
                "prev5_lte",
                "dayrange_lte",
            ),
        )
    ]
    weekday_specs = [
        spec for spec in _weekday_specs()
        if spec.filter_id in {
            "weekday_not_mon",
            "weekday_not_tue",
            "weekday_not_wed",
            "weekday_not_thu",
            "weekday_mon_tue_wed",
            "weekday_tue_wed_thu",
        }
    ]
    for left in time_specs:
        for right in numeric_specs:
            specs.append(_and_spec(left, right))
    for left in weekday_specs:
        for right in numeric_specs:
            specs.append(_and_spec(left, right))
    for left in _direction_specs():
        for right in numeric_specs:
            specs.append(_and_spec(left, right))
    return specs


def _and_spec(left: FilterSpec, right: FilterSpec) -> FilterSpec:
    return FilterSpec(
        f"{left.filter_id}__{right.filter_id}",
        f"{left.label}; {right.label}",
        lambda outcome, features, l=left, r=right: (
            l.keep(outcome, features) and r.keep(outcome, features)
        ),
    )


def _summary_row(
    spec: FilterSpec,
    outcomes: list[be.ManagedOutcome],
    risk: be.ManagedRisk,
    sample_info: be.SampleInfo,
) -> dict[str, object]:
    base_row = be._sweep_row(
        strategy_id=f"{BASE_STRATEGY_ID}:refine{spec.filter_id}",
        family="lookback_be_frequency_refine",
        raw_signal_count=len(outcomes),
        outcomes=outcomes,
        risk=risk,
        sample_info=sample_info,
    )
    direction_mix = _mix(outcome.direction for outcome in outcomes)
    weekday_mix = _mix(str(outcome.entry_time.weekday()) for outcome in outcomes)
    return {
        "schema_version": 1,
        "filter_id": spec.filter_id,
        "filter_label": spec.label,
        "strategy_id": base_row["strategy_id"],
        "quantity": base_row["quantity"],
        "split": f"{base_row['first_leg_quantity']}+{base_row['runner_quantity']}",
        "first_target_points": base_row["first_target_points"],
        "initial_stop_points": base_row["initial_stop_points"],
        "runner_target_points": base_row["runner_target_points"],
        "evaluated_trades": base_row["evaluated_trades"],
        "signal_days": base_row["signal_days"],
        "trades_per_week": base_row["trades_per_week"],
        "first_target_rate": base_row["first_target_rate"],
        "full_stop_rate": base_row["full_stop_rate"],
        "runner_breakeven_rate": base_row["runner_breakeven_rate"],
        "runner_target_rate": base_row["runner_target_rate"],
        "net_usd": base_row["net_usd"],
        "average_trade_usd": base_row["average_trade_usd"],
        "profit_factor": base_row["profit_factor"],
        "max_trade_sequence_drawdown_usd": base_row["max_trade_sequence_drawdown_usd"],
        "latest_year_trades": base_row["latest_year_trades"],
        "latest_year_net_usd": base_row["latest_year_net_usd"],
        "worst_quarter_net_usd": base_row["worst_quarter_net_usd"],
        "worst_day_usd": base_row["worst_day_usd"],
        "average_holding_minutes": base_row["average_holding_minutes"],
        "median_holding_minutes": base_row["median_holding_minutes"],
        "direction_mix": direction_mix,
        "weekday_mix": weekday_mix,
        "notes": "filtered refinement of weak-positive MNQ breakeven-frequency lead",
    }


def _mix(values: Iterable[str]) -> str:
    counts: dict[str, int] = defaultdict(int)
    for value in values:
        counts[value] += 1
    return ";".join(f"{key}:{counts[key]}" for key in sorted(counts))


def _write_report(
    report_output: str,
    bars: list[wave.Bar],
    baseline_outcomes: list[be.ManagedOutcome],
    rows: list[dict[str, object]],
    risk: be.ManagedRisk,
) -> None:
    baseline = next((row for row in rows if row["filter_id"] == "all"), None)
    accepted = [
        row for row in rows
        if int(row["evaluated_trades"]) >= 120
        and float(row["trades_per_week"]) >= 1.2
        and float(row["net_usd"]) > 0.0
        and float(row["latest_year_net_usd"]) > 0.0
        and float(row["profit_factor"]) >= 1.20
        and float(row["worst_quarter_net_usd"]) > -1000.0
        and float(row["max_trade_sequence_drawdown_usd"]) > -2000.0
    ]
    top_rows = rows[:12]
    positive_latest = [
        row for row in rows
        if float(row["net_usd"]) > 0.0 and float(row["latest_year_net_usd"]) > 0.0
    ]
    positive_latest.sort(
        key=lambda row: (
            -float(row["profit_factor"]),
            -float(row["net_usd"]),
            float(row["max_trade_sequence_drawdown_usd"]),
        ),
    )
    lines = [
        "# MNQ Breakeven-Frequency Refinement",
        "",
        "Status: focused filter refinement of the weak-positive MNQ breakeven-frequency lead.",
        "",
        "## Fixed Baseline",
        "",
        f"- strategy: `{BASE_STRATEGY_ID}`",
        f"- management: `{risk.quantity} MNQ`, split `{risk.first_leg_quantity}+{risk.runner_quantity}`, "
        f"`{risk.first_target_points:g} / {risk.initial_stop_points:g} / {risk.runner_target_points:g}`",
        f"- base evaluated trades before filters: `{len(baseline_outcomes)}`",
        f"- source rows: `{len(bars)}`",
        f"- source dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        "",
        "## Result",
        "",
    ]
    if baseline is not None:
        lines.extend(
            [
                "| Baseline Metric | Value |",
                "| --- | ---: |",
                f"| Trades | `{baseline['evaluated_trades']}` |",
                f"| Trades/week | `{baseline['trades_per_week']}` |",
                f"| Net | `${baseline['net_usd']}` |",
                f"| PF | `{baseline['profit_factor']}` |",
                f"| Latest-year net | `${baseline['latest_year_net_usd']}` |",
                f"| Worst quarter | `${baseline['worst_quarter_net_usd']}` |",
                f"| Max trade-sequence DD | `${baseline['max_trade_sequence_drawdown_usd']}` |",
                "",
            ],
        )
    lines.append(f"Rows meeting the acceptance lens: `{len(accepted)}`.")
    if not accepted:
        lines.append(
            "No refined filter is accepted. The weak positive row could not be "
            "stabilized with simple time, weekday, direction, or context filters.",
        )
    lines.extend(
        [
            "",
            "## Top Ranked Filters",
            "",
            "| Rank | Filter | Trades | /Wk | T1 Hit | Full Stop | Net | PF | Latest-Year Net | Worst Quarter | Max DD |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    for rank, row in enumerate(top_rows, start=1):
        lines.append(
            "| "
            f"{rank} | `{row['filter_id']}` | {row['evaluated_trades']} | "
            f"{row['trades_per_week']} | "
            f"{float(row['first_target_rate']) * 100:.1f}% | "
            f"{float(row['full_stop_rate']) * 100:.1f}% | "
            f"{row['net_usd']} | {row['profit_factor']} | "
            f"{row['latest_year_net_usd']} | {row['worst_quarter_net_usd']} | "
            f"{row['max_trade_sequence_drawdown_usd']} |"
        )
    lines.extend(
        [
            "",
            "## Positive Latest-Year Rows",
            "",
        ],
    )
    if not positive_latest:
        lines.append("No rows were positive in both full sample and latest year.")
    else:
        lines.extend(
            [
                "| Rank | Filter | Trades | Net | PF | Latest-Year Net | Worst Quarter | Max DD |",
                "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
            ],
        )
        for rank, row in enumerate(positive_latest[:10], start=1):
            lines.append(
                "| "
                f"{rank} | `{row['filter_id']}` | {row['evaluated_trades']} | "
                f"{row['net_usd']} | {row['profit_factor']} | "
                f"{row['latest_year_net_usd']} | {row['worst_quarter_net_usd']} | "
                f"{row['max_trade_sequence_drawdown_usd']} |"
            )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The breakeven-frequency concept still has one useful observation: a "
            "high target-one touch rate is possible on MNQ lookback continuation. "
            "The problem is that the protected outcomes are too small relative to "
            "the full stops, and the runner does not hit often enough to carry the "
            "strategy.",
            "",
            "Next research should either change the entry family or use a different "
            "trade-management shape. More filtering of this exact baseline is likely "
            "to overfit.",
            "",
        ],
    )
    Path(report_output).write_text("\n".join(lines), encoding="utf-8")


def _write_csv(path: str, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _ranking_key(row: dict[str, object]) -> tuple[float, ...]:
    trades = int(row["evaluated_trades"])
    net = float(row["net_usd"])
    latest = float(row["latest_year_net_usd"])
    pf = float(row["profit_factor"])
    worst_quarter = float(row["worst_quarter_net_usd"])
    max_drawdown = float(row["max_trade_sequence_drawdown_usd"])
    accepted_penalty = (
        0.0
        if (
            trades >= 120
            and net > 0.0
            and latest > 0.0
            and pf >= 1.20
            and worst_quarter > -1000.0
            and max_drawdown > -2000.0
        )
        else 1.0
    )
    return (
        accepted_penalty,
        0.0 if net > 0.0 else 1.0,
        0.0 if latest > 0.0 else 1.0,
        0.0 if worst_quarter > -1000.0 else 1.0,
        0.0 if max_drawdown > -2000.0 else 1.0,
        -pf,
        -net,
        max_drawdown,
        -trades,
    )


def _value_id(value: float) -> str:
    return f"{value:g}".replace(".", "p")


if __name__ == "__main__":
    raise SystemExit(main())
