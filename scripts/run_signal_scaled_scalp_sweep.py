#!/usr/bin/env python3
"""Run scaled-scalp sweeps over logged Sierra signal rows."""

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
    SIGNAL_SCALED_SCALP_SWEEP_HEADER,
    SignalLogError,
    SignalScaledScalpExperimentError,
    TradeOutcomeError,
    load_signal_log_rows_csv,
    run_signal_scaled_scalp_sweep,
    validate_signal_entries_against_bars,
)


DEFAULT_EXPORT_CONFIG = "config/research/sierra_outcome_bar_export.yaml"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sweep two-contract scaled-scalp exits for logged signals.",
    )
    parser.add_argument("bars_export", help="Path to Sierra exported bar/study text or CSV file.")
    parser.add_argument("signal_log", help="Path to AxonTrade signal-log CSV rows.")
    parser.add_argument("output", help="Path to write scaled-scalp sweep CSV rows.")
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
        "--slippage-ticks-per-contract",
        type=float,
        help=(
            "Override total slippage ticks per contract for the whole trade; "
            "use 1 to model passive entry plus one-tick market exit."
        ),
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
        experiment_rows = run_signal_scaled_scalp_sweep(
            normalized_rows,
            signal_rows,
            first_target_points_values=_parse_float_list(args.first_target_points),
            stop_points_values=_parse_float_list(args.stop_points),
            runner_target_points_values=_parse_float_list(args.runner_target_points),
            runner_stop_modes=_parse_string_list(args.runner_stop_modes),
            direction_filters=_parse_string_list(args.direction_filters),
            instrument_root=args.instrument_root,
            slippage_ticks_per_side=args.slippage_ticks_per_side,
            slippage_ticks_per_contract=args.slippage_ticks_per_contract,
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
            fieldnames=SIGNAL_SCALED_SCALP_SWEEP_HEADER,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(experiment_rows)

    best_row = max(experiment_rows, key=lambda row: float(row["net_usd"]), default=None)
    best_summary = (
        "none"
        if best_row is None
        else (
            f"{best_row['experiment_id']} "
            f"net_usd={float(best_row['net_usd']):.2f} "
            f"trades={best_row['evaluated_trades']}"
        )
    )
    print(
        f"wrote {len(experiment_rows)} scaled-scalp sweep rows to {output_path}; "
        f"best={best_summary}",
    )
    return 0


def _parse_float_list(value: str) -> list[float]:
    return [float(part.strip()) for part in value.split(",") if part.strip()]


def _parse_string_list(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
