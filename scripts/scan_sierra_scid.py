#!/usr/bin/env python3
"""Inspect Sierra Chart ``.scid`` intraday data coverage."""

from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path
import time

from axontrade.data.sierra_scid import (
    SierraScidError,
    SierraScidSummary,
    calendar_coverage,
    scan_scid_file,
)


DEFAULT_DATA_DIR = Path("/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data")
DEFAULT_CONTRACTS = [
    "ESU24-CME",
    "ESZ24-CME",
    "ESH25-CME",
    "ESM25-CME",
    "ESU25-CME",
    "ESZ25-CME",
    "ESH26-CME",
    "ESM26-CME",
    "ESU26-CME",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan Sierra Chart SCID files for fast first/last timestamp coverage.",
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Specific .scid files to scan. Defaults to ES quarterly contracts in Sierra Data.",
    )
    parser.add_argument(
        "--data-dir",
        default=str(DEFAULT_DATA_DIR),
        help="Sierra Chart Data directory used when paths are not provided.",
    )
    parser.add_argument(
        "--contracts",
        default=",".join(DEFAULT_CONTRACTS),
        help="Comma-separated contract symbols used when paths are not provided.",
    )
    parser.add_argument(
        "--coverage-start",
        default="2024-06-09",
        help="Inclusive start date for calendar coverage estimate.",
    )
    parser.add_argument(
        "--coverage-end",
        default=date.today().isoformat(),
        help="Inclusive end date for calendar coverage estimate.",
    )
    parser.add_argument(
        "--watch",
        type=int,
        default=0,
        help="Repeat scan every N seconds until interrupted.",
    )
    args = parser.parse_args()

    paths = _resolve_paths(args.paths, Path(args.data_dir), args.contracts)
    coverage_start = date.fromisoformat(args.coverage_start)
    coverage_end = date.fromisoformat(args.coverage_end)

    while True:
        _scan_once(paths, coverage_start, coverage_end)
        if args.watch <= 0:
            return 0
        time.sleep(args.watch)


def _resolve_paths(raw_paths: list[str], data_dir: Path, contracts: str) -> list[Path]:
    if raw_paths:
        return [Path(path) for path in raw_paths]

    symbols = [symbol.strip() for symbol in contracts.split(",") if symbol.strip()]
    return [data_dir / f"{symbol}.scid" for symbol in symbols]


def _scan_once(paths: list[Path], coverage_start: date, coverage_end: date) -> None:
    scan_time = datetime.now().replace(microsecond=0).isoformat(sep=" ")
    print(f"scan_time={scan_time}")

    summaries: list[SierraScidSummary] = []
    missing_paths: list[Path] = []
    for path in paths:
        if not path.exists():
            missing_paths.append(path)
            continue
        try:
            summaries.append(scan_scid_file(path))
        except SierraScidError as exc:
            print(f"status=FAIL path={path} error={exc}")

    if summaries:
        active = max(summaries, key=lambda summary: summary.modified_at)
        print(
            "active_file="
            f"{active.path.name} modified={_format_datetime(active.modified_at)} "
            f"last_tick={_format_datetime(active.last_datetime)} "
            f"size_mib={active.size_mib:.1f}",
        )

        coverage = calendar_coverage(summaries, coverage_start, coverage_end)
        print(
            "calendar_coverage="
            f"{coverage.start_date}..{coverage.end_date} "
            f"covered_days={coverage.covered_days} total_days={coverage.total_days} "
            f"percent={coverage.percent:.1f}",
        )

    if missing_paths:
        print("missing_files=" + ",".join(path.name for path in missing_paths))

    print("files:")
    for summary in summaries:
        print(
            "- "
            f"{summary.path.name} records={summary.record_count:,} "
            f"size_mib={summary.size_mib:.1f} "
            f"modified={_format_datetime(summary.modified_at)} "
            f"first={_format_datetime(summary.first_datetime)} "
            f"last={_format_datetime(summary.last_datetime)}",
        )


def _format_datetime(value: datetime | None) -> str:
    if value is None:
        return "none"
    return value.replace(microsecond=0).isoformat(sep=" ")


if __name__ == "__main__":
    raise SystemExit(main())
