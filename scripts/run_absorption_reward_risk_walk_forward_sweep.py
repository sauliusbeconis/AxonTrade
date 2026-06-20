#!/usr/bin/env python3
"""Run rolling walk-forward reward/risk experiments over absorption outcomes."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from axontrade.research import (
    ABSORPTION_REWARD_RISK_SWEEP_HEADER,
    run_absorption_reward_risk_walk_forward_sweep,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run rolling reward/risk filter experiments over absorption outcomes.",
    )
    parser.add_argument("outcomes", help="Path to liquidity sweep absorption outcome CSV rows.")
    parser.add_argument("output", help="Path to write walk-forward selected rows.")
    parser.add_argument(
        "--train-date-count",
        type=int,
        default=6,
        help="Number of consecutive active outcome trade dates per training window.",
    )
    parser.add_argument(
        "--holdout-date-count",
        type=int,
        default=1,
        help="Number of consecutive active outcome trade dates per holdout window.",
    )
    parser.add_argument(
        "--minimum-reward-risks",
        default="0,0.5,0.75,1,1.25,1.5,2",
        help="Comma-separated minimum reward/risk thresholds to test.",
    )
    parser.add_argument(
        "--minimum-train-trades",
        type=int,
        default=1,
        help="Minimum selected training trades required in each walk-forward window.",
    )
    parser.add_argument(
        "--direction-filters",
        default="all,long,short",
        help="Comma-separated direction filters to test: all,long,short.",
    )
    args = parser.parse_args()

    outcome_rows = _read_csv(Path(args.outcomes))
    split_rows = run_absorption_reward_risk_walk_forward_sweep(
        outcome_rows,
        train_date_count=args.train_date_count,
        holdout_date_count=args.holdout_date_count,
        minimum_reward_risks=_parse_float_list(args.minimum_reward_risks),
        direction_filters=_parse_string_list(args.direction_filters),
        minimum_train_trades=args.minimum_train_trades,
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
        writer.writerows(split_rows)

    holdout_rows = [row for row in split_rows if row["sample"] == "holdout"]
    holdout_trades = sum(int(row["evaluated_trades"]) for row in holdout_rows)
    holdout_net_usd = sum(float(row["net_usd"]) for row in holdout_rows)
    print(
        f"wrote {len(split_rows)} walk-forward rows to {output_path}; "
        f"holdout_windows={len(holdout_rows)}, "
        f"holdout_trades={holdout_trades}, "
        f"holdout_net_usd={holdout_net_usd:.2f}",
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
