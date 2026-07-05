#!/usr/bin/env python3
"""Focused deep search around MNQ eval-pass wave-rider candidates."""

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
from typing import Callable, Iterable


DEFAULT_OUTPUT = "reports/mnq-eval-pass-wave-rider-deep-search.csv"
DEFAULT_REPORT = "reports/mnq-eval-pass-wave-rider-deep-search.md"
DEFAULT_TRAIN_DATE_COUNTS = "120,180,240"
DEFAULT_HOLDOUT_DATE_COUNTS = "40,40,60"
MAX_KEEP_RESULTS = 1500


@dataclass(frozen=True)
class FilterProfile:
    filter_id: str
    keep_signal: Callable[[object], bool]


@dataclass(frozen=True)
class CandidateResult:
    row: dict[str, object]
    outcomes: list[object]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a focused deep search around MNQ eval-pass wave-rider candidates.",
    )
    parser.add_argument("input", nargs="?", help="MNQ Sierra orderflow export path.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT)
    parser.add_argument("--symbol", default="MNQU26-CME")
    parser.add_argument("--minimum-signal-days", type=int, default=40)
    parser.add_argument("--keep-results", type=int, default=MAX_KEEP_RESULTS)
    parser.add_argument("--train-date-counts", default=DEFAULT_TRAIN_DATE_COUNTS)
    parser.add_argument("--holdout-date-counts", default=DEFAULT_HOLDOUT_DATE_COUNTS)
    args = parser.parse_args()

    wave = _load_wave_module()
    input_path = args.input or wave.DEFAULT_INPUT
    bars = wave._load_feature_bars(input_path)
    bars_by_date = wave._bars_by_date(bars)
    rows_by_index = wave._rows_by_global_index(bars_by_date)
    risks = _focused_risk_profiles(wave)
    filters = _filter_profiles()
    results = _run_deep_search(
        wave,
        bars_by_date,
        rows_by_index=rows_by_index,
        filters=filters,
        risks=risks,
        symbol=args.symbol,
        minimum_signal_days=args.minimum_signal_days,
        keep_results=args.keep_results,
    )
    results.sort(key=_deep_ranking_key)
    configs = _parse_configs(args.train_date_counts, args.holdout_date_counts)
    unique_results = _unique_results(results)
    benchmark_rows = _benchmark_rows(wave, unique_results[:20], sorted(bars_by_date), configs)
    _write_csv(args.output, [result.row for result in results])
    _write_report(
        args.report_output,
        bars=bars,
        results=unique_results,
        benchmark_rows=benchmark_rows,
        configs=configs,
    )
    best = results[0].row if results else None
    best_summary = "none"
    if best is not None:
        best_summary = (
            f"{best['strategy_id']} qty={best['quantity']} "
            f"target={best['target_net_usd']} stop={best['stop_net_usd']} "
            f"pass={float(best['signal_start_pass_rate']):.3f} "
            f"two_day={float(best['signal_start_two_trade_day_pass_rate']):.3f} "
            f"fail={float(best['signal_start_fail_rate']):.3f}"
        )
    print(
        f"wrote {len(results)} focused MNQ deep-search rows to {args.output}; "
        f"best={best_summary}",
    )
    return 0


def _load_wave_module():
    module_path = Path(__file__).with_name("run_mnq_eval_pass_wave_rider.py")
    spec = importlib.util.spec_from_file_location("mnq_eval_pass_wave_rider", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["mnq_eval_pass_wave_rider"] = module
    spec.loader.exec_module(module)
    return module


def _run_deep_search(
    wave,
    bars_by_date: dict[date, list[object]],
    *,
    rows_by_index: dict[int, int],
    filters: list[FilterProfile],
    risks: list[object],
    symbol: str,
    minimum_signal_days: int,
    keep_results: int,
) -> list[CandidateResult]:
    results: list[CandidateResult] = []
    reviewed = 0
    for entry_start in (time(9, 45), time(10, 0), time(10, 15)):
        for entry_end in (time(12, 0), time(12, 30), time(13, 0)):
            for lookback_bars in (30, 40, 50, 60):
                for buffer_points in (0.0, 2.5):
                    for delta_threshold in (400.0, 600.0, 800.0):
                        for close_location_threshold in (0.50, 0.55, 0.60):
                            for skip_friday in (False, True):
                                base_strategy_id = (
                                    "lookback_breakout_deep:"
                                    f"lb{lookback_bars}:buf{buffer_points:g}:"
                                    f"delta{delta_threshold:g}:"
                                    f"cl{close_location_threshold:g}:"
                                    f"start{_time_id(entry_start)}:"
                                    f"end{_time_id(entry_end)}:"
                                    f"skipfri{int(skip_friday)}"
                                )
                                signals = _lookback_breakout_signals(
                                    wave,
                                    bars_by_date,
                                    strategy_id=base_strategy_id,
                                    lookback_bars=lookback_bars,
                                    buffer_points=buffer_points,
                                    delta_threshold=delta_threshold,
                                    close_location_threshold=close_location_threshold,
                                    entry_start=entry_start,
                                    entry_end=entry_end,
                                    skip_friday=skip_friday,
                                    symbol=symbol,
                                )
                                if len(signals) < minimum_signal_days:
                                    continue
                                features = [
                                    wave._signal_features(
                                        signal,
                                        bars_by_date=bars_by_date,
                                        rows_by_index=rows_by_index,
                                        lookback_bars=lookback_bars,
                                    )
                                    for signal in signals
                                ]
                                for profile in filters:
                                    filtered_signals = [
                                        wave.Signal(
                                            strategy_id=(
                                                f"{base_strategy_id}:filter"
                                                f"{profile.filter_id}"
                                            ),
                                            direction=signal.direction,
                                            bar=signal.bar,
                                            notes=(
                                                f"{signal.notes}; deep filter "
                                                f"{profile.filter_id}"
                                            ),
                                        )
                                        for signal, feature in zip(signals, features)
                                        if profile.keep_signal(feature)
                                    ]
                                    if len(filtered_signals) < minimum_signal_days:
                                        continue
                                    for risk in risks:
                                        reviewed += 1
                                        outcomes = wave._evaluate_signals(
                                            filtered_signals,
                                            bars_by_date,
                                            risk,
                                        )
                                        row = wave._sweep_row(
                                            filtered_signals[0].strategy_id,
                                            "lookback_breakout_deep",
                                            outcomes,
                                            risk,
                                            bars_by_date,
                                        )
                                        if not _passes_deep_lens(row):
                                            continue
                                        results.append(CandidateResult(row, outcomes))
                                        if len(results) > keep_results * 2:
                                            results.sort(key=_deep_ranking_key)
                                            del results[keep_results:]
    results.sort(key=_deep_ranking_key)
    del results[keep_results:]
    print(f"reviewed {reviewed} deep-search strategy/risk rows")
    return results


def _lookback_breakout_signals(
    wave,
    bars_by_date: dict[date, list[object]],
    *,
    strategy_id: str,
    lookback_bars: int,
    buffer_points: float,
    delta_threshold: float,
    close_location_threshold: float,
    entry_start: time,
    entry_end: time,
    skip_friday: bool,
    symbol: str,
) -> list[object]:
    signals = []
    for rows in bars_by_date.values():
        if not rows or (skip_friday and rows[0].timestamp.weekday() == 4):
            continue
        for index in range(lookback_bars, len(rows)):
            row = rows[index]
            row_time = row.timestamp.time()
            if not entry_start <= row_time <= entry_end:
                continue
            lookback = rows[index - lookback_bars:index]
            previous_close = rows[index - 1].close
            lookback_high = max(previous.high for previous in lookback)
            lookback_low = min(previous.low for previous in lookback)
            high_break = lookback_high + buffer_points
            low_break = lookback_low - buffer_points
            if (
                previous_close <= high_break < row.close
                and row.close >= row.vwap
                and row.delta >= delta_threshold
                and row.close_location >= close_location_threshold
            ):
                signals.append(
                    wave.Signal(
                        strategy_id,
                        "long",
                        row,
                        f"{symbol} deep lookback high breakout",
                    ),
                )
                break
            if (
                previous_close >= low_break > row.close
                and row.close <= row.vwap
                and row.delta <= -delta_threshold
                and row.close_location <= 1.0 - close_location_threshold
            ):
                signals.append(
                    wave.Signal(
                        strategy_id,
                        "short",
                        row,
                        f"{symbol} deep lookback low breakout",
                    ),
                )
                break
    return signals


def _focused_risk_profiles(wave) -> list[object]:
    risk_specs = [
        (4, 650.0, 650.0),
        (5, 650.0, 650.0),
        (6, 650.0, 650.0),
        (8, 650.0, 650.0),
        (10, 650.0, 650.0),
        (10, 700.0, 650.0),
        (12, 650.0, 650.0),
        (12, 700.0, 800.0),
        (15, 700.0, 800.0),
    ]
    return [_make_risk_profile(wave, *spec) for spec in risk_specs]


def _make_risk_profile(
    wave,
    quantity: int,
    target_usd: float,
    stop_usd: float,
) -> object:
    round_turn_cost = quantity * (
        2.0 * wave.COMMISSION_PER_SIDE_USD
        + wave.SLIPPAGE_TICKS_PER_CONTRACT * wave.TICK_VALUE_USD
    )
    target_points = wave._round_up_to_tick(
        (target_usd + round_turn_cost) / (quantity * wave.POINT_VALUE_USD),
    )
    actual_target_usd = target_points * quantity * wave.POINT_VALUE_USD - round_turn_cost
    stop_points = wave._round_down_to_tick(
        (stop_usd - round_turn_cost) / (quantity * wave.POINT_VALUE_USD),
    )
    if stop_points <= 0.0:
        raise ValueError("stop specification produced non-positive stop points")
    actual_stop_usd = stop_points * quantity * wave.POINT_VALUE_USD + round_turn_cost
    return wave.RiskProfile(
        quantity=quantity,
        target_net_usd=actual_target_usd,
        stop_net_usd=actual_stop_usd,
        target_points=target_points,
        stop_points=stop_points,
        round_turn_cost_usd=round_turn_cost,
    )


def _filter_profiles() -> list[FilterProfile]:
    return [
        FilterProfile("abs800", lambda f: f.abs_delta <= 800.0),
        FilterProfile("abs1000", lambda f: f.abs_delta <= 1000.0),
        FilterProfile("abs1200", lambda f: f.abs_delta <= 1200.0),
        FilterProfile(
            "abs1000_move75",
            lambda f: f.abs_delta <= 1000.0 and f.lookback_move <= 75.0,
        ),
        FilterProfile(
            "abs1000_move100",
            lambda f: f.abs_delta <= 1000.0 and f.lookback_move <= 100.0,
        ),
        FilterProfile(
            "abs1000_move125",
            lambda f: f.abs_delta <= 1000.0 and f.lookback_move <= 125.0,
        ),
        FilterProfile(
            "abs1000_bar20",
            lambda f: f.abs_delta <= 1000.0 and f.bar_range <= 20.0,
        ),
        FilterProfile(
            "abs1000_bar25",
            lambda f: f.abs_delta <= 1000.0 and f.bar_range <= 25.0,
        ),
        FilterProfile(
            "abs1000_bar30",
            lambda f: f.abs_delta <= 1000.0 and f.bar_range <= 30.0,
        ),
        FilterProfile(
            "abs1000_vwap75",
            lambda f: f.abs_delta <= 1000.0 and f.directional_vwap_dist <= 75.0,
        ),
        FilterProfile(
            "abs1000_vwap100",
            lambda f: f.abs_delta <= 1000.0 and f.directional_vwap_dist <= 100.0,
        ),
        FilterProfile(
            "abs1000_move100_vwap100",
            lambda f: (
                f.abs_delta <= 1000.0
                and f.lookback_move <= 100.0
                and f.directional_vwap_dist <= 100.0
            ),
        ),
        FilterProfile(
            "abs1000_move100_bar25",
            lambda f: (
                f.abs_delta <= 1000.0
                and f.lookback_move <= 100.0
                and f.bar_range <= 25.0
            ),
        ),
        FilterProfile(
            "abs800_move100",
            lambda f: f.abs_delta <= 800.0 and f.lookback_move <= 100.0,
        ),
        FilterProfile(
            "abs1200_move125",
            lambda f: f.abs_delta <= 1200.0 and f.lookback_move <= 125.0,
        ),
    ]


def _passes_deep_lens(row: dict[str, object]) -> bool:
    return (
        int(row["evaluated_trades"]) >= 40
        and int(row["latest_year_trades"]) >= 8
        and float(row["net_usd"]) > 0.0
        and float(row["latest_year_net_usd"]) > 0.0
        and float(row["signal_start_pass_rate"]) >= 0.70
        and float(row["signal_start_fail_rate"]) <= 0.18
        and float(row["signal_start_two_trade_day_pass_rate"]) >= 0.20
    )


def _deep_ranking_key(result: CandidateResult) -> tuple[float, ...]:
    row = result.row
    fail = float(row["signal_start_fail_rate"])
    two_day = float(row["signal_start_two_trade_day_pass_rate"])
    pass_rate = float(row["signal_start_pass_rate"])
    latest = float(row["latest_year_net_usd"])
    max_dd = abs(float(row["max_trade_sequence_drawdown_usd"]))
    worst_quarter = float(row["worst_quarter_net_usd"])
    average_trade = float(row["average_trade_usd"])
    stop = float(row["stop_net_usd"])
    return (
        fail,
        -two_day,
        -pass_rate,
        -latest,
        max_dd,
        -worst_quarter,
        stop,
        -average_trade,
    )


def _unique_results(results: list[CandidateResult]) -> list[CandidateResult]:
    unique = []
    seen: set[tuple[object, ...]] = set()
    for result in results:
        row = result.row
        key = (
            row["quantity"],
            row["target_net_usd"],
            row["stop_net_usd"],
            row["evaluated_trades"],
            row["net_usd"],
            row["latest_year_net_usd"],
            row["max_trade_sequence_drawdown_usd"],
            row["worst_quarter_net_usd"],
            row["signal_start_pass_rate"],
            row["signal_start_two_trade_day_pass_rate"],
            row["signal_start_fail_rate"],
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(result)
    return unique


def _benchmark_rows(
    wave,
    results: list[CandidateResult],
    trade_dates: list[date],
    configs: list[tuple[int, int]],
) -> list[dict[str, object]]:
    rows = []
    seen: set[tuple[object, ...]] = set()
    for result in results:
        row = result.row
        key = (
            row["strategy_id"],
            row["quantity"],
            row["target_net_usd"],
            row["stop_net_usd"],
        )
        if key in seen:
            continue
        seen.add(key)
        for train_count, holdout_count in configs:
            config_id = f"{train_count}x{holdout_count}"
            holdout_windows = []
            holdout_outcomes = []
            max_start = len(trade_dates) - train_count - holdout_count
            for start_index in range(0, max_start + 1, holdout_count):
                holdout_dates = set(
                    trade_dates[
                        start_index + train_count:
                        start_index + train_count + holdout_count
                    ],
                )
                window_outcomes = [
                    outcome for outcome in result.outcomes
                    if outcome.entry_time.date() in holdout_dates
                ]
                holdout_windows.append(sum(outcome.net_usd for outcome in window_outcomes))
                holdout_outcomes.extend(window_outcomes)
            metrics = _metrics(wave, holdout_outcomes)
            rows.append(
                {
                    "config": config_id,
                    "strategy_id": row["strategy_id"],
                    "quantity": row["quantity"],
                    "target_net_usd": row["target_net_usd"],
                    "stop_net_usd": row["stop_net_usd"],
                    "windows": len(holdout_windows),
                    "trades": len(holdout_outcomes),
                    "net_usd": _format_number(metrics["net_usd"]),
                    "average_trade_usd": _format_number(metrics["average_trade_usd"]),
                    "profit_factor": _format_number(metrics["profit_factor"]),
                    "max_drawdown_usd": _format_number(metrics["max_drawdown_usd"]),
                    "positive_windows": sum(value > 0.0 for value in holdout_windows),
                    "negative_windows": sum(value < 0.0 for value in holdout_windows),
                    "signal_start_pass_rate": _format_number(metrics["pass_rate"]),
                    "signal_start_two_trade_day_pass_rate": _format_number(
                        metrics["two_day_rate"],
                    ),
                    "signal_start_fail_rate": _format_number(metrics["fail_rate"]),
                },
            )
    return rows


def _metrics(wave, outcomes: list[object]) -> dict[str, float]:
    net_values = [outcome.net_usd for outcome in outcomes]
    positive = [value for value in net_values if value > 0.0]
    negative = [value for value in net_values if value < 0.0]
    eval_metrics = wave._simulate_signal_start_eval_attempt_metrics(outcomes)
    return {
        "trades": float(len(outcomes)),
        "net_usd": sum(net_values),
        "average_trade_usd": statistics.mean(net_values) if net_values else 0.0,
        "profit_factor": sum(positive) / abs(sum(negative)) if negative else 999.0,
        "max_drawdown_usd": wave._max_drawdown(net_values),
        "pass_rate": eval_metrics["pass_rate"],
        "two_day_rate": eval_metrics["two_trade_day_pass_rate"],
        "fail_rate": eval_metrics["fail_rate"],
    }


def _write_csv(path: str, rows: list[dict[str, object]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        output_path.write_text("", encoding="utf-8")
        return
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_report(
    path: str,
    *,
    bars: list[object],
    results: list[CandidateResult],
    benchmark_rows: list[dict[str, object]],
    configs: list[tuple[int, int]],
) -> None:
    lines = [
        "# MNQ Eval-Pass Wave Rider Deep Search",
        "",
        "Status: focused offline research only; not implementation-ready.",
        "",
        "## Source",
        "",
        f"- rows: `{len(bars)}`",
        f"- dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        f"- unique dates: `{len({bar.trade_date for bar in bars})}`",
        "- instrument: `MNQ`, point value `$2`, tick value `$0.50`",
        "- cost model: `$0.50/side` commission plus `1` total slippage tick per contract",
        "",
        "## Search Expansion",
        "",
        "- family: lookback breakout continuation",
        "- entry starts: `09:45`, `10:00`, `10:15`",
        "- entry ends: `12:00`, `12:30`, `13:00`",
        "- lookbacks: `30`, `40`, `50`, `60` bars",
        "- buffers: `0`, `2.5` points",
        "- delta thresholds: `400`, `600`, `800`",
        "- close-location thresholds: `0.50`, `0.55`, `0.60`",
        "- filters: abs-delta, bar-range, lookback-move, and VWAP-distance caps",
        "- risk profiles: `4` to `15` MNQ, eval-sized targets/stops",
        "",
        "## Top Robust Rows",
        "",
        "| Rank | Qty | Target | Stop | Trades | Latest-Year Net | Full Net | "
        "Max DD | Worst Q | Signal Pass | 2-Day | Fail | Strategy |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | "
        "---: | ---: | ---: | --- |",
    ]
    for rank, result in enumerate(results[:15], start=1):
        row = result.row
        lines.append(
            "| "
            f"{rank} | {row['quantity']} | {row['target_net_usd']} | "
            f"{row['stop_net_usd']} | {row['evaluated_trades']} | "
            f"{row['latest_year_net_usd']} | {row['net_usd']} | "
            f"{row['max_trade_sequence_drawdown_usd']} | "
            f"{row['worst_quarter_net_usd']} | "
            f"{float(row['signal_start_pass_rate']) * 100:.1f}% | "
            f"{float(row['signal_start_two_trade_day_pass_rate']) * 100:.1f}% | "
            f"{float(row['signal_start_fail_rate']) * 100:.1f}% | "
            f"`{row['strategy_id']}` |"
        )

    fastest = sorted(
        results,
        key=lambda result: (
            -float(result.row["signal_start_two_trade_day_pass_rate"]),
            float(result.row["signal_start_fail_rate"]),
            -float(result.row["signal_start_pass_rate"]),
        ),
    )
    lines.extend(
        [
            "",
            "## Fastest Two-Day Rows",
            "",
            "| Rank | Qty | Target | Stop | Trades | Latest-Year Net | Signal Pass | "
            "2-Day | Fail | Strategy |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ],
    )
    for rank, result in enumerate(fastest[:12], start=1):
        row = result.row
        lines.append(
            "| "
            f"{rank} | {row['quantity']} | {row['target_net_usd']} | "
            f"{row['stop_net_usd']} | {row['evaluated_trades']} | "
            f"{row['latest_year_net_usd']} | "
            f"{float(row['signal_start_pass_rate']) * 100:.1f}% | "
            f"{float(row['signal_start_two_trade_day_pass_rate']) * 100:.1f}% | "
            f"{float(row['signal_start_fail_rate']) * 100:.1f}% | "
            f"`{row['strategy_id']}` |"
        )

    lines.extend(
        [
            "",
            "## Fixed-Candidate Holdout Benchmarks",
            "",
            "These rows freeze each top candidate and evaluate the same rolling holdout "
            f"windows: `{', '.join(f'{a}x{b}' for a, b in configs)}`.",
            "",
            "| Candidate | Config | Trades | Net | Avg | PF | Max DD | Pos Windows | "
            "Neg Windows | Signal Pass | 2-Day | Fail |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | "
            "---: | ---: |",
        ],
    )
    for index, row in enumerate(benchmark_rows[:45], start=1):
        candidate_name = f"#{math.ceil(index / len(configs))}"
        lines.append(
            "| "
            f"{candidate_name} `{row['quantity']}/{row['target_net_usd']}/"
            f"{row['stop_net_usd']}` | {row['config']} | {row['trades']} | "
            f"{row['net_usd']} | {row['average_trade_usd']} | "
            f"{row['profit_factor']} | {row['max_drawdown_usd']} | "
            f"{row['positive_windows']} | {row['negative_windows']} | "
            f"{float(row['signal_start_pass_rate']) * 100:.1f}% | "
            f"{float(row['signal_start_two_trade_day_pass_rate']) * 100:.1f}% | "
            f"{float(row['signal_start_fail_rate']) * 100:.1f}% |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This pass searches around the current best family rather than replacing "
            "the original broader script. It is intended to find better frozen "
            "candidate shapes before any replay/mechanics work.",
            "",
            "Rows are ranked first by lower eval-fail rate, then faster two-day "
            "pass rate, then pass rate, latest-year net, drawdown, worst-quarter "
            "behavior, stop size, and average trade.",
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
        return "0"
    formatted = f"{value:.8f}".rstrip("0").rstrip(".")
    return formatted if formatted else "0"


if __name__ == "__main__":
    raise SystemExit(main())
