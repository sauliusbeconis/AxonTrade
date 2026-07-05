#!/usr/bin/env python3
"""Risk-geometry refinement for MNQ breakeven-frequency near-leads."""

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


DEFAULT_OUTPUT = "reports/mnq-breakeven-frequency-risk-refine.csv"
DEFAULT_REPORT_OUTPUT = "reports/mnq-breakeven-frequency-risk-refine.md"
DEFAULT_FILTER_IDS = (
    "short_only,"
    "short_only__vwapdist_lte120,"
    "weekday_mon_tue_wed__lbmove_lte80,"
    "weekday_mon_tue_wed__lbmove_lte120,"
    "weekday_not_thu__lbmove_lte80,"
    "weekday_not_thu__lbmove_lte120,"
    "prev5_lte30,"
    "weekday_tue_wed_thu__absdelta_lte1600"
)


@dataclass(frozen=True)
class CandidateRow:
    row: dict[str, object]
    filter_label: str


HEADER = [
    "schema_version",
    "filter_id",
    "filter_label",
    "quantity",
    "split",
    "first_target_points",
    "initial_stop_points",
    "runner_target_points",
    "evaluated_trades",
    "signal_days",
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
    "average_holding_minutes",
    "median_holding_minutes",
    "notes",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sweep risk geometry around MNQ breakeven-frequency near-lead filters.",
    )
    parser.add_argument("input", nargs="?", default=wave.DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--symbol", default="MNQU26-CME")
    parser.add_argument("--filter-ids", default=DEFAULT_FILTER_IDS)
    parser.add_argument("--minimum-trades", type=int, default=80)
    args = parser.parse_args()

    requested_filter_ids = [value.strip() for value in args.filter_ids.split(",") if value.strip()]
    filter_specs = {spec.filter_id: spec for spec in refine._filter_specs()}
    missing = [filter_id for filter_id in requested_filter_ids if filter_id not in filter_specs]
    if missing:
        raise ValueError(f"unknown filter ids: {', '.join(missing)}")

    bars = wave._load_feature_bars(args.input)
    bars_by_date = wave._bars_by_date(bars)
    rows_by_index = wave._rows_by_global_index(bars_by_date)
    flatten_index_by_date = be._flatten_index_by_date(bars_by_date)
    sample_info = be._sample_info(bars)
    signals = refine._base_signals(bars_by_date, symbol=args.symbol)
    features_by_index = refine._features_by_index(signals, bars_by_date, rows_by_index)

    rows: list[dict[str, object]] = []
    for path_risk in _path_risks():
        path_outcomes = be._evaluate_signals(
            signals,
            bars_by_date,
            rows_by_index,
            flatten_index_by_date,
            path_risk,
        )
        for filter_id in requested_filter_ids:
            spec = filter_specs[filter_id]
            filtered = [
                outcome
                for outcome in path_outcomes
                if spec.keep(outcome, features_by_index[outcome.entry_bar_index])
            ]
            if len(filtered) < args.minimum_trades:
                continue
            for split_risk in _split_risks(path_risk):
                row = _summary_row(spec.filter_id, spec.label, filtered, split_risk, sample_info)
                rows.append(row)

    rows.sort(key=_ranking_key)
    _write_csv(args.output, HEADER, rows)
    _write_report(args.report_output, bars, rows, requested_filter_ids)
    best = rows[0] if rows else None
    best_summary = "none"
    if best is not None:
        best_summary = (
            f"{best['filter_id']} q={best['quantity']} split={best['split']} "
            f"{best['first_target_points']}/{best['initial_stop_points']}/{best['runner_target_points']} "
            f"trades={best['evaluated_trades']} net={best['net_usd']} "
            f"pf={best['profit_factor']} latest={best['latest_year_net_usd']} "
            f"worstq={best['worst_quarter_net_usd']} dd={best['max_trade_sequence_drawdown_usd']}"
        )
    print(
        f"wrote {len(rows)} MNQ breakeven risk-refine rows to {args.output}; "
        f"best={best_summary}",
    )
    return 0


def _path_risks() -> list[be.ManagedRisk]:
    risks = []
    for first_target_points in (15.0, 20.0, 25.0, 30.0, 35.0):
        for initial_stop_points in (25.0, 30.0, 35.0, 40.0, 45.0, 50.0):
            for runner_target_points in (40.0, 60.0, 80.0, 100.0, 120.0):
                if runner_target_points <= first_target_points:
                    continue
                risks.append(
                    be.ManagedRisk(
                        quantity=2,
                        first_leg_quantity=1,
                        runner_quantity=1,
                        first_target_points=first_target_points,
                        initial_stop_points=initial_stop_points,
                        runner_target_points=runner_target_points,
                        round_turn_cost_usd=2 * be.ROUND_TURN_COST_PER_CONTRACT_USD,
                    ),
                )
    return risks


def _split_risks(path_risk: be.ManagedRisk) -> list[be.ManagedRisk]:
    risks = []
    for quantity, first_leg_quantity, runner_quantity in (
        (2, 1, 1),
        (3, 2, 1),
        (4, 3, 1),
        (4, 2, 2),
    ):
        risks.append(
            be.ManagedRisk(
                quantity=quantity,
                first_leg_quantity=first_leg_quantity,
                runner_quantity=runner_quantity,
                first_target_points=path_risk.first_target_points,
                initial_stop_points=path_risk.initial_stop_points,
                runner_target_points=path_risk.runner_target_points,
                round_turn_cost_usd=quantity * be.ROUND_TURN_COST_PER_CONTRACT_USD,
            ),
        )
    return risks


def _summary_row(
    filter_id: str,
    filter_label: str,
    outcomes: list[be.ManagedOutcome],
    risk: be.ManagedRisk,
    sample_info: be.SampleInfo,
) -> dict[str, object]:
    base = be._sweep_row(
        strategy_id=f"{refine.BASE_STRATEGY_ID}:riskrefine:{filter_id}",
        family="lookback_be_frequency_risk_refine",
        raw_signal_count=len(outcomes),
        outcomes=outcomes,
        risk=risk,
        sample_info=sample_info,
    )
    return {
        "schema_version": 1,
        "filter_id": filter_id,
        "filter_label": filter_label,
        "quantity": base["quantity"],
        "split": f"{base['first_leg_quantity']}+{base['runner_quantity']}",
        "first_target_points": base["first_target_points"],
        "initial_stop_points": base["initial_stop_points"],
        "runner_target_points": base["runner_target_points"],
        "evaluated_trades": base["evaluated_trades"],
        "signal_days": base["signal_days"],
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
        "average_holding_minutes": base["average_holding_minutes"],
        "median_holding_minutes": base["median_holding_minutes"],
        "notes": "risk-geometry refinement around filtered MNQ breakeven-frequency lead",
    }


def _write_report(
    report_output: str,
    bars: list[wave.Bar],
    rows: list[dict[str, object]],
    requested_filter_ids: list[str],
) -> None:
    accepted = _accepted_rows(rows)
    top_rows = rows[:12]
    per_filter = _best_by_filter(rows)
    lines = [
        "# MNQ Breakeven-Frequency Risk Refinement",
        "",
        "Status: risk-geometry refinement around the first filtered MNQ breakeven-frequency near-leads.",
        "",
        "## Fixed Signal Family",
        "",
        f"- base strategy: `{refine.BASE_STRATEGY_ID}`",
        f"- filters tested: `{', '.join(requested_filter_ids)}`",
        f"- source rows: `{len(bars)}`",
        f"- source dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        "- risk grid: first target `15-35`, initial stop `25-50`, runner target `40-120`, splits `1+1`, `2+1`, `3+1`, `2+2`",
        "",
        "## Result",
        "",
        f"Accepted rows by the current risk lens: `{len(accepted)}`.",
    ]
    if accepted:
        best = accepted[0]
        lines.extend(
            [
                "",
                "Best accepted row:",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Filter | `{best['filter_id']}` |",
                f"| Quantity / split | `{best['quantity']} / {best['split']}` |",
                f"| First target / stop / runner | `{best['first_target_points']} / {best['initial_stop_points']} / {best['runner_target_points']}` |",
                f"| Trades | `{best['evaluated_trades']}` |",
                f"| Trades/week | `{best['trades_per_week']}` |",
                f"| First-target reach | `{float(best['first_target_rate']) * 100:.1f}%` |",
                f"| Full-stop rate | `{float(best['full_stop_rate']) * 100:.1f}%` |",
                f"| Net | `${best['net_usd']}` |",
                f"| PF | `{best['profit_factor']}` |",
                f"| Latest-year net | `${best['latest_year_net_usd']}` |",
                f"| Worst quarter | `${best['worst_quarter_net_usd']}` |",
                f"| Max trade-sequence DD | `${best['max_trade_sequence_drawdown_usd']}` |",
            ],
        )
    else:
        lines.append(
            "No row cleared the full risk lens. Rows below may still be useful as "
            "research leads, but they are not build candidates yet.",
        )
    lines.extend(
        [
            "",
            "## Top Rows",
            "",
            "| Rank | Filter | Qty | Split | T1 / Stop / Runner | Trades | /Wk | T1 Hit | Stop | Net | PF | Latest | Worst Q | DD |",
            "| ---: | --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    for rank, row in enumerate(top_rows, start=1):
        lines.append(_markdown_row(rank, row))
    lines.extend(
        [
            "",
            "## Best By Filter",
            "",
            "| Filter | Qty | Split | T1 / Stop / Runner | Trades | Net | PF | Latest | Worst Q | DD |",
            "| --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    for row in per_filter:
        lines.append(
            "| "
            f"`{row['filter_id']}` | {row['quantity']} | {row['split']} | "
            f"{row['first_target_points']} / {row['initial_stop_points']} / {row['runner_target_points']} | "
            f"{row['evaluated_trades']} | {row['net_usd']} | {row['profit_factor']} | "
            f"{row['latest_year_net_usd']} | {row['worst_quarter_net_usd']} | "
            f"{row['max_trade_sequence_drawdown_usd']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This pass tests whether the breakeven-frequency idea is a risk-management "
            "problem or an entry-quality problem. If the accepted set stays empty, "
            "the answer is entry quality: the target-one touch is real, but the "
            "entry family is not strong enough to carry a robust managed-exit bot.",
            "",
        ],
    )
    Path(report_output).write_text("\n".join(lines), encoding="utf-8")


def _markdown_row(rank: int, row: dict[str, object]) -> str:
    return (
        "| "
        f"{rank} | `{row['filter_id']}` | {row['quantity']} | {row['split']} | "
        f"{row['first_target_points']} / {row['initial_stop_points']} / {row['runner_target_points']} | "
        f"{row['evaluated_trades']} | {row['trades_per_week']} | "
        f"{float(row['first_target_rate']) * 100:.1f}% | "
        f"{float(row['full_stop_rate']) * 100:.1f}% | "
        f"{row['net_usd']} | {row['profit_factor']} | "
        f"{row['latest_year_net_usd']} | {row['worst_quarter_net_usd']} | "
        f"{row['max_trade_sequence_drawdown_usd']} |"
    )


def _accepted_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    accepted = [
        row for row in rows
        if int(row["evaluated_trades"]) >= 120
        and float(row["trades_per_week"]) >= 1.2
        and float(row["net_usd"]) > 0.0
        and float(row["latest_year_net_usd"]) > 0.0
        and float(row["profit_factor"]) >= 1.20
        and float(row["worst_quarter_net_usd"]) > -1200.0
        and float(row["max_trade_sequence_drawdown_usd"]) > -2500.0
    ]
    accepted.sort(key=_ranking_key)
    return accepted


def _best_by_filter(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    best_by_filter: dict[str, dict[str, object]] = {}
    for row in rows:
        current = best_by_filter.get(str(row["filter_id"]))
        if current is None or _ranking_key(row) < _ranking_key(current):
            best_by_filter[str(row["filter_id"])] = row
    return sorted(best_by_filter.values(), key=_ranking_key)


def _ranking_key(row: dict[str, object]) -> tuple[float, ...]:
    trades = int(row["evaluated_trades"])
    net = float(row["net_usd"])
    latest = float(row["latest_year_net_usd"])
    pf = float(row["profit_factor"])
    worst_quarter = float(row["worst_quarter_net_usd"])
    max_drawdown = float(row["max_trade_sequence_drawdown_usd"])
    accepted_penalty = (
        0.0
        if (
            trades >= 120
            and net > 0.0
            and latest > 0.0
            and pf >= 1.20
            and worst_quarter > -1200.0
            and max_drawdown > -2500.0
        )
        else 1.0
    )
    return (
        accepted_penalty,
        0.0 if net > 0.0 else 1.0,
        0.0 if latest > 0.0 else 1.0,
        0.0 if worst_quarter > -1200.0 else 1.0,
        0.0 if max_drawdown > -2500.0 else 1.0,
        -pf,
        -net,
        max_drawdown,
        -trades,
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
