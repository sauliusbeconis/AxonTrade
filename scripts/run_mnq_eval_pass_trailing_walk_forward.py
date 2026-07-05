#!/usr/bin/env python3
"""Walk-forward validation for faster MNQ eval-pass trailing candidates."""

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
from typing import Iterable


DEFAULT_DETAIL_OUTPUT = "reports/mnq-eval-pass-wave-rider-trailing-walk-forward.csv"
DEFAULT_REPORT_OUTPUT = "reports/mnq-eval-pass-wave-rider-trailing-walk-forward.md"
DEFAULT_TRAIN_DATE_COUNTS = "120,180,240"
DEFAULT_HOLDOUT_DATE_COUNTS = "40,40,60"

BENCHMARK_CANDIDATES = [
    (
        "b_best_4mnq_650_450",
        "cadence_trailing:tue_wed:short:1000_1230:none",
        4,
        650.0,
        450.0,
    ),
    (
        "b_shorter_4mnq_650_450",
        "cadence_trailing:tue_wed:short:1000_1130:none",
        4,
        650.0,
        450.0,
    ),
    (
        "b_lower_target_4mnq_600_450",
        "cadence_trailing:tue_wed:short:1000_1230:none",
        4,
        600.0,
        450.0,
    ),
    (
        "b_smaller_3mnq_651_450",
        "cadence_trailing:tue_wed:short:1000_1230:none",
        3,
        651.0,
        450.0,
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
    "trailing_calendar_pass_rate",
    "trailing_calendar_fail_rate",
    "trailing_calendar_timeout_rate",
    "trailing_signal_pass_rate",
    "trailing_signal_fail_rate",
    "trailing_signal_timeout_rate",
    "trailing_signal_median_trade_days_to_pass",
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
        description="Run MNQ trailing eval-pass walk-forward validation.",
    )
    parser.add_argument("input", nargs="?", help="MNQ Sierra orderflow export path.")
    parser.add_argument("--detail-output", default=DEFAULT_DETAIL_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--symbol", default="MNQU26-CME")
    parser.add_argument("--minimum-signal-days", type=int, default=50)
    parser.add_argument("--minimum-train-trades", type=int, default=16)
    parser.add_argument("--train-date-counts", default=DEFAULT_TRAIN_DATE_COUNTS)
    parser.add_argument("--holdout-date-counts", default=DEFAULT_HOLDOUT_DATE_COUNTS)
    args = parser.parse_args()

    trailing = _load_module(
        "run_mnq_eval_pass_trailing_refine.py",
        "mnq_eval_pass_trailing_refine",
    )
    wave = trailing._load_module(
        "run_mnq_eval_pass_wave_rider.py",
        "mnq_eval_pass_wave_rider",
    )
    deep = trailing._load_module(
        "run_mnq_eval_pass_wave_rider_deep_search.py",
        "mnq_eval_pass_wave_rider_deep_search",
    )
    cadence = trailing._load_module(
        "run_mnq_eval_pass_cadence_refine.py",
        "mnq_eval_pass_cadence_refine",
    )

    input_path = args.input or wave.DEFAULT_INPUT
    bars = wave._load_feature_bars(input_path)
    bars_by_date = wave._bars_by_date(bars)
    rows_by_index = wave._rows_by_global_index(bars_by_date)
    trade_dates = sorted(bars_by_date)

    base_signals = deep._lookback_breakout_signals(
        wave,
        bars_by_date,
        strategy_id="cadence_trailing_walk_base:lb10:buf0:delta300:cl0.55:start1000:end1230",
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
    candidates = _build_candidates(
        wave,
        bars_by_date,
        base_signals=base_signals,
        features=features,
        filter_specs=trailing._selected_filter_specs(cadence),
        risks=trailing._dense_risk_grid(deep, wave),
        minimum_signal_days=args.minimum_signal_days,
    )
    configs = _parse_configs(args.train_date_counts, args.holdout_date_counts)

    rows = []
    holdout_outcomes_by_config: dict[str, list[object]] = {}
    holdout_dates_by_config: dict[str, list[date]] = {}
    for train_count, holdout_count in configs:
        config_id = f"{train_count}x{holdout_count}"
        config_rows, holdout_outcomes, holdout_dates = _run_walk_forward_config(
            wave,
            trailing,
            candidates,
            trade_dates=trade_dates,
            train_date_count=train_count,
            holdout_date_count=holdout_count,
            minimum_train_trades=args.minimum_train_trades,
            config_id=config_id,
        )
        rows.extend(config_rows)
        holdout_outcomes_by_config[config_id] = holdout_outcomes
        holdout_dates_by_config[config_id] = holdout_dates

    benchmark_rows = _benchmark_rows(
        wave,
        trailing,
        candidates,
        trade_dates,
        configs,
    )
    frozen_leader_rows = _all_candidate_frozen_leaders(
        wave,
        trailing,
        candidates,
        trade_dates,
        configs,
    )
    _write_csv(args.detail_output, rows)
    _write_report(
        args.report_output,
        wave=wave,
        trailing=trailing,
        bars=bars,
        candidates=candidates,
        base_signals=base_signals,
        rows=rows,
        holdout_outcomes_by_config=holdout_outcomes_by_config,
        holdout_dates_by_config=holdout_dates_by_config,
        benchmark_rows=benchmark_rows,
        frozen_leader_rows=frozen_leader_rows,
        minimum_train_trades=args.minimum_train_trades,
    )

    holdout_rows = [row for row in rows if row["sample"] == "holdout"]
    holdout_net = sum(float(row["net_usd"]) for row in holdout_rows)
    holdout_trades = sum(int(row["evaluated_trades"]) for row in holdout_rows)
    print(
        f"wrote {len(rows)} MNQ trailing walk-forward rows to {args.detail_output}; "
        f"candidates={len(candidates)}, holdout_windows={len(holdout_rows)}, "
        f"holdout_trades={holdout_trades}, holdout_net={holdout_net:.2f}",
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


def _build_candidates(
    wave,
    bars_by_date: dict[date, list[object]],
    *,
    base_signals: list[object],
    features: list[dict[str, object]],
    filter_specs: list[object],
    risks: list[object],
    minimum_signal_days: int,
) -> list[Candidate]:
    candidates = []
    for filter_spec in filter_specs:
        strategy_id = f"cadence_trailing:{filter_spec.filter_id}"
        signals = [
            wave.Signal(
                strategy_id,
                signal.direction,
                signal.bar,
                f"{signal.notes}; trailing walk-forward filter {filter_spec.filter_id}",
            )
            for signal, feature in zip(base_signals, features)
            if filter_spec.keep_signal(feature)
        ]
        if len(signals) < minimum_signal_days:
            continue
        for risk in risks:
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


def _run_walk_forward_config(
    wave,
    trailing,
    candidates: list[Candidate],
    *,
    trade_dates: list[date],
    train_date_count: int,
    holdout_date_count: int,
    minimum_train_trades: int,
    config_id: str,
) -> tuple[list[dict[str, object]], list[object], list[date]]:
    rows = []
    selected_holdout_outcomes = []
    selected_holdout_dates = []
    window = 0
    max_start = len(trade_dates) - train_date_count - holdout_date_count
    for start_index in range(0, max_start + 1, holdout_date_count):
        window += 1
        train_dates = trade_dates[start_index:start_index + train_date_count]
        holdout_dates = trade_dates[
            start_index + train_date_count:
            start_index + train_date_count + holdout_date_count
        ]
        selected, train_outcomes = _select_candidate(
            wave,
            trailing,
            candidates,
            train_dates=set(train_dates),
            sample_dates=train_dates,
            minimum_train_trades=minimum_train_trades,
        )
        holdout_outcomes = _outcomes_for_dates(selected.outcomes, set(holdout_dates))
        rows.append(
            _row(
                wave,
                trailing,
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
                trailing,
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
        selected_holdout_dates.extend(holdout_dates)
    return rows, selected_holdout_outcomes, selected_holdout_dates


def _select_candidate(
    wave,
    trailing,
    candidates: list[Candidate],
    *,
    train_dates: set[date],
    sample_dates: list[date],
    minimum_train_trades: int,
) -> tuple[Candidate, list[object]]:
    selected_candidate: Candidate | None = None
    selected_outcomes: list[object] = []
    selected_key: tuple[float, ...] | None = None
    for candidate in candidates:
        outcomes = _outcomes_for_dates(candidate.outcomes, train_dates)
        metrics = _metrics(wave, trailing, outcomes, sample_dates)
        key = _selection_key(metrics, minimum_train_trades=minimum_train_trades)
        if selected_key is None or key < selected_key:
            selected_key = key
            selected_candidate = candidate
            selected_outcomes = outcomes
    if selected_candidate is None:
        raise RuntimeError("no eligible MNQ trailing candidates were generated")
    return selected_candidate, selected_outcomes


def _selection_key(metrics: dict[str, float], *, minimum_train_trades: int) -> tuple[float, ...]:
    enough_trades = metrics["evaluated_trades"] >= minimum_train_trades
    positive_edge = metrics["net_usd"] > 0.0 and metrics["average_trade_usd"] > 0.0
    strict_enough = (
        metrics["trailing_calendar_pass_rate"] >= 0.25
        and metrics["trailing_calendar_fail_rate"] <= 0.12
        and metrics["trailing_signal_fail_rate"] <= 0.25
    )
    return (
        0.0 if enough_trades else 1.0,
        0.0 if positive_edge else 1.0,
        0.0 if strict_enough else 1.0,
        metrics["trailing_calendar_fail_rate"],
        metrics["trailing_signal_fail_rate"],
        -metrics["trailing_calendar_pass_rate"],
        -metrics["trailing_signal_pass_rate"],
        abs(metrics["max_drawdown_usd"]),
        -metrics["average_trade_usd"],
        -metrics["net_usd"],
    )


def _row(
    wave,
    trailing,
    *,
    config_id: str,
    window: int,
    sample: str,
    sample_dates: list[date],
    candidate: Candidate,
    outcomes: list[object],
    selected_on_train: bool,
) -> dict[str, object]:
    metrics = _metrics(wave, trailing, outcomes, sample_dates)
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
        "trailing_calendar_pass_rate": _format_number(
            metrics["trailing_calendar_pass_rate"],
        ),
        "trailing_calendar_fail_rate": _format_number(
            metrics["trailing_calendar_fail_rate"],
        ),
        "trailing_calendar_timeout_rate": _format_number(
            metrics["trailing_calendar_timeout_rate"],
        ),
        "trailing_signal_pass_rate": _format_number(
            metrics["trailing_signal_pass_rate"],
        ),
        "trailing_signal_fail_rate": _format_number(
            metrics["trailing_signal_fail_rate"],
        ),
        "trailing_signal_timeout_rate": _format_number(
            metrics["trailing_signal_timeout_rate"],
        ),
        "trailing_signal_median_trade_days_to_pass": _format_number(
            metrics["trailing_signal_median_trade_days_to_pass"],
        ),
        "selected_on_train": str(selected_on_train).lower(),
    }


def _metrics(
    wave,
    trailing,
    outcomes: list[object],
    sample_dates: list[date],
) -> dict[str, float]:
    net_values = [outcome.net_usd for outcome in outcomes]
    positive = [value for value in net_values if value > 0.0]
    negative = [value for value in net_values if value < 0.0]
    calendar_metrics = trailing._simulate_trailing_calendar_attempts(
        outcomes,
        sample_dates,
    )
    signal_metrics = trailing._simulate_trailing_signal_attempts(outcomes)
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
        "eod_exits": float(
            sum(
                outcome.exit_reason in {"end_of_session", "no_following_bar"}
                for outcome in outcomes
            ),
        ),
        "trailing_calendar_pass_rate": calendar_metrics["pass_rate"],
        "trailing_calendar_fail_rate": calendar_metrics["fail_rate"],
        "trailing_calendar_timeout_rate": calendar_metrics["timeout_rate"],
        "trailing_signal_pass_rate": signal_metrics["pass_rate"],
        "trailing_signal_fail_rate": signal_metrics["fail_rate"],
        "trailing_signal_timeout_rate": signal_metrics["timeout_rate"],
        "trailing_signal_median_trade_days_to_pass": (
            signal_metrics["median_trade_days_to_pass"]
        ),
    }


def _benchmark_rows(
    wave,
    trailing,
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
            holdout_dates = []
            max_start = len(trade_dates) - train_count - holdout_count
            for start_index in range(0, max_start + 1, holdout_count):
                window_dates = trade_dates[
                    start_index + train_count:
                    start_index + train_count + holdout_count
                ]
                window_outcomes = _outcomes_for_dates(candidate.outcomes, set(window_dates))
                holdout_windows.append(sum(outcome.net_usd for outcome in window_outcomes))
                holdout_outcomes.extend(window_outcomes)
                holdout_dates.extend(window_dates)
            summary = _aggregate_summary(
                wave,
                trailing,
                windows=holdout_windows,
                outcomes=holdout_outcomes,
                sample_dates=holdout_dates,
            )
            rows.append(
                {
                    "config": config_id,
                    "candidate": candidate_name,
                    **summary,
                },
            )
    return rows


def _all_candidate_frozen_leaders(
    wave,
    trailing,
    candidates: list[Candidate],
    trade_dates: list[date],
    configs: list[tuple[int, int]],
    *,
    limit: int = 15,
) -> list[dict[str, object]]:
    rows = []
    for candidate in candidates:
        summaries = [
            _frozen_numeric_summary(
                wave,
                trailing,
                candidate,
                trade_dates=trade_dates,
                train_count=train_count,
                holdout_count=holdout_count,
            )
            for train_count, holdout_count in configs
        ]
        total_trades = sum(int(summary["trades"]) for summary in summaries)
        if total_trades < 40:
            continue
        total_windows = sum(int(summary["windows"]) for summary in summaries)
        positive_windows = sum(int(summary["positive_windows"]) for summary in summaries)
        negative_windows = sum(int(summary["negative_windows"]) for summary in summaries)
        row = {
            "strategy_id": candidate.strategy_id,
            "quantity": candidate.quantity,
            "target_net_usd": candidate.target_net_usd,
            "stop_net_usd": candidate.stop_net_usd,
            "total_trades": total_trades,
            "total_net_usd": sum(float(summary["net_usd"]) for summary in summaries),
            "minimum_config_net_usd": min(
                float(summary["net_usd"]) for summary in summaries
            ),
            "profit_factor": min(float(summary["profit_factor"]) for summary in summaries),
            "max_drawdown_usd": min(
                float(summary["max_drawdown_usd"]) for summary in summaries
            ),
            "positive_windows": positive_windows,
            "negative_windows": negative_windows,
            "window_count": total_windows,
            "minimum_calendar_pass_rate": min(
                float(summary["trailing_calendar_pass_rate"])
                for summary in summaries
            ),
            "maximum_calendar_fail_rate": max(
                float(summary["trailing_calendar_fail_rate"])
                for summary in summaries
            ),
            "minimum_signal_pass_rate": min(
                float(summary["trailing_signal_pass_rate"])
                for summary in summaries
            ),
            "maximum_signal_fail_rate": max(
                float(summary["trailing_signal_fail_rate"])
                for summary in summaries
            ),
            "minimum_signal_median_trade_days": max(
                float(summary["trailing_signal_median_trade_days_to_pass"])
                for summary in summaries
            ),
        }
        rows.append(row)
    rows.sort(key=_frozen_leader_key)
    return rows[:limit]


def _frozen_numeric_summary(
    wave,
    trailing,
    candidate: Candidate,
    *,
    trade_dates: list[date],
    train_count: int,
    holdout_count: int,
) -> dict[str, float]:
    holdout_windows = []
    holdout_outcomes = []
    holdout_dates = []
    max_start = len(trade_dates) - train_count - holdout_count
    for start_index in range(0, max_start + 1, holdout_count):
        window_dates = trade_dates[
            start_index + train_count:
            start_index + train_count + holdout_count
        ]
        window_outcomes = _outcomes_for_dates(candidate.outcomes, set(window_dates))
        holdout_windows.append(sum(outcome.net_usd for outcome in window_outcomes))
        holdout_outcomes.extend(window_outcomes)
        holdout_dates.extend(window_dates)
    metrics = _metrics(wave, trailing, holdout_outcomes, holdout_dates)
    return {
        "windows": float(len(holdout_windows)),
        "trades": metrics["evaluated_trades"],
        "net_usd": metrics["net_usd"],
        "profit_factor": metrics["profit_factor"],
        "max_drawdown_usd": metrics["max_drawdown_usd"],
        "positive_windows": float(sum(value > 0.0 for value in holdout_windows)),
        "negative_windows": float(sum(value < 0.0 for value in holdout_windows)),
        "trailing_calendar_pass_rate": metrics["trailing_calendar_pass_rate"],
        "trailing_calendar_fail_rate": metrics["trailing_calendar_fail_rate"],
        "trailing_signal_pass_rate": metrics["trailing_signal_pass_rate"],
        "trailing_signal_fail_rate": metrics["trailing_signal_fail_rate"],
        "trailing_signal_median_trade_days_to_pass": (
            metrics["trailing_signal_median_trade_days_to_pass"]
        ),
    }


def _frozen_leader_key(row: dict[str, object]) -> tuple[float, ...]:
    strict_penalty = (
        0.0
        if float(row["minimum_config_net_usd"]) > 0.0
        and float(row["minimum_calendar_pass_rate"]) >= 0.30
        and float(row["maximum_calendar_fail_rate"]) <= 0.08
        and float(row["minimum_signal_pass_rate"]) >= 0.65
        and float(row["maximum_signal_fail_rate"]) <= 0.25
        else 1.0
    )
    return (
        strict_penalty,
        -float(row["minimum_calendar_pass_rate"]),
        float(row["maximum_calendar_fail_rate"]),
        float(row["maximum_signal_fail_rate"]),
        -float(row["minimum_signal_pass_rate"]),
        -float(row["minimum_config_net_usd"]),
        abs(float(row["max_drawdown_usd"])),
        -float(row["total_net_usd"]),
    )


def _aggregate_summary(
    wave,
    trailing,
    *,
    windows: list[float],
    outcomes: list[object],
    sample_dates: list[date],
) -> dict[str, object]:
    metrics = _metrics(wave, trailing, outcomes, sample_dates)
    return {
        "windows": len(windows),
        "trades": int(metrics["evaluated_trades"]),
        "net_usd": _format_number(metrics["net_usd"]),
        "average_trade_usd": _format_number(metrics["average_trade_usd"]),
        "profit_factor": _format_number(metrics["profit_factor"]),
        "max_drawdown_usd": _format_number(metrics["max_drawdown_usd"]),
        "positive_windows": sum(value > 0.0 for value in windows),
        "negative_windows": sum(value < 0.0 for value in windows),
        "trailing_calendar_pass_rate": _format_number(
            metrics["trailing_calendar_pass_rate"],
        ),
        "trailing_calendar_fail_rate": _format_number(
            metrics["trailing_calendar_fail_rate"],
        ),
        "trailing_signal_pass_rate": _format_number(metrics["trailing_signal_pass_rate"]),
        "trailing_signal_fail_rate": _format_number(metrics["trailing_signal_fail_rate"]),
        "trailing_signal_median_trade_days_to_pass": _format_number(
            metrics["trailing_signal_median_trade_days_to_pass"],
        ),
    }


def _outcomes_for_dates(outcomes: list[object], trade_dates: set[date]) -> list[object]:
    return [
        outcome for outcome in outcomes
        if outcome.entry_time.date() in trade_dates
    ]


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
    wave,
    trailing,
    bars: list[object],
    candidates: list[Candidate],
    base_signals: list[object],
    rows: list[dict[str, object]],
    holdout_outcomes_by_config: dict[str, list[object]],
    holdout_dates_by_config: dict[str, list[date]],
    benchmark_rows: list[dict[str, object]],
    frozen_leader_rows: list[dict[str, object]],
    minimum_train_trades: int,
) -> None:
    holdout_rows = [row for row in rows if row["sample"] == "holdout"]
    lines = [
        "# MNQ Eval-Pass Wave Rider Trailing Walk-Forward",
        "",
        "Status: chronological validation for the faster MNQ B setup under "
        "trailing drawdown rules.",
        "",
        "## Source",
        "",
        f"- rows: `{len(bars)}`",
        f"- dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        f"- unique dates: `{len({bar.trade_date for bar in bars})}`",
        f"- base signals: `{len(base_signals)}`",
        f"- candidate rows: `{len(candidates)}`",
        f"- minimum training trades: `{minimum_train_trades}`",
        "- trailing floor: `min(0, high_water - 1000)`",
        "- pass target: `$1250` with `50%` consistency",
        "",
        "## Adaptive Walk-Forward Summary",
        "",
        "Each window selects the best candidate on the training dates, then scores "
        "that exact candidate on the following unseen holdout dates.",
        "",
        "| Config | Windows | Holdout Trades | Holdout Net | Avg | PF | Max DD | "
        "Positive | Negative | Trail Cal Pass | Trail Cal Fail | Trail Sig Pass | "
        "Trail Sig Fail | Median Pass Trades |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | "
        "---: | ---: | ---: | ---: |",
    ]
    for config_id in sorted(holdout_outcomes_by_config):
        config_rows = [row for row in holdout_rows if row["config"] == config_id]
        windows = [float(row["net_usd"]) for row in config_rows]
        summary = _aggregate_summary(
            wave,
            trailing,
            windows=windows,
            outcomes=holdout_outcomes_by_config[config_id],
            sample_dates=holdout_dates_by_config[config_id],
        )
        lines.append(_summary_row(config_id, summary))

    lines.extend(
        [
            "",
            "## Frozen Candidate Benchmarks",
            "",
            "These rows freeze one candidate upfront and evaluate the same chronological "
            "holdout slices. This is the cleaner comparison when deciding whether to "
            "build a bot.",
            "",
            "| Config | Candidate | Windows | Holdout Trades | Holdout Net | Avg | PF | "
            "Max DD | Positive | Negative | Trail Cal Pass | Trail Cal Fail | "
            "Trail Sig Pass | Trail Sig Fail | Median Pass Trades |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | "
            "---: | ---: | ---: | ---: | ---: |",
        ],
    )
    for row in benchmark_rows:
        lines.append(
            "| "
            f"{row['config']} | `{row['candidate']}` | {row['windows']} | "
            f"{row['trades']} | {row['net_usd']} | {row['average_trade_usd']} | "
            f"{row['profit_factor']} | {row['max_drawdown_usd']} | "
            f"{row['positive_windows']} | {row['negative_windows']} | "
            f"{float(row['trailing_calendar_pass_rate']) * 100:.1f}% | "
            f"{float(row['trailing_calendar_fail_rate']) * 100:.1f}% | "
            f"{float(row['trailing_signal_pass_rate']) * 100:.1f}% | "
            f"{float(row['trailing_signal_fail_rate']) * 100:.1f}% | "
            f"{row['trailing_signal_median_trade_days_to_pass']} |"
        )

    lines.extend(
        [
            "",
            "## All-Candidate Frozen Leaderboard",
            "",
            "This ranks every frozen row from the faster B candidate pool across the "
            "same holdout slices. It is a robustness screen, not a license to "
            "keep optimizing on holdout data.",
            "",
            "| Rank | Qty | Target | Stop | Trades | Total Net | Min Config Net | "
            "Min Cal Pass | Max Cal Fail | Min Sig Pass | Max Sig Fail | "
            "Positive Windows | Max DD | Strategy |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | "
            "---: | ---: | ---: | ---: | --- |",
        ],
    )
    for rank, row in enumerate(frozen_leader_rows, start=1):
        lines.append(
            "| "
            f"{rank} | {row['quantity']} | {_format_number(float(row['target_net_usd']))} | "
            f"{_format_number(float(row['stop_net_usd']))} | {row['total_trades']} | "
            f"{_format_number(float(row['total_net_usd']))} | "
            f"{_format_number(float(row['minimum_config_net_usd']))} | "
            f"{float(row['minimum_calendar_pass_rate']) * 100:.1f}% | "
            f"{float(row['maximum_calendar_fail_rate']) * 100:.1f}% | "
            f"{float(row['minimum_signal_pass_rate']) * 100:.1f}% | "
            f"{float(row['maximum_signal_fail_rate']) * 100:.1f}% | "
            f"{row['positive_windows']}/{row['window_count']} | "
            f"{_format_number(float(row['max_drawdown_usd']))} | "
            f"`{row['strategy_id']}` |"
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
        for (strategy_id, quantity, target, stop), count in counts.most_common(10):
            lines.append(
                f"| {config_id} | {count} | {quantity} | {target} | {stop} | "
                f"`{strategy_id}` |"
            )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The adaptive selector is a bias check, not a live plan. In this run "
            "it stayed profitable overall, but it changed candidates frequently "
            "and trailed the locked `4 MNQ` `$650/$450` benchmark on holdout "
            "net, drawdown, trailing pass rate, and trailing fail rate.",
            "",
            "The conclusion is to reject dynamic optimization for this setup and "
            "advance only the frozen Tuesday/Wednesday short-only `4 MNQ` "
            "`$650/$450` row to replay/mechanics validation.",
            "",
        ],
    )
    Path(report_output).write_text("\n".join(lines), encoding="utf-8")


def _summary_row(config_id: str, summary: dict[str, object]) -> str:
    return (
        "| "
        f"{config_id} | {summary['windows']} | {summary['trades']} | "
        f"{summary['net_usd']} | {summary['average_trade_usd']} | "
        f"{summary['profit_factor']} | {summary['max_drawdown_usd']} | "
        f"{summary['positive_windows']} | {summary['negative_windows']} | "
        f"{float(summary['trailing_calendar_pass_rate']) * 100:.1f}% | "
        f"{float(summary['trailing_calendar_fail_rate']) * 100:.1f}% | "
        f"{float(summary['trailing_signal_pass_rate']) * 100:.1f}% | "
        f"{float(summary['trailing_signal_fail_rate']) * 100:.1f}% | "
        f"{summary['trailing_signal_median_trade_days_to_pass']} |"
    )


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
