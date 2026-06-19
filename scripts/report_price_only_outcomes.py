#!/usr/bin/env python3
"""Write a Markdown report from price-only signal and outcome CSV files."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from axontrade.reports import write_price_only_outcome_report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a Markdown report for price-only baseline outcomes.",
    )
    parser.add_argument("signals", help="Path to price-only signal CSV rows.")
    parser.add_argument("outcomes", help="Path to price-only outcome CSV rows.")
    parser.add_argument("report", help="Path to write the Markdown report.")
    args = parser.parse_args()

    signal_rows = _read_csv(Path(args.signals))
    outcome_rows = _read_csv(Path(args.outcomes))
    write_price_only_outcome_report(
        args.report,
        signal_rows,
        outcome_rows,
        signals_source=args.signals,
        outcomes_source=args.outcomes,
    )
    print(f"wrote report to {args.report}")
    return 0


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    raise SystemExit(main())
