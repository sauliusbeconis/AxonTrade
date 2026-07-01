from __future__ import annotations

from datetime import date, datetime
import struct

from axontrade.data.sierra_scid import (
    HEADER_STRUCT,
    RECORD_STRUCT_SIZE,
    SCID_FILE_TYPE,
    aggregate_scid_time_bars,
    calendar_coverage,
    iter_scid_records,
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


def test_iter_scid_records_reads_volume_fields(tmp_path) -> None:
    scid_path = tmp_path / "NQM26-CME.scid"
    _write_scid(
        scid_path,
        [
            datetime(2026, 6, 1, 9, 30, 1),
            datetime(2026, 6, 1, 9, 30, 2),
        ],
    )

    records = list(iter_scid_records(scid_path))

    assert len(records) == 2
    assert records[0].timestamp == datetime(2026, 6, 1, 9, 30, 1)
    assert records[0].volume == 10
    assert records[0].bid_volume == 4
    assert records[0].ask_volume == 6
    assert records[0].delta == 2


def test_aggregate_scid_time_bars_filters_session_and_sums_volume(tmp_path) -> None:
    scid_path = tmp_path / "NQM26-CME.scid"
    _write_scid(
        scid_path,
        [
            datetime(2026, 6, 1, 9, 29, 59),
            datetime(2026, 6, 1, 9, 30, 1),
            datetime(2026, 6, 1, 9, 31, 1),
            datetime(2026, 6, 1, 9, 33, 1),
            datetime(2026, 6, 1, 16, 0, 0),
        ],
    )

    bars = list(
        aggregate_scid_time_bars(
            iter_scid_records(scid_path),
            bar_seconds=180,
            session_start="09:30:00",
            session_end="16:00:00",
        ),
    )

    assert [bar.timestamp for bar in bars] == [
        datetime(2026, 6, 1, 9, 30),
        datetime(2026, 6, 1, 9, 33),
    ]
    assert bars[0].open == 101.0
    assert bars[0].high == 103.0
    assert bars[0].low == 100.0
    assert bars[0].close == 102.5
    assert bars[0].volume == 20
    assert bars[0].bid_volume == 8
    assert bars[0].ask_volume == 12
    assert bars[0].delta == 4


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
