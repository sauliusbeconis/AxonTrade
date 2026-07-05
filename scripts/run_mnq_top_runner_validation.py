#!/usr/bin/env python3
"""Validate frozen MNQ top-runner candidates."""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_mnq_eval_pass_wave_rider as wave  # noqa: E402
import run_mnq_top_runner_refine as refine  # noqa: E402
import run_mnq_top_runner_research as runner  # noqa: E402


DEFAULT_SUMMARY_OUTPUT = "reports/mnq-top-runner-validation.csv"
DEFAULT_HOLDOUT_OUTPUT = "reports/mnq-top-runner-validation-holdout.csv"
DEFAULT_REPORT_OUTPUT = "reports/mnq-top-runner-validation.md"
DEFAULT_TRAIN_DATE_COUNTS = "120,180,240"
DEFAULT_HOLDOUT_DATE_COUNTS = "40,40,60"


@dataclass(frozen=True)
class CandidateSpec:
    candidate_id: str
    label: str
    base_id: str
    filter_id: str
    target_points: float
    stop_points: float


SUMMARY_HEADER = [
    "schema_version",
    "candidate_id",
    "label",
    "slippage_ticks",
    "base_id",
    "filter_id",
    "quantity",
    "target_points",
    "stop_points",
    "evaluated_trades",
    "trades_per_week",
    "win_rate",
    "target_hit_rate",
    "stop_hit_rate",
    "end_of_session_rate",
    "net_usd",
    "average_trade_usd",
    "profit_factor",
    "payoff_ratio",
    "max_trade_sequence_drawdown_usd",
    "net_to_drawdown",
    "latest_year_trades",
    "latest_year_net_usd",
    "worst_quarter_net_usd",
    "worst_day_usd",
    "worst_trade_usd",
    "average_holding_minutes",
    "median_holding_minutes",
]

HOLDOUT_HEADER = [
    "schema_version",
    "candidate_id",
    "config",
    "window",
    "holdout_start_date",
    "holdout_end_date",
    "evaluated_trades",
    "win_rate",
    "net_usd",
    "average_trade_usd",
    "profit_factor",
    "max_drawdown_usd",
    "worst_trade_usd",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate frozen MNQ normal-profitability top-runner candidates.",
    )
    parser.add_argument("input", nargs="?", default=wave.DEFAULT_INPUT)
    parser.add_argument("--summary-output", default=DEFAULT_SUMMARY_OUTPUT)
    parser.add_argument("--holdout-output", default=DEFAULT_HOLDOUT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--symbol", default="MNQU26-CME")
    parser.add_argument("--slippage-ticks", default="1,2,4,6")
    parser.add_argument("--train-date-counts", default=DEFAULT_TRAIN_DATE_COUNTS)
    parser.add_argument("--holdout-date-counts", default=DEFAULT_HOLDOUT_DATE_COUNTS)
    args = parser.parse_args()

    slippage_ticks = [float(value) for value in args.slippage_ticks.split(",") if value.strip()]
    configs = _parse_configs(args.train_date_counts, args.holdout_date_counts)
    bars = wave._load_feature_bars(args.input)
    bars_by_date = wave._bars_by_date(bars)
    rows_by_index = wave._rows_by_global_index(bars_by_date)
    flatten_index_by_date = runner._flatten_index_by_date(bars_by_date)
    sample_info = runner._sample_info(bars)
    candidate_signals = _candidate_signals(
        _candidate_specs(),
        bars_by_date,
        rows_by_index,
        symbol=args.symbol,
    )

    summary_rows = []
    holdout_rows = []
    period_rows_by_candidate: dict[str, list[dict[str, object]]] = {}
    base_slippage = slippage_ticks[0]
    for candidate in _candidate_specs():
        for slippage in slippage_ticks:
            risk = _risk(candidate, slippage)
            outcomes = runner._evaluate_signals(
                candidate_signals[candidate.candidate_id],
                bars_by_date,
                rows_by_index,
                flatten_index_by_date,
                risk,
                family="runner_lookback_breakout_validation",
            )
            summary_rows.append(
                _summary_row(candidate, slippage, len(candidate_signals[candidate.candidate_id]), outcomes, risk, sample_info),
            )
            if slippage == base_slippage:
                period_rows_by_candidate[candidate.candidate_id] = _period_rows(outcomes)
                holdout_rows.extend(
                    _holdout_rows(candidate, outcomes, sorted(bars_by_date), configs),
                )

    summary_rows.sort(key=_summary_sort_key)
    holdout_rows.sort(key=lambda row: (str(row["candidate_id"]), str(row["config"]), int(row["window"])))
    _write_csv(args.summary_output, SUMMARY_HEADER, summary_rows)
    _write_csv(args.holdout_output, HOLDOUT_HEADER, holdout_rows)
    _write_report(
        args.report_output,
        bars,
        summary_rows,
        holdout_rows,
        period_rows_by_candidate,
        slippage_ticks,
        configs,
    )

    best = summary_rows[0] if summary_rows else None
    best_summary = "none"
    if best is not None:
        best_summary = (
            f"{best['candidate_id']} slip={best['slippage_ticks']} "
            f"net={best['net_usd']} pf={best['profit_factor']} "
            f"dd={best['max_trade_sequence_drawdown_usd']}"
        )
    print(
        f"wrote {len(summary_rows)} summary rows to {args.summary_output}; "
        f"holdout_rows={len(holdout_rows)}; best={best_summary}",
    )
    return 0


def _candidate_specs() -> list[CandidateSpec]:
    base_id = "lookback_lb20_buf0_delta600_cl65_end1230_skipfri"
    return [
        CandidateSpec(
            "mnq_top_runner_lb20_cl90_t160_s70",
            "high PF",
            base_id,
            "time_1000_1100__clmin_gte0p9",
            160.0,
            70.0,
        ),
        CandidateSpec(
            "mnq_top_runner_lb20_cl90_t120_s70",
            "lower DD",
            base_id,
            "time_1000_1100__clmin_gte0p9",
            120.0,
            70.0,
        ),
        CandidateSpec(
            "mnq_top_runner_lb20_cl80_t160_s70",
            "higher sample",
            base_id,
            "time_1000_1100__clmin_gte0p8",
            160.0,
            70.0,
        ),
    ]


def _risk(candidate: CandidateSpec, slippage_ticks: float) -> runner.RunnerRisk:
    quantity = 2
    return runner.RunnerRisk(
        quantity=quantity,
        target_points=candidate.target_points,
        stop_points=candidate.stop_points,
        round_turn_cost_usd=quantity
        * (2.0 * wave.COMMISSION_PER_SIDE_USD + slippage_ticks * wave.TICK_VALUE_USD),
    )


def _candidate_signals(
    candidates: list[CandidateSpec],
    bars_by_date: dict[date, list[wave.Bar]],
    rows_by_index: dict[int, int],
    *,
    symbol: str,
) -> dict[str, list[wave.Signal]]:
    bases = {base.base_id: base for base in refine._base_specs()}
    filters = {filter_spec.filter_id: filter_spec for filter_spec in refine._filter_specs()}
    signal_cache: dict[tuple[str, str], list[wave.Signal]] = {}
    for candidate in candidates:
        key = (candidate.base_id, candidate.filter_id)
        if key in signal_cache:
            continue
        base = bases[candidate.base_id]
        filter_spec = filters[candidate.filter_id]
        base_signals = base.signal_builder(bars_by_date, symbol)
        features_by_index = refine._features_by_index(base_signals, bars_by_date, rows_by_index)
        filtered = [
            wave.Signal(
                f"{candidate.base_id}:filter{candidate.filter_id}:validation",
                signal.direction,
                signal.bar,
                f"{signal.notes}; validation filter {candidate.filter_id}",
            )
            for signal in base_signals
            if filter_spec.keep(signal, features_by_index[signal.bar.index])
        ]
        signal_cache[key] = filtered
    return {
        candidate.candidate_id: signal_cache[(candidate.base_id, candidate.filter_id)]
        for candidate in candidates
    }


def _summary_row(
    candidate: CandidateSpec,
    slippage_ticks: float,
    raw_signal_count: int,
    outcomes: list[runner.RunnerOutcome],
    risk: runner.RunnerRisk,
    sample_info: runner.SampleInfo,
) -> dict[str, object]:
    base = runner._sweep_row(
        f"{candidate.base_id}:filter{candidate.filter_id}:validation:{candidate.candidate_id}",
        "runner_lookback_breakout_validation",
        raw_signal_count,
        outcomes,
        risk,
        sample_info,
    )
    return {
        "schema_version": 1,
        "candidate_id": candidate.candidate_id,
        "label": candidate.label,
        "slippage_ticks": wave._format_number(slippage_ticks),
        "base_id": candidate.base_id,
        "filter_id": candidate.filter_id,
        **{field: base[field] for field in SUMMARY_HEADER if field in base},
    }


def _period_rows(outcomes: list[runner.RunnerOutcome]) -> list[dict[str, object]]:
    groups: dict[str, list[runner.RunnerOutcome]] = defaultdict(list)
    for outcome in outcomes:
        groups[f"year:{outcome.entry_time.year}"].append(outcome)
        quarter = (outcome.entry_time.month - 1) // 3 + 1
        groups[f"quarter:{outcome.entry_time.year}Q{quarter}"].append(outcome)
    rows = []
    for period_id, period_outcomes in sorted(groups.items()):
        rows.append({"period_id": period_id, **_metrics(period_outcomes)})
    return rows


def _holdout_rows(
    candidate: CandidateSpec,
    outcomes: list[runner.RunnerOutcome],
    trade_dates: list[date],
    configs: list[tuple[int, int]],
) -> list[dict[str, object]]:
    rows = []
    by_date: dict[date, list[runner.RunnerOutcome]] = defaultdict(list)
    for outcome in outcomes:
        by_date[outcome.entry_time.date()].append(outcome)
    for train_count, holdout_count in configs:
        config_id = f"{train_count}x{holdout_count}"
        max_start = len(trade_dates) - train_count - holdout_count
        if max_start < 0:
            continue
        for window, start in enumerate(range(0, max_start + 1, holdout_count)):
            holdout_dates = trade_dates[start + train_count:start + train_count + holdout_count]
            holdout_outcomes = []
            for trade_date in holdout_dates:
                holdout_outcomes.extend(by_date.get(trade_date, []))
            metrics = _metrics(sorted(holdout_outcomes, key=lambda outcome: outcome.entry_time))
            rows.append(
                {
                    "schema_version": 1,
                    "candidate_id": candidate.candidate_id,
                    "config": config_id,
                    "window": window,
                    "holdout_start_date": holdout_dates[0].isoformat(),
                    "holdout_end_date": holdout_dates[-1].isoformat(),
                    **metrics,
                },
            )
    return rows


def _metrics(outcomes: list[runner.RunnerOutcome]) -> dict[str, object]:
    if not outcomes:
        return {
            "evaluated_trades": 0,
            "win_rate": "0",
            "net_usd": "0",
            "average_trade_usd": "0",
            "profit_factor": "0",
            "max_drawdown_usd": "0",
            "worst_trade_usd": "0",
        }
    values = [outcome.net_usd for outcome in outcomes]
    positive = [value for value in values if value > 0.0]
    negative = [value for value in values if value < 0.0]
    return {
        "evaluated_trades": len(outcomes),
        "win_rate": wave._format_number(len(positive) / len(outcomes)),
        "net_usd": wave._format_number(sum(values)),
        "average_trade_usd": wave._format_number(statistics.mean(values)),
        "profit_factor": wave._format_number(sum(positive) / abs(sum(negative)) if negative else 999.0),
        "max_drawdown_usd": wave._format_number(wave._max_drawdown(values)),
        "worst_trade_usd": wave._format_number(min(values)),
    }


def _parse_configs(train_counts: str, holdout_counts: str) -> list[tuple[int, int]]:
    train = [int(value) for value in train_counts.split(",") if value.strip()]
    holdout = [int(value) for value in holdout_counts.split(",") if value.strip()]
    if len(train) != len(holdout):
        raise ValueError("train and holdout count lists must have the same length")
    return list(zip(train, holdout))


def _write_report(
    report_output: str,
    bars: list[wave.Bar],
    summary_rows: list[dict[str, object]],
    holdout_rows: list[dict[str, object]],
    period_rows_by_candidate: dict[str, list[dict[str, object]]],
    slippage_ticks: list[float],
    configs: list[tuple[int, int]],
) -> None:
    base_slippage = slippage_ticks[0]
    base_rows = [
        row for row in summary_rows
        if float(row["slippage_ticks"]) == base_slippage
    ]
    stress_rows = sorted(
        summary_rows,
        key=lambda row: (str(row["candidate_id"]), float(row["slippage_ticks"])),
    )
    lines = [
        "# MNQ Top-Runner Validation",
        "",
        "Status: frozen validation of the strongest MNQ normal-profitability runner leads.",
        "",
        "## Objective",
        "",
        "This skips the breakeven-frequency path and tests a different family: "
        "lookback-breakout runners with fixed target/stop exits. The goal is PF, "
        "net profit, and drawdown quality, not eval-pass geometry.",
        "",
        "## Source",
        "",
        f"- rows: `{len(bars)}`",
        f"- dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        f"- unique dates: `{len({bar.trade_date for bar in bars})}`",
        "- quantity: fixed `2 MNQ`",
        "- cost model: `$0.50/side` commission plus variable total slippage ticks per contract",
        "- same-bar handling: stop first",
        "- holdout configs: "
        + ", ".join(f"`{train}x{holdout}`" for train, holdout in configs),
        "",
        "## Frozen Candidates",
        "",
        "| Candidate | Label | Filter | Target / Stop |",
        "| --- | --- | --- | ---: |",
    ]
    for candidate in _candidate_specs():
        lines.append(
            f"| `{candidate.candidate_id}` | {candidate.label} | "
            f"`{candidate.filter_id}` | {candidate.target_points:g} / {candidate.stop_points:g} |"
        )
    lines.extend(
        [
            "",
            "## Base Slippage",
            "",
            "| Candidate | Label | Trades | /Wk | Net | PF | Win | Target Hit | Latest | Worst Q | DD | Net/DD |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    for row in sorted(base_rows, key=_summary_sort_key):
        lines.append(
            "| "
            f"`{row['candidate_id']}` | {row['label']} | {row['evaluated_trades']} | "
            f"{row['trades_per_week']} | {row['net_usd']} | {row['profit_factor']} | "
            f"{float(row['win_rate']) * 100:.1f}% | {float(row['target_hit_rate']) * 100:.1f}% | "
            f"{row['latest_year_net_usd']} | {row['worst_quarter_net_usd']} | "
            f"{row['max_trade_sequence_drawdown_usd']} | {row['net_to_drawdown']} |"
        )
    lines.extend(
        [
            "",
            "## Slippage Stress",
            "",
            "| Candidate | Slippage Ticks | Net | PF | Latest | Worst Q | DD |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    for row in stress_rows:
        lines.append(
            "| "
            f"`{row['candidate_id']}` | {row['slippage_ticks']} | {row['net_usd']} | "
            f"{row['profit_factor']} | {row['latest_year_net_usd']} | "
            f"{row['worst_quarter_net_usd']} | {row['max_trade_sequence_drawdown_usd']} |"
        )
    lines.extend(
        [
            "",
            "## Rolling Holdout",
            "",
            "| Candidate | Config | Windows | Positive | Negative | No Trade | Holdout Net | Worst | Median |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    for row in _holdout_summary_rows(holdout_rows):
        lines.append(
            "| "
            f"`{row['candidate_id']}` | {row['config']} | {row['windows']} | "
            f"{row['positive']} | {row['negative']} | {row['no_trade']} | "
            f"{row['net_usd']} | {row['worst_net_usd']} | {row['median_net_usd']} |"
        )
    best = sorted(base_rows, key=_summary_sort_key)[0] if base_rows else None
    if best is not None:
        lines.extend(
            [
                "",
                f"## Period Breakdown: `{best['candidate_id']}`",
                "",
                "| Period | Trades | Net | PF | Max DD |",
                "| --- | ---: | ---: | ---: | ---: |",
            ],
        )
        for row in period_rows_by_candidate[str(best["candidate_id"])]:
            lines.append(
                "| "
                f"{row['period_id']} | {row['evaluated_trades']} | {row['net_usd']} | "
                f"{row['profit_factor']} | {row['max_drawdown_usd']} |"
            )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This validation promotes the lookback-breakout runner family to serious "
            "replay-candidate status if it keeps positive slippage stress and "
            "mostly positive rolling holdouts. It is not implemented as ACSIL and "
            "is not approved for live routing yet.",
            "",
            "Compare against the current MNQ VWAP/delta live lead: about `186` "
            "trades, `$9584.50` net, `2.09` PF, and `-$976` drawdown. The runner "
            "candidate can beat net/PF, but its drawdown is larger, so replay "
            "quality and operational fit matter before build.",
            "",
        ],
    )
    Path(report_output).write_text("\n".join(lines), encoding="utf-8")


def _holdout_summary_rows(holdout_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in holdout_rows:
        grouped[(str(row["candidate_id"]), str(row["config"]))].append(row)
    summary_rows = []
    for (candidate_id, config), rows in sorted(grouped.items()):
        nets = [float(row["net_usd"]) for row in rows]
        trade_counts = [int(row["evaluated_trades"]) for row in rows]
        summary_rows.append(
            {
                "candidate_id": candidate_id,
                "config": config,
                "windows": len(rows),
                "positive": sum(net > 0.0 for net in nets),
                "negative": sum(net < 0.0 for net in nets),
                "no_trade": sum(count == 0 for count in trade_counts),
                "net_usd": wave._format_number(sum(nets)),
                "worst_net_usd": wave._format_number(min(nets) if nets else 0.0),
                "median_net_usd": wave._format_number(statistics.median(nets) if nets else 0.0),
            },
        )
    return summary_rows


def _write_csv(path: str, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _summary_sort_key(row: dict[str, object]) -> tuple[float, ...]:
    return (
        0.0 if float(row["net_usd"]) > 0.0 else 1.0,
        0.0 if float(row["latest_year_net_usd"]) > 0.0 else 1.0,
        0.0 if float(row["profit_factor"]) >= 1.8 else 1.0,
        0.0 if float(row["max_trade_sequence_drawdown_usd"]) > -2500.0 else 1.0,
        -float(row["profit_factor"]),
        -float(row["net_to_drawdown"]),
        -float(row["net_usd"]),
    )


if __name__ == "__main__":
    raise SystemExit(main())
