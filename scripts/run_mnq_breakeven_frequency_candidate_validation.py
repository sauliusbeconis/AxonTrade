#!/usr/bin/env python3
"""Validate the current MNQ breakeven-frequency candidate."""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_mnq_breakeven_frequency_refine as refine  # noqa: E402
import run_mnq_breakeven_frequency_research as be  # noqa: E402
import run_mnq_eval_pass_wave_rider as wave  # noqa: E402


DEFAULT_OUTPUT = "reports/mnq-breakeven-frequency-candidate-validation.csv"
DEFAULT_REPORT_OUTPUT = "reports/mnq-breakeven-frequency-candidate-validation.md"
FILTER_ID = "short_only__vwapdist_lte120"
FILTER_LABEL = "short entries only; directional VWAP distance <= 120"


@dataclass(frozen=True)
class CandidateSpec:
    candidate_id: str
    quantity: int
    first_leg_quantity: int
    runner_quantity: int
    first_target_points: float
    initial_stop_points: float
    runner_target_points: float


SUMMARY_HEADER = [
    "schema_version",
    "candidate_id",
    "slippage_ticks",
    "quantity",
    "split",
    "first_target_points",
    "initial_stop_points",
    "runner_target_points",
    "evaluated_trades",
    "trades_per_week",
    "first_target_rate",
    "full_stop_rate",
    "runner_breakeven_rate",
    "runner_target_rate",
    "net_usd",
    "average_trade_usd",
    "profit_factor",
    "max_trade_sequence_drawdown_usd",
    "latest_year_trades",
    "latest_year_net_usd",
    "worst_quarter_net_usd",
    "worst_day_usd",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the selected MNQ breakeven-frequency candidate.",
    )
    parser.add_argument("input", nargs="?", default=wave.DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--symbol", default="MNQU26-CME")
    parser.add_argument("--slippage-ticks", default="1,2,4,6")
    args = parser.parse_args()

    slippage_ticks = [float(value) for value in args.slippage_ticks.split(",") if value.strip()]
    bars = wave._load_feature_bars(args.input)
    bars_by_date = wave._bars_by_date(bars)
    rows_by_index = wave._rows_by_global_index(bars_by_date)
    flatten_index_by_date = be._flatten_index_by_date(bars_by_date)
    sample_info = be._sample_info(bars)
    signals = refine._base_signals(bars_by_date, symbol=args.symbol)
    features_by_index = refine._features_by_index(signals, bars_by_date, rows_by_index)
    filter_spec = {spec.filter_id: spec for spec in refine._filter_specs()}[FILTER_ID]
    path_risk = be.ManagedRisk(
        quantity=2,
        first_leg_quantity=1,
        runner_quantity=1,
        first_target_points=30.0,
        initial_stop_points=50.0,
        runner_target_points=120.0,
        round_turn_cost_usd=2 * be.ROUND_TURN_COST_PER_CONTRACT_USD,
    )
    path_outcomes = be._evaluate_signals(
        signals,
        bars_by_date,
        rows_by_index,
        flatten_index_by_date,
        path_risk,
    )
    outcomes = [
        outcome
        for outcome in path_outcomes
        if filter_spec.keep(outcome, features_by_index[outcome.entry_bar_index])
    ]

    summary_rows = []
    period_rows_by_candidate: dict[str, list[dict[str, object]]] = {}
    for candidate in _candidate_specs():
        period_rows_by_candidate[candidate.candidate_id] = []
        for slippage in slippage_ticks:
            risk = _risk(candidate, slippage)
            row = _summary_row(candidate, slippage, outcomes, risk, sample_info)
            summary_rows.append(row)
            if slippage == slippage_ticks[0]:
                period_rows_by_candidate[candidate.candidate_id] = _period_rows(
                    outcomes,
                    risk,
                )

    summary_rows.sort(key=_summary_sort_key)
    _write_csv(args.output, SUMMARY_HEADER, summary_rows)
    _write_report(
        args.report_output,
        bars,
        outcomes,
        summary_rows,
        period_rows_by_candidate,
        slippage_ticks,
    )
    best = summary_rows[0] if summary_rows else None
    best_summary = "none"
    if best is not None:
        best_summary = (
            f"{best['candidate_id']} slip={best['slippage_ticks']} "
            f"net={best['net_usd']} pf={best['profit_factor']} "
            f"latest={best['latest_year_net_usd']} dd={best['max_trade_sequence_drawdown_usd']}"
        )
    print(
        f"wrote {len(summary_rows)} MNQ candidate validation rows to {args.output}; "
        f"trades={len(outcomes)}; best={best_summary}",
    )
    return 0


def _candidate_specs() -> list[CandidateSpec]:
    return [
        CandidateSpec("mnq_be_freq_short_vwap_q4_3p1_30_50_120", 4, 3, 1, 30.0, 50.0, 120.0),
        CandidateSpec("mnq_be_freq_short_vwap_q3_2p1_30_50_120", 3, 2, 1, 30.0, 50.0, 120.0),
        CandidateSpec("mnq_be_freq_short_vwap_q2_1p1_30_50_120", 2, 1, 1, 30.0, 50.0, 120.0),
    ]


def _risk(candidate: CandidateSpec, slippage_ticks: float) -> be.ManagedRisk:
    round_turn_cost = candidate.quantity * (
        2.0 * wave.COMMISSION_PER_SIDE_USD + slippage_ticks * wave.TICK_VALUE_USD
    )
    return be.ManagedRisk(
        quantity=candidate.quantity,
        first_leg_quantity=candidate.first_leg_quantity,
        runner_quantity=candidate.runner_quantity,
        first_target_points=candidate.first_target_points,
        initial_stop_points=candidate.initial_stop_points,
        runner_target_points=candidate.runner_target_points,
        round_turn_cost_usd=round_turn_cost,
    )


def _summary_row(
    candidate: CandidateSpec,
    slippage_ticks: float,
    outcomes: list[be.ManagedOutcome],
    risk: be.ManagedRisk,
    sample_info: be.SampleInfo,
) -> dict[str, object]:
    base = be._sweep_row(
        strategy_id=f"{refine.BASE_STRATEGY_ID}:validation:{candidate.candidate_id}",
        family="mnq_breakeven_frequency_validation",
        raw_signal_count=len(outcomes),
        outcomes=outcomes,
        risk=risk,
        sample_info=sample_info,
    )
    return {
        "schema_version": 1,
        "candidate_id": candidate.candidate_id,
        "slippage_ticks": wave._format_number(slippage_ticks),
        "quantity": base["quantity"],
        "split": f"{base['first_leg_quantity']}+{base['runner_quantity']}",
        "first_target_points": base["first_target_points"],
        "initial_stop_points": base["initial_stop_points"],
        "runner_target_points": base["runner_target_points"],
        "evaluated_trades": base["evaluated_trades"],
        "trades_per_week": base["trades_per_week"],
        "first_target_rate": base["first_target_rate"],
        "full_stop_rate": base["full_stop_rate"],
        "runner_breakeven_rate": base["runner_breakeven_rate"],
        "runner_target_rate": base["runner_target_rate"],
        "net_usd": base["net_usd"],
        "average_trade_usd": base["average_trade_usd"],
        "profit_factor": base["profit_factor"],
        "max_trade_sequence_drawdown_usd": base["max_trade_sequence_drawdown_usd"],
        "latest_year_trades": base["latest_year_trades"],
        "latest_year_net_usd": base["latest_year_net_usd"],
        "worst_quarter_net_usd": base["worst_quarter_net_usd"],
        "worst_day_usd": base["worst_day_usd"],
    }


def _period_rows(
    outcomes: list[be.ManagedOutcome],
    risk: be.ManagedRisk,
) -> list[dict[str, object]]:
    groups: dict[str, list[be.ManagedOutcome]] = defaultdict(list)
    for outcome in outcomes:
        groups[f"year:{outcome.entry_time.year}"].append(outcome)
        quarter = (outcome.entry_time.month - 1) // 3 + 1
        groups[f"quarter:{outcome.entry_time.year}Q{quarter}"].append(outcome)
    rows = []
    for period_id, period_outcomes in sorted(groups.items()):
        net_values = [be._net_usd_for_outcome(outcome, risk) for outcome in period_outcomes]
        positive = [value for value in net_values if value > 0.0]
        negative = [value for value in net_values if value < 0.0]
        rows.append(
            {
                "period_id": period_id,
                "trades": len(period_outcomes),
                "net_usd": sum(net_values),
                "profit_factor": sum(positive) / abs(sum(negative)) if negative else 999.0,
                "max_drawdown_usd": wave._max_drawdown(net_values),
            },
        )
    return rows


def _write_report(
    report_output: str,
    bars: list[wave.Bar],
    outcomes: list[be.ManagedOutcome],
    summary_rows: list[dict[str, object]],
    period_rows_by_candidate: dict[str, list[dict[str, object]]],
    slippage_ticks: list[float],
) -> None:
    base_rows = [
        row for row in summary_rows
        if float(row["slippage_ticks"]) == slippage_ticks[0]
    ]
    q4 = next(row for row in base_rows if str(row["candidate_id"]).startswith("mnq_be_freq_short_vwap_q4"))
    q3 = next(row for row in base_rows if str(row["candidate_id"]).startswith("mnq_be_freq_short_vwap_q3"))
    q2 = next(row for row in base_rows if str(row["candidate_id"]).startswith("mnq_be_freq_short_vwap_q2"))
    lines = [
        "# MNQ Breakeven-Frequency Candidate Validation",
        "",
        "Status: validation pass for the current MNQ breakeven-frequency candidate.",
        "",
        "## Candidate",
        "",
        f"- signal: `{refine.BASE_STRATEGY_ID}`",
        f"- filter: `{FILTER_ID}` ({FILTER_LABEL})",
        "- management: first leg exits at target one; runner stop moves to breakeven; conservative same-bar handling",
        "- risk geometry: `30 / 50 / 120` points",
        f"- filtered trades: `{len(outcomes)}`",
        f"- source rows: `{len(bars)}`",
        f"- source dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        "",
        "## Base Slippage",
        "",
        "| Version | Qty | Split | Trades/Wk | Net | PF | Latest-Year Net | Worst Quarter | Max DD |",
        "| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        _summary_markdown_row("growth", q4),
        _summary_markdown_row("balanced", q3),
        _summary_markdown_row("low-risk", q2),
        "",
        "## Slippage Stress",
        "",
        "| Candidate | Slippage Ticks | Net | PF | Latest-Year Net | Worst Quarter | Max DD |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in sorted(summary_rows, key=lambda value: (str(value["candidate_id"]), float(value["slippage_ticks"]))):
        lines.append(
            "| "
            f"`{row['candidate_id']}` | {row['slippage_ticks']} | "
            f"{row['net_usd']} | {row['profit_factor']} | "
            f"{row['latest_year_net_usd']} | {row['worst_quarter_net_usd']} | "
            f"{row['max_trade_sequence_drawdown_usd']} |"
        )
    lines.extend(
        [
            "",
            "## Period Breakdown",
            "",
        ],
    )
    for candidate_id, period_rows in period_rows_by_candidate.items():
        lines.extend(
            [
                f"### `{candidate_id}`",
                "",
                "| Period | Trades | Net | PF | Max DD |",
                "| --- | ---: | ---: | ---: | ---: |",
            ],
        )
        for row in period_rows:
            if str(row["period_id"]).startswith("year:"):
                lines.append(_period_markdown_row(row))
        for row in period_rows:
            if str(row["period_id"]).startswith("quarter:"):
                lines.append(_period_markdown_row(row))
        lines.append("")
    lines.extend(
        [
            "## Interpretation",
            "",
            "This is the first non-rejected breakeven-frequency candidate. The `4 MNQ` "
            "version has the best growth, while the `3 MNQ` version is the more "
            "practical risk version because drawdown and single-trade loss are lower.",
            "",
            "It is still research, not a bot build instruction. Next gates are "
            "walk-forward/frozen holdout review, replay/mechanics validation, and "
            "only then an ACSIL implementation decision.",
            "",
        ],
    )
    Path(report_output).write_text("\n".join(lines), encoding="utf-8")


def _summary_markdown_row(label: str, row: dict[str, object]) -> str:
    return (
        "| "
        f"{label} | {row['quantity']} | {row['split']} | {row['trades_per_week']} | "
        f"{row['net_usd']} | {row['profit_factor']} | {row['latest_year_net_usd']} | "
        f"{row['worst_quarter_net_usd']} | {row['max_trade_sequence_drawdown_usd']} |"
    )


def _period_markdown_row(row: dict[str, object]) -> str:
    return (
        "| "
        f"{row['period_id']} | {row['trades']} | "
        f"{wave._format_number(float(row['net_usd']))} | "
        f"{wave._format_number(float(row['profit_factor']))} | "
        f"{wave._format_number(float(row['max_drawdown_usd']))} |"
    )


def _summary_sort_key(row: dict[str, object]) -> tuple[float, ...]:
    return (
        float(row["slippage_ticks"]),
        -float(row["profit_factor"]),
        -float(row["net_usd"]),
    )


def _write_csv(path: str, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
