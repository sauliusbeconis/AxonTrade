#!/usr/bin/env python3
"""Run rolling walk-forward auction-regime filter sweeps."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from axontrade.research import (
    SIGNAL_AUCTION_REGIME_FILTER_SWEEP_HEADER,
    SignalAuctionRegimeFilterExperimentError,
    run_signal_auction_regime_filter_walk_forward_sweep,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run rolling auction-regime filter walk-forward selection.",
    )
    parser.add_argument("regime_diagnostics", help="Path to auction-regime diagnostic CSV rows.")
    parser.add_argument("output", help="Path to write auction-regime walk-forward CSV rows.")
    parser.add_argument("--train-date-count", type=int, default=8)
    parser.add_argument("--holdout-date-count", type=int, default=2)
    parser.add_argument("--minimum-train-trades", type=int, default=4)
    parser.add_argument("--max-original-reward-risks", default="2,2.5,3.5,999")
    parser.add_argument("--min-minutes-after-rth-open", default="0,60")
    parser.add_argument("--max-minutes-after-rth-open", default="120,240,390")
    parser.add_argument("--max-session-range-points", default="20,35,50,999")
    parser.add_argument("--max-fade-edge-scores", default="0.65,0.75,0.85,1")
    parser.add_argument("--max-vwap-stretch-points", default="3,6,10,20,999")
    parser.add_argument("--max-open-stretch-points", default="3,6,10,20,999")
    parser.add_argument("--direction-filters", default="all,long,short")
    args = parser.parse_args()

    try:
        regime_rows = _read_csv(Path(args.regime_diagnostics))
        split_rows = run_signal_auction_regime_filter_walk_forward_sweep(
            regime_rows,
            train_date_count=args.train_date_count,
            holdout_date_count=args.holdout_date_count,
            minimum_train_trades=args.minimum_train_trades,
            max_original_reward_risks=_parse_float_list(args.max_original_reward_risks),
            min_minutes_after_rth_open_values=_parse_float_list(args.min_minutes_after_rth_open),
            max_minutes_after_rth_open_values=_parse_float_list(args.max_minutes_after_rth_open),
            max_session_range_points_values=_parse_float_list(args.max_session_range_points),
            max_fade_edge_scores=_parse_float_list(args.max_fade_edge_scores),
            max_vwap_stretch_points_values=_parse_float_list(args.max_vwap_stretch_points),
            max_open_stretch_points_values=_parse_float_list(args.max_open_stretch_points),
            direction_filters=_parse_string_list(args.direction_filters),
        )
    except (SignalAuctionRegimeFilterExperimentError, OSError) as exc:
        print(f"error: {exc}")
        return 2

    output_path = Path(args.output)
    _write_csv(output_path, SIGNAL_AUCTION_REGIME_FILTER_SWEEP_HEADER, split_rows)
    holdout_rows = [row for row in split_rows if row["sample"] == "holdout"]
    holdout_trades = sum(int(row["evaluated_trades"]) for row in holdout_rows)
    holdout_net_usd = sum(float(row["net_usd"]) for row in holdout_rows)
    print(
        f"wrote {len(split_rows)} auction-regime walk-forward rows to {output_path}; "
        f"holdout_windows={len(holdout_rows)}, "
        f"holdout_trades={holdout_trades}, "
        f"holdout_net_usd={holdout_net_usd:.2f}",
    )
    return 0


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, header: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _parse_float_list(value: str) -> list[float]:
    return [float(part.strip()) for part in value.split(",") if part.strip()]


def _parse_string_list(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
