#!/usr/bin/env python3
"""Test a simple pre-entry quality model on the frozen MGC strategy."""

from __future__ import annotations

import argparse
import csv
import math
import statistics
import sys
from dataclasses import dataclass
from datetime import date, time
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
import run_tradeify_50k_mgc_strategy_research as tradeify  # noqa: E402
import run_tradeify_50k_mnq_strategy_research as account  # noqa: E402


DEFAULT_OUTPUT = "reports/tradeify-50k-mgc-quality-filter-sweep.csv"
DEFAULT_REPORT = "reports/tradeify-50k-mgc-quality-filter.md"

FEATURE_NAMES = (
    "direction_long",
    "weekday_monday",
    "weekday_tuesday",
    "time_minutes",
    "directional_close_location",
    "abs_delta",
    "bar_range",
    "aligned_body",
    "abs_vwap_distance",
    "day_range_so_far",
    "aligned_prior_5_move",
    "aligned_prior_5_delta",
    "aligned_vwap_slope_5",
    "volume_ratio_20",
)

CSV_HEADER = [
    "schema_version",
    "model_id",
    "l2_penalty",
    "threshold",
    "train_trades",
    "train_net_usd",
    "train_profit_factor",
    "train_win_rate",
    "train_max_drawdown_usd",
    "validation_trades",
    "validation_net_usd",
    "validation_profit_factor",
    "validation_win_rate",
    "validation_max_drawdown_usd",
    "holdout_trades",
    "holdout_net_usd",
    "holdout_profit_factor",
    "holdout_win_rate",
    "holdout_max_drawdown_usd",
    "development_eligible",
    "selected_on_development",
]


@dataclass(frozen=True)
class FeatureOutcome:
    trade_date: date
    outcome: Any
    features: tuple[float, ...]
    label: float


@dataclass(frozen=True)
class LogisticModel:
    model_id: str
    l2_penalty: float
    means: tuple[float, ...]
    scales: tuple[float, ...]
    intercept: float
    coefficients: tuple[float, ...]

    def probability(self, features: tuple[float, ...]) -> float:
        standardized = [
            (value - mean) / scale
            for value, mean, scale in zip(
                features,
                self.means,
                self.scales,
                strict=True,
            )
        ]
        score = self.intercept + sum(
            coefficient * value
            for coefficient, value in zip(
                self.coefficients,
                standardized,
                strict=True,
            )
        )
        return _sigmoid(score)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Test a transparent logistic quality gate on frozen MGC entries.",
    )
    parser.add_argument("input", nargs="?", default=normal.DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT)
    parser.add_argument("--seed", type=int, default=20260805)
    parser.add_argument("--target-points", type=float, default=25.0)
    parser.add_argument("--stop-points", type=float, default=15.0)
    parser.add_argument(
        "--management",
        choices=("fixed", "breakeven"),
        default="breakeven",
    )
    parser.add_argument("--trigger-points", type=float, default=20.0)
    parser.add_argument("--minimum-win-rate", type=float, default=0.58)
    parser.add_argument(
        "--holdout-status",
        choices=("untouched", "previously_inspected"),
        default="untouched",
    )
    args = parser.parse_args()

    core = mgc_eval._load_mnq_core()
    mgc_eval._patch_core_for_mgc(core)
    bars = core._load_feature_bars(args.input)
    bars_by_date = mgc_eval._active_bars_by_date(core._bars_by_date(bars))
    rows_by_index = core._rows_by_global_index(bars_by_date)
    trade_dates = sorted(bars_by_date)
    train_dates, validation_dates, holdout_dates = account._split_dates(trade_dates)
    date_sets = {
        "train": set(train_dates),
        "validation": set(validation_dates),
        "holdout": set(holdout_dates),
    }

    signals = final._lead_signals(core, bars_by_date, rows_by_index, symbol="MGC")
    trigger_points = args.trigger_points if args.management == "breakeven" else 0.0
    profile_id = (
        f"{args.management}:t{args.target_points:g}:s{args.stop_points:g}:"
        f"trig{trigger_points:g}"
    )
    management_spec = management.ManagementSpec(
        profile_id,
        args.target_points,
        args.stop_points,
        args.management,
        time(16, 30),
        trigger_points,
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
    feature_outcomes = _feature_outcomes(outcomes, bars_by_date, rows_by_index)
    train_rows = [
        row for row in feature_outcomes if row.trade_date in date_sets["train"]
    ]
    print(
        f"built {len(feature_outcomes)} feature rows; train={len(train_rows)} "
        f"validation={sum(row.trade_date in date_sets['validation'] for row in feature_outcomes)} "
        f"holdout={sum(row.trade_date in date_sets['holdout'] for row in feature_outcomes)}",
        flush=True,
    )

    models = [
        _fit_logistic(train_rows, l2_penalty=l2_penalty)
        for l2_penalty in (0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0)
    ]
    rows: list[dict[str, object]] = []
    accepted_by_key: dict[tuple[str, float], list[Any]] = {}
    for model in models:
        for threshold in (
            0.40,
            0.425,
            0.45,
            0.475,
            0.50,
            0.525,
            0.55,
            0.575,
            0.60,
            0.625,
            0.65,
            0.675,
            0.70,
            0.725,
            0.75,
        ):
            accepted = [
                row.outcome
                for row in feature_outcomes
                if model.probability(row.features) >= threshold
            ]
            metrics = {
                label: tradeify._strategy_metrics(
                    tradeify._outcomes_for_dates(accepted, dates),
                    total_slippage_ticks=tradeify.BASE_TOTAL_SLIPPAGE_TICKS,
                )
                for label, dates in date_sets.items()
            }
            output_row = _sweep_row(
                model,
                threshold,
                metrics,
                minimum_win_rate=args.minimum_win_rate,
            )
            rows.append(output_row)
            accepted_by_key[(model.model_id, threshold)] = accepted

    eligible = [row for row in rows if bool(row["development_eligible"])]
    selected = min(eligible, key=_development_rank_key) if eligible else None
    selected_model: LogisticModel | None = None
    selected_outcomes: list[Any] = []
    selected_metrics: dict[str, tradeify.StrategyMetrics] = {}
    if selected is not None:
        selected["selected_on_development"] = True
        selected_model = next(
            model for model in models if model.model_id == selected["model_id"]
        )
        selected_outcomes = accepted_by_key[
            (str(selected["model_id"]), float(selected["threshold"]))
        ]
        selected_metrics = {
            "full_base": tradeify._strategy_metrics(
                selected_outcomes,
                total_slippage_ticks=tradeify.BASE_TOTAL_SLIPPAGE_TICKS,
            ),
            "full_stress": tradeify._strategy_metrics(
                selected_outcomes,
                total_slippage_ticks=tradeify.STRESS_TOTAL_SLIPPAGE_TICKS,
            ),
            "holdout_stress": tradeify._strategy_metrics(
                tradeify._outcomes_for_dates(
                    selected_outcomes,
                    date_sets["holdout"],
                ),
                total_slippage_ticks=tradeify.STRESS_TOTAL_SLIPPAGE_TICKS,
            ),
        }

    rows.sort(key=_report_sort_key)
    _write_csv(args.output, rows)
    neighborhood = _threshold_neighborhood(rows, selected)
    policy_rows = (
        _account_policy_rows(
            selected_outcomes,
            trade_dates,
            train_dates + validation_dates,
            holdout_dates,
            seed=args.seed,
        )
        if selected is not None
        else []
    )
    verdict = _promoted(
        selected,
        neighborhood,
        policy_rows,
        selected_metrics,
        minimum_win_rate=args.minimum_win_rate,
    )
    _write_report(
        args.report_output,
        bars=bars,
        feature_outcomes=feature_outcomes,
        train_dates=train_dates,
        validation_dates=validation_dates,
        holdout_dates=holdout_dates,
        selected=selected,
        selected_model=selected_model,
        neighborhood=neighborhood,
        policy_rows=policy_rows,
        promoted=verdict,
        profile_id=profile_id,
        minimum_win_rate=args.minimum_win_rate,
        holdout_status=args.holdout_status,
        selected_metrics=selected_metrics,
    )
    print(
        f"selected={selected['model_id'] if selected else 'none'} "
        f"threshold={selected['threshold'] if selected else 'none'} "
        f"verdict={'GATES_PASS' if verdict else 'REJECT'} "
        f"holdout_status={args.holdout_status}",
        flush=True,
    )
    return 0


def _feature_outcomes(
    outcomes: list[Any],
    bars_by_date: dict[date, list[Any]],
    rows_by_index: dict[int, int],
) -> list[FeatureOutcome]:
    rows = []
    for outcome in outcomes:
        day_rows = bars_by_date[outcome.entry_time.date()]
        local_index = rows_by_index[outcome.entry_bar_index]
        bar = day_rows[local_index]
        sign = 1.0 if outcome.direction == "long" else -1.0
        previous_5 = day_rows[max(0, local_index - 5)]
        previous_20_rows = day_rows[max(0, local_index - 20) : local_index]
        average_volume = (
            statistics.mean(previous.volume for previous in previous_20_rows)
            if previous_20_rows
            else max(bar.volume, 1.0)
        )
        session_rows = day_rows[: local_index + 1]
        features = (
            1.0 if outcome.direction == "long" else 0.0,
            1.0 if outcome.entry_time.weekday() == 0 else 0.0,
            1.0 if outcome.entry_time.weekday() == 1 else 0.0,
            float(outcome.entry_time.hour * 60 + outcome.entry_time.minute),
            bar.close_location if sign > 0.0 else 1.0 - bar.close_location,
            abs(bar.delta),
            bar.high - bar.low,
            sign * (bar.close - bar.open),
            abs(bar.close - bar.vwap),
            max(value.high for value in session_rows)
            - min(value.low for value in session_rows),
            sign * (bar.close - previous_5.close),
            sign
            * sum(
                value.delta
                for value in day_rows[max(0, local_index - 4) : local_index + 1]
            ),
            sign * (bar.vwap - previous_5.vwap),
            bar.volume / max(average_volume, 1.0),
        )
        base_net = tradeify._net(
            outcome.gross_points,
            1,
            total_slippage_ticks=tradeify.BASE_TOTAL_SLIPPAGE_TICKS,
        )
        rows.append(
            FeatureOutcome(
                trade_date=outcome.entry_time.date(),
                outcome=outcome,
                features=tuple(float(value) for value in features),
                label=1.0 if base_net > 0.0 else 0.0,
            ),
        )
    return rows


def _fit_logistic(
    rows: list[FeatureOutcome],
    *,
    l2_penalty: float,
) -> LogisticModel:
    columns = list(zip(*(row.features for row in rows), strict=True))
    means = tuple(statistics.mean(column) for column in columns)
    scales = tuple(max(statistics.pstdev(column), 1e-9) for column in columns)
    matrix = [
        [
            (value - mean) / scale
            for value, mean, scale in zip(row.features, means, scales, strict=True)
        ]
        for row in rows
    ]
    labels = [row.label for row in rows]
    intercept = math.log((sum(labels) + 0.5) / (len(labels) - sum(labels) + 0.5))
    coefficients = [0.0] * len(FEATURE_NAMES)
    for iteration in range(4000):
        intercept_gradient = 0.0
        gradients = [0.0] * len(coefficients)
        for features, label in zip(matrix, labels, strict=True):
            probability = _sigmoid(
                intercept
                + sum(
                    coefficient * value
                    for coefficient, value in zip(coefficients, features, strict=True)
                ),
            )
            error = probability - label
            intercept_gradient += error
            for index, value in enumerate(features):
                gradients[index] += error * value
        learning_rate = 0.08 / math.sqrt(1.0 + iteration / 500.0)
        intercept -= learning_rate * intercept_gradient / len(rows)
        for index in range(len(coefficients)):
            regularized = gradients[index] / len(rows) + l2_penalty * coefficients[
                index
            ] / len(rows)
            coefficients[index] -= learning_rate * regularized
    return LogisticModel(
        model_id=f"mfg_logit_l2_{l2_penalty:g}",
        l2_penalty=l2_penalty,
        means=means,
        scales=scales,
        intercept=intercept,
        coefficients=tuple(coefficients),
    )


def _sigmoid(value: float) -> float:
    if value >= 0.0:
        return 1.0 / (1.0 + math.exp(-min(value, 40.0)))
    exponential = math.exp(max(value, -40.0))
    return exponential / (1.0 + exponential)


def _sweep_row(
    model: LogisticModel,
    threshold: float,
    metrics: dict[str, tradeify.StrategyMetrics],
    *,
    minimum_win_rate: float,
) -> dict[str, object]:
    train = metrics["train"]
    validation = metrics["validation"]
    holdout = metrics["holdout"]
    eligible = (
        train.trades >= 70
        and train.net_usd > 0.0
        and train.profit_factor >= 1.40
        and train.win_rate >= minimum_win_rate
        and train.max_drawdown_usd > -1000.0
        and validation.trades >= 30
        and validation.net_usd > 0.0
        and validation.profit_factor >= 1.40
        and validation.win_rate >= minimum_win_rate
        and validation.max_drawdown_usd > -700.0
    )
    return {
        "schema_version": 1,
        "model_id": model.model_id,
        "l2_penalty": account._fmt(model.l2_penalty),
        "threshold": account._fmt(threshold),
        **_metric_fields("train", train),
        **_metric_fields("validation", validation),
        **_metric_fields("holdout", holdout),
        "development_eligible": eligible,
        "selected_on_development": False,
    }


def _metric_fields(
    prefix: str,
    metrics: tradeify.StrategyMetrics,
) -> dict[str, object]:
    return {
        f"{prefix}_trades": metrics.trades,
        f"{prefix}_net_usd": account._fmt(metrics.net_usd),
        f"{prefix}_profit_factor": account._fmt(metrics.profit_factor),
        f"{prefix}_win_rate": account._fmt(metrics.win_rate),
        f"{prefix}_max_drawdown_usd": account._fmt(metrics.max_drawdown_usd),
    }


def _development_rank_key(row: dict[str, object]) -> tuple[float, ...]:
    minimum_pf = min(
        float(row["train_profit_factor"]),
        float(row["validation_profit_factor"]),
    )
    minimum_win = min(
        float(row["train_win_rate"]),
        float(row["validation_win_rate"]),
    )
    return (
        -min(minimum_pf, 4.0),
        -minimum_win,
        -float(row["validation_net_usd"]),
        -float(row["validation_trades"]),
        -float(row["train_net_usd"]),
    )


def _report_sort_key(row: dict[str, object]) -> tuple[float, ...]:
    return (
        0.0 if bool(row["selected_on_development"]) else 1.0,
        0.0 if bool(row["development_eligible"]) else 1.0,
        *_development_rank_key(row),
    )


def _threshold_neighborhood(
    rows: list[dict[str, object]],
    selected: dict[str, object] | None,
) -> list[dict[str, object]]:
    if selected is None:
        return []
    threshold = float(selected["threshold"])
    model_id = str(selected["model_id"])
    return sorted(
        [
            row
            for row in rows
            if row["model_id"] == model_id
            and abs(float(row["threshold"]) - threshold) <= 0.051
        ],
        key=lambda row: float(row["threshold"]),
    )


def _account_policy_rows(
    outcomes: list[Any],
    trade_dates: list[date],
    development_dates: list[date],
    holdout_dates: list[date],
    *,
    seed: int,
) -> list[dict[str, object]]:
    outcomes_by_date = {outcome.entry_time.date(): outcome for outcome in outcomes}
    rows = []
    for index, policy in enumerate(tradeify._sizing_policies()):
        development = tradeify._historical_attempts(
            outcomes_by_date,
            development_dates,
            policy,
            horizon_calendar_days=365,
        )
        full = tradeify._historical_attempts(
            outcomes_by_date,
            trade_dates,
            policy,
            horizon_calendar_days=365,
        )
        development_mc = tradeify._monte_carlo_attempts(
            outcomes_by_date,
            development_dates,
            policy,
            total_slippage_ticks=tradeify.STRESS_TOTAL_SLIPPAGE_TICKS,
            seed=seed + 100 + index,
        )
        holdout_mc = tradeify._monte_carlo_attempts(
            outcomes_by_date,
            holdout_dates,
            policy,
            total_slippage_ticks=tradeify.STRESS_TOTAL_SLIPPAGE_TICKS,
            seed=seed + 200 + index,
        )
        funded_lock = tradeify._historical_attempts(
            outcomes_by_date,
            trade_dates,
            policy,
            horizon_calendar_days=365,
            profit_target_usd=tradeify.FUNDED_LOCK_TARGET_USD,
            consistency_fraction=1.0,
        )
        rows.append(
            {
                "policy_id": policy.policy_id,
                "development_pass": development.pass_rate,
                "development_fail": development.fail_rate,
                "development_lock": development.risk_lock_rate,
                "development_days": development.median_calendar_days_to_pass,
                "development_mc_pass": development_mc.pass_rate,
                "development_mc_fail": development_mc.fail_rate,
                "development_mc_lock": development_mc.risk_lock_rate,
                "full_pass": full.pass_rate,
                "full_fail": full.fail_rate,
                "full_lock": full.risk_lock_rate,
                "full_days": full.median_calendar_days_to_pass,
                "holdout_mc_pass": holdout_mc.pass_rate,
                "holdout_mc_fail": holdout_mc.fail_rate,
                "holdout_mc_lock": holdout_mc.risk_lock_rate,
                "funded_lock_pass": funded_lock.pass_rate,
                "funded_lock_fail": funded_lock.fail_rate,
                "funded_lock_risk_lock": funded_lock.risk_lock_rate,
                "funded_lock_days": funded_lock.median_calendar_days_to_pass,
            },
        )
    rows.sort(
        key=lambda row: (
            0.0
            if row["development_pass"] >= 0.50
            and row["development_fail"] <= 0.10
            and row["development_lock"] <= 0.10
            and row["development_mc_pass"] >= 0.50
            and row["development_mc_fail"] <= 0.10
            and row["development_mc_lock"] <= 0.10
            else 1.0,
            -min(
                float(row["development_pass"]),
                float(row["development_mc_pass"]),
            ),
            float(row["development_fail"])
            + float(row["development_lock"])
            + float(row["development_mc_fail"])
            + float(row["development_mc_lock"]),
            float(row["development_days"]),
        ),
    )
    return rows


def _promoted(
    selected: dict[str, object] | None,
    neighborhood: list[dict[str, object]],
    policy_rows: list[dict[str, object]],
    selected_metrics: dict[str, tradeify.StrategyMetrics],
    *,
    minimum_win_rate: float,
) -> bool:
    if selected is None or not policy_rows or not selected_metrics:
        return False
    robust_neighbors = [
        row
        for row in neighborhood
        if int(row["holdout_trades"]) >= 25
        and float(row["holdout_net_usd"]) > 0.0
        and float(row["holdout_profit_factor"]) >= 1.30
        and float(row["holdout_win_rate"]) >= max(minimum_win_rate - 0.03, 0.55)
    ]
    best_policy = policy_rows[0]
    full_stress = selected_metrics["full_stress"]
    holdout_stress = selected_metrics["holdout_stress"]
    return (
        int(selected["holdout_trades"]) >= 25
        and float(selected["holdout_net_usd"]) > 0.0
        and float(selected["holdout_profit_factor"]) >= 1.50
        and float(selected["holdout_win_rate"]) >= max(minimum_win_rate, 0.60)
        and float(selected["holdout_max_drawdown_usd"]) > -700.0
        and full_stress.net_usd > 0.0
        and full_stress.profit_factor >= 1.45
        and holdout_stress.net_usd > 0.0
        and holdout_stress.profit_factor >= 1.40
        and len(robust_neighbors) >= max(3, len(neighborhood) - 1)
        and float(best_policy["development_pass"]) >= 0.50
        and float(best_policy["development_fail"]) <= 0.10
        and float(best_policy["development_lock"]) <= 0.10
        and float(best_policy["development_mc_pass"]) >= 0.50
        and float(best_policy["development_mc_fail"]) <= 0.10
        and float(best_policy["development_mc_lock"]) <= 0.10
        and float(best_policy["holdout_mc_pass"]) >= 0.50
        and float(best_policy["holdout_mc_fail"]) <= 0.10
        and float(best_policy["holdout_mc_lock"]) <= 0.10
        and float(best_policy["funded_lock_pass"]) >= 0.90
        and float(best_policy["funded_lock_fail"]) <= 0.10
        and float(best_policy["funded_lock_risk_lock"]) <= 0.10
    )


def _write_csv(path: str, rows: list[dict[str, object]]) -> None:
    with Path(path).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_HEADER)
        writer.writeheader()
        writer.writerows(rows)


def _write_report(
    path: str,
    *,
    bars: list[Any],
    feature_outcomes: list[FeatureOutcome],
    train_dates: list[date],
    validation_dates: list[date],
    holdout_dates: list[date],
    selected: dict[str, object] | None,
    selected_model: LogisticModel | None,
    neighborhood: list[dict[str, object]],
    policy_rows: list[dict[str, object]],
    promoted: bool,
    profile_id: str,
    minimum_win_rate: float,
    holdout_status: str,
    selected_metrics: dict[str, tradeify.StrategyMetrics],
) -> None:
    lines = [
        "# Tradeify 50K MGC Quality-Filter Research",
        "",
        "Status: development/validation test of a simple pre-entry logistic gate on the frozen MGC strategy. No NinjaTrader code is included.",
        "",
        "## Method",
        "",
        f"- source bars: `{len(bars)}`; frozen outcomes: `{len(feature_outcomes)}`;",
        f"- frozen management profile: `{profile_id}`; minimum development win rate: `{minimum_win_rate * 100:.1f}%`;",
        f"- final-period process status: `{holdout_status}`;",
        f"- chronological active-date split: `{len(train_dates)} / {len(validation_dates)} / {len(holdout_dates)}`;",
        "- coefficients fit only on the first 50%; regularization and probability threshold selected only on the next 25%; final 25% excluded from selection;",
        "- model inputs are available at entry: direction, weekday, time, close location, delta, range/body, VWAP distance/slope, five-bar move/delta, session range, and relative volume;",
        "- label: positive net trade after Tradeify fee and two total slippage ticks;",
        "- purpose: reject weak entries, not predict price or alter the frozen stop/target.",
        "",
        "## Decision",
        "",
    ]
    if selected is None or selected_model is None:
        lines.extend(
            [
                "No quality model met the development gates. The filter is rejected.",
                "",
                "Verdict: `REJECT_AFTER_DEVELOPMENT`.",
            ],
        )
        Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    lines.extend(
        [
            f"Development-selected model: `{selected['model_id']}` at probability `>= {selected['threshold']}`.",
            "",
            "| Sample | Trades | Net | PF | Win | DD |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
            _row_line("Train", selected, "train"),
            _row_line("Validation", selected, "validation"),
            _row_line("Final holdout", selected, "holdout"),
            _metrics_line("Full base", selected_metrics["full_base"]),
            _metrics_line("Full, six-tick stress", selected_metrics["full_stress"]),
            _metrics_line(
                "Final holdout, six-tick stress", selected_metrics["holdout_stress"]
            ),
            "",
            "Final-period threshold neighborhood:",
            "",
            "| Threshold | Trades | Net | PF | Win | DD |",
            "| ---: | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    for row in neighborhood:
        lines.append(
            f"| {row['threshold']} | {row['holdout_trades']} | "
            f"{row['holdout_net_usd']} | {row['holdout_profit_factor']} | "
            f"{float(row['holdout_win_rate']) * 100:.1f}% | "
            f"{row['holdout_max_drawdown_usd']} |",
        )

    lines.extend(
        [
            "",
            "Frozen standardized logistic coefficients:",
            "",
            f"- intercept: `{account._fmt(selected_model.intercept)}`;",
        ],
    )
    for name, coefficient, mean, scale in zip(
        FEATURE_NAMES,
        selected_model.coefficients,
        selected_model.means,
        selected_model.scales,
        strict=True,
    ):
        lines.append(
            f"- `{name}`: coefficient `{account._fmt(coefficient)}`, mean `{account._fmt(mean)}`, scale `{account._fmt(scale)}`;",
        )

    lines.extend(
        [
            "",
            "## Account Policies",
            "",
            "| Policy | Dev Historical Pass/Fail/Lock | Dev MC Pass/Fail/Lock | Full Historical Pass/Fail/Lock | Median Days | Holdout MC Pass/Fail/Lock | Funded Lock Pass/Fail/Lock; Days |",
            "| --- | --- | --- | --- | ---: | --- | --- |",
        ],
    )
    for row in policy_rows:
        lines.append(
            f"| `{row['policy_id']}` | "
            f"{row['development_pass'] * 100:.1f}% / {row['development_fail'] * 100:.1f}% / {row['development_lock'] * 100:.1f}% | "
            f"{row['development_mc_pass'] * 100:.1f}% / {row['development_mc_fail'] * 100:.1f}% / {row['development_mc_lock'] * 100:.1f}% | "
            f"{row['full_pass'] * 100:.1f}% / {row['full_fail'] * 100:.1f}% / {row['full_lock'] * 100:.1f}% | "
            f"{account._fmt(float(row['full_days']))} | "
            f"{row['holdout_mc_pass'] * 100:.1f}% / {row['holdout_mc_fail'] * 100:.1f}% / {row['holdout_mc_lock'] * 100:.1f}% | "
            f"{row['funded_lock_pass'] * 100:.1f}% / {row['funded_lock_fail'] * 100:.1f}% / {row['funded_lock_risk_lock'] * 100:.1f}%; "
            f"{account._fmt(float(row['funded_lock_days']))} |",
        )
    lines.extend(
        [
            "",
            _verdict_line(promoted, holdout_status),
        ],
    )
    if not promoted:
        lines.extend(
            [
                "",
                "The filter does not replace the fixed 1 MGC safety baseline. A good development fit is insufficient without stable holdout and account-path behavior.",
            ],
        )
    elif holdout_status == "previously_inspected":
        lines.extend(
            [
                "",
                "The numerical gates pass, but the final period is no longer independent because an earlier model iteration exposed its behavior. Keep this as the frozen NinjaTrader research lead and require independent Playback/replay evidence before implementation approval.",
            ],
        )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _row_line(
    label: str,
    row: dict[str, object],
    prefix: str,
) -> str:
    return (
        f"| {label} | {row[f'{prefix}_trades']} | {row[f'{prefix}_net_usd']} | "
        f"{row[f'{prefix}_profit_factor']} | "
        f"{float(row[f'{prefix}_win_rate']) * 100:.1f}% | "
        f"{row[f'{prefix}_max_drawdown_usd']} |"
    )


def _metrics_line(label: str, metrics: tradeify.StrategyMetrics) -> str:
    return (
        f"| {label} | {metrics.trades} | {account._fmt(metrics.net_usd)} | "
        f"{account._fmt(metrics.profit_factor)} | {metrics.win_rate * 100:.1f}% | "
        f"{account._fmt(metrics.max_drawdown_usd)} |"
    )


def _verdict_line(promoted: bool, holdout_status: str) -> str:
    if not promoted:
        return "Verdict: `REJECT_AFTER_HOLDOUT`."
    if holdout_status == "previously_inspected":
        return "Verdict: `PROVISIONAL_GATES_PASS_REQUIRES_INDEPENDENT_REPLAY`."
    return "Verdict: `NON_REJECTED_QUALITY_FILTER`."


if __name__ == "__main__":
    raise SystemExit(main())
