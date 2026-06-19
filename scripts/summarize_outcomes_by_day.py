#!/usr/bin/env python3
"""Write daily aggregate rows from a trade outcome CSV file."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from axontrade.research import (
    TRADE_OUTCOME_DAILY_CSV_HEADER,
    load_signal_rows_csv,
    summarize_trade_outcomes_by_day,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Summarize trade outcomes by entry date.",
    )
    parser.add_argument("outcomes", help="Path to trade outcome CSV rows.")
    parser.add_argument("output", help="Path to write daily aggregate CSV rows.")
    args = parser.parse_args()

    outcome_rows = load_signal_rows_csv(args.outcomes)
    daily_rows = summarize_trade_outcomes_by_day(outcome_rows)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=TRADE_OUTCOME_DAILY_CSV_HEADER,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(daily_rows)

    worst = min(daily_rows, key=lambda row: float(row["net_usd"]), default=None)
    if worst is None:
        print(f"wrote 0 daily rows to {output_path}")
    else:
        print(
            f"wrote {len(daily_rows)} daily rows to {output_path}; "
            f"worst day={worst['trade_date']} net_usd={float(worst['net_usd']):.2f}",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
