#!/usr/bin/env python3
"""Run rolling walk-forward entry-quality filter sweeps."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from axontrade.research import (
    SIGNAL_QUALITY_FILTER_WALK_FORWARD_HEADER,
    NewsExclusionError,
    SignalQualityFilterExperimentError,
    filter_news_blackout_rows,
    run_signal_quality_filter_walk_forward_sweep,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run rolling quality-filter walk-forward selection.",
    )
    parser.add_argument("diagnostics", help="Path to signal quality diagnostic CSV rows.")
    parser.add_argument("output", help="Path to write quality filter walk-forward CSV rows.")
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
        default="1.5,2,2.5,3,3.5,4,999",
        help="Comma-separated maximum original reward/risk thresholds.",
    )
    parser.add_argument(
        "--min-minutes-after-rth-open",
        default="0,60,90",
        help="Comma-separated minimum minutes after RTH open.",
    )
    parser.add_argument(
        "--max-minutes-after-rth-open",
        default="120,150,180,240,390",
        help="Comma-separated maximum minutes after RTH open.",
    )
    parser.add_argument(
        "--max-sweep-abs-deltas",
        default="3,5,10,20,999999",
        help="Comma-separated maximum absolute sweep delta thresholds.",
    )
    parser.add_argument(
        "--direction-filters",
        default="all,long,short",
        help="Comma-separated direction filters to test: all,long,short.",
    )
    parser.add_argument(
        "--exclude-news-blackout",
        action="store_true",
        help="Require and exclude rows with in_news_blackout=true.",
    )
    args = parser.parse_args()

    try:
        diagnostic_rows = _read_csv(Path(args.diagnostics))
        if args.exclude_news_blackout:
            diagnostic_rows = filter_news_blackout_rows(
                diagnostic_rows,
                require_annotation=True,
            )
        split_rows = run_signal_quality_filter_walk_forward_sweep(
            diagnostic_rows,
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
            direction_filters=_parse_string_list(args.direction_filters),
        )
    except (NewsExclusionError, SignalQualityFilterExperimentError, OSError) as exc:
        print(f"error: {exc}")
        return 2

    _write_csv(Path(args.output), SIGNAL_QUALITY_FILTER_WALK_FORWARD_HEADER, split_rows)
    holdout_rows = [row for row in split_rows if row["sample"] == "holdout"]
    holdout_trades = sum(int(row["evaluated_trades"]) for row in holdout_rows)
    holdout_net_usd = sum(float(row["net_usd"]) for row in holdout_rows)
    print(
        f"wrote {len(split_rows)} quality filter walk-forward rows to {args.output}; "
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
