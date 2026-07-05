#!/usr/bin/env python3
"""Fixed-candidate holdout validation for the MNQ breakeven-frequency lead."""

from __future__ import annotations

import argparse
import csv
import statistics
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_mnq_breakeven_frequency_candidate_validation as validation  # noqa: E402
import run_mnq_breakeven_frequency_refine as refine  # noqa: E402
import run_mnq_breakeven_frequency_research as be  # noqa: E402
import run_mnq_eval_pass_wave_rider as wave  # noqa: E402


DEFAULT_OUTPUT = "reports/mnq-breakeven-frequency-walk-forward.csv"
DEFAULT_REPORT_OUTPUT = "reports/mnq-breakeven-frequency-walk-forward.md"
DEFAULT_CONFIGS = "120x40,180x40,240x60"

HEADER = [
    "schema_version",
    "candidate_id",
    "config",
    "window_index",
    "train_start",
    "train_end",
    "holdout_start",
    "holdout_end",
    "train_trades",
    "train_net_usd",
    "train_profit_factor",
    "train_max_drawdown_usd",
    "holdout_trades",
    "holdout_net_usd",
    "holdout_profit_factor",
    "holdout_max_drawdown_usd",
]


@dataclass(frozen=True)
class WindowConfig:
    train_days: int
    holdout_days: int

    @property
    def config_id(self) -> str:
        return f"{self.train_days}x{self.holdout_days}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run fixed-candidate holdout validation for MNQ breakeven-frequency.",
    )
    parser.add_argument("input", nargs="?", default=wave.DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--symbol", default="MNQU26-CME")
    parser.add_argument("--configs", default=DEFAULT_CONFIGS)
    parser.add_argument("--slippage-ticks", type=float, default=1.0)
    args = parser.parse_args()

    configs = _parse_configs(args.configs)
    bars = wave._load_feature_bars(args.input)
    bars_by_date = wave._bars_by_date(bars)
    trade_dates = sorted(bars_by_date)
    outcomes = _candidate_outcomes(bars_by_date, args.symbol)
    rows = []
    for candidate in validation._candidate_specs():
        risk = validation._risk(candidate, args.slippage_ticks)
        for config in configs:
            rows.extend(_window_rows(candidate.candidate_id, outcomes, risk, trade_dates, config))

    _write_csv(args.output, HEADER, rows)
    _write_report(args.report_output, bars, rows, configs, args.slippage_ticks)
    print(
        f"wrote {len(rows)} MNQ breakeven holdout rows to {args.output}; "
        f"configs={','.join(config.config_id for config in configs)}",
    )
    return 0


def _candidate_outcomes(
    bars_by_date: dict[date, list[wave.Bar]],
    symbol: str,
) -> list[be.ManagedOutcome]:
    rows_by_index = wave._rows_by_global_index(bars_by_date)
    flatten_index_by_date = be._flatten_index_by_date(bars_by_date)
    signals = refine._base_signals(bars_by_date, symbol=symbol)
    features_by_index = refine._features_by_index(signals, bars_by_date, rows_by_index)
    filter_spec = {spec.filter_id: spec for spec in refine._filter_specs()}[validation.FILTER_ID]
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
    return [
        outcome
        for outcome in path_outcomes
        if filter_spec.keep(outcome, features_by_index[outcome.entry_bar_index])
    ]


def _window_rows(
    candidate_id: str,
    outcomes: list[be.ManagedOutcome],
    risk: be.ManagedRisk,
    trade_dates: list[date],
    config: WindowConfig,
) -> list[dict[str, object]]:
    rows = []
    window_index = 0
    step = config.holdout_days
    for start in range(0, len(trade_dates) - config.train_days - config.holdout_days + 1, step):
        train_dates = set(trade_dates[start:start + config.train_days])
        holdout_dates = set(
            trade_dates[
                start + config.train_days:start + config.train_days + config.holdout_days
            ],
        )
        train_outcomes = [outcome for outcome in outcomes if outcome.entry_time.date() in train_dates]
        holdout_outcomes = [
            outcome for outcome in outcomes if outcome.entry_time.date() in holdout_dates
        ]
        train_summary = _summary(train_outcomes, risk)
        holdout_summary = _summary(holdout_outcomes, risk)
        rows.append(
            {
                "schema_version": 1,
                "candidate_id": candidate_id,
                "config": config.config_id,
                "window_index": window_index,
                "train_start": min(train_dates).isoformat(),
                "train_end": max(train_dates).isoformat(),
                "holdout_start": min(holdout_dates).isoformat(),
                "holdout_end": max(holdout_dates).isoformat(),
                "train_trades": train_summary["trades"],
                "train_net_usd": wave._format_number(train_summary["net_usd"]),
                "train_profit_factor": wave._format_number(train_summary["profit_factor"]),
                "train_max_drawdown_usd": wave._format_number(train_summary["max_drawdown_usd"]),
                "holdout_trades": holdout_summary["trades"],
                "holdout_net_usd": wave._format_number(holdout_summary["net_usd"]),
                "holdout_profit_factor": wave._format_number(holdout_summary["profit_factor"]),
                "holdout_max_drawdown_usd": wave._format_number(
                    holdout_summary["max_drawdown_usd"],
                ),
            },
        )
        window_index += 1
    return rows


def _summary(
    outcomes: list[be.ManagedOutcome],
    risk: be.ManagedRisk,
) -> dict[str, float]:
    net_values = [be._net_usd_for_outcome(outcome, risk) for outcome in outcomes]
    positive = [value for value in net_values if value > 0.0]
    negative = [value for value in net_values if value < 0.0]
    return {
        "trades": float(len(outcomes)),
        "net_usd": sum(net_values),
        "profit_factor": sum(positive) / abs(sum(negative)) if negative else 999.0,
        "max_drawdown_usd": wave._max_drawdown(net_values),
    }


def _write_report(
    report_output: str,
    bars: list[wave.Bar],
    rows: list[dict[str, object]],
    configs: list[WindowConfig],
    slippage_ticks: float,
) -> None:
    grouped = _summary_by_candidate_config(rows)
    lines = [
        "# MNQ Breakeven-Frequency Walk-Forward Holdout",
        "",
        "Status: fixed-candidate holdout validation.",
        "",
        "## Candidate",
        "",
        f"- signal: `{refine.BASE_STRATEGY_ID}`",
        f"- filter: `{validation.FILTER_ID}`",
        "- management: `30 / 50 / 120`, target-one then runner breakeven",
        f"- slippage ticks: `{slippage_ticks:g}`",
        f"- source rows: `{len(bars)}`",
        f"- source dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        f"- configs: `{', '.join(config.config_id for config in configs)}`",
        "",
        "## Summary",
        "",
        "| Candidate | Config | Windows | Positive | Negative | No-Trade | Holdout Net | Worst Holdout | Median Holdout |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in grouped:
        lines.append(
            "| "
            f"`{row['candidate_id']}` | {row['config']} | {row['windows']} | "
            f"{row['positive_windows']} | {row['negative_windows']} | "
            f"{row['no_trade_windows']} | {wave._format_number(row['holdout_net_usd'])} | "
            f"{wave._format_number(row['worst_holdout_usd'])} | "
            f"{wave._format_number(row['median_holdout_usd'])} |"
        )
    lines.extend(
        [
            "",
            "## Window Detail",
            "",
            "| Candidate | Config | Window | Holdout Dates | Trades | Holdout Net | PF | Max DD |",
            "| --- | --- | ---: | --- | ---: | ---: | ---: | ---: |",
        ],
    )
    for row in rows:
        lines.append(
            "| "
            f"`{row['candidate_id']}` | {row['config']} | {row['window_index']} | "
            f"{row['holdout_start']} to {row['holdout_end']} | "
            f"{row['holdout_trades']} | {row['holdout_net_usd']} | "
            f"{row['holdout_profit_factor']} | {row['holdout_max_drawdown_usd']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "Because the candidate trades only about `1.25` times per week, short "
            "holdout windows are noisy and can have no trades. The important signal "
            "is whether losses cluster catastrophically in later windows. This check "
            "does not replace replay/mechanics testing.",
            "",
        ],
    )
    Path(report_output).write_text("\n".join(lines), encoding="utf-8")


def _summary_by_candidate_config(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[tuple[str, str], list[dict[str, object]]] = {}
    for row in rows:
        grouped.setdefault((str(row["candidate_id"]), str(row["config"])), []).append(row)
    summaries = []
    for (candidate_id, config), values in sorted(grouped.items()):
        holdout_values = [float(row["holdout_net_usd"]) for row in values]
        summaries.append(
            {
                "candidate_id": candidate_id,
                "config": config,
                "windows": len(values),
                "positive_windows": sum(value > 0.0 for value in holdout_values),
                "negative_windows": sum(value < 0.0 for value in holdout_values),
                "no_trade_windows": sum(int(row["holdout_trades"]) == 0 for row in values),
                "holdout_net_usd": sum(holdout_values),
                "worst_holdout_usd": min(holdout_values) if holdout_values else 0.0,
                "median_holdout_usd": statistics.median(holdout_values) if holdout_values else 0.0,
            },
        )
    return summaries


def _parse_configs(value: str) -> list[WindowConfig]:
    configs = []
    for token in value.split(","):
        token = token.strip().lower()
        if not token:
            continue
        train_days, holdout_days = token.split("x", 1)
        configs.append(WindowConfig(int(train_days), int(holdout_days)))
    return configs


def _write_csv(path: str, fieldnames: list[str], rows: Iterable[dict[str, object]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
