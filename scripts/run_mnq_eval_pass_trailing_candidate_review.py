#!/usr/bin/env python3
"""Focused review of frozen MNQ trailing eval-pass candidates."""

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
from typing import Iterable


DEFAULT_OUTPUT = "reports/mnq-eval-pass-wave-rider-trailing-candidate-review.csv"
DEFAULT_REPORT_OUTPUT = (
    "reports/mnq-eval-pass-wave-rider-trailing-candidate-review.md"
)
DEFAULT_TRAIN_DATE_COUNTS = "120,180,240"
DEFAULT_HOLDOUT_DATE_COUNTS = "40,40,60"

CANDIDATE_PROFILES = [
    (
        "primary_fast_4mnq_650_450",
        "cadence_trailing:tue_wed:short:1000_1230:none",
        4,
        650.0,
        450.0,
    ),
    (
        "same_signal_shorter_window_4mnq_650_450",
        "cadence_trailing:tue_wed:short:1000_1130:none",
        4,
        650.0,
        450.0,
    ),
    (
        "lower_target_4mnq_600_450",
        "cadence_trailing:tue_wed:short:1000_1230:none",
        4,
        600.0,
        450.0,
    ),
    (
        "lower_target_lower_fail_4mnq_500_450",
        "cadence_trailing:tue_wed:short:1000_1230:none",
        4,
        500.0,
        450.0,
    ),
    (
        "wide_stop_4mnq_500_700",
        "cadence_trailing:tue_wed:short:1000_1230:none",
        4,
        500.0,
        700.0,
    ),
    (
        "smaller_size_3mnq_600_450",
        "cadence_trailing:tue_wed:short:1000_1230:none",
        3,
        600.0,
        450.0,
    ),
]

SUMMARY_HEADER = [
    "schema_version",
    "candidate",
    "strategy_id",
    "quantity",
    "target_net_usd",
    "stop_net_usd",
    "target_points",
    "stop_points",
    "trades",
    "net_usd",
    "average_trade_usd",
    "profit_factor",
    "win_rate",
    "max_drawdown_usd",
    "worst_trade_usd",
    "worst_two_trade_sum_usd",
    "worst_three_trade_sum_usd",
    "max_consecutive_losses",
    "trailing_calendar_pass_rate",
    "trailing_calendar_fail_rate",
    "trailing_signal_pass_rate",
    "trailing_signal_fail_rate",
    "trailing_signal_median_trade_days_to_pass",
    "average_calendar_gap_between_signals",
    "max_calendar_gap_between_signals",
    "average_trade_day_gap_between_signals",
    "max_trade_day_gap_between_signals",
]


@dataclass(frozen=True)
class ReviewedCandidate:
    name: str
    candidate: object
    signals: list[object]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Review frozen MNQ trailing eval-pass candidates.",
    )
    parser.add_argument("input", nargs="?", help="MNQ Sierra orderflow export path.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--symbol", default="MNQU26-CME")
    parser.add_argument("--train-date-counts", default=DEFAULT_TRAIN_DATE_COUNTS)
    parser.add_argument("--holdout-date-counts", default=DEFAULT_HOLDOUT_DATE_COUNTS)
    args = parser.parse_args()

    walk = _load_module(
        "run_mnq_eval_pass_trailing_walk_forward.py",
        "mnq_eval_pass_trailing_walk_forward",
    )
    trailing = walk._load_module(
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
        strategy_id="cadence_trailing_review_base:lb10:buf0:delta300:cl0.55:start1000:end1230",
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
    filter_specs = trailing._selected_filter_specs(cadence)
    signals_by_strategy = _signals_by_strategy(wave, base_signals, features, filter_specs)
    candidates = walk._build_candidates(
        wave,
        bars_by_date,
        base_signals=base_signals,
        features=features,
        filter_specs=filter_specs,
        risks=trailing._dense_risk_grid(deep, wave),
        minimum_signal_days=50,
    )
    reviewed = _reviewed_candidates(walk, candidates, signals_by_strategy)
    if not reviewed:
        raise RuntimeError("no reviewed candidates matched the generated candidate pool")
    configs = walk._parse_configs(args.train_date_counts, args.holdout_date_counts)
    summary_rows = [
        _summary_row(wave, trailing, reviewed_candidate, trade_dates)
        for reviewed_candidate in reviewed
    ]
    holdout_rows = _holdout_rows(walk, wave, trailing, reviewed, trade_dates, configs)
    stress_rows = _slippage_rows(wave, trailing, bars_by_date, trade_dates, reviewed)
    breakdown_rows = _breakdown_rows(reviewed[0].candidate.outcomes)
    _write_csv(args.output, summary_rows)
    _write_report(
        args.report_output,
        bars=bars,
        reviewed=reviewed,
        summary_rows=summary_rows,
        holdout_rows=holdout_rows,
        stress_rows=stress_rows,
        breakdown_rows=breakdown_rows,
    )
    best = summary_rows[0]
    print(
        f"wrote {len(summary_rows)} MNQ trailing candidate review rows to "
        f"{args.output}; best={best['candidate']} "
        f"net={best['net_usd']} trail_cal_fail={best['trailing_calendar_fail_rate']}",
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


def _signals_by_strategy(
    wave,
    base_signals: list[object],
    features: list[dict[str, object]],
    filter_specs: list[object],
) -> dict[str, list[object]]:
    signals_by_strategy = {}
    for filter_spec in filter_specs:
        strategy_id = f"cadence_trailing:{filter_spec.filter_id}"
        signals_by_strategy[strategy_id] = [
            wave.Signal(
                strategy_id,
                signal.direction,
                signal.bar,
                f"{signal.notes}; trailing candidate review {filter_spec.filter_id}",
            )
            for signal, feature in zip(base_signals, features)
            if filter_spec.keep_signal(feature)
        ]
    return signals_by_strategy


def _reviewed_candidates(
    walk,
    candidates: list[object],
    signals_by_strategy: dict[str, list[object]],
) -> list[ReviewedCandidate]:
    reviewed = []
    for name, strategy_id, quantity, target, stop in CANDIDATE_PROFILES:
        candidate = walk._find_candidate(candidates, strategy_id, quantity, target, stop)
        if candidate is None:
            continue
        reviewed.append(
            ReviewedCandidate(
                name=name,
                candidate=candidate,
                signals=signals_by_strategy[strategy_id],
            ),
        )
    return reviewed


def _summary_row(
    wave,
    trailing,
    reviewed: ReviewedCandidate,
    trade_dates: list[date],
) -> dict[str, object]:
    candidate = reviewed.candidate
    outcomes = candidate.outcomes
    values = [outcome.net_usd for outcome in outcomes]
    positive = [value for value in values if value > 0.0]
    negative = [value for value in values if value < 0.0]
    calendar_metrics = trailing._simulate_trailing_calendar_attempts(outcomes, trade_dates)
    signal_metrics = trailing._simulate_trailing_signal_attempts(outcomes)
    gap_metrics = _gap_metrics(outcomes, trade_dates)
    return {
        "schema_version": 1,
        "candidate": reviewed.name,
        "strategy_id": candidate.strategy_id,
        "quantity": candidate.quantity,
        "target_net_usd": _format_number(candidate.target_net_usd),
        "stop_net_usd": _format_number(candidate.stop_net_usd),
        "target_points": _format_number(candidate.target_points),
        "stop_points": _format_number(candidate.stop_points),
        "trades": len(outcomes),
        "net_usd": _format_number(sum(values)),
        "average_trade_usd": _format_number(
            statistics.mean(values) if values else 0.0,
        ),
        "profit_factor": _format_number(
            sum(positive) / abs(sum(negative)) if negative else 999.0,
        ),
        "win_rate": _format_number(len(positive) / len(values) if values else 0.0),
        "max_drawdown_usd": _format_number(wave._max_drawdown(values)),
        "worst_trade_usd": _format_number(min(values) if values else 0.0),
        "worst_two_trade_sum_usd": _format_number(_worst_n_sum(values, 2)),
        "worst_three_trade_sum_usd": _format_number(_worst_n_sum(values, 3)),
        "max_consecutive_losses": _max_consecutive_losses(values),
        "trailing_calendar_pass_rate": _format_number(calendar_metrics["pass_rate"]),
        "trailing_calendar_fail_rate": _format_number(calendar_metrics["fail_rate"]),
        "trailing_signal_pass_rate": _format_number(signal_metrics["pass_rate"]),
        "trailing_signal_fail_rate": _format_number(signal_metrics["fail_rate"]),
        "trailing_signal_median_trade_days_to_pass": _format_number(
            signal_metrics["median_trade_days_to_pass"],
        ),
        **gap_metrics,
    }


def _gap_metrics(outcomes: list[object], trade_dates: list[date]) -> dict[str, object]:
    signal_dates = sorted({outcome.entry_time.date() for outcome in outcomes})
    trade_index = {trade_date: index for index, trade_date in enumerate(trade_dates)}
    calendar_gaps = [
        float((right - left).days)
        for left, right in zip(signal_dates, signal_dates[1:])
    ]
    trade_day_gaps = [
        float(trade_index[right] - trade_index[left])
        for left, right in zip(signal_dates, signal_dates[1:])
    ]
    return {
        "average_calendar_gap_between_signals": _format_number(
            statistics.mean(calendar_gaps) if calendar_gaps else 0.0,
        ),
        "max_calendar_gap_between_signals": _format_number(
            max(calendar_gaps) if calendar_gaps else 0.0,
        ),
        "average_trade_day_gap_between_signals": _format_number(
            statistics.mean(trade_day_gaps) if trade_day_gaps else 0.0,
        ),
        "max_trade_day_gap_between_signals": _format_number(
            max(trade_day_gaps) if trade_day_gaps else 0.0,
        ),
    }


def _holdout_rows(
    walk,
    wave,
    trailing,
    reviewed_candidates: list[ReviewedCandidate],
    trade_dates: list[date],
    configs: list[tuple[int, int]],
) -> list[dict[str, object]]:
    rows = []
    for reviewed in reviewed_candidates:
        for train_count, holdout_count in configs:
            summary = walk._frozen_numeric_summary(
                wave,
                trailing,
                reviewed.candidate,
                trade_dates=trade_dates,
                train_count=train_count,
                holdout_count=holdout_count,
            )
            rows.append(
                {
                    "candidate": reviewed.name,
                    "config": f"{train_count}x{holdout_count}",
                    **{
                        key: _format_number(value) if isinstance(value, float) else value
                        for key, value in summary.items()
                    },
                },
            )
    return rows


def _slippage_rows(
    wave,
    trailing,
    bars_by_date: dict[date, list[object]],
    trade_dates: list[date],
    reviewed_candidates: list[ReviewedCandidate],
) -> list[dict[str, object]]:
    rows = []
    for reviewed in reviewed_candidates[:4]:
        candidate = reviewed.candidate
        for slippage_ticks in (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 8.0):
            risk = _risk_with_slippage(wave, candidate, slippage_ticks)
            outcomes = wave._evaluate_signals(reviewed.signals, bars_by_date, risk)
            values = [outcome.net_usd for outcome in outcomes]
            calendar_metrics = trailing._simulate_trailing_calendar_attempts(
                outcomes,
                trade_dates,
            )
            signal_metrics = trailing._simulate_trailing_signal_attempts(outcomes)
            rows.append(
                {
                    "candidate": reviewed.name,
                    "slippage_ticks": _format_number(slippage_ticks),
                    "target_net_usd": _format_number(risk.target_net_usd),
                    "stop_net_usd": _format_number(risk.stop_net_usd),
                    "net_usd": _format_number(sum(values)),
                    "max_drawdown_usd": _format_number(wave._max_drawdown(values)),
                    "trailing_calendar_pass_rate": _format_number(
                        calendar_metrics["pass_rate"],
                    ),
                    "trailing_calendar_fail_rate": _format_number(
                        calendar_metrics["fail_rate"],
                    ),
                    "trailing_signal_pass_rate": _format_number(
                        signal_metrics["pass_rate"],
                    ),
                    "trailing_signal_fail_rate": _format_number(
                        signal_metrics["fail_rate"],
                    ),
                },
            )
    return rows


def _risk_with_slippage(wave, candidate: object, slippage_ticks: float) -> object:
    round_turn_cost = candidate.quantity * (
        2.0 * wave.COMMISSION_PER_SIDE_USD
        + slippage_ticks * wave.TICK_VALUE_USD
    )
    target_net_usd = (
        candidate.target_points
        * candidate.quantity
        * wave.POINT_VALUE_USD
        - round_turn_cost
    )
    stop_net_usd = (
        candidate.stop_points
        * candidate.quantity
        * wave.POINT_VALUE_USD
        + round_turn_cost
    )
    return wave.RiskProfile(
        quantity=candidate.quantity,
        target_net_usd=target_net_usd,
        stop_net_usd=stop_net_usd,
        target_points=candidate.target_points,
        stop_points=candidate.stop_points,
        round_turn_cost_usd=round_turn_cost,
    )


def _breakdown_rows(outcomes: list[object]) -> list[dict[str, object]]:
    rows = []
    for bucket_name, key_function in (
        ("year", lambda outcome: outcome.entry_time.year),
        (
            "quarter",
            lambda outcome: (
                outcome.entry_time.year,
                (outcome.entry_time.month - 1) // 3 + 1,
            ),
        ),
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
        for key in sorted(count_by_key):
            rows.append(
                {
                    "bucket_type": bucket_name,
                    "bucket": str(key),
                    "trades": count_by_key[key],
                    "net_usd": _format_number(net_by_key[key]),
                    "wins": wins_by_key[key],
                    "losses": losses_by_key[key],
                },
            )
    return rows


def _write_csv(path: str, rows: list[dict[str, object]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_HEADER, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_report(
    path: str,
    *,
    bars: list[object],
    reviewed: list[ReviewedCandidate],
    summary_rows: list[dict[str, object]],
    holdout_rows: list[dict[str, object]],
    stress_rows: list[dict[str, object]],
    breakdown_rows: list[dict[str, object]],
) -> None:
    lines = [
        "# MNQ Eval-Pass Wave Rider Trailing Candidate Review",
        "",
        "Status: focused robustness review for frozen faster-B MNQ candidates.",
        "",
        "## Source",
        "",
        f"- rows: `{len(bars)}`",
        f"- dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        f"- unique dates: `{len({bar.trade_date for bar in bars})}`",
        f"- reviewed candidates: `{len(reviewed)}`",
        "- trailing floor: `min(0, high_water - 1000)`",
        "- pass target: `$1250` with `50%` consistency",
        "",
        "## Candidate Summary",
        "",
        "| Candidate | Qty | Target | Stop | Trades | Net | PF | DD | Worst 2 | "
        "Worst 3 | Max Loss Streak | Trail Cal Pass | Trail Cal Fail | "
        "Trail Sig Pass | Trail Sig Fail | Median Pass Trades | Avg Gap | Max Gap |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | "
        "---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary_rows:
        lines.append(
            "| "
            f"`{row['candidate']}` | {row['quantity']} | {row['target_net_usd']} | "
            f"{row['stop_net_usd']} | {row['trades']} | {row['net_usd']} | "
            f"{row['profit_factor']} | {row['max_drawdown_usd']} | "
            f"{row['worst_two_trade_sum_usd']} | {row['worst_three_trade_sum_usd']} | "
            f"{row['max_consecutive_losses']} | "
            f"{float(row['trailing_calendar_pass_rate']) * 100:.1f}% | "
            f"{float(row['trailing_calendar_fail_rate']) * 100:.1f}% | "
            f"{float(row['trailing_signal_pass_rate']) * 100:.1f}% | "
            f"{float(row['trailing_signal_fail_rate']) * 100:.1f}% | "
            f"{row['trailing_signal_median_trade_days_to_pass']} | "
            f"{row['average_calendar_gap_between_signals']}d | "
            f"{row['max_calendar_gap_between_signals']}d |"
        )

    lines.extend(
        [
            "",
            "## Frozen Holdout Comparison",
            "",
            "| Candidate | Config | Windows | Trades | Net | PF | DD | Positive | Negative | "
            "Trail Cal Pass | Trail Cal Fail | Trail Sig Pass | Trail Sig Fail |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | "
            "---: | ---: | ---: |",
        ],
    )
    for row in holdout_rows:
        lines.append(
            "| "
            f"`{row['candidate']}` | {row['config']} | {row['windows']} | "
            f"{row['trades']} | {row['net_usd']} | {row['profit_factor']} | "
            f"{row['max_drawdown_usd']} | {row['positive_windows']} | "
            f"{row['negative_windows']} | "
            f"{float(row['trailing_calendar_pass_rate']) * 100:.1f}% | "
            f"{float(row['trailing_calendar_fail_rate']) * 100:.1f}% | "
            f"{float(row['trailing_signal_pass_rate']) * 100:.1f}% | "
            f"{float(row['trailing_signal_fail_rate']) * 100:.1f}% |"
        )

    lines.extend(
        [
            "",
            "## Slippage Stress",
            "",
            "| Candidate | Slip Ticks | Target | Stop | Net | DD | Trail Cal Pass | "
            "Trail Cal Fail | Trail Sig Pass | Trail Sig Fail |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    for row in stress_rows:
        lines.append(
            "| "
            f"`{row['candidate']}` | {row['slippage_ticks']} | "
            f"{row['target_net_usd']} | {row['stop_net_usd']} | "
            f"{row['net_usd']} | {row['max_drawdown_usd']} | "
            f"{float(row['trailing_calendar_pass_rate']) * 100:.1f}% | "
            f"{float(row['trailing_calendar_fail_rate']) * 100:.1f}% | "
            f"{float(row['trailing_signal_pass_rate']) * 100:.1f}% | "
            f"{float(row['trailing_signal_fail_rate']) * 100:.1f}% |"
        )

    lines.extend(
        [
            "",
            "## Primary Breakdown",
            "",
            "| Bucket Type | Bucket | Trades | Net | Wins | Losses |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ],
    )
    for row in breakdown_rows:
        lines.append(
            "| "
            f"{row['bucket_type']} | {row['bucket']} | {row['trades']} | "
            f"{row['net_usd']} | {row['wins']} | {row['losses']} |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The primary `4 MNQ` `$650/$450` row remains the best replay candidate. "
            "It has the strongest frozen holdout pass profile and its target is "
            "aligned with the `$650` daily profit objective.",
            "",
            "The `4 MNQ` `$500/$450` sibling is the main defensive fallback. It has "
            "lower trailing fail and smaller drawdown, but it usually needs more "
            "than two winning trades to pass because the target is below the "
            "`$625-$650` two-day eval geometry.",
            "",
            "The wide-stop rows are rejected for eval use despite high paper net. "
            "They increase the chance of damaging the trailing floor and are less "
            "aligned with the goal of controlled two-to-several-trade passing.",
            "",
        ],
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def _worst_n_sum(values: list[float], n: int) -> float:
    if len(values) < n:
        return sum(values)
    return min(sum(values[index:index + n]) for index in range(len(values) - n + 1))


def _max_consecutive_losses(values: Iterable[float]) -> int:
    current = 0
    maximum = 0
    for value in values:
        if value < 0.0:
            current += 1
            maximum = max(maximum, current)
        else:
            current = 0
    return maximum


def _format_number(value: float) -> str:
    if not math.isfinite(value):
        return "0"
    formatted = f"{value:.8f}".rstrip("0").rstrip(".")
    return formatted if formatted else "0"


if __name__ == "__main__":
    raise SystemExit(main())
