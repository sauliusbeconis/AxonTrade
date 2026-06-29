#!/usr/bin/env python3
"""Evaluate logged Sierra overlay candidates with two-contract scaled exits."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path
from typing import Any

from axontrade.data import (
    SierraExportError,
    load_sierra_export_config,
    normalize_sierra_bar_study_file,
)
from axontrade.research import (
    SignalLogError,
    SignalScaledScalpExperimentError,
    evaluate_signal_scaled_scalp_outcomes,
    load_signal_log_rows_csv,
    validate_signal_entries_against_bars,
)


DEFAULT_EXPORT_CONFIG = "config/research/sierra_outcome_bar_export.yaml"
SCALED_SCALP_OUTCOME_HEADER = [
    "schema_version",
    "outcome_id",
    "event_key",
    "signal_id",
    "symbol",
    "direction",
    "entry_bar_index",
    "exit_bar_index",
    "entry_time",
    "exit_time",
    "entry_price",
    "stop_price",
    "first_target_price",
    "runner_target_price",
    "leg1_exit_price",
    "runner_exit_price",
    "exit_reason",
    "first_target_hit",
    "holding_bars",
    "gross_points",
    "gross_usd",
    "commission_usd",
    "slippage_usd",
    "net_usd",
    "notes",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate logged Sierra overlay candidate signals as a two-contract "
            "scaled scalp: one first target and one runner."
        ),
    )
    parser.add_argument("bars_export", help="Path to Sierra exported bar/study text or CSV file.")
    parser.add_argument("signal_log", help="Path to AxonTrade signal-log CSV rows.")
    parser.add_argument("outcomes_output", help="Path to write scaled outcome CSV rows.")
    parser.add_argument("--symbol", required=True, help="Futures symbol for the export, e.g. ESU26-CME.")
    parser.add_argument("--chart-number", type=int, default=2, help="Chart number to write in export rows.")
    parser.add_argument("--session-phase", default="rth")
    parser.add_argument("--export-config", default=DEFAULT_EXPORT_CONFIG)
    parser.add_argument("--first-target-points", type=float, required=True)
    parser.add_argument("--stop-points", type=float, required=True)
    parser.add_argument("--runner-target-points", type=float, required=True)
    parser.add_argument(
        "--runner-stop-mode",
        choices=("breakeven", "initial"),
        default="breakeven",
    )
    parser.add_argument(
        "--direction-filter",
        choices=("all", "long", "short"),
        default="all",
    )
    parser.add_argument("--instrument-root")
    parser.add_argument("--slippage-ticks-per-side", type=int)
    parser.add_argument(
        "--slippage-ticks-per-contract",
        type=float,
        help="Override total slippage ticks per contract for the whole trade.",
    )
    parser.add_argument(
        "--entry-match-mode",
        choices=("bar_index", "timestamp", "auto"),
        default="auto",
    )
    parser.add_argument(
        "--maximum-entry-time-difference-seconds",
        type=float,
        default=300.0,
    )
    parser.add_argument(
        "--maximum-entry-price-difference-points",
        type=float,
        default=0.25,
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
        entry_diagnostics = validate_signal_entries_against_bars(
            normalized_rows,
            signal_rows,
            maximum_time_difference_seconds=args.maximum_entry_time_difference_seconds,
            maximum_price_difference_points=args.maximum_entry_price_difference_points,
        )
        outcome_rows = evaluate_signal_scaled_scalp_outcomes(
            normalized_rows,
            signal_rows,
            first_target_points=args.first_target_points,
            stop_points=args.stop_points,
            runner_target_points=args.runner_target_points,
            runner_stop_mode=args.runner_stop_mode,
            direction_filter=args.direction_filter,
            instrument_root=args.instrument_root,
            slippage_ticks_per_side=args.slippage_ticks_per_side,
            slippage_ticks_per_contract=args.slippage_ticks_per_contract,
            entry_match_mode=args.entry_match_mode,
        )
    except (SierraExportError, SignalLogError, SignalScaledScalpExperimentError, ValueError) as exc:
        print(f"error: {exc}")
        return 2

    _write_csv(Path(args.outcomes_output), SCALED_SCALP_OUTCOME_HEADER, outcome_rows)
    summary = summarize_scaled_outcomes(outcome_rows)
    print(
        f"validated {len(entry_diagnostics)} candidate entries against "
        f"{len(normalized_rows)} exported bars",
    )
    print(
        f"wrote {len(outcome_rows)} scaled outcomes to {args.outcomes_output} "
        f"(first_target_hits={summary['first_target_hits']}, "
        f"runner_targets={summary['runner_target_hits']}, "
        f"breakeven_exits={summary['runner_breakeven_stop_hits']}, "
        f"full_stops={summary['full_stop_hits']}, "
        f"net_usd={summary['net_usd']:.2f})",
    )
    return 0


def summarize_scaled_outcomes(rows: list[dict[str, Any]]) -> dict[str, Any]:
    exit_counts = Counter(str(row["exit_reason"]) for row in rows)
    first_target_hits = sum(str(row["first_target_hit"]).lower() == "true" for row in rows)
    net_usd = sum(float(row["net_usd"]) for row in rows)
    return {
        "trades": len(rows),
        "first_target_hits": first_target_hits,
        "runner_target_hits": exit_counts["runner_target_hit"],
        "runner_breakeven_stop_hits": exit_counts["runner_breakeven_stop_hit"],
        "full_stop_hits": exit_counts["full_stop_hit"],
        "other_exits": len(rows)
        - exit_counts["runner_target_hit"]
        - exit_counts["runner_breakeven_stop_hit"]
        - exit_counts["full_stop_hit"],
        "net_usd": net_usd,
    }


def _write_csv(path: Path, header: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
