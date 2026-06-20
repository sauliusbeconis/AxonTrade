#!/usr/bin/env python3
"""Write a Markdown report from a Sierra/AxonTrade signal-log CSV file."""

from __future__ import annotations

import argparse

from axontrade.reports import write_signal_log_report
from axontrade.research import load_signal_log_rows_csv


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a Markdown report for AxonTrade signal-log rows.",
    )
    parser.add_argument("signal_log", help="Path to AxonTrade signal-log CSV rows.")
    parser.add_argument("report", help="Path to write the Markdown report.")
    args = parser.parse_args()

    signal_rows = load_signal_log_rows_csv(args.signal_log)
    write_signal_log_report(
        args.report,
        signal_rows,
        source=args.signal_log,
    )
    candidate_count = sum(row["event_type"] == "candidate_signal" for row in signal_rows)
    print(
        f"wrote report to {args.report}; "
        f"rows={len(signal_rows)}, candidates={candidate_count}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
