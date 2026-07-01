#!/usr/bin/env python3
"""Export fixed-time bars from a Sierra Chart ``.scid`` file."""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path

from axontrade.data.sierra_scid import aggregate_scid_time_bars, iter_scid_records


FIELDNAMES = [
    "Date Time",
    "Symbol",
    "Chart Number",
    "Bar Index",
    "Open",
    "High",
    "Low",
    "Last",
    "Volume",
    "# of Trades",
    "Bid Volume",
    "Ask Volume",
    "Ask Volume Bid Volume Difference",
    "HLC Avg",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stream a Sierra .scid file into Sierra-export-compatible OHLCV bars.",
    )
    parser.add_argument("scid_path", help="Input Sierra Chart .scid file.")
    parser.add_argument("output", help="CSV output path.")
    parser.add_argument("--symbol", required=True, help="Symbol to write in output rows.")
    parser.add_argument("--chart-number", type=int, default=1, help="Chart number metadata.")
    parser.add_argument("--bar-seconds", type=int, default=180, help="Output bar size in seconds.")
    parser.add_argument("--session-start", default="09:30:00", help="Inclusive session start time.")
    parser.add_argument("--session-end", default="16:00:00", help="Exclusive session end time.")
    parser.add_argument("--date-from", help="Inclusive start timestamp/date, e.g. 2026-01-01.")
    parser.add_argument("--date-to", help="Inclusive end timestamp/date, e.g. 2026-06-18.")
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    records = iter_scid_records(
        args.scid_path,
        start_datetime=_parse_datetime_arg(args.date_from, end_of_day=False),
        end_datetime=_parse_datetime_arg(args.date_to, end_of_day=True),
    )
    bars = aggregate_scid_time_bars(
        records,
        bar_seconds=args.bar_seconds,
        session_start=args.session_start,
        session_end=args.session_end,
    )

    row_count = 0
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row_count, bar in enumerate(bars, start=1):
            writer.writerow(
                {
                    "Date Time": bar.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "Symbol": args.symbol,
                    "Chart Number": args.chart_number,
                    "Bar Index": row_count - 1,
                    "Open": _format_number(bar.open),
                    "High": _format_number(bar.high),
                    "Low": _format_number(bar.low),
                    "Last": _format_number(bar.close),
                    "Volume": bar.volume,
                    "# of Trades": bar.number_of_trades,
                    "Bid Volume": bar.bid_volume,
                    "Ask Volume": bar.ask_volume,
                    "Ask Volume Bid Volume Difference": bar.delta,
                    "HLC Avg": _format_number(bar.hlc_average),
                },
            )

    print(f"wrote {row_count} bars to {output_path}")
    return 0


def _parse_datetime_arg(value: str | None, *, end_of_day: bool) -> datetime | None:
    if not value:
        return None
    raw_value = value.strip()
    if len(raw_value) == 10:
        suffix = "23:59:59.999999" if end_of_day else "00:00:00"
        raw_value = f"{raw_value} {suffix}"
    for timestamp_format in (
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(raw_value, timestamp_format)
        except ValueError:
            continue
    raise ValueError(f"invalid date/datetime: {value!r}")


def _format_number(value: float) -> str:
    return f"{value:.8f}".rstrip("0").rstrip(".")


if __name__ == "__main__":
    raise SystemExit(main())
