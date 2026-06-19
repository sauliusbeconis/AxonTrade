#!/usr/bin/env python3
"""Run chronological train/holdout parameter experiments."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from axontrade.data import normalize_sierra_bar_study_file
from axontrade.research import (
    PRICE_ONLY_TRAIN_HOLDOUT_SWEEP_HEADER,
    run_price_only_train_holdout_sweep,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run price-only parameter experiments on train and holdout dates.",
    )
    parser.add_argument("input", help="Path to Sierra exported bar/study text or CSV file.")
    parser.add_argument("output", help="Path to write train/holdout experiment CSV rows.")
    parser.add_argument("--symbol", required=True, help="Futures symbol for the export, e.g. ESU26-CME.")
    parser.add_argument("--chart-number", type=int, default=1, help="Chart number to write in signal rows.")
    parser.add_argument("--session-phase", default="rth", help="Session phase label for rows.")
    parser.add_argument("--opening-range-start", default="09:30:00", help="Opening range start time.")
    parser.add_argument("--opening-range-end", default="09:59:59", help="Opening range end time.")
    parser.add_argument(
        "--train-date-count",
        type=int,
        default=5,
        help="Number of earliest trade dates to use as the training sample.",
    )
    parser.add_argument(
        "--target-r-multiples",
        default="0.5,1,1.5,2,2.5,3",
        help="Comma-separated target R multiples to test.",
    )
    parser.add_argument(
        "--stop-buffers",
        default="0,0.25,0.5,1",
        help="Comma-separated stop buffer point values to test.",
    )
    parser.add_argument(
        "--minimum-opening-range-widths",
        default="1",
        help="Comma-separated minimum opening-range width point values to test.",
    )
    parser.add_argument(
        "--direction-filters",
        default="all,long,short",
        help="Comma-separated direction filters to test: all,long,short.",
    )
    parser.add_argument(
        "--instrument-root",
        help="Instrument root for cost modeling, e.g. ES or MES. Defaults to symbol inference.",
    )
    parser.add_argument(
        "--slippage-ticks-per-side",
        type=int,
        help="Override default slippage assumption from config/research/default_costs.yaml.",
    )
    args = parser.parse_args()

    normalized_rows = normalize_sierra_bar_study_file(
        args.input,
        symbol=args.symbol,
        chart_number=args.chart_number,
        session_phase=args.session_phase,
        compute_opening_range=True,
        opening_range_start_time=args.opening_range_start,
        opening_range_end_time=args.opening_range_end,
    )
    split_rows = run_price_only_train_holdout_sweep(
        normalized_rows,
        train_date_count=args.train_date_count,
        target_r_multiples=_parse_float_list(args.target_r_multiples),
        stop_buffer_points=_parse_float_list(args.stop_buffers),
        minimum_opening_range_width_points=_parse_float_list(
            args.minimum_opening_range_widths,
        ),
        direction_filters=_parse_string_list(args.direction_filters),
        instrument_root=args.instrument_root,
        slippage_ticks_per_side=args.slippage_ticks_per_side,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=PRICE_ONLY_TRAIN_HOLDOUT_SWEEP_HEADER,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(split_rows)

    selected = [row for row in split_rows if row["selected_on_train"] == "true"]
    train = next((row for row in selected if row["sample"] == "train"), None)
    holdout = next((row for row in selected if row["sample"] == "holdout"), None)
    if train is None or holdout is None:
        print(f"wrote {len(split_rows)} split rows to {output_path}")
    else:
        print(
            f"wrote {len(split_rows)} split rows to {output_path}; "
            f"selected direction_filter={train['direction_filter']}, "
            f"target_r={train['target_r_multiple']}, "
            f"stop_buffer={train['stop_buffer_points']}; "
            f"train_net_usd={float(train['net_usd']):.2f}, "
            f"holdout_net_usd={float(holdout['net_usd']):.2f}",
        )
    return 0


def _parse_float_list(value: str) -> list[float]:
    return [float(part.strip()) for part in value.split(",") if part.strip()]


def _parse_string_list(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
