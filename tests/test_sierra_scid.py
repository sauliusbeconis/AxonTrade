from __future__ import annotations

from datetime import date, datetime
import struct

from axontrade.data.sierra_scid import (
    HEADER_STRUCT,
    RECORD_STRUCT_SIZE,
    SCID_FILE_TYPE,
    calendar_coverage,
    scan_scid_file,
    scid_microseconds_from_datetime,
)


def test_scan_scid_file_reads_first_and_last_record(tmp_path) -> None:
    scid_path = tmp_path / "ESU26-CME.scid"
    _write_scid(
        scid_path,
        [
            datetime(2026, 6, 1, 9, 30),
            datetime(2026, 6, 1, 9, 31),
            datetime(2026, 6, 2, 16, 0),
        ],
    )

    summary = scan_scid_file(scid_path)

    assert summary.record_count == 3
    assert summary.header.record_size == RECORD_STRUCT_SIZE
    assert summary.first_datetime == datetime(2026, 6, 1, 9, 30)
    assert summary.last_datetime == datetime(2026, 6, 2, 16, 0)
    assert summary.first_date == date(2026, 6, 1)
    assert summary.last_date == date(2026, 6, 2)


def test_calendar_coverage_merges_overlapping_file_ranges(tmp_path) -> None:
    first_path = tmp_path / "ESU25-CME.scid"
    second_path = tmp_path / "ESZ25-CME.scid"
    _write_scid(first_path, [datetime(2025, 6, 1), datetime(2025, 9, 20)])
    _write_scid(second_path, [datetime(2025, 9, 10), datetime(2025, 12, 20)])

    coverage = calendar_coverage(
        [scan_scid_file(first_path), scan_scid_file(second_path)],
        date(2025, 6, 1),
        date(2025, 12, 31),
    )

    assert coverage.covered_days == (date(2025, 12, 20) - date(2025, 6, 1)).days + 1
    assert coverage.total_days == (date(2025, 12, 31) - date(2025, 6, 1)).days + 1
    assert round(coverage.percent, 1) == 94.9


def _write_scid(path, timestamps: list[datetime]) -> None:
    header = HEADER_STRUCT.pack(
        SCID_FILE_TYPE,
        HEADER_STRUCT.size,
        RECORD_STRUCT_SIZE,
        1,
        0,
        0,
        b"",
    )
    record_struct = struct.Struct("<qffffIIII")
    with path.open("wb") as handle:
        handle.write(header)
        for index, timestamp in enumerate(timestamps):
            handle.write(
                record_struct.pack(
                    scid_microseconds_from_datetime(timestamp),
                    100.0 + index,
                    101.0 + index,
                    99.0 + index,
                    100.5 + index,
                    1,
                    10,
                    4,
                    6,
                ),
            )
