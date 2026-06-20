#!/usr/bin/env python3
"""Annotate research rows with scheduled-news blackout flags."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from axontrade.research import (
    NEWS_ANNOTATION_FIELDS,
    NewsExclusionError,
    annotate_rows_with_news_blackouts,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Append scheduled-news blackout fields to diagnostic CSV rows.",
    )
    parser.add_argument("input_rows", help="Path to diagnostic CSV rows with an entry timestamp.")
    parser.add_argument("news_events", help="Path to scheduled-news event CSV rows.")
    parser.add_argument("output", help="Path to write annotated diagnostic rows.")
    parser.add_argument(
        "--timestamp-field",
        default="entry_time",
        help="Input row timestamp field to compare against event_time.",
    )
    parser.add_argument(
        "--default-blackout-before-minutes",
        type=float,
        default=10.0,
        help="Default minutes before event_time to mark as blackout when event row is blank.",
    )
    parser.add_argument(
        "--default-blackout-after-minutes",
        type=float,
        default=15.0,
        help="Default minutes after event_time to mark as blackout when event row is blank.",
    )
    args = parser.parse_args()

    try:
        input_rows, input_header = _read_csv_with_header(Path(args.input_rows))
        news_rows, _ = _read_csv_with_header(Path(args.news_events))
        annotated_rows = annotate_rows_with_news_blackouts(
            input_rows,
            news_rows,
            timestamp_field=args.timestamp_field,
            default_blackout_before_minutes=args.default_blackout_before_minutes,
            default_blackout_after_minutes=args.default_blackout_after_minutes,
        )
    except (NewsExclusionError, OSError) as exc:
        print(f"error: {exc}")
        return 2

    output_header = list(input_header)
    output_header.extend(field for field in NEWS_ANNOTATION_FIELDS if field not in output_header)
    _write_csv(Path(args.output), output_header, annotated_rows)
    blackout_rows = [
        row
        for row in annotated_rows
        if str(row["in_news_blackout"]).strip().lower() == "true"
    ]
    print(
        f"wrote {len(annotated_rows)} news-annotated rows to {args.output}; "
        f"blackout_rows={len(blackout_rows)}",
    )
    return 0


def _read_csv_with_header(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        header = list(reader.fieldnames or [])
        rows: list[dict[str, str]] = []
        for row in reader:
            line_number = reader.line_num
            if None in row:
                raise NewsExclusionError(
                    f"{path}: CSV row {line_number} has more columns than the header; "
                    "quote fields containing commas",
                )
            missing_fields = [field for field in header if row.get(field) is None]
            if missing_fields:
                raise NewsExclusionError(
                    f"{path}: CSV row {line_number} has fewer columns than the header; "
                    "keep each event on one physical line",
                )
            rows.append({field: row.get(field, "") for field in header})
        return rows, header


def _write_csv(path: Path, header: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
