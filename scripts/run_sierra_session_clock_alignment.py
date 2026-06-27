#!/usr/bin/env python3
"""Run session clock alignment diagnostics for a Sierra Chart export."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from axontrade.data import load_sierra_bar_study_rows
from axontrade.research import (
    SESSION_CLOCK_ALIGNMENT_HEADER,
    SessionClockAlignmentError,
    run_session_clock_alignment_diagnostics,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check whether Sierra export timestamps align with the intended session clock.",
    )
    parser.add_argument("sierra_export", help="Path to Sierra exported bar/study text or CSV file.")
    parser.add_argument("output", help="Path to write session clock diagnostic CSV rows.")
    parser.add_argument("--expected-timezone", default="America/New_York")
    parser.add_argument("--local-timezone", default="Europe/Vilnius")
    parser.add_argument("--session-start-time", default="09:30:00")
    parser.add_argument("--session-end-time", default="16:15:00")
    parser.add_argument(
        "--check-time",
        default="16:30:00",
        help="New York clock time to count as a sanity check.",
    )
    args = parser.parse_args()

    try:
        rows = run_session_clock_alignment_diagnostics(
            load_sierra_bar_study_rows(args.sierra_export),
            expected_timezone=args.expected_timezone,
            local_timezone=args.local_timezone,
            session_start_time=args.session_start_time,
            session_end_time=args.session_end_time,
            check_time=args.check_time,
        )
    except (OSError, SessionClockAlignmentError) as exc:
        print(f"error: {exc}")
        return 2

    output_path = Path(args.output)
    _write_csv(output_path, SESSION_CLOCK_ALIGNMENT_HEADER, rows)
    aligned_dates = sum(abs(float(row["first_bar_delay_seconds"])) <= 120 for row in rows)
    check_time_rows = sum(int(row["check_time_rows"]) for row in rows)
    start_rank_1_dates = sum(int(row["session_start_5m_volume_rank"]) == 1 for row in rows)
    print(
        f"wrote {len(rows)} session clock rows to {output_path}; "
        f"aligned_dates={aligned_dates}, "
        f"check_time_rows={check_time_rows}, "
        f"start_volume_rank_1_dates={start_rank_1_dates}",
    )
    return 0


def _write_csv(path: Path, header: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
