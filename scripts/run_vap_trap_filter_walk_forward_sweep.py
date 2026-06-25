#!/usr/bin/env python3
"""Run rolling walk-forward VAP trap filter sweeps."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from axontrade.research import (
    VAP_TRAP_FILTER_SWEEP_HEADER,
    run_vap_trap_filter_walk_forward_sweep,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run rolling VAP trap filter walk-forward selection.",
    )
    parser.add_argument("diagnostics", help="Path to VAP diagnostic CSV rows.")
    parser.add_argument("output", help="Path to write VAP trap walk-forward CSV rows.")
    parser.add_argument(
        "--train-date-count",
        type=int,
        default=8,
        help="Number of consecutive active outcome trade dates per training window.",
    )
    parser.add_argument(
        "--holdout-date-count",
        type=int,
        default=2,
        help="Number of consecutive active outcome trade dates per holdout window.",
    )
    parser.add_argument(
        "--minimum-zone-aggression-ratios",
        default="1,1.25,1.5,2,3",
        help="Comma-separated minimum swept-zone aggression ratios to test.",
    )
    parser.add_argument(
        "--maximum-zone-volumes",
        default="3,5,10,20,50,100,250",
        help="Comma-separated maximum swept-zone bid+ask volume thresholds.",
    )
    parser.add_argument(
        "--maximum-zone-levels",
        default="1,2,3,5",
        help="Comma-separated maximum count of swept-zone price levels.",
    )
    parser.add_argument(
        "--minimum-extreme-volume-shares",
        default="0,0.25,0.5,0.75,1",
        help="Comma-separated minimum exact-extreme volume share thresholds.",
    )
    parser.add_argument(
        "--direction-filters",
        default="all,long,short",
        help="Comma-separated direction filters to test: all,long,short.",
    )
    parser.add_argument(
        "--minimum-train-trades",
        type=int,
        default=4,
        help="Minimum selected training trades required in each walk-forward window.",
    )
    args = parser.parse_args()

    diagnostic_rows = _read_csv(Path(args.diagnostics))
    split_rows = run_vap_trap_filter_walk_forward_sweep(
        diagnostic_rows,
        train_date_count=args.train_date_count,
        holdout_date_count=args.holdout_date_count,
        minimum_zone_aggression_ratios=_parse_float_list(args.minimum_zone_aggression_ratios),
        maximum_zone_volumes=_parse_float_list(args.maximum_zone_volumes),
        maximum_zone_levels=_parse_float_list(args.maximum_zone_levels),
        minimum_extreme_volume_shares=_parse_float_list(args.minimum_extreme_volume_shares),
        direction_filters=_parse_string_list(args.direction_filters),
        minimum_train_trades=args.minimum_train_trades,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=VAP_TRAP_FILTER_SWEEP_HEADER,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(split_rows)

    holdout_rows = [row for row in split_rows if row["sample"] == "holdout"]
    holdout_trades = sum(int(row["evaluated_trades"]) for row in holdout_rows)
    holdout_net_usd = sum(float(row["net_usd"]) for row in holdout_rows)
    print(
        f"wrote {len(split_rows)} VAP trap walk-forward rows to {output_path}; "
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
