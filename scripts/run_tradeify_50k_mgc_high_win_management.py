#!/usr/bin/env python3
"""Search high-win management around the frozen MGC entry."""

from __future__ import annotations

import argparse
import csv
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


DEFAULT_OUTPUT = "reports/tradeify-50k-mgc-high-win-management-sweep.csv"
DEFAULT_REPORT = "reports/tradeify-50k-mgc-high-win-management.md"


CSV_HEADER = [
    "schema_version",
    "profile_id",
    "target_points",
    "stop_points",
    "management",
    "trigger_points",
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
    "holdout_stress_net_usd",
    "holdout_stress_profit_factor",
    "holdout_stress_win_rate",
    "holdout_stress_max_drawdown_usd",
    "development_eligible",
    "selected_on_development",
]


@dataclass(frozen=True)
class ProfileResult:
    spec: Any
    outcomes: list[Any]
    row: dict[str, object]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Search high-win management around the frozen MGC entry.",
    )
    parser.add_argument("input", nargs="?", default=normal.DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT)
    parser.add_argument("--seed", type=int, default=20260805)
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
    specs = _management_specs()
    print(
        f"testing {len(specs)} management profiles on {len(signals)} frozen MGC setups",
        flush=True,
    )

    results: list[ProfileResult] = []
    for spec in specs:
        risk = review._risk(
            core,
            normal,
            target_points=spec.target_points,
            stop_points=spec.stop_points,
            slippage_ticks=0.0,
        )
        outcomes = management._evaluate_sequence(
            core,
            signals,
            bars_by_date,
            rows_by_index,
            risk,
            spec,
        )
        base_metrics = {
            label: tradeify._strategy_metrics(
                tradeify._outcomes_for_dates(outcomes, dates),
                total_slippage_ticks=tradeify.BASE_TOTAL_SLIPPAGE_TICKS,
            )
            for label, dates in date_sets.items()
        }
        holdout_stress = tradeify._strategy_metrics(
            tradeify._outcomes_for_dates(outcomes, date_sets["holdout"]),
            total_slippage_ticks=tradeify.STRESS_TOTAL_SLIPPAGE_TICKS,
        )
        row = _sweep_row(spec, base_metrics, holdout_stress)
        results.append(ProfileResult(spec=spec, outcomes=outcomes, row=row))

    eligible = [
        result for result in results if bool(result.row["development_eligible"])
    ]
    selected = (
        min(eligible, key=lambda result: _development_rank_key(result.row))
        if eligible
        else None
    )
    if selected is not None:
        selected.row["selected_on_development"] = True
    rows = [result.row for result in results]
    rows.sort(key=_report_sort_key)
    _write_csv(args.output, rows)

    neighborhood = _management_neighborhood(results, selected)
    policy_rows = (
        _account_policy_rows(
            selected.outcomes,
            trade_dates,
            train_dates + validation_dates,
            holdout_dates,
            seed=args.seed,
        )
        if selected is not None
        else []
    )
    promoted = _promoted(selected, neighborhood, policy_rows)
    _write_report(
        args.report_output,
        bars=bars,
        signals=signals,
        train_dates=train_dates,
        validation_dates=validation_dates,
        holdout_dates=holdout_dates,
        results=results,
        selected=selected,
        neighborhood=neighborhood,
        policy_rows=policy_rows,
        promoted=promoted,
    )
    print(
        f"eligible={len(eligible)} selected={selected.row['profile_id'] if selected else 'none'} "
        f"verdict={'PROMOTE' if promoted else 'REJECT'}",
        flush=True,
    )
    return 0


def _management_specs() -> list[Any]:
    specs = []
    for target_points in (8.0, 10.0, 12.0, 15.0, 18.0, 20.0, 22.0, 25.0):
        for stop_points in (8.0, 10.0, 12.0, 15.0):
            specs.append(
                management.ManagementSpec(
                    f"high_win_fixed:t{target_points:g}:s{stop_points:g}",
                    target_points,
                    stop_points,
                    "fixed",
                    time(16, 30),
                    0.0,
                    0.0,
                ),
            )
            for trigger_points in (5.0, 6.0, 8.0, 10.0, 12.0, 15.0, 18.0, 20.0):
                if trigger_points >= target_points:
                    continue
                specs.append(
                    management.ManagementSpec(
                        f"high_win_be:t{target_points:g}:s{stop_points:g}:trig{trigger_points:g}",
                        target_points,
                        stop_points,
                        "breakeven",
                        time(16, 30),
                        trigger_points,
                        0.0,
                    ),
                )
    return specs


def _sweep_row(
    spec: Any,
    metrics: dict[str, tradeify.StrategyMetrics],
    holdout_stress: tradeify.StrategyMetrics,
) -> dict[str, object]:
    train = metrics["train"]
    validation = metrics["validation"]
    holdout = metrics["holdout"]
    eligible = (
        train.trades >= 150
        and train.net_usd > 0.0
        and train.profit_factor >= 1.50
        and train.win_rate >= 0.65
        and train.max_drawdown_usd > -800.0
        and validation.trades >= 65
        and validation.net_usd > 0.0
        and validation.profit_factor >= 1.50
        and validation.win_rate >= 0.65
        and validation.max_drawdown_usd > -600.0
    )
    return {
        "schema_version": 1,
        "profile_id": spec.management_id,
        "target_points": account._fmt(spec.target_points),
        "stop_points": account._fmt(spec.stop_points),
        "management": spec.management,
        "trigger_points": account._fmt(spec.trigger_points),
        **_metric_fields("train", train),
        **_metric_fields("validation", validation),
        **_metric_fields("holdout", holdout),
        "holdout_stress_net_usd": account._fmt(holdout_stress.net_usd),
        "holdout_stress_profit_factor": account._fmt(holdout_stress.profit_factor),
        "holdout_stress_win_rate": account._fmt(holdout_stress.win_rate),
        "holdout_stress_max_drawdown_usd": account._fmt(
            holdout_stress.max_drawdown_usd
        ),
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
    net_to_dd = (float(row["train_net_usd"]) + float(row["validation_net_usd"])) / max(
        abs(float(row["train_max_drawdown_usd"])),
        abs(float(row["validation_max_drawdown_usd"])),
        1.0,
    )
    return (
        -min(minimum_pf, 4.0),
        -minimum_win,
        -net_to_dd,
        -float(row["validation_net_usd"]),
    )


def _report_sort_key(row: dict[str, object]) -> tuple[float, ...]:
    return (
        0.0 if bool(row["selected_on_development"]) else 1.0,
        0.0 if bool(row["development_eligible"]) else 1.0,
        *_development_rank_key(row),
    )


def _management_neighborhood(
    results: list[ProfileResult],
    selected: ProfileResult | None,
) -> list[ProfileResult]:
    if selected is None:
        return []
    spec = selected.spec
    return sorted(
        [
            result
            for result in results
            if result.spec.management == spec.management
            and abs(result.spec.target_points - spec.target_points) <= 2.1
            and abs(result.spec.stop_points - spec.stop_points) <= 2.1
            and abs(result.spec.trigger_points - spec.trigger_points) <= 2.1
        ],
        key=lambda result: (
            result.spec.target_points,
            result.spec.stop_points,
            result.spec.trigger_points,
        ),
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
        holdout_mc = tradeify._monte_carlo_attempts(
            outcomes_by_date,
            holdout_dates,
            policy,
            total_slippage_ticks=tradeify.STRESS_TOTAL_SLIPPAGE_TICKS,
            seed=seed + index,
        )
        rows.append(
            {
                "policy_id": policy.policy_id,
                "development_pass": development.pass_rate,
                "development_fail": development.fail_rate,
                "development_lock": development.risk_lock_rate,
                "development_days": development.median_calendar_days_to_pass,
                "full_pass": full.pass_rate,
                "full_fail": full.fail_rate,
                "full_lock": full.risk_lock_rate,
                "full_days": full.median_calendar_days_to_pass,
                "holdout_mc_pass": holdout_mc.pass_rate,
                "holdout_mc_fail": holdout_mc.fail_rate,
                "holdout_mc_lock": holdout_mc.risk_lock_rate,
            },
        )
    rows.sort(
        key=lambda row: (
            0.0
            if row["development_pass"] >= 0.50
            and row["development_fail"] <= 0.10
            and row["development_lock"] <= 0.10
            else 1.0,
            -float(row["development_pass"]),
            float(row["development_fail"]) + float(row["development_lock"]),
            float(row["development_days"]),
        ),
    )
    return rows


def _promoted(
    selected: ProfileResult | None,
    neighborhood: list[ProfileResult],
    policy_rows: list[dict[str, object]],
) -> bool:
    if selected is None or not policy_rows:
        return False
    row = selected.row
    robust_neighbors = [
        result
        for result in neighborhood
        if int(result.row["holdout_trades"]) >= 60
        and float(result.row["holdout_net_usd"]) > 0.0
        and float(result.row["holdout_profit_factor"]) >= 1.35
        and float(result.row["holdout_win_rate"]) >= 0.62
    ]
    policy = policy_rows[0]
    return (
        int(row["holdout_trades"]) >= 65
        and float(row["holdout_net_usd"]) > 0.0
        and float(row["holdout_profit_factor"]) >= 1.50
        and float(row["holdout_win_rate"]) >= 0.65
        and float(row["holdout_max_drawdown_usd"]) > -700.0
        and float(row["holdout_stress_profit_factor"]) >= 1.35
        and float(row["holdout_stress_win_rate"]) >= 0.60
        and len(robust_neighbors) >= max(3, round(len(neighborhood) * 0.70))
        and float(policy["development_pass"]) >= 0.50
        and float(policy["development_fail"]) <= 0.10
        and float(policy["development_lock"]) <= 0.10
        and float(policy["holdout_mc_pass"]) >= 0.50
        and float(policy["holdout_mc_fail"]) <= 0.10
        and float(policy["holdout_mc_lock"]) <= 0.10
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
    signals: list[Any],
    train_dates: list[date],
    validation_dates: list[date],
    holdout_dates: list[date],
    results: list[ProfileResult],
    selected: ProfileResult | None,
    neighborhood: list[ProfileResult],
    policy_rows: list[dict[str, object]],
    promoted: bool,
) -> None:
    lines = [
        "# Tradeify 50K MGC High-Win Management",
        "",
        "Status: strategy-only management search around the frozen MGC entry. No NinjaTrader code is included.",
        "",
        "## Method",
        "",
        f"- source bars: `{len(bars)}`; frozen raw setups: `{len(signals)}`;",
        f"- chronological active-date split: `{len(train_dates)} / {len(validation_dates)} / {len(holdout_dates)}`;",
        f"- profiles: `{len(results)}` across 8-25 point targets, 8-15 point stops, fixed or breakeven management;",
        "- selection used only train and validation; final holdout was excluded;",
        "- Tradeify fee plus two slippage ticks for selection, six ticks for final stress; same-bar stop first.",
        "",
        "## Decision",
        "",
    ]
    if selected is None:
        lines.extend(
            [
                "No management profile combined at least 65% wins with PF >= 1.50 on both development periods.",
                "",
                "Verdict: `REJECT_AFTER_DEVELOPMENT`.",
            ],
        )
        Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
        return

    row = selected.row
    lines.extend(
        [
            f"Development-selected profile: `{row['profile_id']}`.",
            "",
            "| Sample | Trades | Net | PF | Win | DD |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
            _row_line("Train", row, "train"),
            _row_line("Validation", row, "validation"),
            _row_line("Final holdout", row, "holdout"),
            f"| Final holdout, six-tick stress | {row['holdout_trades']} | {row['holdout_stress_net_usd']} | {row['holdout_stress_profit_factor']} | {float(row['holdout_stress_win_rate']) * 100:.1f}% | {row['holdout_stress_max_drawdown_usd']} |",
            "",
            "Local management neighborhood on the final holdout:",
            "",
            "| Profile | Trades | Net | PF | Win | DD |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    for result in neighborhood:
        value = result.row
        lines.append(
            f"| `{value['profile_id']}` | {value['holdout_trades']} | "
            f"{value['holdout_net_usd']} | {value['holdout_profit_factor']} | "
            f"{float(value['holdout_win_rate']) * 100:.1f}% | "
            f"{value['holdout_max_drawdown_usd']} |",
        )

    lines.extend(
        [
            "",
            "## Account Policies",
            "",
            "| Policy | Dev Pass/Fail/Lock | Full Pass/Fail/Lock | Median Days | Holdout MC Pass/Fail/Lock |",
            "| --- | --- | --- | ---: | --- |",
        ],
    )
    for policy in policy_rows:
        lines.append(
            f"| `{policy['policy_id']}` | "
            f"{policy['development_pass'] * 100:.1f}% / {policy['development_fail'] * 100:.1f}% / {policy['development_lock'] * 100:.1f}% | "
            f"{policy['full_pass'] * 100:.1f}% / {policy['full_fail'] * 100:.1f}% / {policy['full_lock'] * 100:.1f}% | "
            f"{account._fmt(float(policy['full_days']))} | "
            f"{policy['holdout_mc_pass'] * 100:.1f}% / {policy['holdout_mc_fail'] * 100:.1f}% / {policy['holdout_mc_lock'] * 100:.1f}% |",
        )
    lines.extend(
        [
            "",
            f"Verdict: `{'NON_REJECTED_HIGH_WIN_CANDIDATE' if promoted else 'REJECT_AFTER_HOLDOUT'}`.",
        ],
    )
    if not promoted:
        lines.extend(
            [
                "",
                "A shorter target can raise the displayed win rate, but it is not accepted unless PF, drawdown, neighboring settings, and account paths remain strong on the final holdout.",
            ],
        )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _row_line(label: str, row: dict[str, object], prefix: str) -> str:
    return (
        f"| {label} | {row[f'{prefix}_trades']} | {row[f'{prefix}_net_usd']} | "
        f"{row[f'{prefix}_profit_factor']} | "
        f"{float(row[f'{prefix}_win_rate']) * 100:.1f}% | "
        f"{row[f'{prefix}_max_drawdown_usd']} |"
    )


if __name__ == "__main__":
    raise SystemExit(main())
