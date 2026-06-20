#!/usr/bin/env python3
"""Run reward/risk threshold experiments over absorption outcomes."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from axontrade.research import (
    ABSORPTION_REWARD_RISK_SWEEP_HEADER,
    run_absorption_reward_risk_train_holdout_sweep,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run chronological reward/risk filter experiments over absorption outcomes.",
    )
    parser.add_argument("outcomes", help="Path to liquidity sweep absorption outcome CSV rows.")
    parser.add_argument("output", help="Path to write reward/risk sweep CSV rows.")
    parser.add_argument(
        "--train-date-count",
        type=int,
        default=12,
        help="Number of active outcome trade dates to use for training.",
    )
    parser.add_argument(
        "--minimum-reward-risks",
        default="0,0.5,0.75,1,1.25,1.5,2",
        help="Comma-separated minimum reward/risk thresholds to test.",
    )
    parser.add_argument(
        "--direction-filters",
        default="all,long,short",
        help="Comma-separated direction filters to test: all,long,short.",
    )
    args = parser.parse_args()

    outcome_rows = _read_csv(Path(args.outcomes))
    experiment_rows = run_absorption_reward_risk_train_holdout_sweep(
        outcome_rows,
        train_date_count=args.train_date_count,
        minimum_reward_risks=_parse_float_list(args.minimum_reward_risks),
        direction_filters=_parse_string_list(args.direction_filters),
    )
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=ABSORPTION_REWARD_RISK_SWEEP_HEADER,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(experiment_rows)

    selected_holdout = [
        row
        for row in experiment_rows
        if row["sample"] == "holdout" and row["selected_on_train"] == "true"
    ]
    selected_net = sum(float(row["net_usd"]) for row in selected_holdout)
    selected_trades = sum(int(row["evaluated_trades"]) for row in selected_holdout)
    print(
        f"wrote {len(experiment_rows)} reward/risk sweep rows to {output_path}; "
        f"selected_holdout_trades={selected_trades}, "
        f"selected_holdout_net_usd={selected_net:.2f}",
    )
    return 0


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _parse_float_list(value: str) -> list[float]:
    return [float(part.strip()) for part in value.split(",") if part.strip()]


def _parse_string_list(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
