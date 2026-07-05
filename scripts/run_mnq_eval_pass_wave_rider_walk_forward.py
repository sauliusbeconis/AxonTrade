#!/usr/bin/env python3
"""Run walk-forward validation for MNQ eval-pass wave-rider candidates."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import math
import statistics
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable


DEFAULT_DETAIL_OUTPUT = "reports/mnq-eval-pass-wave-rider-walk-forward.csv"
DEFAULT_REPORT_OUTPUT = "reports/mnq-eval-pass-wave-rider-walk-forward.md"
DEFAULT_TRAIN_DATE_COUNTS = "120,180,240"
DEFAULT_HOLDOUT_DATE_COUNTS = "40,40,60"
BENCHMARK_CANDIDATES = [
    (
        "new_practical_10mnq_650_650",
        "lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri1:"
        "filterabsdelta1000",
        10,
        650.0,
        650.0,
    ),
    (
        "new_best_10mnq_625_650",
        "lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri1:"
        "filterabsdelta1000",
        10,
        625.0,
        650.0,
    ),
    (
        "new_practical_5mnq_650_650",
        "lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri0:"
        "filterabsdelta1000",
        5,
        650.0,
        650.0,
    ),
    (
        "new_balanced_5mnq_625_650",
        "lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri0:"
        "filterabsdelta1000",
        5,
        625.0,
        650.0,
    ),
    (
        "new_fast_12mnq_702_798",
        "lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri0:"
        "filterabsdelta1000",
        12,
        702.0,
        798.0,
    ),
    (
        "old_balanced_5mnq_650_800",
        "lookback_breakout:lb10:buf0:delta600:cl0.55:end1230:skipfri0:"
        "filterabsdelta1172_lbmove103_75",
        5,
        650.0,
        800.0,
    ),
    (
        "old_balanced_5mnq_625_800",
        "lookback_breakout:lb10:buf0:delta600:cl0.55:end1230:skipfri0:"
        "filterabsdelta1172_lbmove103_75",
        5,
        625.0,
        800.0,
    ),
    (
        "old_fast_12mnq_702_798",
        "lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri0:"
        "filterabsdelta1172",
        12,
        702.0,
        798.0,
    ),
    (
        "old_lower_stop_10mnq_650_650",
        "lookback_breakout:lb40:buf0:delta600:cl0.55:end1230:skipfri0:"
        "filterabsdelta1172",
        10,
        650.0,
        650.0,
    ),
]

HEADER = [
    "schema_version",
    "config",
    "window",
    "sample",
    "start_date",
    "end_date",
    "selected_strategy_id",
    "quantity",
    "target_net_usd",
    "stop_net_usd",
    "target_points",
    "stop_points",
    "evaluated_trades",
    "win_rate",
    "net_usd",
    "average_trade_usd",
    "profit_factor",
    "max_drawdown_usd",
    "worst_trade_usd",
    "target_hits",
    "stop_hits",
    "eod_exits",
    "signal_start_pass_rate",
    "signal_start_two_trade_day_pass_rate",
    "signal_start_fail_rate",
    "signal_start_timeout_rate",
    "signal_start_median_calendar_days_to_pass",
    "signal_start_median_trade_days_to_pass",
    "selected_on_train",
]


@dataclass(frozen=True)
class Candidate:
    strategy_id: str
    quantity: int
    target_net_usd: float
    stop_net_usd: float
    target_points: float
    stop_points: float
    outcomes: list[object]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run MNQ eval-pass wave-rider walk-forward validation.",
    )
    parser.add_argument("input", nargs="?", help="MNQ Sierra orderflow export path.")
    parser.add_argument("--detail-output", default=DEFAULT_DETAIL_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--symbol", default="MNQU26-CME")
    parser.add_argument("--minimum-signal-days", type=int, default=40)
    parser.add_argument("--minimum-train-trades", type=int, default=12)
    parser.add_argument("--train-date-counts", default=DEFAULT_TRAIN_DATE_COUNTS)
    parser.add_argument("--holdout-date-counts", default=DEFAULT_HOLDOUT_DATE_COUNTS)
    parser.add_argument(
        "--maximum-quantity",
        type=int,
        default=12,
        help="Maximum MNQ quantity allowed in the selected candidate family.",
    )
    args = parser.parse_args()

    wave = _load_wave_module()
    input_path = args.input or wave.DEFAULT_INPUT
    bars = wave._load_feature_bars(input_path)
    bars_by_date = wave._bars_by_date(bars)
    candidates = _build_candidates(
        wave,
        bars_by_date,
        symbol=args.symbol,
        minimum_signal_days=args.minimum_signal_days,
        maximum_quantity=args.maximum_quantity,
    )
    configs = _parse_configs(args.train_date_counts, args.holdout_date_counts)
    rows = []
    selected_holdout_outcomes_by_config: dict[str, list[object]] = {}
    for train_count, holdout_count in configs:
        config_id = f"{train_count}x{holdout_count}"
        config_rows, holdout_outcomes = _run_walk_forward_config(
            wave,
            candidates,
            trade_dates=sorted(bars_by_date),
            train_date_count=train_count,
            holdout_date_count=holdout_count,
            minimum_train_trades=args.minimum_train_trades,
            config_id=config_id,
        )
        rows.extend(config_rows)
        selected_holdout_outcomes_by_config[config_id] = holdout_outcomes

    _write_csv(args.detail_output, rows)
    _write_report(
        args.report_output,
        bars=bars,
        rows=rows,
        holdout_outcomes_by_config=selected_holdout_outcomes_by_config,
        benchmark_rows=_benchmark_rows(candidates, sorted(bars_by_date), configs),
        minimum_train_trades=args.minimum_train_trades,
        maximum_quantity=args.maximum_quantity,
    )

    holdout_rows = [row for row in rows if row["sample"] == "holdout"]
    holdout_net = sum(float(row["net_usd"]) for row in holdout_rows)
    holdout_trades = sum(int(row["evaluated_trades"]) for row in holdout_rows)
    print(
        f"wrote {len(rows)} MNQ eval-pass walk-forward rows to {args.detail_output}; "
        f"holdout_windows={len(holdout_rows)}, "
        f"holdout_trades={holdout_trades}, holdout_net={holdout_net:.2f}",
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


def _build_candidates(
    wave,
    bars_by_date: dict[date, list[object]],
    *,
    symbol: str,
    minimum_signal_days: int,
    maximum_quantity: int,
) -> list[Candidate]:
    raw_signals = wave._generate_strategy_signals(bars_by_date, symbol=symbol)
    signals_by_strategy = wave._with_filtered_signal_variants(raw_signals, bars_by_date)
    risk_profiles = [
        risk for risk in wave._risk_profiles()
        if risk.quantity <= maximum_quantity
    ]
    candidates = []
    for strategy_id, signals in signals_by_strategy.items():
        if not _strategy_is_eligible(strategy_id) or len(signals) < minimum_signal_days:
            continue
        for risk in risk_profiles:
            outcomes = wave._evaluate_signals(signals, bars_by_date, risk)
            candidates.append(
                Candidate(
                    strategy_id=strategy_id,
                    quantity=risk.quantity,
                    target_net_usd=risk.target_net_usd,
                    stop_net_usd=risk.stop_net_usd,
                    target_points=risk.target_points,
                    stop_points=risk.stop_points,
                    outcomes=outcomes,
                ),
            )
    return candidates


def _strategy_is_eligible(strategy_id: str) -> bool:
    return strategy_id.startswith("lookback_breakout:") and ":filter" in strategy_id


def _run_walk_forward_config(
    wave,
    candidates: list[Candidate],
    *,
    trade_dates: list[date],
    train_date_count: int,
    holdout_date_count: int,
    minimum_train_trades: int,
    config_id: str,
) -> tuple[list[dict[str, object]], list[object]]:
    rows = []
    selected_holdout_outcomes = []
    window = 0
    step = holdout_date_count
    max_start = len(trade_dates) - train_date_count - holdout_date_count
    for start_index in range(0, max_start + 1, step):
        window += 1
        train_dates = trade_dates[start_index:start_index + train_date_count]
        holdout_dates = trade_dates[
            start_index + train_date_count:
            start_index + train_date_count + holdout_date_count
        ]
        selected, train_outcomes = _select_candidate(
            wave,
            candidates,
            train_dates=set(train_dates),
            minimum_train_trades=minimum_train_trades,
        )
        holdout_outcomes = _outcomes_for_dates(selected.outcomes, set(holdout_dates))
        rows.append(
            _row(
                wave,
                config_id=config_id,
                window=window,
                sample="train",
                sample_dates=train_dates,
                candidate=selected,
                outcomes=train_outcomes,
                selected_on_train=True,
            ),
        )
        rows.append(
            _row(
                wave,
                config_id=config_id,
                window=window,
                sample="holdout",
                sample_dates=holdout_dates,
                candidate=selected,
                outcomes=holdout_outcomes,
                selected_on_train=True,
            ),
        )
        selected_holdout_outcomes.extend(holdout_outcomes)
    return rows, selected_holdout_outcomes


def _select_candidate(
    wave,
    candidates: list[Candidate],
    *,
    train_dates: set[date],
    minimum_train_trades: int,
) -> tuple[Candidate, list[object]]:
    selected_candidate: Candidate | None = None
    selected_outcomes: list[object] = []
    selected_key: tuple[float, ...] | None = None
    for candidate in candidates:
        outcomes = _outcomes_for_dates(candidate.outcomes, train_dates)
        metrics = _metrics(wave, outcomes)
        key = _selection_key(metrics, minimum_train_trades=minimum_train_trades)
        if selected_key is None or key < selected_key:
            selected_key = key
            selected_candidate = candidate
            selected_outcomes = outcomes
    if selected_candidate is None:
        raise RuntimeError("no eligible MNQ eval-pass candidates were generated")
    return selected_candidate, selected_outcomes


def _selection_key(metrics: dict[str, float], *, minimum_train_trades: int) -> tuple[float, ...]:
    sample_penalty = 0.0 if metrics["evaluated_trades"] >= minimum_train_trades else 1.0
    net_penalty = 0.0 if metrics["net_usd"] > 0.0 and metrics["average_trade_usd"] > 0.0 else 1.0
    return (
        sample_penalty,
        net_penalty,
        -metrics["signal_start_pass_rate"],
        metrics["signal_start_fail_rate"],
        -metrics["signal_start_two_trade_day_pass_rate"],
        -metrics["average_trade_usd"],
        -metrics["net_usd"],
    )


def _outcomes_for_dates(outcomes: list[object], trade_dates: set[date]) -> list[object]:
    return [
        outcome for outcome in outcomes
        if outcome.entry_time.date() in trade_dates
    ]


def _row(
    wave,
    *,
    config_id: str,
    window: int,
    sample: str,
    sample_dates: list[date],
    candidate: Candidate,
    outcomes: list[object],
    selected_on_train: bool,
) -> dict[str, object]:
    metrics = _metrics(wave, outcomes)
    return {
        "schema_version": 1,
        "config": config_id,
        "window": window,
        "sample": sample,
        "start_date": sample_dates[0].isoformat(),
        "end_date": sample_dates[-1].isoformat(),
        "selected_strategy_id": candidate.strategy_id,
        "quantity": candidate.quantity,
        "target_net_usd": _format_number(candidate.target_net_usd),
        "stop_net_usd": _format_number(candidate.stop_net_usd),
        "target_points": _format_number(candidate.target_points),
        "stop_points": _format_number(candidate.stop_points),
        "evaluated_trades": int(metrics["evaluated_trades"]),
        "win_rate": _format_number(metrics["win_rate"]),
        "net_usd": _format_number(metrics["net_usd"]),
        "average_trade_usd": _format_number(metrics["average_trade_usd"]),
        "profit_factor": _format_number(metrics["profit_factor"]),
        "max_drawdown_usd": _format_number(metrics["max_drawdown_usd"]),
        "worst_trade_usd": _format_number(metrics["worst_trade_usd"]),
        "target_hits": int(metrics["target_hits"]),
        "stop_hits": int(metrics["stop_hits"]),
        "eod_exits": int(metrics["eod_exits"]),
        "signal_start_pass_rate": _format_number(metrics["signal_start_pass_rate"]),
        "signal_start_two_trade_day_pass_rate": _format_number(
            metrics["signal_start_two_trade_day_pass_rate"],
        ),
        "signal_start_fail_rate": _format_number(metrics["signal_start_fail_rate"]),
        "signal_start_timeout_rate": _format_number(metrics["signal_start_timeout_rate"]),
        "signal_start_median_calendar_days_to_pass": _format_number(
            metrics["signal_start_median_calendar_days_to_pass"],
        ),
        "signal_start_median_trade_days_to_pass": _format_number(
            metrics["signal_start_median_trade_days_to_pass"],
        ),
        "selected_on_train": str(selected_on_train).lower(),
    }


def _metrics(wave, outcomes: list[object]) -> dict[str, float]:
    net_values = [outcome.net_usd for outcome in outcomes]
    positive = [value for value in net_values if value > 0.0]
    negative = [value for value in net_values if value < 0.0]
    eval_metrics = wave._simulate_signal_start_eval_attempt_metrics(outcomes)
    return {
        "evaluated_trades": float(len(outcomes)),
        "win_rate": len(positive) / len(outcomes) if outcomes else 0.0,
        "net_usd": sum(net_values),
        "average_trade_usd": statistics.mean(net_values) if net_values else 0.0,
        "profit_factor": sum(positive) / abs(sum(negative)) if negative else 999.0,
        "max_drawdown_usd": wave._max_drawdown(net_values),
        "worst_trade_usd": min(net_values) if net_values else 0.0,
        "target_hits": float(sum(outcome.exit_reason == "target_hit" for outcome in outcomes)),
        "stop_hits": float(sum(outcome.exit_reason == "stop_hit" for outcome in outcomes)),
        "eod_exits": float(sum(
            outcome.exit_reason in {"end_of_session", "no_following_bar"}
            for outcome in outcomes
        )),
        "signal_start_pass_rate": eval_metrics["pass_rate"],
        "signal_start_two_trade_day_pass_rate": eval_metrics["two_trade_day_pass_rate"],
        "signal_start_fail_rate": eval_metrics["fail_rate"],
        "signal_start_timeout_rate": eval_metrics["timeout_rate"],
        "signal_start_median_calendar_days_to_pass": (
            eval_metrics["median_calendar_days_to_pass"]
        ),
        "signal_start_median_trade_days_to_pass": eval_metrics["median_trade_days_to_pass"],
    }


def _write_csv(path: str, rows: Iterable[dict[str, object]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADER, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_report(
    report_output: str,
    *,
    bars: list[object],
    rows: list[dict[str, object]],
    holdout_outcomes_by_config: dict[str, list[object]],
    benchmark_rows: list[dict[str, object]],
    minimum_train_trades: int,
    maximum_quantity: int,
) -> None:
    holdout_rows = [row for row in rows if row["sample"] == "holdout"]
    lines = [
        "# MNQ Eval-Pass Wave Rider Walk-Forward",
        "",
        "Status: walk-forward validation for the filtered lookback-breakout MNQ "
        "eval-pass family.",
        "",
        "## Source",
        "",
        f"- rows: `{len(bars)}`",
        f"- dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        f"- unique dates: `{len({bar.trade_date for bar in bars})}`",
        f"- minimum training trades: `{minimum_train_trades}`",
        f"- maximum quantity in selection pool: `{maximum_quantity}` MNQ",
        "",
        "## Summary",
        "",
        "| Config | Windows | Holdout Trades | Holdout Net | Avg | PF | Max DD | "
        "Positive Windows | Negative Windows | Signal Pass | 2-Day | Signal Fail |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for config_id in sorted(holdout_outcomes_by_config):
        config_rows = [row for row in holdout_rows if row["config"] == config_id]
        outcomes = holdout_outcomes_by_config[config_id]
        summary = _aggregate_rows(config_rows, outcomes)
        lines.append(
            "| "
            f"{config_id} | {summary['windows']} | {summary['trades']} | "
            f"{_format_number(summary['net'])} | {_format_number(summary['average'])} | "
            f"{_format_number(summary['profit_factor'])} | {_format_number(summary['max_drawdown'])} | "
            f"{summary['positive_windows']} | {summary['negative_windows']} | "
            f"{summary['signal_pass_rate'] * 100:.1f}% | "
            f"{summary['signal_two_trade_day_pass_rate'] * 100:.1f}% | "
            f"{summary['signal_fail_rate'] * 100:.1f}% |"
        )

    lines.extend(
        [
            "",
            "## Locked Candidate Benchmarks",
            "",
            "These rows do not reselect parameters in each window. They freeze a candidate "
            "upfront and evaluate only the same chronological holdout slices used above.",
            "",
            "| Config | Candidate | Windows | Holdout Trades | Holdout Net | Avg | PF | Max DD | "
            "Positive Windows | Negative Windows | Signal Pass | 2-Day | Signal Fail |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    for row in benchmark_rows:
        lines.append(
            "| "
            f"{row['config']} | `{row['candidate']}` | {row['windows']} | "
            f"{row['trades']} | {row['net_usd']} | {row['average_trade_usd']} | "
            f"{row['profit_factor']} | {row['max_drawdown_usd']} | "
            f"{row['positive_windows']} | {row['negative_windows']} | "
            f"{float(row['signal_start_pass_rate']) * 100:.1f}% | "
            f"{float(row['signal_start_two_trade_day_pass_rate']) * 100:.1f}% | "
            f"{float(row['signal_start_fail_rate']) * 100:.1f}% |"
        )

    lines.extend(
        [
            "",
            "## Selected Candidate Counts",
            "",
            "| Config | Count | Qty | Target | Stop | Strategy |",
            "| --- | ---: | ---: | ---: | ---: | --- |",
        ],
    )
    for config_id in sorted({row["config"] for row in rows}):
        config_train_rows = [
            row for row in rows
            if row["config"] == config_id and row["sample"] == "train"
        ]
        counts = Counter(
            (
                row["selected_strategy_id"],
                row["quantity"],
                row["target_net_usd"],
                row["stop_net_usd"],
            )
            for row in config_train_rows
        )
        for (strategy_id, quantity, target, stop), count in counts.most_common(8):
            lines.append(
                f"| {config_id} | {count} | {quantity} | {target} | {stop} | "
                f"`{strategy_id}` |"
            )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This is a chronological selection test. Each window selects the best "
            "candidate on the training dates, then evaluates that exact candidate "
            "on the following holdout dates.",
            "",
            "The adaptive selection result is currently weaker than the locked candidate "
            "benchmarks. That means the next MNQ eval-pass path should freeze one "
            "candidate family instead of changing parameters window by window.",
            "",
            "A deployable eval-pass bot would need positive holdout behavior across "
            "multiple window sizes, reasonable selected-candidate stability, replay "
            "mechanics, and live chart data validation.",
            "",
        ],
    )
    Path(report_output).write_text("\n".join(lines), encoding="utf-8")


def _benchmark_rows(
    candidates: list[Candidate],
    trade_dates: list[date],
    configs: list[tuple[int, int]],
) -> list[dict[str, object]]:
    rows = []
    for candidate_name, strategy_id, quantity, target, stop in BENCHMARK_CANDIDATES:
        candidate = _find_candidate(candidates, strategy_id, quantity, target, stop)
        if candidate is None:
            continue
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
                window_outcomes = _outcomes_for_dates(candidate.outcomes, holdout_dates)
                holdout_windows.append(sum(outcome.net_usd for outcome in window_outcomes))
                holdout_outcomes.extend(window_outcomes)
            net_values = [outcome.net_usd for outcome in holdout_outcomes]
            positive = [value for value in net_values if value > 0.0]
            negative = [value for value in net_values if value < 0.0]
            signal_metrics = _signal_start_metrics(holdout_outcomes)
            rows.append(
                {
                    "config": config_id,
                    "candidate": candidate_name,
                    "windows": len(holdout_windows),
                    "trades": len(holdout_outcomes),
                    "net_usd": _format_number(sum(net_values)),
                    "average_trade_usd": _format_number(
                        statistics.mean(net_values) if net_values else 0.0,
                    ),
                    "profit_factor": _format_number(
                        sum(positive) / abs(sum(negative)) if negative else 999.0,
                    ),
                    "max_drawdown_usd": _format_number(_max_drawdown(net_values)),
                    "positive_windows": sum(value > 0.0 for value in holdout_windows),
                    "negative_windows": sum(value < 0.0 for value in holdout_windows),
                    "signal_start_pass_rate": _format_number(signal_metrics["pass_rate"]),
                    "signal_start_two_trade_day_pass_rate": _format_number(
                        signal_metrics["two_trade_day_pass_rate"],
                    ),
                    "signal_start_fail_rate": _format_number(signal_metrics["fail_rate"]),
                },
            )
    return rows


def _find_candidate(
    candidates: list[Candidate],
    strategy_id: str,
    quantity: int,
    target_net_usd: float,
    stop_net_usd: float,
) -> Candidate | None:
    for candidate in candidates:
        if (
            candidate.strategy_id == strategy_id
            and candidate.quantity == quantity
            and abs(candidate.target_net_usd - target_net_usd) < 0.01
            and abs(candidate.stop_net_usd - stop_net_usd) < 0.01
        ):
            return candidate
    return None


def _aggregate_rows(rows: list[dict[str, object]], outcomes: list[object]) -> dict[str, float]:
    net_values = [outcome.net_usd for outcome in outcomes]
    positive = [value for value in net_values if value > 0.0]
    negative = [value for value in net_values if value < 0.0]
    eval_metrics = _signal_start_metrics(outcomes)
    return {
        "windows": len(rows),
        "trades": len(outcomes),
        "net": sum(net_values),
        "average": statistics.mean(net_values) if net_values else 0.0,
        "profit_factor": sum(positive) / abs(sum(negative)) if negative else 999.0,
        "max_drawdown": _max_drawdown(net_values),
        "positive_windows": sum(float(row["net_usd"]) > 0.0 for row in rows),
        "negative_windows": sum(float(row["net_usd"]) < 0.0 for row in rows),
        "signal_pass_rate": eval_metrics["pass_rate"],
        "signal_two_trade_day_pass_rate": eval_metrics["two_trade_day_pass_rate"],
        "signal_fail_rate": eval_metrics["fail_rate"],
    }


def _signal_start_metrics(outcomes: list[object]) -> dict[str, float]:
    ordered_outcomes = sorted(outcomes, key=lambda outcome: outcome.entry_time)
    attempts = 0
    passed = 0
    failed = 0
    timed_out = 0
    two_trade_day_passes = 0
    for start_index, _start_outcome in enumerate(ordered_outcomes):
        attempts += 1
        equity = 0.0
        largest_day = 0.0
        trade_days = 0
        status = "timeout"
        for outcome in ordered_outcomes[start_index:start_index + 12]:
            trade_days += 1
            equity += outcome.net_usd
            largest_day = max(largest_day, outcome.net_usd)
            if equity <= -1000.0 - 0.01:
                status = "failed"
                break
            if (
                trade_days >= 2
                and equity >= 1250.0 - 0.01
                and largest_day <= equity * 0.50 + 0.01
            ):
                status = "passed"
                break
        if status == "passed":
            passed += 1
            if trade_days <= 2:
                two_trade_day_passes += 1
        elif status == "failed":
            failed += 1
        else:
            timed_out += 1
    if attempts == 0:
        return {
            "pass_rate": 0.0,
            "two_trade_day_pass_rate": 0.0,
            "fail_rate": 0.0,
            "timeout_rate": 0.0,
        }
    return {
        "pass_rate": passed / attempts,
        "two_trade_day_pass_rate": two_trade_day_passes / attempts,
        "fail_rate": failed / attempts,
        "timeout_rate": timed_out / attempts,
    }


def _max_drawdown(values: Iterable[float]) -> float:
    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_drawdown = min(max_drawdown, equity - peak)
    return max_drawdown


def _parse_configs(train_counts: str, holdout_counts: str) -> list[tuple[int, int]]:
    train_values = _parse_int_list(train_counts)
    holdout_values = _parse_int_list(holdout_counts)
    if len(train_values) != len(holdout_values):
        raise ValueError("train-date-counts and holdout-date-counts lengths must match")
    return list(zip(train_values, holdout_values))


def _parse_int_list(value: str) -> list[int]:
    values = [int(part.strip()) for part in value.split(",") if part.strip()]
    if not values or any(value <= 0 for value in values):
        raise ValueError("date-count lists must contain positive integers")
    return values


def _format_number(value: float) -> str:
    if not math.isfinite(value):
        return "0"
    formatted = f"{value:.8f}".rstrip("0").rstrip(".")
    return formatted if formatted else "0"


if __name__ == "__main__":
    raise SystemExit(main())
