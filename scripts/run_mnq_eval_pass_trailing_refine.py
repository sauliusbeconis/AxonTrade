#!/usr/bin/env python3
"""Refine MNQ eval-pass candidates with trailing drawdown semantics."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import math
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, time
from pathlib import Path


DEFAULT_OUTPUT = "reports/mnq-eval-pass-wave-rider-trailing-refine.csv"
DEFAULT_REPORT = "reports/mnq-eval-pass-wave-rider-trailing-refine.md"
PROFIT_TARGET_USD = 1250.0
MAX_TRAILING_DRAWDOWN_USD = 1000.0
CONSISTENCY_FRACTION = 0.50
MAX_EVAL_CALENDAR_DAYS = 30
MAX_EVAL_TRADE_DAYS = 12


@dataclass(frozen=True)
class CandidateResult:
    row: dict[str, object]
    outcomes: list[object]
    risk: object
    signals: list[object]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run MNQ cadence refinement under eval trailing drawdown.",
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
    cadence = _load_module(
        "run_mnq_eval_pass_cadence_refine.py",
        "mnq_eval_pass_cadence_refine",
    )
    refine = _load_module(
        "run_mnq_eval_pass_wave_rider_new_lead_refine.py",
        "mnq_eval_pass_wave_rider_new_lead_refine",
    )

    input_path = args.input or wave.DEFAULT_INPUT
    bars = wave._load_feature_bars(input_path)
    bars_by_date = wave._bars_by_date(bars)
    trade_dates = sorted(bars_by_date)
    rows_by_index = wave._rows_by_global_index(bars_by_date)
    base_signals = deep._lookback_breakout_signals(
        wave,
        bars_by_date,
        strategy_id="cadence_trailing_base:lb10:buf0:delta300:cl0.55:start1000:end1230",
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
        cadence._signal_context_features(
            wave,
            signal,
            bars_by_date=bars_by_date,
            rows_by_index=rows_by_index,
            lookback_bars=10,
        )
        for signal in base_signals
    ]
    filter_specs = _selected_filter_specs(cadence)
    risks = _dense_risk_grid(deep, wave)
    results = _run_search(
        wave,
        bars_by_date,
        trade_dates=trade_dates,
        base_signals=base_signals,
        features=features,
        filter_specs=filter_specs,
        risks=risks,
    )
    results.sort(key=_ranking_key)
    _write_csv(args.output, [result.row for result in results])
    best = results[0] if results else None
    stress_rows = (
        _slippage_stress_rows(refine, wave, bars_by_date, trade_dates, best)
        if best is not None
        else []
    )
    holdout_rows = _holdout_rows(wave, trade_dates, best.outcomes) if best is not None else []
    _write_report(
        args.report_output,
        bars=bars,
        base_signals=base_signals,
        results=results,
        stress_rows=stress_rows,
        holdout_rows=holdout_rows,
    )
    best_summary = "none"
    if best is not None:
        row = best.row
        best_summary = (
            f"{row['strategy_id']} qty={row['quantity']} "
            f"target={row['target_net_usd']} stop={row['stop_net_usd']} "
            f"trail_pass={float(row['trailing_calendar_pass_rate']):.3f} "
            f"trail_fail={float(row['trailing_calendar_fail_rate']):.3f}"
        )
    print(
        f"wrote {len(results)} MNQ trailing-refine rows to {args.output}; "
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


def _selected_filter_specs(cadence) -> list[object]:
    selected_ids = {
        "no_thu_fri:short:1000_1230:none",
        "no_thu_fri:short:1000_1130:none",
        "no_thu_fri:short:1000_1230:move125_bar60",
        "tue_wed:short:1000_1230:none",
        "tue_wed:short:1000_1130:none",
        "tue_wed:both:1000_1045:none",
        "tue_wed:both:1000_1230:move_le125",
        "tue_wed:both:1000_1045:vwap_le100",
    }
    return [
        filter_spec for filter_spec in cadence._filter_specs()
        if filter_spec.filter_id in selected_ids
    ]


def _dense_risk_grid(deep, wave) -> list[object]:
    risks = []
    seen: set[tuple[object, ...]] = set()
    for quantity in (2, 3, 4, 5, 6, 8):
        for target_usd in (300, 325, 350, 375, 400, 425, 450, 475, 500, 550, 600, 650):
            for stop_usd in (300, 350, 400, 450, 500, 550, 600, 650, 700, 750, 800):
                try:
                    risk = deep._make_risk_profile(
                        wave,
                        quantity,
                        float(target_usd),
                        float(stop_usd),
                    )
                except ValueError:
                    continue
                if risk.stop_net_usd > 900.0:
                    continue
                key = (
                    risk.quantity,
                    round(risk.target_net_usd, 8),
                    round(risk.stop_net_usd, 8),
                    round(risk.target_points, 8),
                    round(risk.stop_points, 8),
                )
                if key in seen:
                    continue
                seen.add(key)
                risks.append(risk)
    return risks


def _run_search(
    wave,
    bars_by_date: dict[date, list[object]],
    *,
    trade_dates: list[date],
    base_signals: list[object],
    features: list[dict[str, object]],
    filter_specs: list[object],
    risks: list[object],
) -> list[CandidateResult]:
    results = []
    for filter_spec in filter_specs:
        strategy_id = f"cadence_trailing:{filter_spec.filter_id}"
        signals = [
            wave.Signal(
                strategy_id,
                signal.direction,
                signal.bar,
                f"{signal.notes}; trailing filter {filter_spec.filter_id}",
            )
            for signal, feature in zip(base_signals, features)
            if filter_spec.keep_signal(feature)
        ]
        if len(signals) < 50:
            continue
        for risk in risks:
            outcomes = wave._evaluate_signals(signals, bars_by_date, risk)
            fixed_row = wave._sweep_row(
                strategy_id,
                "mnq_cadence_trailing_refine",
                outcomes,
                risk,
                bars_by_date,
            )
            if (
                float(fixed_row["net_usd"]) <= 0.0
                or float(fixed_row["latest_year_net_usd"]) <= 0.0
            ):
                continue
            calendar_metrics = _simulate_trailing_calendar_attempts(outcomes, trade_dates)
            signal_metrics = _simulate_trailing_signal_attempts(outcomes)
            row = {
                **fixed_row,
                **_prefixed("trailing_calendar", calendar_metrics),
                **_prefixed("trailing_signal", signal_metrics),
            }
            results.append(CandidateResult(row, outcomes, risk, signals))
    return results


def _simulate_trailing_calendar_attempts(
    outcomes: list[object],
    trade_dates: list[date],
    *,
    horizon_days: int = MAX_EVAL_CALENDAR_DAYS,
    max_trade_days: int = MAX_EVAL_TRADE_DAYS,
) -> dict[str, float]:
    outcomes_by_date = {outcome.entry_time.date(): outcome for outcome in outcomes}
    attempt_results = []
    for start_index, start_date in enumerate(trade_dates):
        ordered_outcomes = []
        for current_date in trade_dates[start_index:]:
            if (current_date - start_date).days > horizon_days:
                break
            outcome = outcomes_by_date.get(current_date)
            if outcome is not None:
                ordered_outcomes.append(outcome)
        attempt_results.append(
            _simulate_one_trailing_attempt(
                ordered_outcomes[:max_trade_days],
                start_date=start_date,
            ),
        )
    return _summarize_attempts(attempt_results)


def _simulate_trailing_signal_attempts(
    outcomes: list[object],
    *,
    max_trade_days: int = MAX_EVAL_TRADE_DAYS,
) -> dict[str, float]:
    ordered_outcomes = sorted(outcomes, key=lambda outcome: outcome.entry_time)
    attempt_results = [
        _simulate_one_trailing_attempt(
            ordered_outcomes[start_index:start_index + max_trade_days],
            start_date=start_outcome.entry_time.date(),
        )
        for start_index, start_outcome in enumerate(ordered_outcomes)
    ]
    return _summarize_attempts(attempt_results)


def _simulate_one_trailing_attempt(
    outcomes: list[object],
    *,
    start_date: date,
) -> dict[str, object]:
    equity = 0.0
    high_water = 0.0
    largest_day = 0.0
    trade_days = 0
    status = "timeout"
    end_date = start_date
    failed_after_profit = False
    for outcome in outcomes:
        trade_days += 1
        equity += outcome.net_usd
        largest_day = max(largest_day, outcome.net_usd)
        high_water = max(high_water, equity)
        floor = min(0.0, high_water - MAX_TRAILING_DRAWDOWN_USD)
        end_date = outcome.entry_time.date()
        if equity <= floor + 0.01:
            status = "failed"
            failed_after_profit = high_water > 0.0
            break
        if (
            trade_days >= 2
            and equity >= PROFIT_TARGET_USD - 0.01
            and largest_day <= equity * CONSISTENCY_FRACTION + 0.01
        ):
            status = "passed"
            break
    return {
        "status": status,
        "equity": equity,
        "trade_days": float(trade_days),
        "calendar_days": float((end_date - start_date).days + 1),
        "failed_after_profit": failed_after_profit,
    }


def _summarize_attempts(attempts: list[dict[str, object]]) -> dict[str, float]:
    if not attempts:
        return {
            "attempts": 0.0,
            "pass_rate": 0.0,
            "fail_rate": 0.0,
            "timeout_rate": 0.0,
            "median_calendar_days_to_pass": 0.0,
            "median_trade_days_to_pass": 0.0,
            "fail_after_profit_count": 0.0,
            "worst_attempt_equity": 0.0,
        }
    passed = [attempt for attempt in attempts if attempt["status"] == "passed"]
    failed = [attempt for attempt in attempts if attempt["status"] == "failed"]
    timed_out = [attempt for attempt in attempts if attempt["status"] == "timeout"]
    return {
        "attempts": float(len(attempts)),
        "pass_rate": len(passed) / len(attempts),
        "fail_rate": len(failed) / len(attempts),
        "timeout_rate": len(timed_out) / len(attempts),
        "median_calendar_days_to_pass": (
            statistics.median(float(attempt["calendar_days"]) for attempt in passed)
            if passed
            else 0.0
        ),
        "median_trade_days_to_pass": (
            statistics.median(float(attempt["trade_days"]) for attempt in passed)
            if passed
            else 0.0
        ),
        "fail_after_profit_count": float(
            sum(bool(attempt["failed_after_profit"]) for attempt in failed),
        ),
        "worst_attempt_equity": min(float(attempt["equity"]) for attempt in attempts),
    }


def _prefixed(prefix: str, values: dict[str, float]) -> dict[str, object]:
    return {f"{prefix}_{key}": _format_number(value) for key, value in values.items()}


def _ranking_key(result: CandidateResult) -> tuple[float, ...]:
    row = result.row
    calendar_pass = float(row["trailing_calendar_pass_rate"])
    calendar_fail = float(row["trailing_calendar_fail_rate"])
    signal_fail = float(row["trailing_signal_fail_rate"])
    signal_pass = float(row["trailing_signal_pass_rate"])
    strict_penalty = (
        0.0
        if calendar_pass >= 0.30 and calendar_fail <= 0.08 and signal_fail <= 0.18
        else 1.0
    )
    return (
        strict_penalty,
        -calendar_pass,
        calendar_fail,
        signal_fail,
        -signal_pass,
        -float(row["latest_year_net_usd"]),
        abs(float(row["max_trade_sequence_drawdown_usd"])),
    )


def _slippage_stress_rows(
    refine,
    wave,
    bars_by_date: dict[date, list[object]],
    trade_dates: list[date],
    result: CandidateResult,
) -> list[dict[str, object]]:
    rows = []
    for slippage_ticks in (1.0, 2.0, 3.0, 4.0, 5.0, 6.0):
        risk = refine._risk_with_slippage(wave, result.risk, slippage_ticks)
        outcomes = wave._evaluate_signals(result.signals, bars_by_date, risk)
        fixed_row = wave._sweep_row(
            result.row["strategy_id"],
            "mnq_cadence_trailing_refine",
            outcomes,
            risk,
            bars_by_date,
        )
        calendar_metrics = _simulate_trailing_calendar_attempts(outcomes, trade_dates)
        signal_metrics = _simulate_trailing_signal_attempts(outcomes)
        rows.append(
            {
                "slippage_ticks": _format_number(slippage_ticks),
                "target_net_usd": _format_number(risk.target_net_usd),
                "stop_net_usd": _format_number(risk.stop_net_usd),
                "net_usd": fixed_row["net_usd"],
                "latest_year_net_usd": fixed_row["latest_year_net_usd"],
                "calendar_pass_rate": _format_number(calendar_metrics["pass_rate"]),
                "calendar_fail_rate": _format_number(calendar_metrics["fail_rate"]),
                "signal_pass_rate": _format_number(signal_metrics["pass_rate"]),
                "signal_fail_rate": _format_number(signal_metrics["fail_rate"]),
            },
        )
    return rows


def _holdout_rows(
    wave,
    trade_dates: list[date],
    outcomes: list[object],
) -> list[dict[str, object]]:
    rows = []
    for train_count, holdout_count in ((120, 40), (180, 40), (240, 60)):
        windows = []
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
                outcome for outcome in outcomes
                if outcome.entry_time.date() in holdout_dates
            ]
            windows.append(sum(outcome.net_usd for outcome in window_outcomes))
            holdout_outcomes.extend(window_outcomes)
        signal_metrics = _simulate_trailing_signal_attempts(holdout_outcomes)
        values = [outcome.net_usd for outcome in holdout_outcomes]
        rows.append(
            {
                "window": f"{train_count}x{holdout_count}",
                "windows": len(windows),
                "positive_windows": sum(value > 0.0 for value in windows),
                "negative_windows": sum(value < 0.0 for value in windows),
                "net_usd": _format_number(sum(windows)),
                "worst_window_usd": _format_number(min(windows) if windows else 0.0),
                "trades": len(holdout_outcomes),
                "max_drawdown_usd": _format_number(wave._max_drawdown(values)),
                "signal_pass_rate": _format_number(signal_metrics["pass_rate"]),
                "signal_fail_rate": _format_number(signal_metrics["fail_rate"]),
            },
        )
    return rows


def _write_csv(path: str, rows: list[dict[str, object]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        if not rows:
            handle.write("")
            return
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_report(
    path: str,
    *,
    bars: list[object],
    base_signals: list[object],
    results: list[CandidateResult],
    stress_rows: list[dict[str, object]],
    holdout_rows: list[dict[str, object]],
) -> None:
    strict_rows = [
        result for result in results
        if float(result.row["trailing_calendar_pass_rate"]) >= 0.30
        and float(result.row["trailing_calendar_fail_rate"]) <= 0.08
        and float(result.row["trailing_signal_fail_rate"]) <= 0.18
        and int(result.row["evaluated_trades"]) >= 75
    ]
    top_rows = results[:15]
    best = results[0] if results else None
    lines = [
        "# MNQ Eval-Pass Wave Rider Trailing Refinement",
        "",
        "Status: trailing-drawdown refinement for the faster MNQ B setup.",
        "",
        "## Source",
        "",
        f"- rows: `{len(bars)}`",
        f"- dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        f"- unique dates: `{len({bar.trade_date for bar in bars})}`",
        f"- base signals: `{len(base_signals)}`",
        "- trailing floor: `min(0, high_water - 1000)`",
        "- pass target: `$1250` with `50%` consistency",
        "- calendar attempts use a `30` calendar-day horizon and `12` max trade days",
        "",
        "## Best Trailing-Aware Row",
        "",
    ]
    if best is None:
        lines.append("No rows were generated.")
    else:
        row = best.row
        lines.extend(
            [
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Strategy | `{row['strategy_id']}` |",
                f"| Quantity | `{row['quantity']}` MNQ |",
                f"| Target / stop | `${row['target_net_usd']} / ${row['stop_net_usd']}` |",
                f"| Target / stop points | `{row['target_points']} / {row['stop_points']}` |",
                f"| Trades | `{row['evaluated_trades']}` |",
                f"| Full-sample net | `${row['net_usd']}` |",
                f"| Latest-year net | `${row['latest_year_net_usd']}` |",
                f"| Worst quarter | `${row['worst_quarter_net_usd']}` |",
                f"| Trade-sequence max DD | `${row['max_trade_sequence_drawdown_usd']}` |",
                f"| Fixed calendar pass / fail | `{float(row['pass_rate']) * 100:.1f}% / {float(row['fail_rate']) * 100:.1f}%` |",
                f"| Trailing calendar pass / fail / timeout | `{float(row['trailing_calendar_pass_rate']) * 100:.1f}% / {float(row['trailing_calendar_fail_rate']) * 100:.1f}% / {float(row['trailing_calendar_timeout_rate']) * 100:.1f}%` |",
                f"| Trailing signal pass / fail / timeout | `{float(row['trailing_signal_pass_rate']) * 100:.1f}% / {float(row['trailing_signal_fail_rate']) * 100:.1f}% / {float(row['trailing_signal_timeout_rate']) * 100:.1f}%` |",
                f"| Trailing median pass time | `{row['trailing_calendar_median_calendar_days_to_pass']}` calendar days, `{row['trailing_calendar_median_trade_days_to_pass']}` trade days |",
                "",
            ],
        )
    lines.extend(
        [
            "## Strict Rows",
            "",
            "Rows shown here have trailing calendar pass `>=30%`, trailing calendar "
            "fail `<=8%`, trailing signal fail `<=18%`, and at least `75` trades.",
            "",
            "| Rank | Qty | Target | Stop | Trades | Latest Net | Trail Cal Pass | Trail Cal Fail | Trail Sig Pass | Trail Sig Fail | DD | Worst Q | Strategy |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ],
    )
    for rank, result in enumerate(strict_rows[:12], start=1):
        lines.append(_result_row(rank, result.row))
    lines.extend(
        [
            "",
            "## Top Ranked Rows",
            "",
            "| Rank | Qty | Target | Stop | Trades | Latest Net | Trail Cal Pass | Trail Cal Fail | Trail Sig Pass | Trail Sig Fail | DD | Worst Q | Strategy |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ],
    )
    for rank, result in enumerate(top_rows[:12], start=1):
        lines.append(_result_row(rank, result.row))
    lines.extend(
        [
            "",
            "## Best Row Slippage Stress",
            "",
            "| Slip Ticks | Target | Stop | Net | Latest Net | Trail Cal Pass | Trail Cal Fail | Trail Sig Pass | Trail Sig Fail |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    for row in stress_rows:
        lines.append(
            "| "
            f"{row['slippage_ticks']} | {row['target_net_usd']} | {row['stop_net_usd']} | "
            f"{row['net_usd']} | {row['latest_year_net_usd']} | "
            f"{float(row['calendar_pass_rate']) * 100:.1f}% | "
            f"{float(row['calendar_fail_rate']) * 100:.1f}% | "
            f"{float(row['signal_pass_rate']) * 100:.1f}% | "
            f"{float(row['signal_fail_rate']) * 100:.1f}% |"
        )
    lines.extend(
        [
            "",
            "## Best Row Rolling Holdout",
            "",
            "| Window | Windows | Positive | Negative | Net | Worst Window | Trades | Max DD | Trail Sig Pass | Trail Sig Fail |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    for row in holdout_rows:
        lines.append(
            "| "
            f"{row['window']} | {row['windows']} | {row['positive_windows']} | "
            f"{row['negative_windows']} | {row['net_usd']} | "
            f"{row['worst_window_usd']} | {row['trades']} | "
            f"{row['max_drawdown_usd']} | "
            f"{float(row['signal_pass_rate']) * 100:.1f}% | "
            f"{float(row['signal_fail_rate']) * 100:.1f}% |"
        )
    if best is not None:
        _append_breakdowns(lines, best.outcomes)
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The faster B setup improved materially after optimizing against trailing "
            "drawdown instead of fixed loss. The best row is a Tuesday/Wednesday "
            "short-only setup with a larger target than stop, so two winning days "
            "can satisfy the eval objective while a stopped trade remains below "
            "half the max-loss limit.",
            "",
            "This is still not implementation-ready. It has only `86` trades, one "
            "negative rolling holdout window in the `120x40` view, and a negative "
            "`2025 Q2` quarter. It should be treated as the best B research lead, "
            "not a bot build instruction.",
            "",
        ],
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def _result_row(rank: int, row: dict[str, object]) -> str:
    return (
        "| "
        f"{rank} | {row['quantity']} | {row['target_net_usd']} | "
        f"{row['stop_net_usd']} | {row['evaluated_trades']} | "
        f"{row['latest_year_net_usd']} | "
        f"{float(row['trailing_calendar_pass_rate']) * 100:.1f}% | "
        f"{float(row['trailing_calendar_fail_rate']) * 100:.1f}% | "
        f"{float(row['trailing_signal_pass_rate']) * 100:.1f}% | "
        f"{float(row['trailing_signal_fail_rate']) * 100:.1f}% | "
        f"{row['max_trade_sequence_drawdown_usd']} | "
        f"{row['worst_quarter_net_usd']} | "
        f"`{row['strategy_id']}` |"
    )


def _append_breakdowns(lines: list[str], outcomes: list[object]) -> None:
    for title, key_function in (
        ("Year", lambda outcome: outcome.entry_time.year),
        (
            "Quarter",
            lambda outcome: (
                outcome.entry_time.year,
                (outcome.entry_time.month - 1) // 3 + 1,
            ),
        ),
        ("Weekday", lambda outcome: outcome.entry_time.strftime("%a")),
    ):
        net_by_key: dict[object, float] = defaultdict(float)
        count_by_key: Counter[object] = Counter()
        wins_by_key: Counter[object] = Counter()
        losses_by_key: Counter[object] = Counter()
        for outcome in outcomes:
            key = key_function(outcome)
            net_by_key[key] += outcome.net_usd
            count_by_key[key] += 1
            wins_by_key[key] += outcome.net_usd > 0.0
            losses_by_key[key] += outcome.net_usd < 0.0
        lines.extend(
            [
                "",
                f"Best row {title.lower()} breakdown:",
                "",
                "| Bucket | Trades | Net | Wins | Losses |",
                "| --- | ---: | ---: | ---: | ---: |",
            ],
        )
        for key in sorted(count_by_key):
            lines.append(
                "| "
                f"{key} | {count_by_key[key]} | {_format_number(net_by_key[key])} | "
                f"{wins_by_key[key]} | {losses_by_key[key]} |"
            )


def _format_number(value: float) -> str:
    if not math.isfinite(value):
        return "0"
    formatted = f"{value:.8f}".rstrip("0").rstrip(".")
    return formatted if formatted else "0"


if __name__ == "__main__":
    raise SystemExit(main())
