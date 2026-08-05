#!/usr/bin/env python3
"""Validate the frozen MGC strategy against Tradeify 50K Select rules."""

from __future__ import annotations

import argparse
import csv
import random
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, time, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_mgc_eval_pass_initial_scan as mgc_eval  # noqa: E402
import run_mgc_final_validation as final  # noqa: E402
import run_mgc_lookback_breakout_candidate_review as review  # noqa: E402
import run_mgc_lookback_trade_management as management  # noqa: E402
import run_mgc_normal_bot_research as normal  # noqa: E402
import run_tradeify_50k_mnq_strategy_research as account  # noqa: E402


DEFAULT_OUTPUT = "reports/tradeify-50k-mgc-strategy-sizing.csv"
DEFAULT_REPORT = "reports/tradeify-50k-mgc-strategy-research.md"
DEFAULT_AUDIT = "reports/tradeify-50k-mgc-strategy-trade-audit.csv"

STRATEGY_ID = final.STRATEGY_ID
MGC_POINT_VALUE_USD = 10.0
MGC_TICK_VALUE_USD = 1.0
MGC_ROUND_TURN_FEE_USD = 2.12
BASE_TOTAL_SLIPPAGE_TICKS = 2
STRESS_TOTAL_SLIPPAGE_TICKS = 6
INITIAL_STOP_POINTS = 15.0
EVALUATION_TARGET_USD = 3000.0
FUNDED_LOCK_TARGET_USD = 2100.0
MAX_DRAWDOWN_USD = 2000.0
CONSISTENCY_FRACTION = 0.40
RISK_RESERVE_USD = 100.0
MONTE_CARLO_RUNS = 10000
MONTE_CARLO_SESSIONS = 260
MONTE_CARLO_BLOCK_SESSIONS = 5


@dataclass(frozen=True)
class SizingPolicy:
    policy_id: str
    high_quantity: int
    middle_quantity: int
    high_to_middle_drawdown: float
    middle_to_low_drawdown: float

    def quantity(self, drawdown_usd: float) -> int:
        if drawdown_usd >= self.high_to_middle_drawdown:
            return self.high_quantity
        if drawdown_usd >= self.middle_to_low_drawdown:
            return self.middle_quantity
        return 1


@dataclass(frozen=True)
class StrategyMetrics:
    trades: int
    net_usd: float
    average_trade_usd: float
    profit_factor: float
    win_rate: float
    max_drawdown_usd: float
    worst_day_usd: float
    average_holding_minutes: float


@dataclass(frozen=True)
class AttemptResult:
    status: str
    calendar_days: float
    trade_days: int
    end_equity_usd: float
    max_drawdown_usd: float
    average_quantity: float


@dataclass(frozen=True)
class AttemptSummary:
    attempts: int
    pass_rate: float
    fail_rate: float
    risk_lock_rate: float
    timeout_rate: float
    median_calendar_days_to_pass: float
    median_trade_days_to_pass: float
    median_average_quantity: float
    p95_drawdown_usd: float


CSV_HEADER = [
    "schema_version",
    "policy_id",
    "high_quantity",
    "middle_quantity",
    "high_to_middle_drawdown",
    "middle_to_low_drawdown",
    "development_180_pass_rate",
    "development_180_fail_rate",
    "development_180_risk_lock_rate",
    "development_365_pass_rate",
    "development_365_fail_rate",
    "development_365_risk_lock_rate",
    "development_365_median_calendar_days",
    "development_mc_pass_rate",
    "development_mc_fail_rate",
    "development_mc_risk_lock_rate",
    "development_mc_p95_drawdown_usd",
    "holdout_mc_pass_rate",
    "holdout_mc_fail_rate",
    "holdout_mc_risk_lock_rate",
    "holdout_mc_p95_drawdown_usd",
    "full_365_pass_rate",
    "full_365_fail_rate",
    "full_365_risk_lock_rate",
    "funded_lock_365_rate",
    "funded_lock_365_fail_rate",
    "selected_on_development",
    "final_eligible",
]


AUDIT_HEADER = [
    "schema_version",
    "strategy_id",
    "direction",
    "entry_time",
    "exit_time",
    "entry_price",
    "exit_price",
    "exit_reason",
    "gross_points",
    "base_net_1_mgc_usd",
    "stress_net_1_mgc_usd",
    "holding_minutes",
    "notes",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the frozen MGC strategy for Tradeify 50K Select.",
    )
    parser.add_argument("input", nargs="?", default=normal.DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT)
    parser.add_argument("--audit-output", default=DEFAULT_AUDIT)
    parser.add_argument("--seed", type=int, default=20260805)
    args = parser.parse_args()

    core = mgc_eval._load_mnq_core()
    mgc_eval._patch_core_for_mgc(core)
    bars = core._load_feature_bars(args.input)
    bars_by_date = mgc_eval._active_bars_by_date(core._bars_by_date(bars))
    rows_by_index = core._rows_by_global_index(bars_by_date)
    trade_dates = sorted(bars_by_date)
    train_dates, validation_dates, holdout_dates = account._split_dates(trade_dates)
    development_dates = train_dates + validation_dates

    signals = final._lead_signals(core, bars_by_date, rows_by_index, symbol="MGC")
    management_spec = management.ManagementSpec(
        "breakeven:t25:s15:trig20",
        25.0,
        15.0,
        "breakeven",
        time(16, 30),
        20.0,
        0.0,
    )
    risk = review._risk(
        core,
        normal,
        target_points=management_spec.target_points,
        stop_points=management_spec.stop_points,
        slippage_ticks=0.0,
    )
    outcomes = management._evaluate_sequence(
        core,
        signals,
        bars_by_date,
        rows_by_index,
        risk,
        management_spec,
    )
    outcomes_by_date = {outcome.entry_time.date(): outcome for outcome in outcomes}
    print(
        f"loaded {len(bars)} MGC bars, {len(signals)} raw setups, "
        f"and {len(outcomes)} sequenced trades",
        flush=True,
    )

    date_sets = {
        "train": set(train_dates),
        "validation": set(validation_dates),
        "holdout": set(holdout_dates),
        "full": set(trade_dates),
    }
    base_metrics = {
        label: _strategy_metrics(
            _outcomes_for_dates(outcomes, dates),
            total_slippage_ticks=BASE_TOTAL_SLIPPAGE_TICKS,
        )
        for label, dates in date_sets.items()
    }
    stress_metrics = {
        label: _strategy_metrics(
            _outcomes_for_dates(outcomes, dates),
            total_slippage_ticks=STRESS_TOTAL_SLIPPAGE_TICKS,
        )
        for label, dates in date_sets.items()
    }

    policies = _sizing_policies()
    policy_rows: list[dict[str, object]] = []
    summaries_by_policy: dict[str, dict[str, AttemptSummary]] = {}
    for policy_index, policy in enumerate(policies):
        summaries = {
            "development_180": _historical_attempts(
                outcomes_by_date,
                development_dates,
                policy,
                horizon_calendar_days=180,
            ),
            "development_365": _historical_attempts(
                outcomes_by_date,
                development_dates,
                policy,
                horizon_calendar_days=365,
            ),
            "development_mc": _monte_carlo_attempts(
                outcomes_by_date,
                development_dates,
                policy,
                total_slippage_ticks=STRESS_TOTAL_SLIPPAGE_TICKS,
                seed=args.seed + policy_index,
            ),
            "holdout_mc": _monte_carlo_attempts(
                outcomes_by_date,
                holdout_dates,
                policy,
                total_slippage_ticks=STRESS_TOTAL_SLIPPAGE_TICKS,
                seed=args.seed + 100 + policy_index,
            ),
            "full_365": _historical_attempts(
                outcomes_by_date,
                trade_dates,
                policy,
                horizon_calendar_days=365,
            ),
            "funded_lock_365": _historical_attempts(
                outcomes_by_date,
                trade_dates,
                policy,
                horizon_calendar_days=365,
                profit_target_usd=FUNDED_LOCK_TARGET_USD,
                consistency_fraction=1.0,
            ),
        }
        summaries_by_policy[policy.policy_id] = summaries
        policy_rows.append(_policy_row(policy, summaries))

    development_eligible = [row for row in policy_rows if _development_eligible(row)]
    selected_row = (
        min(development_eligible, key=_development_rank_key)
        if development_eligible
        else None
    )
    selected_policy: SizingPolicy | None = None
    if selected_row is not None:
        selected_row["selected_on_development"] = True
        selected_policy = next(
            policy
            for policy in policies
            if policy.policy_id == selected_row["policy_id"]
        )
        selected_row["final_eligible"] = _final_eligible(
            selected_row,
            base_metrics,
            stress_metrics,
        )

    policy_rows.sort(key=_report_sort_key)
    _write_csv(args.output, CSV_HEADER, policy_rows)
    _write_audit(args.audit_output, outcomes)
    shuffled_drawdowns = _shuffled_drawdowns(
        outcomes,
        total_slippage_ticks=STRESS_TOTAL_SLIPPAGE_TICKS,
        seed=args.seed + 500,
    )
    _write_report(
        args.report_output,
        bars=bars,
        signals=signals,
        outcomes=outcomes,
        trade_dates=trade_dates,
        train_dates=train_dates,
        validation_dates=validation_dates,
        holdout_dates=holdout_dates,
        base_metrics=base_metrics,
        stress_metrics=stress_metrics,
        policy_rows=policy_rows,
        selected_row=selected_row,
        selected_policy=selected_policy,
        selected_summaries=(
            summaries_by_policy[selected_policy.policy_id]
            if selected_policy is not None
            else None
        ),
        shuffled_drawdowns=shuffled_drawdowns,
    )

    verdict = (
        "NON_REJECTED_STRATEGY_CANDIDATE"
        if selected_row is not None and bool(selected_row["final_eligible"])
        else "REJECT_AFTER_STRESS"
    )
    print(
        f"selected={selected_row['policy_id'] if selected_row else 'none'} "
        f"verdict={verdict} report={args.report_output}",
        flush=True,
    )
    return 0


def _sizing_policies() -> list[SizingPolicy]:
    return [
        SizingPolicy("fixed_1_mgc", 1, 1, -999999.0, -999999.0),
        SizingPolicy("fixed_2_mgc", 2, 2, -999999.0, -999999.0),
        SizingPolicy("fixed_3_mgc", 3, 3, -999999.0, -999999.0),
        SizingPolicy("adaptive_2_to_1_dd250", 2, 1, -250.0, -250.0),
        SizingPolicy("adaptive_2_to_1_dd500", 2, 1, -500.0, -500.0),
        SizingPolicy("adaptive_2_to_1_dd750", 2, 1, -750.0, -750.0),
        SizingPolicy("adaptive_2_to_1_dd1000", 2, 1, -1000.0, -1000.0),
        SizingPolicy("adaptive_3_2_1_dd250_750", 3, 2, -250.0, -750.0),
        SizingPolicy("adaptive_3_2_1_dd250_1000", 3, 2, -250.0, -1000.0),
        SizingPolicy("adaptive_3_2_1_dd500_1000", 3, 2, -500.0, -1000.0),
    ]


def _strategy_metrics(
    outcomes: list[Any],
    *,
    total_slippage_ticks: int,
) -> StrategyMetrics:
    values = [
        _net(outcome.gross_points, 1, total_slippage_ticks=total_slippage_ticks)
        for outcome in outcomes
    ]
    positives = [value for value in values if value > 0.0]
    negatives = [value for value in values if value < 0.0]
    daily: dict[date, float] = defaultdict(float)
    for outcome, value in zip(outcomes, values, strict=True):
        daily[outcome.entry_time.date()] += value
    return StrategyMetrics(
        trades=len(values),
        net_usd=sum(values),
        average_trade_usd=statistics.mean(values) if values else 0.0,
        profit_factor=sum(positives) / abs(sum(negatives)) if negatives else 999.0,
        win_rate=len(positives) / len(values) if values else 0.0,
        max_drawdown_usd=account._max_drawdown(values),
        worst_day_usd=min(daily.values()) if daily else 0.0,
        average_holding_minutes=(
            statistics.mean(outcome.holding_minutes for outcome in outcomes)
            if outcomes
            else 0.0
        ),
    )


def _historical_attempts(
    outcomes_by_date: dict[date, Any],
    available_dates: list[date],
    policy: SizingPolicy,
    *,
    horizon_calendar_days: int,
    profit_target_usd: float = EVALUATION_TARGET_USD,
    consistency_fraction: float = CONSISTENCY_FRACTION,
) -> AttemptSummary:
    if not available_dates:
        return _summarize_attempts([])
    last_date = available_dates[-1]
    results = []
    for start_index, start_date in enumerate(available_dates):
        end_date = start_date + timedelta(days=horizon_calendar_days)
        if end_date > last_date:
            continue
        dates = [
            trade_date
            for trade_date in available_dates[start_index:]
            if trade_date <= end_date
        ]
        results.append(
            _simulate_attempt(
                dates,
                outcomes_by_date,
                policy,
                total_slippage_ticks=BASE_TOTAL_SLIPPAGE_TICKS,
                profit_target_usd=profit_target_usd,
                consistency_fraction=consistency_fraction,
            ),
        )
    return _summarize_attempts(results)


def _monte_carlo_attempts(
    outcomes_by_date: dict[date, Any],
    source_dates: list[date],
    policy: SizingPolicy,
    *,
    total_slippage_ticks: int,
    seed: int,
) -> AttemptSummary:
    source = [
        outcomes_by_date[trade_date].gross_points
        if trade_date in outcomes_by_date
        else None
        for trade_date in source_dates
    ]
    if len(source) < MONTE_CARLO_BLOCK_SESSIONS:
        return _summarize_attempts([])
    blocks = [
        source[index : index + MONTE_CARLO_BLOCK_SESSIONS]
        for index in range(len(source) - MONTE_CARLO_BLOCK_SESSIONS + 1)
    ]
    rng = random.Random(seed)
    synthetic_start = date(2030, 1, 1)
    results = []
    for _ in range(MONTE_CARLO_RUNS):
        path: list[float | None] = []
        while len(path) < MONTE_CARLO_SESSIONS:
            path.extend(rng.choice(blocks))
        dates = [
            synthetic_start + timedelta(days=index)
            for index in range(MONTE_CARLO_SESSIONS)
        ]
        synthetic_outcomes = {
            trade_date: gross_points
            for trade_date, gross_points in zip(
                dates, path[:MONTE_CARLO_SESSIONS], strict=True
            )
            if gross_points is not None
        }
        results.append(
            _simulate_attempt(
                dates,
                synthetic_outcomes,
                policy,
                total_slippage_ticks=total_slippage_ticks,
            ),
        )
    return _summarize_attempts(results)


def _simulate_attempt(
    dates: list[date],
    outcomes_by_date: dict[date, Any],
    policy: SizingPolicy,
    *,
    total_slippage_ticks: int,
    profit_target_usd: float = EVALUATION_TARGET_USD,
    consistency_fraction: float = CONSISTENCY_FRACTION,
) -> AttemptResult:
    equity = 0.0
    high_water = 0.0
    floor = -MAX_DRAWDOWN_USD
    largest_winning_day = 0.0
    trade_days = 0
    quantities: list[int] = []
    max_drawdown = 0.0
    start_date = dates[0] if dates else date.min

    for trade_date in dates:
        raw_outcome = outcomes_by_date.get(trade_date)
        if raw_outcome is None:
            continue
        gross_points = (
            float(raw_outcome.gross_points)
            if hasattr(raw_outcome, "gross_points")
            else float(raw_outcome)
        )
        drawdown = equity - high_water
        requested_quantity = policy.quantity(drawdown)
        available_cushion = equity - floor
        quantity = requested_quantity
        while (
            quantity > 0
            and _nominal_stop_loss(quantity) + RISK_RESERVE_USD >= available_cushion
        ):
            quantity -= 1
        if quantity == 0:
            return AttemptResult(
                "risk_lock",
                float((trade_date - start_date).days + 1),
                trade_days,
                equity,
                max_drawdown,
                statistics.mean(quantities) if quantities else 0.0,
            )

        value = _net(
            gross_points,
            quantity,
            total_slippage_ticks=total_slippage_ticks,
        )
        trade_days += 1
        quantities.append(quantity)
        equity += value
        largest_winning_day = max(largest_winning_day, value)
        max_drawdown = min(max_drawdown, equity - high_water)
        if equity <= floor + 0.01:
            return AttemptResult(
                "fail",
                float((trade_date - start_date).days + 1),
                trade_days,
                equity,
                max_drawdown,
                statistics.mean(quantities),
            )
        high_water = max(high_water, equity)
        floor = max(floor, high_water - MAX_DRAWDOWN_USD)
        consistency_ok = (
            largest_winning_day <= max(equity, 0.01) * consistency_fraction + 0.01
        )
        if trade_days >= 3 and equity >= profit_target_usd - 0.01 and consistency_ok:
            return AttemptResult(
                "pass",
                float((trade_date - start_date).days + 1),
                trade_days,
                equity,
                max_drawdown,
                statistics.mean(quantities),
            )

    return AttemptResult(
        "timeout",
        0.0,
        trade_days,
        equity,
        max_drawdown,
        statistics.mean(quantities) if quantities else 0.0,
    )


def _summarize_attempts(results: list[AttemptResult]) -> AttemptSummary:
    attempts = len(results)
    passes = [result for result in results if result.status == "pass"]
    drawdowns = sorted(result.max_drawdown_usd for result in results)
    return AttemptSummary(
        attempts=attempts,
        pass_rate=len(passes) / attempts if attempts else 0.0,
        fail_rate=(
            sum(result.status == "fail" for result in results) / attempts
            if attempts
            else 0.0
        ),
        risk_lock_rate=(
            sum(result.status == "risk_lock" for result in results) / attempts
            if attempts
            else 0.0
        ),
        timeout_rate=(
            sum(result.status == "timeout" for result in results) / attempts
            if attempts
            else 0.0
        ),
        median_calendar_days_to_pass=(
            statistics.median(result.calendar_days for result in passes)
            if passes
            else 0.0
        ),
        median_trade_days_to_pass=(
            statistics.median(result.trade_days for result in passes) if passes else 0.0
        ),
        median_average_quantity=(
            statistics.median(result.average_quantity for result in results)
            if results
            else 0.0
        ),
        p95_drawdown_usd=account._percentile(drawdowns, 0.05) if drawdowns else 0.0,
    )


def _policy_row(
    policy: SizingPolicy,
    summaries: dict[str, AttemptSummary],
) -> dict[str, object]:
    dev180 = summaries["development_180"]
    dev365 = summaries["development_365"]
    dev_mc = summaries["development_mc"]
    holdout_mc = summaries["holdout_mc"]
    full365 = summaries["full_365"]
    funded = summaries["funded_lock_365"]
    return {
        "schema_version": 1,
        "policy_id": policy.policy_id,
        "high_quantity": policy.high_quantity,
        "middle_quantity": policy.middle_quantity,
        "high_to_middle_drawdown": account._fmt(policy.high_to_middle_drawdown),
        "middle_to_low_drawdown": account._fmt(policy.middle_to_low_drawdown),
        "development_180_pass_rate": account._fmt(dev180.pass_rate),
        "development_180_fail_rate": account._fmt(dev180.fail_rate),
        "development_180_risk_lock_rate": account._fmt(dev180.risk_lock_rate),
        "development_365_pass_rate": account._fmt(dev365.pass_rate),
        "development_365_fail_rate": account._fmt(dev365.fail_rate),
        "development_365_risk_lock_rate": account._fmt(dev365.risk_lock_rate),
        "development_365_median_calendar_days": account._fmt(
            dev365.median_calendar_days_to_pass
        ),
        "development_mc_pass_rate": account._fmt(dev_mc.pass_rate),
        "development_mc_fail_rate": account._fmt(dev_mc.fail_rate),
        "development_mc_risk_lock_rate": account._fmt(dev_mc.risk_lock_rate),
        "development_mc_p95_drawdown_usd": account._fmt(dev_mc.p95_drawdown_usd),
        "holdout_mc_pass_rate": account._fmt(holdout_mc.pass_rate),
        "holdout_mc_fail_rate": account._fmt(holdout_mc.fail_rate),
        "holdout_mc_risk_lock_rate": account._fmt(holdout_mc.risk_lock_rate),
        "holdout_mc_p95_drawdown_usd": account._fmt(holdout_mc.p95_drawdown_usd),
        "full_365_pass_rate": account._fmt(full365.pass_rate),
        "full_365_fail_rate": account._fmt(full365.fail_rate),
        "full_365_risk_lock_rate": account._fmt(full365.risk_lock_rate),
        "funded_lock_365_rate": account._fmt(funded.pass_rate),
        "funded_lock_365_fail_rate": account._fmt(funded.fail_rate),
        "selected_on_development": False,
        "final_eligible": False,
    }


def _development_eligible(row: dict[str, object]) -> bool:
    return (
        float(row["development_365_pass_rate"]) >= 0.50
        and float(row["development_365_fail_rate"]) <= 0.10
        and float(row["development_365_risk_lock_rate"]) <= 0.10
        and float(row["development_mc_pass_rate"]) >= 0.50
        and float(row["development_mc_fail_rate"]) <= 0.10
        and float(row["development_mc_risk_lock_rate"]) <= 0.10
    )


def _development_rank_key(row: dict[str, object]) -> tuple[float, ...]:
    return (
        -float(row["development_180_pass_rate"]),
        float(row["development_180_fail_rate"])
        + float(row["development_180_risk_lock_rate"]),
        -float(row["development_mc_pass_rate"]),
        float(row["development_mc_fail_rate"])
        + float(row["development_mc_risk_lock_rate"]),
        float(row["development_365_median_calendar_days"]),
        -float(row["full_365_pass_rate"]),
    )


def _final_eligible(
    row: dict[str, object],
    base_metrics: dict[str, StrategyMetrics],
    stress_metrics: dict[str, StrategyMetrics],
) -> bool:
    return (
        base_metrics["full"].profit_factor >= 1.60
        and stress_metrics["full"].profit_factor >= 1.50
        and base_metrics["holdout"].net_usd > 0.0
        and base_metrics["holdout"].profit_factor >= 1.40
        and stress_metrics["holdout"].net_usd > 0.0
        and stress_metrics["holdout"].profit_factor >= 1.30
        and float(row["holdout_mc_pass_rate"]) >= 0.50
        and float(row["holdout_mc_fail_rate"]) <= 0.10
        and float(row["holdout_mc_risk_lock_rate"]) <= 0.10
        and float(row["funded_lock_365_rate"]) >= 0.65
        and float(row["funded_lock_365_fail_rate"]) <= 0.10
    )


def _report_sort_key(row: dict[str, object]) -> tuple[float, ...]:
    return (
        0.0 if bool(row["selected_on_development"]) else 1.0,
        0.0 if _development_eligible(row) else 1.0,
        *_development_rank_key(row),
    )


def _shuffled_drawdowns(
    outcomes: list[Any],
    *,
    total_slippage_ticks: int,
    seed: int,
) -> list[float]:
    values = [
        _net(outcome.gross_points, 1, total_slippage_ticks=total_slippage_ticks)
        for outcome in outcomes
    ]
    rng = random.Random(seed)
    drawdowns = []
    for _ in range(MONTE_CARLO_RUNS):
        shuffled = list(values)
        rng.shuffle(shuffled)
        drawdowns.append(account._max_drawdown(shuffled))
    return sorted(drawdowns)


def _nominal_stop_loss(quantity: int) -> float:
    return INITIAL_STOP_POINTS * MGC_POINT_VALUE_USD * quantity + _cost(
        quantity,
        BASE_TOTAL_SLIPPAGE_TICKS,
    )


def _net(
    gross_points: float,
    quantity: int,
    *,
    total_slippage_ticks: int,
) -> float:
    return gross_points * MGC_POINT_VALUE_USD * quantity - _cost(
        quantity,
        total_slippage_ticks,
    )


def _cost(quantity: int, total_slippage_ticks: int) -> float:
    return quantity * (
        MGC_ROUND_TURN_FEE_USD + total_slippage_ticks * MGC_TICK_VALUE_USD
    )


def _outcomes_for_dates(outcomes: list[Any], dates: set[date]) -> list[Any]:
    return [outcome for outcome in outcomes if outcome.entry_time.date() in dates]


def _write_csv(
    path: str,
    header: list[str],
    rows: list[dict[str, object]],
) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def _write_audit(path: str, outcomes: list[Any]) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=AUDIT_HEADER)
        writer.writeheader()
        for outcome in outcomes:
            writer.writerow(
                {
                    "schema_version": 1,
                    "strategy_id": STRATEGY_ID,
                    "direction": outcome.direction,
                    "entry_time": outcome.entry_time.isoformat(sep=" "),
                    "exit_time": outcome.exit_time.isoformat(sep=" "),
                    "entry_price": account._fmt(outcome.entry_price),
                    "exit_price": account._fmt(outcome.exit_price),
                    "exit_reason": outcome.exit_reason,
                    "gross_points": account._fmt(outcome.gross_points),
                    "base_net_1_mgc_usd": account._fmt(
                        _net(
                            outcome.gross_points,
                            1,
                            total_slippage_ticks=BASE_TOTAL_SLIPPAGE_TICKS,
                        ),
                    ),
                    "stress_net_1_mgc_usd": account._fmt(
                        _net(
                            outcome.gross_points,
                            1,
                            total_slippage_ticks=STRESS_TOTAL_SLIPPAGE_TICKS,
                        ),
                    ),
                    "holding_minutes": account._fmt(outcome.holding_minutes),
                    "notes": outcome.notes,
                },
            )


def _write_report(
    path: str,
    *,
    bars: list[Any],
    signals: list[Any],
    outcomes: list[Any],
    trade_dates: list[date],
    train_dates: list[date],
    validation_dates: list[date],
    holdout_dates: list[date],
    base_metrics: dict[str, StrategyMetrics],
    stress_metrics: dict[str, StrategyMetrics],
    policy_rows: list[dict[str, object]],
    selected_row: dict[str, object] | None,
    selected_policy: SizingPolicy | None,
    selected_summaries: dict[str, AttemptSummary] | None,
    shuffled_drawdowns: list[float],
) -> None:
    full = base_metrics["full"]
    stress = stress_metrics["full"]
    holdout = base_metrics["holdout"]
    holdout_stress = stress_metrics["holdout"]
    sample_weeks = max((trade_dates[-1] - trade_dates[0]).days / 7.0, 1.0)
    promoted = selected_row is not None and bool(selected_row["final_eligible"])
    lines = [
        "# Tradeify 50K MGC Strategy Research",
        "",
        "Status: strategy-only validation for a future NinjaTrader implementation. No NinjaTrader or live-routing code is included.",
        "",
        "## Instrument Decision",
        "",
        "`MGC` is the primary instrument for this account profile. Its frozen strategy has more trades and materially lower path risk than the available MNQ candidates, while one-contract sizing keeps the initial stop near $154 including base friction.",
        "",
        "## Frozen Strategy",
        "",
        f"- strategy: `{STRATEGY_ID}`;",
        "- entry: 10-bar breakout, directional close-location >= 0.45, entries through 10:30, Monday/Tuesday/Friday only, absolute entry-bar delta <= 125;",
        "- management: 25-point target, 15-point initial stop, stop to breakeven after +20 points, one trade per session, 16:30 ET flatten;",
        f"- source: `{len(bars)}` one-minute MGC bars, `{trade_dates[0]}` through `{trade_dates[-1]}`;",
        f"- raw setups: `{len(signals)}`; sequenced trades: `{len(outcomes)}` (`{len(outcomes) / sample_weeks:.2f}` per week);",
        f"- chronological split: `{len(train_dates)} / {len(validation_dates)} / {len(holdout_dates)}` active dates;",
        "- base friction: Tradeify `$2.12` round trip plus two total slippage ticks per MGC; stress uses six slippage ticks;",
        "- same-bar ambiguity: stop first.",
        "",
        "## Strategy Results",
        "",
        "| Sample | Trades | Net | PF | Win | DD | Avg/Trade |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        _metrics_line("Full base", full),
        _metrics_line("Full stress", stress),
        _metrics_line("Final holdout base", holdout),
        _metrics_line("Final holdout stress", holdout_stress),
        "",
        f"Fixed `1 MGC` shuffled stress drawdown: median `${account._fmt(statistics.median(shuffled_drawdowns))}`, P95 `${account._fmt(account._percentile(shuffled_drawdowns, 0.05))}`, P99 `${account._fmt(account._percentile(shuffled_drawdowns, 0.01))}`.",
        "",
        "## Evaluation Sizing",
        "",
        "Sizing was selected on the first 75% of dates. The final 25% was used only for the final bootstrap gate. `Risk lock` means the remaining drawdown cushion cannot support even one MGC plus the $100 reserve; the strategy stops rather than breaching the account.",
        "",
        "| Policy | Dev 180 Pass/Fail/Lock | Dev 365 Pass/Fail/Lock | Dev MC Pass/Fail/Lock | Holdout MC Pass/Fail/Lock | Full 365 Pass | Funded Lock |",
        "| --- | --- | --- | --- | --- | ---: | ---: |",
    ]
    for row in policy_rows:
        marker = " **selected**" if bool(row["selected_on_development"]) else ""
        lines.append(
            f"| `{row['policy_id']}`{marker} | "
            f"{_rates(row, 'development_180')} | "
            f"{_rates(row, 'development_365')} | "
            f"{_rates(row, 'development_mc')} | "
            f"{_rates(row, 'holdout_mc')} | "
            f"{float(row['full_365_pass_rate']) * 100:.1f}% | "
            f"{float(row['funded_lock_365_rate']) * 100:.1f}% |",
        )

    lines.extend(["", "## Decision", ""])
    if selected_row is None or selected_policy is None or selected_summaries is None:
        lines.extend(
            [
                "No sizing policy met the development survival and pass-rate gates.",
                "",
                "Verdict: `REJECT_AFTER_STRESS`.",
            ],
        )
    else:
        full365 = selected_summaries["full_365"]
        holdout_mc = selected_summaries["holdout_mc"]
        lines.extend(
            [
                f"Selected policy: `{selected_policy.policy_id}`.",
                "",
                f"- historical rolling 365-day evaluation pass: `{full365.pass_rate * 100:.1f}%`; fail `{full365.fail_rate * 100:.1f}%`; risk-lock `{full365.risk_lock_rate * 100:.1f}%`;",
                f"- median successful evaluation: `{account._fmt(full365.median_calendar_days_to_pass)}` calendar days and `{account._fmt(full365.median_trade_days_to_pass)}` trade days;",
                f"- final-holdout block bootstrap: pass `{holdout_mc.pass_rate * 100:.1f}%`; fail `{holdout_mc.fail_rate * 100:.1f}%`; risk-lock `{holdout_mc.risk_lock_rate * 100:.1f}%`;",
                f"- verdict: `{'NON_REJECTED_STRATEGY_CANDIDATE' if promoted else 'REJECT_AFTER_STRESS'}`.",
            ],
        )
        if promoted:
            lines.extend(
                [
                    "",
                    "This clears the offline strategy gate, not the live-trading gate. The future NinjaTrader version must reproduce these fills, use account-aware sizing, reject entries when the risk reserve cannot fit, and flatten before Tradeify's cutoff.",
                ],
            )
        else:
            lines.extend(
                [
                    "",
                    "The signal remains profitable, but its account-level sizing did not survive the final gate. Do not implement it as the single production bot.",
                ],
            )

    lines.extend(
        [
            "",
            "## Research Limits",
            "",
            "- The export is Sierra-derived historical data, not NinjaTrader historical or Market Replay data.",
            "- Commission and slippage are modeled, but queue position, partial fills, disconnections, and adverse gaps beyond the bar stop are not.",
            "- Bootstrap results measure sensitivity to sampled historical regimes; they are not probabilities guaranteed for a future evaluation.",
            "- The strategy must remain disabled for live routing until NinjaTrader parity, replay, simulation, and controlled staging pass.",
        ],
    )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _metrics_line(label: str, metrics: StrategyMetrics) -> str:
    return (
        f"| {label} | {metrics.trades} | {account._fmt(metrics.net_usd)} | "
        f"{account._fmt(metrics.profit_factor)} | {metrics.win_rate * 100:.1f}% | "
        f"{account._fmt(metrics.max_drawdown_usd)} | "
        f"{account._fmt(metrics.average_trade_usd)} |"
    )


def _rates(row: dict[str, object], prefix: str) -> str:
    return (
        f"{float(row[f'{prefix}_pass_rate']) * 100:.1f}% / "
        f"{float(row[f'{prefix}_fail_rate']) * 100:.1f}% / "
        f"{float(row[f'{prefix}_risk_lock_rate']) * 100:.1f}%"
    )


if __name__ == "__main__":
    raise SystemExit(main())
