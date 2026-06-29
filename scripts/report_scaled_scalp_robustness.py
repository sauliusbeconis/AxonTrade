#!/usr/bin/env python3
"""Write a Markdown robustness report for fixed scaled-scalp outcomes."""

from __future__ import annotations

import argparse

from axontrade.reports import (
    load_csv_rows,
    load_holiday_calendar_dates,
    load_holiday_calendar_metadata,
    write_scaled_scalp_robustness_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate a Markdown robustness report for fixed scaled-scalp outcomes.",
    )
    parser.add_argument("outcomes", help="Path to fixed-row scaled outcome CSV.")
    parser.add_argument("sweep", help="Path to scaled exit sweep CSV.")
    parser.add_argument("report", help="Path to write the Markdown report.")
    parser.add_argument("--title", default="Sierra Delta Impulse 3-Min Fixed Row Robustness")
    parser.add_argument("--variant-label", required=True)
    parser.add_argument("--main-summary-source")
    parser.add_argument("--holiday-calendar")
    parser.add_argument("--holiday-dates", default="")
    parser.add_argument("--holiday-source-url")
    parser.add_argument("--holiday-retrieved-date")
    parser.add_argument("--first-target-points", type=float, required=True)
    parser.add_argument("--stop-points", type=float, required=True)
    parser.add_argument("--runner-target-points", type=float, required=True)
    args = parser.parse_args()

    outcome_rows = load_csv_rows(args.outcomes)
    sweep_rows = load_csv_rows(args.sweep)
    holiday_dates = [
        date.strip()
        for date in args.holiday_dates.split(",")
        if date.strip()
    ]
    holiday_calendar_source = args.holiday_calendar
    if args.holiday_calendar:
        holiday_dates.extend(load_holiday_calendar_dates(args.holiday_calendar))
        calendar_metadata = load_holiday_calendar_metadata(args.holiday_calendar)
        if not args.holiday_source_url:
            args.holiday_source_url = calendar_metadata["source_url"] or None
        if not args.holiday_retrieved_date:
            args.holiday_retrieved_date = calendar_metadata["retrieved_date"] or None
    holiday_dates = sorted(set(holiday_dates))
    write_scaled_scalp_robustness_report(
        args.report,
        outcome_rows,
        sweep_rows,
        title=args.title,
        variant_label=args.variant_label,
        outcome_source=args.outcomes,
        sweep_source=args.sweep,
        main_summary_source=args.main_summary_source,
        holiday_calendar_source=holiday_calendar_source,
        holiday_dates=holiday_dates,
        holiday_source_url=args.holiday_source_url,
        holiday_retrieved_date=args.holiday_retrieved_date,
        first_target_points=args.first_target_points,
        stop_points=args.stop_points,
        runner_target_points=args.runner_target_points,
    )
    print(
        f"wrote robustness report to {args.report}; "
        f"outcomes={len(outcome_rows)}, sweep_rows={len(sweep_rows)}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
