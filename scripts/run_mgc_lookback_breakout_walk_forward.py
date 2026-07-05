#!/usr/bin/env python3
"""Chronological holdout validation for MGC lookback-breakout candidates."""

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
from types import ModuleType
from typing import Any, Callable, Iterable


DEFAULT_DETAIL_OUTPUT = "reports/mgc-lookback-breakout-walk-forward.csv"
DEFAULT_REPORT_OUTPUT = "reports/mgc-lookback-breakout-walk-forward.md"
DEFAULT_TRAIN_DATE_COUNTS = "120,180,240"
DEFAULT_HOLDOUT_DATE_COUNTS = "40,40,60"

HEADER = [
    "schema_version",
    "config",
    "window",
    "sample",
    "start_date",
    "end_date",
    "selected_strategy_id",
    "target_points",
    "stop_points",
    "target_net_usd",
    "stop_net_usd",
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
    "selected_on_train",
]


@dataclass(frozen=True)
class Candidate:
    strategy_id: str
    target_points: float
    stop_points: float
    target_net_usd: float
    stop_net_usd: float
    outcomes: list[Any]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run MGC lookback-breakout chronological holdout validation.",
    )
    parser.add_argument("input", nargs="?", default=None)
    parser.add_argument("--detail-output", default=DEFAULT_DETAIL_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--symbol", default="MGC")
    parser.add_argument("--minimum-full-trades", type=int, default=250)
    parser.add_argument("--minimum-train-trades", type=int, default=25)
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
    candidates = _build_candidates(
        core,
        normal,
        comp,
        refine,
        bars_by_date,
        rows_by_index,
        symbol=args.symbol,
        minimum_full_trades=args.minimum_full_trades,
    )
    configs = _parse_configs(args.train_date_counts, args.holdout_date_counts)

    rows = []
    adaptive_holdouts_by_config: dict[str, list[Any]] = {}
    for train_count, holdout_count in configs:
        config_id = f"{train_count}x{holdout_count}"
        config_rows, holdout_outcomes = _run_adaptive_config(
            core,
            candidates,
            trade_dates=trade_dates,
            train_date_count=train_count,
            holdout_date_count=holdout_count,
            minimum_train_trades=args.minimum_train_trades,
            config_id=config_id,
        )
        rows.extend(config_rows)
        adaptive_holdouts_by_config[config_id] = holdout_outcomes

    current_lead_rows = _current_lead_rows(core, candidates, trade_dates, configs)
    frozen_leaders = _frozen_leader_rows(core, candidates, trade_dates, configs)

    _write_csv(args.detail_output, rows)
    _write_report(
        args.report_output,
        bars=bars,
        candidates=candidates,
        rows=rows,
        adaptive_holdouts_by_config=adaptive_holdouts_by_config,
        current_lead_rows=current_lead_rows,
        frozen_leaders=frozen_leaders,
        configs=configs,
        minimum_train_trades=args.minimum_train_trades,
    )

    holdout_rows = [row for row in rows if row["sample"] == "holdout"]
    holdout_net = sum(float(row["net_usd"]) for row in holdout_rows)
    holdout_trades = sum(int(row["evaluated_trades"]) for row in holdout_rows)
    current_lead_net = sum(float(row["net_usd"]) for row in current_lead_rows)
    print(
        f"wrote {len(rows)} MGC lookback walk-forward rows to {args.detail_output}; "
        f"candidates={len(candidates)}, adaptive_holdout_windows={len(holdout_rows)}, "
        f"adaptive_holdout_trades={holdout_trades}, adaptive_holdout_net={holdout_net:.2f}, "
        f"current_lead_holdout_net={current_lead_net:.2f}",
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


def _build_candidates(
    core: ModuleType,
    normal: ModuleType,
    comp: ModuleType,
    refine: ModuleType,
    bars_by_date: dict[date, list[Any]],
    rows_by_index: dict[int, int],
    *,
    symbol: str,
    minimum_full_trades: int,
) -> list[Candidate]:
    filters = _filter_specs()
    policies = [
        {"policy_id": "maxday1_gap0", "max_trades_per_day": 1, "reentry_gap_minutes": 0},
        {"policy_id": "maxday2_gap15", "max_trades_per_day": 2, "reentry_gap_minutes": 15},
    ]
    candidates = []
    for base_strategy_id, base_signals in _base_signal_sets(comp, core, bars_by_date, symbol):
        if not base_signals:
            continue
        ordered_signals = sorted(base_signals, key=lambda signal: signal.bar.timestamp)
        features_by_index = {
            signal.bar.index: refine._features(signal, bars_by_date, rows_by_index)
            for signal in ordered_signals
        }
        filtered_by_id = []
        for filter_id, keep in filters:
            filtered_signals = [
                signal for signal in ordered_signals
                if keep(signal, features_by_index[signal.bar.index])
            ]
            if len({signal.bar.trade_date for signal in filtered_signals}) >= minimum_full_trades:
                filtered_by_id.append((filter_id, filtered_signals))
        if not filtered_by_id:
            continue

        for risk in _risk_profiles(core, normal):
            outcomes_by_signal_index = refine._outcomes_by_signal_index(
                core,
                ordered_signals,
                bars_by_date,
                rows_by_index,
                risk,
            )
            for filter_id, filtered_signals in filtered_by_id:
                for policy in policies:
                    outcomes = refine._evaluate_sequence(
                        filtered_signals,
                        outcomes_by_signal_index,
                        max_trades_per_day=policy["max_trades_per_day"],
                        reentry_gap_minutes=policy["reentry_gap_minutes"],
                    )
                    if len(outcomes) < minimum_full_trades:
                        continue
                    candidates.append(
                        Candidate(
                            strategy_id=f"{base_strategy_id}:filter{filter_id}:{policy['policy_id']}",
                            target_points=risk.target_points,
                            stop_points=risk.stop_points,
                            target_net_usd=risk.target_net_usd,
                            stop_net_usd=risk.stop_net_usd,
                            outcomes=outcomes,
                        ),
                    )
    return candidates


def _base_signal_sets(
    comp: ModuleType,
    core: ModuleType,
    bars_by_date: dict[date, list[Any]],
    symbol: str,
) -> list[tuple[str, list[Any]]]:
    signal_sets = []
    for entry_end in (time(10, 30), time(13, 30)):
        for lookback_bars in (5, 10, 15):
            for buffer_points in (0.0, 0.5):
                for close_location_threshold in (0.50, 0.55):
                    strategy_id = (
                        "mgc_lookback_breakout_walk_base:"
                        f"lb{lookback_bars}:buf{buffer_points:g}:"
                        f"delta0:cl{close_location_threshold:g}:"
                        f"end{_time_id(entry_end)}"
                    )
                    signals = comp._all_lookback_breakouts(
                        core,
                        bars_by_date,
                        strategy_id=strategy_id,
                        lookback_bars=lookback_bars,
                        buffer_points=buffer_points,
                        delta_threshold=0.0,
                        close_location_threshold=close_location_threshold,
                        entry_end=entry_end,
                        symbol=symbol,
                    )
                    signal_sets.append((strategy_id, signals))
    return signal_sets


def _filter_specs() -> list[tuple[str, Callable[[Any, dict[str, float | int | str]], bool]]]:
    return [
        ("none", lambda _signal, _features: True),
        ("bar8", lambda _signal, features: float(features["bar_range"]) <= 8.0),
        ("absdelta100", lambda _signal, features: float(features["abs_delta"]) <= 100.0),
        ("vwapdist20", lambda _signal, features: float(features["abs_vwap_distance"]) <= 20.0),
        ("nofri", lambda _signal, features: int(features["weekday"]) in {0, 1, 2, 3}),
        (
            "nofri_bar8",
            lambda _signal, features: (
                int(features["weekday"]) in {0, 1, 2, 3}
                and float(features["bar_range"]) <= 8.0
            ),
        ),
        (
            "start0900_nofri",
            lambda _signal, features: (
                int(features["time_minutes"]) >= 9 * 60
                and int(features["weekday"]) in {0, 1, 2, 3}
            ),
        ),
    ]


def _risk_profiles(core: ModuleType, normal: ModuleType) -> list[Any]:
    profiles = []
    round_turn_cost = 2.0 * normal.COMMISSION_PER_SIDE_USD + normal.SLIPPAGE_TICKS_PER_CONTRACT * normal.TICK_VALUE_USD
    for target_points, stop_points in ((20.0, 12.0), (25.0, 15.0), (30.0, 15.0)):
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


def _run_adaptive_config(
    core: ModuleType,
    candidates: list[Candidate],
    *,
    trade_dates: list[date],
    train_date_count: int,
    holdout_date_count: int,
    minimum_train_trades: int,
    config_id: str,
) -> tuple[list[dict[str, object]], list[Any]]:
    rows = []
    selected_holdout_outcomes = []
    max_start = len(trade_dates) - train_date_count - holdout_date_count
    window = 0
    for start_index in range(0, max_start + 1, holdout_date_count):
        window += 1
        train_dates = trade_dates[start_index:start_index + train_date_count]
        holdout_dates = trade_dates[
            start_index + train_date_count:
            start_index + train_date_count + holdout_date_count
        ]
        selected, train_outcomes = _select_candidate(
            core,
            candidates,
            train_dates=set(train_dates),
            minimum_train_trades=minimum_train_trades,
        )
        holdout_outcomes = _outcomes_for_dates(selected.outcomes, set(holdout_dates))
        rows.append(
            _detail_row(
                core,
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
            _detail_row(
                core,
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
    core: ModuleType,
    candidates: list[Candidate],
    *,
    train_dates: set[date],
    minimum_train_trades: int,
) -> tuple[Candidate, list[Any]]:
    best_candidate = candidates[0]
    best_outcomes = _outcomes_for_dates(best_candidate.outcomes, train_dates)
    best_key = _selection_key(core, best_outcomes, minimum_train_trades=minimum_train_trades)
    for candidate in candidates[1:]:
        outcomes = _outcomes_for_dates(candidate.outcomes, train_dates)
        key = _selection_key(core, outcomes, minimum_train_trades=minimum_train_trades)
        if key < best_key:
            best_candidate = candidate
            best_outcomes = outcomes
            best_key = key
    return best_candidate, best_outcomes


def _selection_key(
    core: ModuleType,
    outcomes: list[Any],
    *,
    minimum_train_trades: int,
) -> tuple[float, ...]:
    metrics = _metrics(core, outcomes)
    enough = metrics["evaluated_trades"] >= minimum_train_trades
    net = metrics["net_usd"]
    pf = metrics["profit_factor"]
    drawdown_to_net = abs(metrics["max_drawdown_usd"]) / net if net > 0.0 else 999.0
    return (
        0.0 if enough else 1.0,
        0.0 if net > 0.0 and pf >= 1.10 else 1.0,
        drawdown_to_net,
        -pf,
        -metrics["average_trade_usd"],
        -net,
        -metrics["evaluated_trades"],
    )


def _current_lead_rows(
    core: ModuleType,
    candidates: list[Candidate],
    trade_dates: list[date],
    configs: list[tuple[int, int]],
) -> list[dict[str, object]]:
    candidate = _find_current_lead(candidates)
    return [
        {
            "candidate": "current_lead",
            "config": f"{train_count}x{holdout_count}",
            **_frozen_summary(
                core,
                candidate,
                trade_dates=trade_dates,
                train_count=train_count,
                holdout_count=holdout_count,
            ),
        }
        for train_count, holdout_count in configs
    ]


def _frozen_leader_rows(
    core: ModuleType,
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
                core,
                candidate,
                trade_dates=trade_dates,
                train_count=train_count,
                holdout_count=holdout_count,
            )
            for train_count, holdout_count in configs
        ]
        total_trades = sum(int(summary["trades"]) for summary in summaries)
        if total_trades < 80:
            continue
        row = {
            "strategy_id": candidate.strategy_id,
            "target_points": candidate.target_points,
            "stop_points": candidate.stop_points,
            "target_net_usd": candidate.target_net_usd,
            "stop_net_usd": candidate.stop_net_usd,
            "total_trades": total_trades,
            "total_net_usd": sum(float(summary["net_usd"]) for summary in summaries),
            "minimum_config_net_usd": min(float(summary["net_usd"]) for summary in summaries),
            "minimum_profit_factor": min(float(summary["profit_factor"]) for summary in summaries),
            "max_drawdown_usd": min(float(summary["max_drawdown_usd"]) for summary in summaries),
            "positive_windows": sum(int(summary["positive_windows"]) for summary in summaries),
            "negative_windows": sum(int(summary["negative_windows"]) for summary in summaries),
            "window_count": sum(int(summary["windows"]) for summary in summaries),
            "worst_window_usd": min(float(summary["worst_window_usd"]) for summary in summaries),
        }
        rows.append(row)
    rows.sort(key=_frozen_leader_key)
    return rows[:limit]


def _frozen_summary(
    core: ModuleType,
    candidate: Candidate,
    *,
    trade_dates: list[date],
    train_count: int,
    holdout_count: int,
) -> dict[str, object]:
    summary = _frozen_numeric_summary(
        core,
        candidate,
        trade_dates=trade_dates,
        train_count=train_count,
        holdout_count=holdout_count,
    )
    return {
        "strategy_id": candidate.strategy_id,
        "target_points": _format_number(candidate.target_points),
        "stop_points": _format_number(candidate.stop_points),
        "target_net_usd": _format_number(candidate.target_net_usd),
        "stop_net_usd": _format_number(candidate.stop_net_usd),
        "windows": int(summary["windows"]),
        "trades": int(summary["trades"]),
        "net_usd": _format_number(summary["net_usd"]),
        "average_trade_usd": _format_number(summary["average_trade_usd"]),
        "profit_factor": _format_number(summary["profit_factor"]),
        "max_drawdown_usd": _format_number(summary["max_drawdown_usd"]),
        "positive_windows": int(summary["positive_windows"]),
        "negative_windows": int(summary["negative_windows"]),
        "worst_window_usd": _format_number(summary["worst_window_usd"]),
    }


def _frozen_numeric_summary(
    core: ModuleType,
    candidate: Candidate,
    *,
    trade_dates: list[date],
    train_count: int,
    holdout_count: int,
) -> dict[str, float]:
    holdout_windows = []
    holdout_outcomes = []
    max_start = len(trade_dates) - train_count - holdout_count
    for start_index in range(0, max_start + 1, holdout_count):
        window_dates = trade_dates[
            start_index + train_count:
            start_index + train_count + holdout_count
        ]
        window_outcomes = _outcomes_for_dates(candidate.outcomes, set(window_dates))
        holdout_windows.append(sum(outcome.net_usd for outcome in window_outcomes))
        holdout_outcomes.extend(window_outcomes)
    metrics = _metrics(core, holdout_outcomes)
    return {
        "windows": float(len(holdout_windows)),
        "trades": metrics["evaluated_trades"],
        "net_usd": metrics["net_usd"],
        "average_trade_usd": metrics["average_trade_usd"],
        "profit_factor": metrics["profit_factor"],
        "max_drawdown_usd": metrics["max_drawdown_usd"],
        "positive_windows": float(sum(value > 0.0 for value in holdout_windows)),
        "negative_windows": float(sum(value < 0.0 for value in holdout_windows)),
        "worst_window_usd": min(holdout_windows) if holdout_windows else 0.0,
    }


def _frozen_leader_key(row: dict[str, object]) -> tuple[float, ...]:
    strict = (
        0.0
        if float(row["minimum_config_net_usd"]) > 0.0
        and float(row["minimum_profit_factor"]) >= 1.05
        and int(row["negative_windows"]) <= max(2, int(row["window_count"]) // 4)
        else 1.0
    )
    return (
        strict,
        int(row["negative_windows"]),
        -float(row["minimum_config_net_usd"]),
        -float(row["minimum_profit_factor"]),
        abs(float(row["max_drawdown_usd"])),
        -float(row["total_net_usd"]),
    )


def _detail_row(
    core: ModuleType,
    *,
    config_id: str,
    window: int,
    sample: str,
    sample_dates: list[date],
    candidate: Candidate,
    outcomes: list[Any],
    selected_on_train: bool,
) -> dict[str, object]:
    metrics = _metrics(core, outcomes)
    return {
        "schema_version": 1,
        "config": config_id,
        "window": window,
        "sample": sample,
        "start_date": sample_dates[0].isoformat(),
        "end_date": sample_dates[-1].isoformat(),
        "selected_strategy_id": candidate.strategy_id,
        "target_points": _format_number(candidate.target_points),
        "stop_points": _format_number(candidate.stop_points),
        "target_net_usd": _format_number(candidate.target_net_usd),
        "stop_net_usd": _format_number(candidate.stop_net_usd),
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
        "selected_on_train": str(selected_on_train).lower(),
    }


def _metrics(core: ModuleType, outcomes: list[Any]) -> dict[str, float]:
    values = [outcome.net_usd for outcome in outcomes]
    positive = [value for value in values if value > 0.0]
    negative = [value for value in values if value < 0.0]
    return {
        "evaluated_trades": float(len(outcomes)),
        "win_rate": len(positive) / len(outcomes) if outcomes else 0.0,
        "net_usd": sum(values),
        "average_trade_usd": statistics.mean(values) if values else 0.0,
        "profit_factor": sum(positive) / abs(sum(negative)) if negative else 999.0,
        "max_drawdown_usd": core._max_drawdown(values),
        "worst_trade_usd": min(values) if values else 0.0,
        "target_hits": float(sum(outcome.exit_reason == "target_hit" for outcome in outcomes)),
        "stop_hits": float(sum(outcome.exit_reason == "stop_hit" for outcome in outcomes)),
        "eod_exits": float(
            sum(
                outcome.exit_reason in {"end_of_session", "no_following_bar"}
                for outcome in outcomes
            ),
        ),
    }


def _outcomes_for_dates(outcomes: list[Any], trade_dates: set[date]) -> list[Any]:
    return [
        outcome for outcome in outcomes
        if outcome.entry_time.date() in trade_dates
    ]


def _find_current_lead(candidates: list[Candidate]) -> Candidate:
    expected = (
        "mgc_lookback_breakout_walk_base:lb10:buf0:delta0:cl0.5:end1030:"
        "filterbar8:maxday1_gap0"
    )
    for candidate in candidates:
        if (
            candidate.strategy_id == expected
            and abs(candidate.target_points - 25.0) < 0.01
            and abs(candidate.stop_points - 15.0) < 0.01
        ):
            return candidate
    raise RuntimeError("current MGC lookback lead was not built")


def _write_csv(path: str, rows: Iterable[dict[str, object]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADER, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_report(
    path: str,
    *,
    bars: list[Any],
    candidates: list[Candidate],
    rows: list[dict[str, object]],
    adaptive_holdouts_by_config: dict[str, list[Any]],
    current_lead_rows: list[dict[str, object]],
    frozen_leaders: list[dict[str, object]],
    configs: list[tuple[int, int]],
    minimum_train_trades: int,
) -> None:
    holdout_rows = [row for row in rows if row["sample"] == "holdout"]
    lines = [
        "# MGC Lookback Breakout Walk-Forward",
        "",
        "Status: chronological validation for the refined MGC lookback-breakout normal lead.",
        "",
        "## Source",
        "",
        f"- rows: `{len(bars)}`",
        f"- dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        f"- unique dates: `{len({bar.trade_date for bar in bars})}`",
        f"- candidates: `{len(candidates)}`",
        f"- windows: `{', '.join(f'{a}x{b}' for a, b in configs)}`",
        f"- minimum training trades for adaptive selection: `{minimum_train_trades}`",
        "- instrument: `MGC`, one-minute Sierra order-flow export",
        "",
        "## Adaptive Walk-Forward Summary",
        "",
        "Each window selects the best nearby lookback candidate on the training dates, "
        "then scores that exact candidate on the following unseen holdout dates.",
        "",
        "| Config | Windows | Trades | Net | Avg | PF | Max DD | Pos Windows | Neg Windows |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for config_id in sorted(adaptive_holdouts_by_config):
        config_rows = [row for row in holdout_rows if row["config"] == config_id]
        windows = [float(row["net_usd"]) for row in config_rows]
        outcomes = adaptive_holdouts_by_config[config_id]
        summary = _aggregate_summary(outcomes, windows)
        lines.append(
            "| "
            f"{config_id} | {summary['windows']} | {summary['trades']} | "
            f"{summary['net_usd']} | {summary['average_trade_usd']} | "
            f"{summary['profit_factor']} | {summary['max_drawdown_usd']} | "
            f"{summary['positive_windows']} | {summary['negative_windows']} |"
        )

    lines.extend(
        [
            "",
            "## Frozen Current Lead",
            "",
            "These rows freeze the current refined lead upfront and evaluate the same "
            "rolling holdout slices.",
            "",
            "| Config | Trades | Net | Avg | PF | Max DD | Pos Windows | Neg Windows | Worst Window |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    for row in current_lead_rows:
        lines.append(
            "| "
            f"{row['config']} | {row['trades']} | {row['net_usd']} | "
            f"{row['average_trade_usd']} | {row['profit_factor']} | "
            f"{row['max_drawdown_usd']} | {row['positive_windows']} | "
            f"{row['negative_windows']} | {row['worst_window_usd']} |"
        )

    lines.extend(
        [
            "",
            "## Frozen Leaderboard",
            "",
            "This ranks nearby frozen candidates on the same holdout slices. It is a "
            "robustness screen, not permission to keep optimizing on holdout data.",
            "",
            "| Rank | Target | Stop | Trades | Net | Min Config Net | Min PF | Max DD | Pos/Windows | Worst Window | Strategy |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ],
    )
    for rank, row in enumerate(frozen_leaders, start=1):
        lines.append(
            "| "
            f"{rank} | {_format_number(float(row['target_points']))} | "
            f"{_format_number(float(row['stop_points']))} | {row['total_trades']} | "
            f"{_format_number(float(row['total_net_usd']))} | "
            f"{_format_number(float(row['minimum_config_net_usd']))} | "
            f"{_format_number(float(row['minimum_profit_factor']))} | "
            f"{_format_number(float(row['max_drawdown_usd']))} | "
            f"{row['positive_windows']}/{row['window_count']} | "
            f"{_format_number(float(row['worst_window_usd']))} | "
            f"`{row['strategy_id']}` |"
        )

    lines.extend(
        [
            "",
            "## Selection Stability",
            "",
            "| Config | Distinct Selected Candidates | Most Common Selection |",
            "| --- | ---: | --- |",
        ],
    )
    for config_id in sorted({row["config"] for row in rows}):
        train_rows = [
            row for row in rows
            if row["config"] == config_id and row["sample"] == "train"
        ]
        counts: dict[str, int] = {}
        for row in train_rows:
            strategy = str(row["selected_strategy_id"])
            counts[strategy] = counts.get(strategy, 0) + 1
        most_common = max(counts.items(), key=lambda item: item[1]) if counts else ("none", 0)
        lines.append(
            "| "
            f"{config_id} | {len(counts)} | `{most_common[0]}` ({most_common[1]}) |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "A deployable MGC normal bot needs positive frozen holdout behavior across "
            "multiple window sizes, acceptable negative-window behavior, and then "
            "replay/mechanics validation. Adaptive selection is included to detect "
            "whether the edge is stable enough to choose from recent history; the "
            "frozen current lead remains the cleaner implementation candidate if it "
            "survives.",
            "",
        ],
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def _aggregate_summary(outcomes: list[Any], windows: list[float]) -> dict[str, object]:
    values = [outcome.net_usd for outcome in outcomes]
    positive = [value for value in values if value > 0.0]
    negative = [value for value in values if value < 0.0]
    return {
        "windows": len(windows),
        "trades": len(outcomes),
        "net_usd": _format_number(sum(values)),
        "average_trade_usd": _format_number(statistics.mean(values) if values else 0.0),
        "profit_factor": _format_number(sum(positive) / abs(sum(negative)) if negative else 999.0),
        "max_drawdown_usd": _format_number(_max_drawdown(values)),
        "positive_windows": sum(value > 0.0 for value in windows),
        "negative_windows": sum(value < 0.0 for value in windows),
    }


def _max_drawdown(values: list[float]) -> float:
    peak = 0.0
    equity = 0.0
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
