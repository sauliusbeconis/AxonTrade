#!/usr/bin/env python3
"""Run price-only baseline signals and conservative outcome evaluation."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from axontrade.data import normalize_sierra_bar_study_file
from axontrade.research import (
    TRADE_OUTCOME_CSV_HEADER,
    evaluate_price_only_vwap_reclaim,
    evaluate_trade_outcomes,
    load_signal_log_schema,
    summarize_trade_outcomes,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate conservative stop/target outcomes for the price-only baseline.",
    )
    parser.add_argument("input", help="Path to Sierra exported bar/study text or CSV file.")
    parser.add_argument("signals_output", help="Path to write generated signal CSV rows.")
    parser.add_argument("outcomes_output", help="Path to write trade outcome CSV rows.")
    parser.add_argument("--symbol", required=True, help="Futures symbol for the export, e.g. ESU26-CME.")
    parser.add_argument("--chart-number", type=int, default=1, help="Chart number to write in signal rows.")
    parser.add_argument(
        "--session-phase",
        default="rth",
        help="Session phase label for rows when not present in the export.",
    )
    parser.add_argument(
        "--opening-range-start",
        default="09:30:00",
        help="Opening range start time used when deriving levels from exported bars.",
    )
    parser.add_argument(
        "--opening-range-end",
        default="09:59:59",
        help="Opening range end time used when deriving levels from exported bars.",
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
    signal_rows = evaluate_price_only_vwap_reclaim(normalized_rows)
    outcome_rows = evaluate_trade_outcomes(
        normalized_rows,
        signal_rows,
        instrument_root=args.instrument_root,
        slippage_ticks_per_side=args.slippage_ticks_per_side,
    )

    _write_csv(
        Path(args.signals_output),
        load_signal_log_schema()["csv"]["header"],
        signal_rows,
    )
    _write_csv(Path(args.outcomes_output), TRADE_OUTCOME_CSV_HEADER, outcome_rows)

    candidates = sum(row["event_type"] == "candidate_signal" for row in signal_rows)
    rejected = sum(row["event_type"] == "rejected_signal" for row in signal_rows)
    summary = summarize_trade_outcomes(outcome_rows)
    print(
        f"wrote {len(signal_rows)} signals to {args.signals_output} "
        f"({candidates} candidate, {rejected} rejected)",
    )
    print(
        f"wrote {len(outcome_rows)} outcomes to {args.outcomes_output} "
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
