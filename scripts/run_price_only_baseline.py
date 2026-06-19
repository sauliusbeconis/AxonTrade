#!/usr/bin/env python3
"""Run the first price-only baseline over a Sierra Chart export file."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from axontrade.data import normalize_sierra_bar_study_file
from axontrade.research import evaluate_price_only_vwap_reclaim, load_signal_log_schema


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert a Sierra bar/study export into AxonTrade signal rows.",
    )
    parser.add_argument("input", help="Path to Sierra exported bar/study text or CSV file.")
    parser.add_argument("output", help="Path to write AxonTrade signal CSV rows.")
    parser.add_argument("--symbol", required=True, help="Futures symbol for the export, e.g. ESU26-CME.")
    parser.add_argument("--chart-number", type=int, default=1, help="Chart number to write in signal rows.")
    parser.add_argument(
        "--session-phase",
        default="rth",
        help="Session phase label for rows when not present in the export.",
    )
    args = parser.parse_args()

    normalized_rows = normalize_sierra_bar_study_file(
        args.input,
        symbol=args.symbol,
        chart_number=args.chart_number,
        session_phase=args.session_phase,
    )
    signal_rows = evaluate_price_only_vwap_reclaim(normalized_rows)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    header = load_signal_log_schema()["csv"]["header"]
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(signal_rows)

    candidates = sum(row["event_type"] == "candidate_signal" for row in signal_rows)
    rejected = sum(row["event_type"] == "rejected_signal" for row in signal_rows)
    print(
        f"wrote {len(signal_rows)} rows to {output_path} "
        f"({candidates} candidate, {rejected} rejected)",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
