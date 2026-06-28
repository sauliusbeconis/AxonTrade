#!/usr/bin/env python3
"""Run rolling walk-forward scaled-scalp sweeps over logged Sierra signals."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from axontrade.data import (
    SierraExportError,
    load_sierra_export_config,
    normalize_sierra_bar_study_file,
)
from axontrade.research import (
    SIGNAL_SCALED_SCALP_WALK_FORWARD_HEADER,
    SignalLogError,
    SignalScaledScalpExperimentError,
    TradeOutcomeError,
    load_signal_log_rows_csv,
    run_signal_scaled_scalp_walk_forward_sweep,
    validate_signal_entries_against_bars,
)


DEFAULT_EXPORT_CONFIG = "config/research/sierra_outcome_bar_export.yaml"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run rolling two-contract scaled-scalp walk-forward selection "
            "for logged signals."
        ),
    )
    parser.add_argument("bars_export", help="Path to Sierra exported bar/study text or CSV file.")
    parser.add_argument("signal_log", help="Path to AxonTrade signal-log CSV rows.")
    parser.add_argument("output", help="Path to write scaled-scalp walk-forward CSV rows.")
    parser.add_argument("--symbol", required=True, help="Futures symbol for the export, e.g. ESU26-CME.")
    parser.add_argument("--chart-number", type=int, default=2, help="Chart number to write in export rows.")
    parser.add_argument(
        "--session-phase",
        default="rth",
        help="Session phase label for rows when not present in the export.",
    )
    parser.add_argument(
        "--export-config",
        default=DEFAULT_EXPORT_CONFIG,
        help="Sierra export normalization config for outcome bar rows.",
    )
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
        "--first-target-points",
        default="0.75,1,1.25,1.5",
        help="Comma-separated fixed first-target point distances to test.",
    )
    parser.add_argument(
        "--stop-points",
        default="1.5,2,2.5,3",
        help="Comma-separated fixed initial stop point distances to test.",
    )
    parser.add_argument(
        "--runner-target-points",
        default="1.5,2,2.5,3,4,5",
        help="Comma-separated fixed runner target point distances to test.",
    )
    parser.add_argument(
        "--runner-stop-modes",
        default="breakeven,initial",
        help="Comma-separated runner stop modes to test: breakeven,initial.",
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
    parser.add_argument(
        "--entry-match-mode",
        choices=("bar_index", "timestamp", "auto"),
        default="auto",
        help="How to find bars after each logged signal entry.",
    )
    args = parser.parse_args()

    try:
        normalized_rows = normalize_sierra_bar_study_file(
            args.bars_export,
            symbol=args.symbol,
            chart_number=args.chart_number,
            session_phase=args.session_phase,
            config=load_sierra_export_config(args.export_config),
            compute_opening_range=False,
        )
        signal_rows = load_signal_log_rows_csv(args.signal_log)
        validate_signal_entries_against_bars(normalized_rows, signal_rows)
        split_rows = run_signal_scaled_scalp_walk_forward_sweep(
            normalized_rows,
            signal_rows,
            train_date_count=args.train_date_count,
            holdout_date_count=args.holdout_date_count,
            first_target_points_values=_parse_float_list(args.first_target_points),
            stop_points_values=_parse_float_list(args.stop_points),
            runner_target_points_values=_parse_float_list(args.runner_target_points),
            runner_stop_modes=_parse_string_list(args.runner_stop_modes),
            direction_filters=_parse_string_list(args.direction_filters),
            minimum_train_trades=args.minimum_train_trades,
            instrument_root=args.instrument_root,
            slippage_ticks_per_side=args.slippage_ticks_per_side,
            entry_match_mode=args.entry_match_mode,
        )
    except (
        SierraExportError,
        SignalLogError,
        SignalScaledScalpExperimentError,
        TradeOutcomeError,
    ) as exc:
        print(f"error: {exc}")
        return 2

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=SIGNAL_SCALED_SCALP_WALK_FORWARD_HEADER,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(split_rows)

    holdout_rows = [row for row in split_rows if row["sample"] == "holdout"]
    holdout_trades = sum(int(row["evaluated_trades"]) for row in holdout_rows)
    holdout_net_usd = sum(float(row["net_usd"]) for row in holdout_rows)
    print(
        f"wrote {len(split_rows)} scaled-scalp walk-forward rows to {output_path}; "
        f"holdout_windows={len(holdout_rows)}, "
        f"holdout_trades={holdout_trades}, "
        f"holdout_net_usd={holdout_net_usd:.2f}",
    )
    return 0


def _parse_float_list(value: str) -> list[float]:
    return [float(part.strip()) for part in value.split(",") if part.strip()]


def _parse_string_list(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
