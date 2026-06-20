#!/usr/bin/env python3
"""Run rolling walk-forward context-aware entry filter sweeps."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from axontrade.research import (
    SIGNAL_CONTEXT_FILTER_WALK_FORWARD_HEADER,
    SignalContextFilterExperimentError,
    run_signal_context_filter_walk_forward_sweep,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run rolling context-filter walk-forward selection.",
    )
    parser.add_argument("context_diagnostics", help="Path to signal context diagnostic CSV rows.")
    parser.add_argument("output", help="Path to write context filter walk-forward CSV rows.")
    parser.add_argument(
        "--train-date-count",
        type=int,
        default=8,
        help="Number of consecutive candidate trade dates per training window.",
    )
    parser.add_argument(
        "--holdout-date-count",
        type=int,
        default=2,
        help="Number of consecutive candidate trade dates per holdout window.",
    )
    parser.add_argument(
        "--minimum-train-trades",
        type=int,
        default=4,
        help="Minimum selected training trades required in each window.",
    )
    parser.add_argument(
        "--max-original-reward-risks",
        default="2.5,3.5,999",
        help="Comma-separated maximum original reward/risk thresholds.",
    )
    parser.add_argument(
        "--min-minutes-after-rth-open",
        default="0,60",
        help="Comma-separated minimum minutes after RTH open.",
    )
    parser.add_argument(
        "--max-minutes-after-rth-open",
        default="120,240,390",
        help="Comma-separated maximum minutes after RTH open.",
    )
    parser.add_argument(
        "--max-sweep-abs-deltas",
        default="3,10,999999",
        help="Comma-separated maximum absolute sweep delta thresholds.",
    )
    parser.add_argument(
        "--max-risk-to-average-bar-ranges",
        default="4,8,999999",
        help="Comma-separated maximum risk / average bar range thresholds.",
    )
    parser.add_argument(
        "--max-target-distance-to-average-bar-ranges",
        default="12,24,999999",
        help="Comma-separated maximum target distance / average bar range thresholds.",
    )
    parser.add_argument(
        "--max-sweep-abs-delta-to-average-abs-deltas",
        default="1,2,999999",
        help="Comma-separated maximum sweep absolute delta / average absolute delta thresholds.",
    )
    parser.add_argument(
        "--min-entry-volume-to-average-volumes",
        default="0,1",
        help="Comma-separated minimum entry volume / average volume thresholds.",
    )
    parser.add_argument(
        "--min-entry-trades-to-average-trades",
        default="0,1",
        help="Comma-separated minimum entry trades / average trades thresholds.",
    )
    parser.add_argument(
        "--direction-filters",
        default="all,long,short",
        help="Comma-separated direction filters to test: all,long,short.",
    )
    args = parser.parse_args()

    try:
        context_rows = _read_csv(Path(args.context_diagnostics))
        split_rows = run_signal_context_filter_walk_forward_sweep(
            context_rows,
            train_date_count=args.train_date_count,
            holdout_date_count=args.holdout_date_count,
            minimum_train_trades=args.minimum_train_trades,
            max_original_reward_risks=_parse_float_list(args.max_original_reward_risks),
            min_minutes_after_rth_open_values=_parse_float_list(
                args.min_minutes_after_rth_open,
            ),
            max_minutes_after_rth_open_values=_parse_float_list(
                args.max_minutes_after_rth_open,
            ),
            max_sweep_abs_deltas=_parse_float_list(args.max_sweep_abs_deltas),
            max_risk_to_average_bar_ranges=_parse_float_list(
                args.max_risk_to_average_bar_ranges,
            ),
            max_target_distance_to_average_bar_ranges=_parse_float_list(
                args.max_target_distance_to_average_bar_ranges,
            ),
            max_sweep_abs_delta_to_average_abs_deltas=_parse_float_list(
                args.max_sweep_abs_delta_to_average_abs_deltas,
            ),
            min_entry_volume_to_average_volumes=_parse_float_list(
                args.min_entry_volume_to_average_volumes,
            ),
            min_entry_trades_to_average_trades=_parse_float_list(
                args.min_entry_trades_to_average_trades,
            ),
            direction_filters=_parse_string_list(args.direction_filters),
        )
    except (SignalContextFilterExperimentError, OSError) as exc:
        print(f"error: {exc}")
        return 2

    _write_csv(Path(args.output), SIGNAL_CONTEXT_FILTER_WALK_FORWARD_HEADER, split_rows)
    holdout_rows = [row for row in split_rows if row["sample"] == "holdout"]
    holdout_trades = sum(int(row["evaluated_trades"]) for row in holdout_rows)
    holdout_net_usd = sum(float(row["net_usd"]) for row in holdout_rows)
    print(
        f"wrote {len(split_rows)} context filter walk-forward rows to {args.output}; "
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
