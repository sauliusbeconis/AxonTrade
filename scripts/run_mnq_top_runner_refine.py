#!/usr/bin/env python3
"""Refine the strongest MNQ top-runner families from the first pass."""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, time
from pathlib import Path
from typing import Callable, Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_mnq_eval_pass_wave_rider as wave  # noqa: E402
import run_mnq_top_runner_research as runner  # noqa: E402


DEFAULT_OUTPUT = "reports/mnq-top-runner-refine.csv"
DEFAULT_REPORT_OUTPUT = "reports/mnq-top-runner-refine.md"


@dataclass(frozen=True)
class BaseSpec:
    base_id: str
    family: str
    signal_builder: Callable[[dict[date, list[wave.Bar]], str], list[wave.Signal]]
    target_points: tuple[float, ...]
    stop_points: tuple[float, ...]


@dataclass(frozen=True)
class FilterSpec:
    filter_id: str
    label: str
    keep: Callable[[wave.Signal, dict[str, float | int | str]], bool]


HEADER = [
    "schema_version",
    "base_id",
    "filter_id",
    "filter_label",
    "strategy_id",
    "family",
    "quantity",
    "target_points",
    "stop_points",
    "evaluated_trades",
    "trades_per_week",
    "win_rate",
    "target_hit_rate",
    "stop_hit_rate",
    "net_usd",
    "average_trade_usd",
    "profit_factor",
    "payoff_ratio",
    "max_trade_sequence_drawdown_usd",
    "net_to_drawdown",
    "latest_year_trades",
    "latest_year_net_usd",
    "worst_quarter_net_usd",
    "worst_day_usd",
    "average_holding_minutes",
    "median_holding_minutes",
    "notes",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refine MNQ runner leads with simple context filters and risk geometry.",
    )
    parser.add_argument("input", nargs="?", default=wave.DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--symbol", default="MNQU26-CME")
    parser.add_argument("--minimum-trades", type=int, default=60)
    args = parser.parse_args()

    bars = wave._load_feature_bars(args.input)
    bars_by_date = wave._bars_by_date(bars)
    rows_by_index = wave._rows_by_global_index(bars_by_date)
    flatten_index_by_date = runner._flatten_index_by_date(bars_by_date)
    sample_info = runner._sample_info(bars)
    filters = _filter_specs()

    rows: list[dict[str, object]] = []
    for base in _base_specs():
        signals = base.signal_builder(bars_by_date, args.symbol)
        features_by_index = _features_by_index(signals, bars_by_date, rows_by_index)
        for filter_spec in filters:
            filtered = [
                signal
                for signal in signals
                if filter_spec.keep(signal, features_by_index[signal.bar.index])
            ]
            if len(filtered) < args.minimum_trades:
                continue
            for risk in _risk_profiles(base):
                outcomes = runner._evaluate_signals(
                    filtered,
                    bars_by_date,
                    rows_by_index,
                    flatten_index_by_date,
                    risk,
                    family=base.family,
                )
                if len(outcomes) < args.minimum_trades:
                    continue
                row = runner._sweep_row(
                    f"{base.base_id}:filter{filter_spec.filter_id}",
                    base.family,
                    len(filtered),
                    outcomes,
                    risk,
                    sample_info,
                )
                row["base_id"] = base.base_id
                row["filter_id"] = filter_spec.filter_id
                row["filter_label"] = filter_spec.label
                row["notes"] = "top-runner refinement; no breakeven logic"
                rows.append(_ordered_row(row))

    rows.sort(key=_ranking_key)
    _write_csv(args.output, HEADER, rows)
    _write_report(args.report_output, bars, rows)
    best = rows[0] if rows else None
    best_summary = "none"
    if best is not None:
        best_summary = (
            f"{best['base_id']} filter={best['filter_id']} "
            f"target={best['target_points']} stop={best['stop_points']} "
            f"trades={best['evaluated_trades']} net={best['net_usd']} "
            f"pf={best['profit_factor']} dd={best['max_trade_sequence_drawdown_usd']}"
        )
    print(
        f"wrote {len(rows)} MNQ top-runner refine rows to {args.output}; "
        f"best={best_summary}",
    )
    return 0


def _base_specs() -> list[BaseSpec]:
    return [
        BaseSpec(
            "vwap_pullback_120_30_delta600_cl65_end1230_allweek",
            "runner_vwap_pullback_refine",
            lambda bars_by_date, symbol: _vwap_pullback_signals(
                bars_by_date,
                symbol=symbol,
                strategy_id="vwap_pullback_120_30_delta600_cl65_end1230_allweek",
                stretch_points=120.0,
                pullback_points=30.0,
                delta_threshold=600.0,
                close_location_threshold=0.65,
                entry_end=time(12, 30),
                skip_friday=False,
            ),
            (120.0, 160.0, 200.0, 260.0, 320.0, 400.0),
            (20.0, 25.0, 30.0, 35.0, 50.0),
        ),
        BaseSpec(
            "vwap_pullback_120_30_delta0_cl65_end1230_allweek",
            "runner_vwap_pullback_refine",
            lambda bars_by_date, symbol: _vwap_pullback_signals(
                bars_by_date,
                symbol=symbol,
                strategy_id="vwap_pullback_120_30_delta0_cl65_end1230_allweek",
                stretch_points=120.0,
                pullback_points=30.0,
                delta_threshold=0.0,
                close_location_threshold=0.65,
                entry_end=time(12, 30),
                skip_friday=False,
            ),
            (120.0, 160.0, 200.0, 260.0, 320.0, 400.0),
            (20.0, 25.0, 30.0, 35.0, 50.0),
        ),
        BaseSpec(
            "lookback_lb20_buf0_delta600_cl65_end1230_skipfri",
            "runner_lookback_breakout_refine",
            lambda bars_by_date, symbol: _lookback_breakout_signals(
                bars_by_date,
                symbol=symbol,
                strategy_id="lookback_lb20_buf0_delta600_cl65_end1230_skipfri",
                lookback_bars=20,
                buffer_points=0.0,
                delta_threshold=600.0,
                close_location_threshold=0.65,
                entry_end=time(12, 30),
                skip_friday=True,
            ),
            (80.0, 100.0, 120.0, 160.0, 200.0, 260.0),
            (50.0, 70.0, 90.0, 120.0),
        ),
        BaseSpec(
            "or60_buf0_delta0_cl65_end1430_allweek",
            "runner_opening_range_breakout_refine",
            lambda bars_by_date, symbol: _opening_range_signals(
                bars_by_date,
                symbol=symbol,
                strategy_id="or60_buf0_delta0_cl65_end1430_allweek",
                min_or_width=60.0,
                buffer_points=0.0,
                delta_threshold=0.0,
                close_location_threshold=0.65,
                entry_end=time(14, 30),
                skip_friday=False,
            ),
            (80.0, 100.0, 120.0, 160.0, 200.0),
            (50.0, 70.0, 90.0, 120.0),
        ),
    ]


def _vwap_pullback_signals(
    bars_by_date: dict[date, list[wave.Bar]],
    *,
    symbol: str,
    strategy_id: str,
    stretch_points: float,
    pullback_points: float,
    delta_threshold: float,
    close_location_threshold: float,
    entry_end: time,
    skip_friday: bool,
) -> list[wave.Signal]:
    signals = []
    for rows in bars_by_date.values():
        signals.extend(
            runner._vwap_pullback_signals(
                rows,
                strategy_id=strategy_id,
                stretch_points=stretch_points,
                pullback_points=pullback_points,
                delta_threshold=delta_threshold,
                close_location_threshold=close_location_threshold,
                entry_end=entry_end,
                skip_friday=skip_friday,
                symbol=symbol,
            ),
        )
    return signals


def _lookback_breakout_signals(
    bars_by_date: dict[date, list[wave.Bar]],
    *,
    symbol: str,
    strategy_id: str,
    lookback_bars: int,
    buffer_points: float,
    delta_threshold: float,
    close_location_threshold: float,
    entry_end: time,
    skip_friday: bool,
) -> list[wave.Signal]:
    signals = []
    for rows in bars_by_date.values():
        signals.extend(
            runner._lookback_breakout_signals(
                rows,
                strategy_id=strategy_id,
                lookback_bars=lookback_bars,
                buffer_points=buffer_points,
                delta_threshold=delta_threshold,
                close_location_threshold=close_location_threshold,
                entry_end=entry_end,
                skip_friday=skip_friday,
                symbol=symbol,
            ),
        )
    return signals


def _opening_range_signals(
    bars_by_date: dict[date, list[wave.Bar]],
    *,
    symbol: str,
    strategy_id: str,
    min_or_width: float,
    buffer_points: float,
    delta_threshold: float,
    close_location_threshold: float,
    entry_end: time,
    skip_friday: bool,
) -> list[wave.Signal]:
    signals = []
    for rows in bars_by_date.values():
        signals.extend(
            runner._opening_range_breakout_signals(
                rows,
                strategy_id=strategy_id,
                min_or_width=min_or_width,
                buffer_points=buffer_points,
                delta_threshold=delta_threshold,
                close_location_threshold=close_location_threshold,
                entry_end=entry_end,
                skip_friday=skip_friday,
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
        lookback20 = rows[max(0, local_index - 20):local_index]
        prev5 = rows[max(0, local_index - 5):local_index]
        day_rows = rows[: local_index + 1]
        direction = 1.0 if signal.direction == "long" else -1.0
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
            "lookback20_move": (row.close - lookback20[0].close) * direction
            if lookback20
            else 0.0,
            "prev5_move": (row.close - prev5[0].close) * direction if prev5 else 0.0,
            "open_move": (row.close - day_rows[0].open) * direction if day_rows else 0.0,
            "day_range_so_far": max(day.high for day in day_rows) - min(day.low for day in day_rows),
        }
    return features


def _filter_specs() -> list[FilterSpec]:
    specs = [FilterSpec("all", "no extra filter", lambda _signal, _f: True)]
    specs.extend(_direction_specs())
    specs.extend(_weekday_specs())
    specs.extend(_time_specs())
    numeric = _numeric_specs()
    specs.extend(numeric)
    for left in _direction_specs():
        for right in numeric:
            specs.append(_and_spec(left, right))
    for left in _weekday_combo_specs():
        for right in numeric:
            specs.append(_and_spec(left, right))
    for left in _time_specs():
        for right in numeric:
            specs.append(_and_spec(left, right))
    return specs


def _direction_specs() -> list[FilterSpec]:
    return [
        FilterSpec("long", "long only", lambda _s, f: f["direction"] == "long"),
        FilterSpec("short", "short only", lambda _s, f: f["direction"] == "short"),
    ]


def _weekday_specs() -> list[FilterSpec]:
    specs = []
    for day, name in ((0, "mon"), (1, "tue"), (2, "wed"), (3, "thu"), (4, "fri")):
        specs.append(
            FilterSpec(
                f"weekday_{name}",
                f"weekday {name}",
                lambda _s, f, day=day: int(f["weekday"]) == day,
            ),
        )
    specs.extend(_weekday_combo_specs())
    return specs


def _weekday_combo_specs() -> list[FilterSpec]:
    groups = {
        "not_fri": (0, 1, 2, 3),
        "not_mon": (1, 2, 3, 4),
        "not_thu": (0, 1, 2, 4),
        "mon_tue_wed": (0, 1, 2),
        "tue_wed_thu": (1, 2, 3),
        "wed_thu_fri": (2, 3, 4),
    }
    return [
        FilterSpec(
            f"weekday_{name}",
            f"weekday group {name}",
            lambda _s, f, allowed=set(days): int(f["weekday"]) in allowed,
        )
        for name, days in groups.items()
    ]


def _time_specs() -> list[FilterSpec]:
    windows = (
        ("1000_1100", 10 * 60, 11 * 60),
        ("1000_1130", 10 * 60, 11 * 60 + 30),
        ("1000_1200", 10 * 60, 12 * 60),
        ("1030_1230", 10 * 60 + 30, 12 * 60 + 30),
        ("1100_1230", 11 * 60, 12 * 60 + 30),
        ("1200_1430", 12 * 60, 14 * 60 + 30),
    )
    return [
        FilterSpec(
            f"time_{name}",
            f"time {name}",
            lambda _s, f, start=start, end=end: start <= int(f["minute"]) <= end,
        )
        for name, start, end in windows
    ]


def _numeric_specs() -> list[FilterSpec]:
    specs: list[FilterSpec] = []
    specs.extend(_cap_specs("bar_range", "bar", (10.0, 15.0, 20.0, 25.0, 35.0)))
    specs.extend(_cap_specs("abs_delta", "absdelta", (1000.0, 1400.0, 1800.0, 2400.0)))
    specs.extend(_cap_specs("directional_vwap_dist", "vwapdist", (40.0, 80.0, 120.0, 180.0)))
    specs.extend(_cap_specs("lookback20_move", "lbmove", (40.0, 80.0, 120.0, 180.0)))
    specs.extend(_cap_specs("prev5_move", "prev5", (20.0, 40.0, 60.0, 90.0)))
    specs.extend(_cap_specs("day_range_so_far", "dayrange", (60.0, 90.0, 120.0, 180.0)))
    specs.extend(_floor_specs("directional_vwap_dist", "vwapdistmin", (0.0, 20.0, 40.0, 80.0)))
    specs.extend(_floor_specs("lookback20_move", "lbmovemin", (0.0, 20.0, 40.0, 80.0)))
    specs.extend(_floor_specs("directional_close_location", "clmin", (0.7, 0.8, 0.9)))
    return specs


def _cap_specs(feature_name: str, prefix: str, values: Iterable[float]) -> list[FilterSpec]:
    return [
        FilterSpec(
            f"{prefix}_lte{_value_id(value)}",
            f"{feature_name} <= {value:g}",
            lambda _s, f, name=feature_name, value=value: float(f[name]) <= value,
        )
        for value in values
    ]


def _floor_specs(feature_name: str, prefix: str, values: Iterable[float]) -> list[FilterSpec]:
    return [
        FilterSpec(
            f"{prefix}_gte{_value_id(value)}",
            f"{feature_name} >= {value:g}",
            lambda _s, f, name=feature_name, value=value: float(f[name]) >= value,
        )
        for value in values
    ]


def _and_spec(left: FilterSpec, right: FilterSpec) -> FilterSpec:
    return FilterSpec(
        f"{left.filter_id}__{right.filter_id}",
        f"{left.label}; {right.label}",
        lambda signal, features, l=left, r=right: (
            l.keep(signal, features) and r.keep(signal, features)
        ),
    )


def _risk_profiles(base: BaseSpec) -> list[runner.RunnerRisk]:
    profiles = []
    quantity = 2
    round_turn_cost = quantity * runner.ROUND_TURN_COST_PER_CONTRACT_USD
    for target_points in base.target_points:
        for stop_points in base.stop_points:
            if target_points < stop_points:
                continue
            profiles.append(
                runner.RunnerRisk(
                    quantity=quantity,
                    target_points=target_points,
                    stop_points=stop_points,
                    round_turn_cost_usd=round_turn_cost,
                ),
            )
    return profiles


def _ordered_row(row: dict[str, object]) -> dict[str, object]:
    return {field: row.get(field, "") for field in HEADER}


def _write_report(
    report_output: str,
    bars: list[wave.Bar],
    rows: list[dict[str, object]],
) -> None:
    accepted = [
        row for row in rows
        if int(row["evaluated_trades"]) >= 80
        and float(row["net_usd"]) > 0.0
        and float(row["latest_year_net_usd"]) > 0.0
        and float(row["profit_factor"]) >= 1.70
        and float(row["max_trade_sequence_drawdown_usd"]) > -2500.0
        and float(row["worst_quarter_net_usd"]) > -1500.0
        and float(row["net_to_drawdown"]) >= 2.0
    ]
    top_rows = rows[:15]
    best_by_base = _best_by_base(rows)
    lines = [
        "# MNQ Top-Runner Refinement",
        "",
        "Status: focused refinement of the first-pass MNQ runner leads.",
        "",
        "## Source",
        "",
        f"- rows: `{len(bars)}`",
        f"- dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        "- quantity: fixed `2 MNQ`",
        "- no breakeven or eval-pass geometry",
        "",
        "## Result",
        "",
        f"Accepted rows by stricter runner lens: `{len(accepted)}`.",
    ]
    if accepted:
        best = accepted[0]
        lines.extend(
            [
                "",
                "Best accepted row:",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Base | `{best['base_id']}` |",
                f"| Filter | `{best['filter_id']}` |",
                f"| Target / Stop | `{best['target_points']} / {best['stop_points']}` |",
                f"| Trades | `{best['evaluated_trades']}` |",
                f"| Net | `${best['net_usd']}` |",
                f"| PF | `{best['profit_factor']}` |",
                f"| Net/DD | `{best['net_to_drawdown']}` |",
                f"| DD | `${best['max_trade_sequence_drawdown_usd']}` |",
                f"| Latest-year net | `${best['latest_year_net_usd']}` |",
                f"| Worst quarter | `${best['worst_quarter_net_usd']}` |",
            ],
        )
    else:
        lines.append(
            "No row cleared the stricter runner lens. Top rows are research leads only.",
        )
    lines.extend(
        [
            "",
            "## Top Rows",
            "",
            "| Rank | Base | Filter | Target / Stop | Trades | Net | PF | Net/DD | DD | Latest | Worst Q |",
            "| ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    for rank, row in enumerate(top_rows, start=1):
        lines.append(
            "| "
            f"{rank} | `{row['base_id']}` | `{row['filter_id']}` | "
            f"{row['target_points']} / {row['stop_points']} | {row['evaluated_trades']} | "
            f"{row['net_usd']} | {row['profit_factor']} | {row['net_to_drawdown']} | "
            f"{row['max_trade_sequence_drawdown_usd']} | {row['latest_year_net_usd']} | "
            f"{row['worst_quarter_net_usd']} |"
        )
    lines.extend(
        [
            "",
            "## Best By Base",
            "",
            "| Base | Filter | Target / Stop | Trades | Net | PF | DD | Latest | Worst Q |",
            "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    for row in best_by_base:
        lines.append(
            "| "
            f"`{row['base_id']}` | `{row['filter_id']}` | "
            f"{row['target_points']} / {row['stop_points']} | {row['evaluated_trades']} | "
            f"{row['net_usd']} | {row['profit_factor']} | "
            f"{row['max_trade_sequence_drawdown_usd']} | {row['latest_year_net_usd']} | "
            f"{row['worst_quarter_net_usd']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The goal of this pass is to find a stronger normal-profitability runner "
            "than the current MNQ VWAP/delta lead. Any accepted row still needs "
            "slippage stress and fixed holdout validation before replay.",
            "",
        ],
    )
    Path(report_output).write_text("\n".join(lines), encoding="utf-8")


def _best_by_base(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    best: dict[str, dict[str, object]] = {}
    for row in rows:
        key = str(row["base_id"])
        current = best.get(key)
        if current is None or _ranking_key(row) < _ranking_key(current):
            best[key] = row
    return sorted(best.values(), key=_ranking_key)


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
    max_drawdown = float(row["max_trade_sequence_drawdown_usd"])
    worst_quarter = float(row["worst_quarter_net_usd"])
    net_to_drawdown = float(row["net_to_drawdown"])
    accepted_penalty = (
        0.0
        if (
            trades >= 80
            and net > 0.0
            and latest > 0.0
            and pf >= 1.70
            and max_drawdown > -2500.0
            and worst_quarter > -1500.0
            and net_to_drawdown >= 2.0
        )
        else 1.0
    )
    return (
        accepted_penalty,
        0.0 if net > 0.0 else 1.0,
        0.0 if latest > 0.0 else 1.0,
        0.0 if worst_quarter > -1500.0 else 1.0,
        0.0 if max_drawdown > -2500.0 else 1.0,
        -pf,
        -net_to_drawdown,
        -net,
        max_drawdown,
        -trades,
    )


def _value_id(value: float) -> str:
    return f"{value:g}".replace(".", "p")


if __name__ == "__main__":
    raise SystemExit(main())
