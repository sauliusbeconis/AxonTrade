#!/usr/bin/env python3
"""Research combined MNQ A+ and faster-B eval-pass policies."""

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


DEFAULT_OUTPUT = "reports/mnq-eval-pass-combined-ab.csv"
DEFAULT_REPORT_OUTPUT = "reports/mnq-eval-pass-combined-ab.md"
DEFAULT_TRAIN_DATE_COUNTS = "120,180,240"
DEFAULT_HOLDOUT_DATE_COUNTS = "40,40,60"


@dataclass(frozen=True)
class TaggedOutcome:
    module: str
    outcome: object


@dataclass(frozen=True)
class PolicyResult:
    policy_id: str
    description: str
    tagged_outcomes: list[TaggedOutcome]


SUMMARY_HEADER = [
    "schema_version",
    "policy_id",
    "description",
    "trades",
    "a_plus_trades",
    "b_trades",
    "net_usd",
    "average_trade_usd",
    "win_rate",
    "profit_factor",
    "max_drawdown_usd",
    "worst_trade_usd",
    "worst_two_trade_sum_usd",
    "worst_three_trade_sum_usd",
    "max_consecutive_losses",
    "average_calendar_gap_between_signals",
    "max_calendar_gap_between_signals",
    "calendar_pass_rate",
    "calendar_fail_rate",
    "calendar_timeout_rate",
    "calendar_median_calendar_days_to_pass",
    "calendar_median_trade_days_to_pass",
    "signal_pass_rate",
    "signal_fail_rate",
    "signal_timeout_rate",
    "signal_median_calendar_days_to_pass",
    "signal_median_trade_days_to_pass",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Research combined MNQ A+ and B eval-pass policies.",
    )
    parser.add_argument("input", nargs="?", help="MNQ Sierra orderflow export path.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--symbol", default="MNQU26-CME")
    parser.add_argument("--train-date-counts", default=DEFAULT_TRAIN_DATE_COUNTS)
    parser.add_argument("--holdout-date-counts", default=DEFAULT_HOLDOUT_DATE_COUNTS)
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
    trailing = _load_module(
        "run_mnq_eval_pass_trailing_refine.py",
        "mnq_eval_pass_trailing_refine",
    )
    newlead = _load_module(
        "run_mnq_eval_pass_wave_rider_new_lead_refine.py",
        "mnq_eval_pass_wave_rider_new_lead_refine",
    )
    walk = _load_module(
        "run_mnq_eval_pass_trailing_walk_forward.py",
        "mnq_eval_pass_trailing_walk_forward",
    )

    input_path = args.input or wave.DEFAULT_INPUT
    bars = wave._load_feature_bars(input_path)
    bars_by_date = wave._bars_by_date(bars)
    trade_dates = sorted(bars_by_date)
    rows_by_index = wave._rows_by_global_index(bars_by_date)

    a_plus_outcomes = _a_plus_outcomes(
        wave,
        deep,
        newlead,
        bars_by_date,
        rows_by_index=rows_by_index,
        symbol=args.symbol,
    )
    b_fast_outcomes = _b_outcomes(
        wave,
        deep,
        cadence,
        trailing,
        walk,
        bars_by_date,
        rows_by_index=rows_by_index,
        symbol=args.symbol,
        target_usd=650.0,
        stop_usd=450.0,
    )
    b_defensive_outcomes = _b_outcomes(
        wave,
        deep,
        cadence,
        trailing,
        walk,
        bars_by_date,
        rows_by_index=rows_by_index,
        symbol=args.symbol,
        target_usd=500.0,
        stop_usd=450.0,
    )

    policies = _policies(a_plus_outcomes, b_fast_outcomes, b_defensive_outcomes)
    summary_rows = [
        _summary_row(wave, trailing, policy, trade_dates)
        for policy in policies
    ]
    configs = _parse_configs(args.train_date_counts, args.holdout_date_counts)
    holdout_rows = _holdout_rows(wave, trailing, policies, trade_dates, configs)
    overlap = _overlap_summary(a_plus_outcomes, b_fast_outcomes)
    breakdown_rows = _breakdown_rows(
        _outcomes(_policy_by_id(policies, "ab_earliest_one_per_day_fast")),
    )

    _write_csv(args.output, summary_rows)
    _write_report(
        args.report_output,
        bars=bars,
        summary_rows=summary_rows,
        holdout_rows=holdout_rows,
        overlap=overlap,
        breakdown_rows=breakdown_rows,
    )
    combined = _row_by_policy(summary_rows, "ab_earliest_one_per_day_fast")
    print(
        f"wrote {len(summary_rows)} MNQ A+B policy rows to {args.output}; "
        f"combined_pass={float(combined['calendar_pass_rate']):.3f} "
        f"combined_fail={float(combined['calendar_fail_rate']):.3f} "
        f"signal_pass={float(combined['signal_pass_rate']):.3f}",
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


def _a_plus_outcomes(
    wave,
    deep,
    newlead,
    bars_by_date: dict[date, list[object]],
    *,
    rows_by_index: dict[int, int],
    symbol: str,
) -> list[TaggedOutcome]:
    strategy_id = (
        "lookback_breakout_deep:lb40:buf2.5:delta600:cl0.5:"
        "start1000:end1230:skipfri0:filterabs1000"
    )
    signals = newlead._new_lead_signals(
        wave,
        deep,
        bars_by_date,
        rows_by_index=rows_by_index,
        strategy_id=strategy_id,
        symbol=symbol,
    )
    risk = newlead._make_risk_profile(wave, 12, 726.0, 750.0)
    return [
        TaggedOutcome("A_PLUS", outcome)
        for outcome in wave._evaluate_signals(signals, bars_by_date, risk)
    ]


def _b_outcomes(
    wave,
    deep,
    cadence,
    trailing,
    walk,
    bars_by_date: dict[date, list[object]],
    *,
    rows_by_index: dict[int, int],
    symbol: str,
    target_usd: float,
    stop_usd: float,
) -> list[TaggedOutcome]:
    base_signals = deep._lookback_breakout_signals(
        wave,
        bars_by_date,
        strategy_id="cadence_trailing_combined_base:lb10:buf0:delta300:cl0.55:start1000:end1230",
        lookback_bars=10,
        buffer_points=0.0,
        delta_threshold=300.0,
        close_location_threshold=0.55,
        entry_start=time(10, 0),
        entry_end=time(12, 30),
        skip_friday=False,
        symbol=symbol,
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
    candidates = walk._build_candidates(
        wave,
        bars_by_date,
        base_signals=base_signals,
        features=features,
        filter_specs=trailing._selected_filter_specs(cadence),
        risks=trailing._dense_risk_grid(deep, wave),
        minimum_signal_days=50,
    )
    candidate = walk._find_candidate(
        candidates,
        "cadence_trailing:tue_wed:short:1000_1230:none",
        4,
        target_usd,
        stop_usd,
    )
    if candidate is None:
        raise RuntimeError(f"B candidate {target_usd}/{stop_usd} was not generated")
    return [TaggedOutcome("B_FAST", outcome) for outcome in candidate.outcomes]


def _policies(
    a_plus: list[TaggedOutcome],
    b_fast: list[TaggedOutcome],
    b_defensive: list[TaggedOutcome],
) -> list[PolicyResult]:
    return [
        PolicyResult(
            "a_plus_only",
            "Sparse A+ only, 12 MNQ, about $726/$750",
            _sort_tagged(a_plus),
        ),
        PolicyResult(
            "b_fast_only",
            "Faster B only, 4 MNQ, $650/$450",
            _sort_tagged(b_fast),
        ),
        PolicyResult(
            "b_defensive_only",
            "Defensive B only, 4 MNQ, $500/$450",
            _sort_tagged(b_defensive),
        ),
        PolicyResult(
            "ab_take_all_fast",
            "A+ plus B fast, take every signal; research-only reject",
            _sort_tagged(a_plus + b_fast),
        ),
        PolicyResult(
            "ab_earliest_one_per_day_fast",
            "A+ plus B fast, one trade/day, earliest signal; exact ties choose B",
            _one_per_day(a_plus + b_fast, tie_priority=("B_FAST", "A_PLUS")),
        ),
        PolicyResult(
            "ab_a_priority_one_per_day_fast",
            "A+ plus B fast, one trade/day, A+ priority",
            _one_per_day(a_plus + b_fast, module_priority=("A_PLUS", "B_FAST")),
        ),
        PolicyResult(
            "ab_earliest_one_per_day_defensive",
            "A+ plus defensive B, one trade/day, earliest signal; exact ties choose B",
            _one_per_day(a_plus + b_defensive, tie_priority=("B_FAST", "A_PLUS")),
        ),
    ]


def _one_per_day(
    tagged_outcomes: list[TaggedOutcome],
    *,
    tie_priority: tuple[str, ...] | None = None,
    module_priority: tuple[str, ...] | None = None,
) -> list[TaggedOutcome]:
    by_date: dict[date, list[TaggedOutcome]] = defaultdict(list)
    for tagged in tagged_outcomes:
        by_date[tagged.outcome.entry_time.date()].append(tagged)
    selected = []
    for values in by_date.values():
        if module_priority is not None:
            priority = {module: index for index, module in enumerate(module_priority)}
            selected.append(
                sorted(
                    values,
                    key=lambda tagged: (
                        priority.get(tagged.module, len(priority)),
                        tagged.outcome.entry_time,
                    ),
                )[0],
            )
        else:
            priority = {
                module: index
                for index, module in enumerate(tie_priority or ())
            }
            selected.append(
                sorted(
                    values,
                    key=lambda tagged: (
                        tagged.outcome.entry_time,
                        priority.get(tagged.module, len(priority)),
                    ),
                )[0],
            )
    return _sort_tagged(selected)


def _summary_row(
    wave,
    trailing,
    policy: PolicyResult,
    trade_dates: list[date],
) -> dict[str, object]:
    outcomes = _outcomes(policy)
    values = [outcome.net_usd for outcome in outcomes]
    positive = [value for value in values if value > 0.0]
    negative = [value for value in values if value < 0.0]
    calendar_metrics = trailing._simulate_trailing_calendar_attempts(outcomes, trade_dates)
    signal_metrics = trailing._simulate_trailing_signal_attempts(outcomes)
    gaps = _gap_metrics(outcomes)
    counts = Counter(tagged.module for tagged in policy.tagged_outcomes)
    return {
        "schema_version": 1,
        "policy_id": policy.policy_id,
        "description": policy.description,
        "trades": len(outcomes),
        "a_plus_trades": counts["A_PLUS"],
        "b_trades": counts["B_FAST"],
        "net_usd": _format_number(sum(values)),
        "average_trade_usd": _format_number(
            statistics.mean(values) if values else 0.0,
        ),
        "win_rate": _format_number(len(positive) / len(values) if values else 0.0),
        "profit_factor": _format_number(
            sum(positive) / abs(sum(negative)) if negative else 999.0,
        ),
        "max_drawdown_usd": _format_number(wave._max_drawdown(values)),
        "worst_trade_usd": _format_number(min(values) if values else 0.0),
        "worst_two_trade_sum_usd": _format_number(_worst_n_sum(values, 2)),
        "worst_three_trade_sum_usd": _format_number(_worst_n_sum(values, 3)),
        "max_consecutive_losses": _max_consecutive_losses(values),
        "average_calendar_gap_between_signals": _format_number(gaps["average"]),
        "max_calendar_gap_between_signals": _format_number(gaps["maximum"]),
        "calendar_pass_rate": _format_number(calendar_metrics["pass_rate"]),
        "calendar_fail_rate": _format_number(calendar_metrics["fail_rate"]),
        "calendar_timeout_rate": _format_number(calendar_metrics["timeout_rate"]),
        "calendar_median_calendar_days_to_pass": _format_number(
            calendar_metrics["median_calendar_days_to_pass"],
        ),
        "calendar_median_trade_days_to_pass": _format_number(
            calendar_metrics["median_trade_days_to_pass"],
        ),
        "signal_pass_rate": _format_number(signal_metrics["pass_rate"]),
        "signal_fail_rate": _format_number(signal_metrics["fail_rate"]),
        "signal_timeout_rate": _format_number(signal_metrics["timeout_rate"]),
        "signal_median_calendar_days_to_pass": _format_number(
            signal_metrics["median_calendar_days_to_pass"],
        ),
        "signal_median_trade_days_to_pass": _format_number(
            signal_metrics["median_trade_days_to_pass"],
        ),
    }


def _holdout_rows(
    wave,
    trailing,
    policies: list[PolicyResult],
    trade_dates: list[date],
    configs: list[tuple[int, int]],
) -> list[dict[str, object]]:
    rows = []
    for policy in policies:
        if policy.policy_id == "ab_take_all_fast":
            continue
        for train_count, holdout_count in configs:
            holdout_windows = []
            holdout_outcomes = []
            holdout_dates = []
            max_start = len(trade_dates) - train_count - holdout_count
            for start_index in range(0, max_start + 1, holdout_count):
                window_dates = trade_dates[
                    start_index + train_count:
                    start_index + train_count + holdout_count
                ]
                window_date_set = set(window_dates)
                window_outcomes = [
                    tagged.outcome
                    for tagged in policy.tagged_outcomes
                    if tagged.outcome.entry_time.date() in window_date_set
                ]
                holdout_windows.append(sum(outcome.net_usd for outcome in window_outcomes))
                holdout_outcomes.extend(window_outcomes)
                holdout_dates.extend(window_dates)
            values = [outcome.net_usd for outcome in holdout_outcomes]
            positive = [value for value in values if value > 0.0]
            negative = [value for value in values if value < 0.0]
            calendar_metrics = trailing._simulate_trailing_calendar_attempts(
                holdout_outcomes,
                holdout_dates,
            )
            signal_metrics = trailing._simulate_trailing_signal_attempts(holdout_outcomes)
            rows.append(
                {
                    "policy_id": policy.policy_id,
                    "config": f"{train_count}x{holdout_count}",
                    "windows": len(holdout_windows),
                    "trades": len(holdout_outcomes),
                    "net_usd": _format_number(sum(values)),
                    "profit_factor": _format_number(
                        sum(positive) / abs(sum(negative)) if negative else 999.0,
                    ),
                    "max_drawdown_usd": _format_number(wave._max_drawdown(values)),
                    "positive_windows": sum(value > 0.0 for value in holdout_windows),
                    "negative_windows": sum(value < 0.0 for value in holdout_windows),
                    "calendar_pass_rate": _format_number(calendar_metrics["pass_rate"]),
                    "calendar_fail_rate": _format_number(calendar_metrics["fail_rate"]),
                    "signal_pass_rate": _format_number(signal_metrics["pass_rate"]),
                    "signal_fail_rate": _format_number(signal_metrics["fail_rate"]),
                },
            )
    return rows


def _overlap_summary(
    a_plus: list[TaggedOutcome],
    b_fast: list[TaggedOutcome],
) -> dict[str, object]:
    a_times = {tagged.outcome.entry_time for tagged in a_plus}
    b_times = {tagged.outcome.entry_time for tagged in b_fast}
    a_dates = {tagged.outcome.entry_time.date() for tagged in a_plus}
    b_dates = {tagged.outcome.entry_time.date() for tagged in b_fast}
    return {
        "a_signals": len(a_plus),
        "b_signals": len(b_fast),
        "exact_datetime_overlap": len(a_times & b_times),
        "same_date_overlap": len(a_dates & b_dates),
        "a_same_date_overlap_rate": (
            len(a_dates & b_dates) / len(a_dates) if a_dates else 0.0
        ),
        "b_same_date_overlap_rate": (
            len(a_dates & b_dates) / len(b_dates) if b_dates else 0.0
        ),
    }


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
    summary_rows: list[dict[str, object]],
    holdout_rows: list[dict[str, object]],
    overlap: dict[str, object],
    breakdown_rows: list[dict[str, object]],
) -> None:
    combined = _row_by_policy(summary_rows, "ab_earliest_one_per_day_fast")
    lines = [
        "# MNQ Eval-Pass Combined A+B Research",
        "",
        "Status: combined sparse A+ and faster-B policy research for MNQ eval pass.",
        "",
        "## Source",
        "",
        f"- rows: `{len(bars)}`",
        f"- dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        f"- unique dates: `{len({bar.trade_date for bar in bars})}`",
        "- eval trailing floor: `min(0, high_water - 1000)`",
        "- pass target: `$1250` with `50%` consistency",
        "- calendar attempts use `30` calendar days and `12` max trade days",
        "",
        "## Overlap",
        "",
        f"- A+ signals: `{overlap['a_signals']}`",
        f"- B signals: `{overlap['b_signals']}`",
        f"- exact same-bar overlap: `{overlap['exact_datetime_overlap']}`",
        f"- same-date overlap: `{overlap['same_date_overlap']}` "
        f"(`{float(overlap['a_same_date_overlap_rate']) * 100:.1f}%` of A+, "
        f"`{float(overlap['b_same_date_overlap_rate']) * 100:.1f}%` of B)",
        "",
        "## Policy Summary",
        "",
        "| Policy | Trades | A+ | B | Net | Win | PF | DD | Worst 2 | Worst 3 | "
        "Max Loss Streak | Cal Pass | Cal Fail | Cal Med Days | Cal Med Trades | "
        "Sig Pass | Sig Fail | Sig Med Days | Sig Med Trades | Avg Gap | Max Gap |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | "
        "---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary_rows:
        lines.append(
            "| "
            f"`{row['policy_id']}` | {row['trades']} | {row['a_plus_trades']} | "
            f"{row['b_trades']} | {row['net_usd']} | "
            f"{float(row['win_rate']) * 100:.1f}% | {row['profit_factor']} | "
            f"{row['max_drawdown_usd']} | {row['worst_two_trade_sum_usd']} | "
            f"{row['worst_three_trade_sum_usd']} | {row['max_consecutive_losses']} | "
            f"{float(row['calendar_pass_rate']) * 100:.1f}% | "
            f"{float(row['calendar_fail_rate']) * 100:.1f}% | "
            f"{row['calendar_median_calendar_days_to_pass']} | "
            f"{row['calendar_median_trade_days_to_pass']} | "
            f"{float(row['signal_pass_rate']) * 100:.1f}% | "
            f"{float(row['signal_fail_rate']) * 100:.1f}% | "
            f"{row['signal_median_calendar_days_to_pass']} | "
            f"{row['signal_median_trade_days_to_pass']} | "
            f"{row['average_calendar_gap_between_signals']}d | "
            f"{row['max_calendar_gap_between_signals']}d |"
        )

    lines.extend(
        [
            "",
            "## Frozen Holdout",
            "",
            "| Policy | Config | Windows | Trades | Net | PF | DD | Positive | Negative | "
            "Cal Pass | Cal Fail | Sig Pass | Sig Fail |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | "
            "---: | ---: | ---: | ---: |",
        ],
    )
    for row in holdout_rows:
        lines.append(
            "| "
            f"`{row['policy_id']}` | {row['config']} | {row['windows']} | "
            f"{row['trades']} | {row['net_usd']} | {row['profit_factor']} | "
            f"{row['max_drawdown_usd']} | {row['positive_windows']} | "
            f"{row['negative_windows']} | "
            f"{float(row['calendar_pass_rate']) * 100:.1f}% | "
            f"{float(row['calendar_fail_rate']) * 100:.1f}% | "
            f"{float(row['signal_pass_rate']) * 100:.1f}% | "
            f"{float(row['signal_fail_rate']) * 100:.1f}% |"
        )

    lines.extend(
        [
            "",
            "## Combined Candidate Breakdown",
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
            "## Eval Time Estimate",
            "",
            "For the build candidate `ab_earliest_one_per_day_fast`:",
            "",
            f"- from a random calendar start, historical pass rate was "
            f"`{float(combined['calendar_pass_rate']) * 100:.1f}%` within the "
            f"`30`-day eval horizon, with fail rate "
            f"`{float(combined['calendar_fail_rate']) * 100:.1f}%`;",
            f"- successful random-start attempts had median pass time "
            f"`{combined['calendar_median_calendar_days_to_pass']}` calendar days "
            f"and `{combined['calendar_median_trade_days_to_pass']}` trade days;",
            f"- from a valid signal start, historical pass rate was "
            f"`{float(combined['signal_pass_rate']) * 100:.1f}%`, fail rate "
            f"`{float(combined['signal_fail_rate']) * 100:.1f}%`, and median "
            f"pass time `{combined['signal_median_calendar_days_to_pass']}` "
            f"calendar days / `{combined['signal_median_trade_days_to_pass']}` "
            "trade days.",
            "",
            "Practical expectation: if the account is started on a random day, a "
            "reasonable planning estimate is about `2-3` calendar weeks when it "
            "passes. If started on a valid signal day, the median historical pass "
            "path was about `4` traded signals, not a guaranteed two-day pass.",
            "",
            "## Decision",
            "",
            "The build candidate is `ab_earliest_one_per_day_fast`: one combined bot, "
            "A+ and B signals both enabled, exactly one trade per day, earliest "
            "valid signal wins, exact same-bar ties choose B for lower per-trade "
            "risk.",
            "",
            "`ab_take_all_fast` is rejected for eval routing because it improves "
            "calendar pass rate but pushes fail rate to an unacceptable level.",
            "",
        ],
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def _policy_by_id(policies: list[PolicyResult], policy_id: str) -> PolicyResult:
    for policy in policies:
        if policy.policy_id == policy_id:
            return policy
    raise KeyError(policy_id)


def _row_by_policy(rows: list[dict[str, object]], policy_id: str) -> dict[str, object]:
    for row in rows:
        if row["policy_id"] == policy_id:
            return row
    raise KeyError(policy_id)


def _outcomes(policy: PolicyResult) -> list[object]:
    return [tagged.outcome for tagged in policy.tagged_outcomes]


def _sort_tagged(values: Iterable[TaggedOutcome]) -> list[TaggedOutcome]:
    return sorted(values, key=lambda tagged: tagged.outcome.entry_time)


def _gap_metrics(outcomes: list[object]) -> dict[str, float]:
    dates = sorted({outcome.entry_time.date() for outcome in outcomes})
    gaps = [
        float((right - left).days)
        for left, right in zip(dates, dates[1:])
    ]
    return {
        "average": statistics.mean(gaps) if gaps else 0.0,
        "maximum": max(gaps) if gaps else 0.0,
    }


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


def _breakdown_key(value: str) -> tuple[int, str]:
    try:
        return (0, f"{int(value):04d}")
    except ValueError:
        return (1, value)


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


def _format_number(value: float) -> str:
    if not math.isfinite(value):
        return "0"
    formatted = f"{value:.8f}".rstrip("0").rstrip(".")
    return formatted if formatted else "0"


if __name__ == "__main__":
    raise SystemExit(main())
