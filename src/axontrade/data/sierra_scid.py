"""Inspect Sierra Chart intraday data files.

Sierra intraday ``.scid`` files are binary files with a fixed header and
fixed-size records. This module intentionally reads only header, first-record,
and last-record metadata by default, so it stays fast on multi-gigabyte tick
files.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Iterable, Iterator
import struct


SC_EPOCH = datetime(1899, 12, 30)
HEADER_STRUCT = struct.Struct("<IIIHHI36s")
RECORD_DATETIME_STRUCT = struct.Struct("<q")
RECORD_STRUCT_SIZE = 40
SCID_FILE_TYPE = 0x44494353


class SierraScidError(ValueError):
    """Raised when a Sierra intraday data file cannot be parsed."""


@dataclass(frozen=True)
class SierraScidHeader:
    file_type_unique_header_id: int
    header_size: int
    record_size: int
    version: int


@dataclass(frozen=True)
class SierraScidSummary:
    path: Path
    size_bytes: int
    modified_at: datetime
    header: SierraScidHeader
    record_count: int
    first_datetime: datetime | None
    last_datetime: datetime | None

    @property
    def first_date(self) -> date | None:
        return self.first_datetime.date() if self.first_datetime else None

    @property
    def last_date(self) -> date | None:
        return self.last_datetime.date() if self.last_datetime else None

    @property
    def size_mib(self) -> float:
        return self.size_bytes / 1024 / 1024


@dataclass(frozen=True)
class SierraScidRecord:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    number_of_trades: int
    volume: int
    bid_volume: int
    ask_volume: int

    @property
    def delta(self) -> int:
        return self.ask_volume - self.bid_volume


@dataclass(frozen=True)
class SierraScidBar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    number_of_trades: int
    volume: int
    bid_volume: int
    ask_volume: int

    @property
    def delta(self) -> int:
        return self.ask_volume - self.bid_volume

    @property
    def hlc_average(self) -> float:
        return (self.high + self.low + self.close) / 3.0


@dataclass(frozen=True)
class CalendarCoverage:
    start_date: date
    end_date: date
    covered_days: int
    total_days: int

    @property
    def percent(self) -> float:
        if self.total_days <= 0:
            return 0.0
        return self.covered_days / self.total_days * 100.0


def datetime_from_scid_microseconds(value: int) -> datetime:
    """Convert Sierra's integer microsecond timestamp to a ``datetime``."""

    return SC_EPOCH + timedelta(microseconds=value)


def scid_microseconds_from_datetime(value: datetime) -> int:
    """Convert a ``datetime`` to Sierra's integer microsecond timestamp."""

    return int((value - SC_EPOCH).total_seconds() * 1_000_000)


def read_scid_header(path: str | Path) -> SierraScidHeader:
    scid_path = Path(path)
    with scid_path.open("rb") as handle:
        raw_header = handle.read(HEADER_STRUCT.size)

    if len(raw_header) != HEADER_STRUCT.size:
        raise SierraScidError(f"SCID header is incomplete: {scid_path}")

    file_type_unique_header_id, header_size, record_size, version, *_ = HEADER_STRUCT.unpack(
        raw_header,
    )
    if file_type_unique_header_id != SCID_FILE_TYPE:
        raise SierraScidError(
            f"Unexpected SCID header id {file_type_unique_header_id:#x}: {scid_path}",
        )
    if header_size < HEADER_STRUCT.size:
        raise SierraScidError(f"Invalid SCID header size {header_size}: {scid_path}")
    if record_size < RECORD_DATETIME_STRUCT.size:
        raise SierraScidError(f"Invalid SCID record size {record_size}: {scid_path}")

    return SierraScidHeader(
        file_type_unique_header_id=file_type_unique_header_id,
        header_size=header_size,
        record_size=record_size,
        version=version,
    )


def scan_scid_file(path: str | Path) -> SierraScidSummary:
    """Return fast metadata for a Sierra intraday data file."""

    scid_path = Path(path)
    stat_result = scid_path.stat()
    header = read_scid_header(scid_path)

    if stat_result.st_size < header.header_size:
        raise SierraScidError(f"SCID file is smaller than its header: {scid_path}")

    record_count = (stat_result.st_size - header.header_size) // header.record_size
    first_datetime = None
    last_datetime = None
    if record_count:
        first_datetime = _read_record_datetime(scid_path, header, 0)
        last_datetime = _read_record_datetime(scid_path, header, record_count - 1)

    return SierraScidSummary(
        path=scid_path,
        size_bytes=stat_result.st_size,
        modified_at=datetime.fromtimestamp(stat_result.st_mtime),
        header=header,
        record_count=record_count,
        first_datetime=first_datetime,
        last_datetime=last_datetime,
    )


def iter_scid_records(
    path: str | Path,
    *,
    start_datetime: datetime | None = None,
    end_datetime: datetime | None = None,
    chunk_records: int = 250_000,
) -> Iterator[SierraScidRecord]:
    """Yield records from a Sierra intraday data file.

    The file is streamed in chunks so multi-gigabyte tick files do not need to
    be loaded into memory.
    """

    scid_path = Path(path)
    header = read_scid_header(scid_path)
    if header.record_size != RECORD_STRUCT_SIZE:
        raise SierraScidError(
            f"Unsupported SCID record size {header.record_size}; expected {RECORD_STRUCT_SIZE}: {scid_path}",
        )
    if chunk_records <= 0:
        raise ValueError("chunk_records must be positive")
    if start_datetime is not None and end_datetime is not None and end_datetime < start_datetime:
        raise ValueError("end_datetime must be on or after start_datetime")

    chunk_size = header.record_size * chunk_records
    record_struct = struct.Struct("<qffffIIII")
    with scid_path.open("rb") as handle:
        handle.seek(header.header_size)
        while True:
            raw_chunk = handle.read(chunk_size)
            if not raw_chunk:
                break
            usable_size = len(raw_chunk) // header.record_size * header.record_size
            for fields in record_struct.iter_unpack(raw_chunk[:usable_size]):
                timestamp = datetime_from_scid_microseconds(fields[0])
                if start_datetime is not None and timestamp < start_datetime:
                    continue
                if end_datetime is not None and timestamp > end_datetime:
                    return
                yield SierraScidRecord(
                    timestamp=timestamp,
                    open=float(fields[1]),
                    high=float(fields[2]),
                    low=float(fields[3]),
                    close=float(fields[4]),
                    number_of_trades=int(fields[5]),
                    volume=int(fields[6]),
                    bid_volume=int(fields[7]),
                    ask_volume=int(fields[8]),
                )


def aggregate_scid_time_bars(
    records: Iterable[SierraScidRecord],
    *,
    bar_seconds: int = 180,
    session_start: str | None = None,
    session_end: str | None = None,
) -> Iterator[SierraScidBar]:
    """Aggregate SCID records into fixed-time OHLCV bars."""

    if bar_seconds <= 0:
        raise ValueError("bar_seconds must be positive")

    start_time = _parse_optional_time(session_start, "session_start")
    end_time = _parse_optional_time(session_end, "session_end")
    if start_time is not None and end_time is not None and end_time <= start_time:
        raise ValueError("session_end must be after session_start")

    current_start: datetime | None = None
    current_bar: _MutableScidBar | None = None

    for record in records:
        if start_time is not None and record.timestamp.time() < start_time:
            continue
        if end_time is not None and record.timestamp.time() >= end_time:
            continue

        bar_start = _floor_datetime(record.timestamp, bar_seconds)
        if current_start is not None and bar_start != current_start and current_bar is not None:
            yield current_bar.to_bar()
            current_bar = None

        if current_bar is None:
            current_start = bar_start
            current_bar = _MutableScidBar.from_record(bar_start, record)
            continue

        current_bar.add_record(record)

    if current_bar is not None:
        yield current_bar.to_bar()


def calendar_coverage(
    summaries: list[SierraScidSummary],
    start_date: date,
    end_date: date,
) -> CalendarCoverage:
    """Calculate inclusive calendar-day coverage from SCID summary ranges."""

    if end_date < start_date:
        raise ValueError("end_date must be on or after start_date")

    ranges: list[tuple[date, date]] = []
    for summary in summaries:
        if summary.first_date is None or summary.last_date is None:
            continue
        range_start = max(summary.first_date, start_date)
        range_end = min(summary.last_date, end_date)
        if range_start <= range_end:
            ranges.append((range_start, range_end))

    ranges.sort()
    merged: list[tuple[date, date]] = []
    for range_start, range_end in ranges:
        if not merged or range_start > merged[-1][1] + timedelta(days=1):
            merged.append((range_start, range_end))
            continue
        merged[-1] = (merged[-1][0], max(merged[-1][1], range_end))

    covered_days = sum((range_end - range_start).days + 1 for range_start, range_end in merged)
    total_days = (end_date - start_date).days + 1
    return CalendarCoverage(
        start_date=start_date,
        end_date=end_date,
        covered_days=covered_days,
        total_days=total_days,
    )


def _read_record_datetime(path: Path, header: SierraScidHeader, record_index: int) -> datetime:
    offset = header.header_size + record_index * header.record_size
    with path.open("rb") as handle:
        handle.seek(offset)
        raw_datetime = handle.read(RECORD_DATETIME_STRUCT.size)

    if len(raw_datetime) != RECORD_DATETIME_STRUCT.size:
        raise SierraScidError(f"SCID record datetime is incomplete: {path}")

    timestamp_microseconds = RECORD_DATETIME_STRUCT.unpack(raw_datetime)[0]
    return datetime_from_scid_microseconds(timestamp_microseconds)


@dataclass
class _MutableScidBar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    number_of_trades: int
    volume: int
    bid_volume: int
    ask_volume: int

    @classmethod
    def from_record(cls, timestamp: datetime, record: SierraScidRecord) -> "_MutableScidBar":
        open_price = record.open if record.open > 0 else record.close
        return cls(
            timestamp=timestamp,
            open=open_price,
            high=record.high,
            low=record.low,
            close=record.close,
            number_of_trades=record.number_of_trades,
            volume=record.volume,
            bid_volume=record.bid_volume,
            ask_volume=record.ask_volume,
        )

    def add_record(self, record: SierraScidRecord) -> None:
        self.high = max(self.high, record.high)
        self.low = min(self.low, record.low)
        self.close = record.close
        self.number_of_trades += record.number_of_trades
        self.volume += record.volume
        self.bid_volume += record.bid_volume
        self.ask_volume += record.ask_volume

    def to_bar(self) -> SierraScidBar:
        return SierraScidBar(
            timestamp=self.timestamp,
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            number_of_trades=self.number_of_trades,
            volume=self.volume,
            bid_volume=self.bid_volume,
            ask_volume=self.ask_volume,
        )


def _floor_datetime(value: datetime, seconds: int) -> datetime:
    seconds_since_midnight = value.hour * 3600 + value.minute * 60 + value.second
    floored_seconds = seconds_since_midnight // seconds * seconds
    return value.replace(
        hour=floored_seconds // 3600,
        minute=(floored_seconds % 3600) // 60,
        second=floored_seconds % 60,
        microsecond=0,
    )


def _parse_optional_time(value: str | None, field_name: str):
    if value is None or value == "":
        return None
    try:
        return datetime.strptime(value, "%H:%M:%S").time()
    except ValueError as exc:
        raise ValueError(f"{field_name} must use HH:MM:SS format") from exc
