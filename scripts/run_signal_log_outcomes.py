#!/usr/bin/env python3
"""Evaluate Sierra overlay signal-log candidates against exported bar data."""

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
    TRADE_OUTCOME_CSV_HEADER,
    SignalLogError,
    TradeOutcomeError,
    evaluate_trade_outcomes,
    load_signal_log_rows_csv,
    summarize_trade_outcomes,
    validate_signal_entries_against_bars,
)


DEFAULT_EXPORT_CONFIG = "config/research/sierra_outcome_bar_export.yaml"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate logged Sierra overlay candidate signals against exported bars.",
    )
    parser.add_argument("bars_export", help="Path to Sierra exported bar/study text or CSV file.")
    parser.add_argument("signal_log", help="Path to AxonTrade signal-log CSV rows.")
    parser.add_argument("outcomes_output", help="Path to write trade outcome CSV rows.")
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
    parser.add_argument(
        "--maximum-entry-time-difference-seconds",
        type=float,
        default=300.0,
        help="Maximum allowed distance between a signal time and nearest exported bar.",
    )
    parser.add_argument(
        "--maximum-entry-price-difference-points",
        type=float,
        default=0.25,
        help="Maximum allowed close/entry price difference at the nearest exported bar.",
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
        outcome_rows = evaluate_trade_outcomes(
            normalized_rows,
            signal_rows,
            instrument_root=args.instrument_root,
            slippage_ticks_per_side=args.slippage_ticks_per_side,
            entry_match_mode=args.entry_match_mode,
        )
    except (SierraExportError, SignalLogError, TradeOutcomeError) as exc:
        print(f"error: {exc}")
        return 2

    _write_csv(Path(args.outcomes_output), TRADE_OUTCOME_CSV_HEADER, outcome_rows)

    candidate_count = sum(row["event_type"] == "candidate_signal" for row in signal_rows)
    summary = summarize_trade_outcomes(outcome_rows)
    print(
        f"validated {len(entry_diagnostics)} candidate entries against "
        f"{len(normalized_rows)} exported bars",
    )
    print(
        f"wrote {len(outcome_rows)} outcomes to {args.outcomes_output} "
        f"from {candidate_count} candidates "
        f"(wins={summary['wins']}, losses={summary['losses']}, "
        f"other={summary['other_exits']}, net_usd={summary['net_usd']:.2f})",
    )
    return 0


def _write_csv(path: Path, header: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
