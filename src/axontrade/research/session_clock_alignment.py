"""Session clock alignment diagnostics for Sierra Chart exports."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, time
from typing import Any, Iterable
from zoneinfo import ZoneInfo


SESSION_CLOCK_ALIGNMENT_HEADER = [
    "schema_version",
    "trade_date",
    "expected_session_timezone",
    "local_timezone",
    "ny_utc_offset_hours",
    "ny_dst_active",
    "expected_session_start_time",
    "expected_local_session_start_time",
    "expected_session_end_time",
    "expected_local_session_end_time",
    "first_bar_time",
    "last_bar_time",
    "first_bar_delay_seconds",
    "last_bar_seconds_before_expected_end",
    "check_time",
    "check_time_rows",
    "first_30m_volume_share",
    "first_60m_volume_share",
    "session_start_5m_volume",
    "session_start_5m_volume_rank",
    "session_start_5m_trades",
    "session_start_5m_trade_rank",
    "top_volume_5m_bin",
    "top_volume_5m_volume",
    "top_trade_5m_bin",
    "top_trade_5m_trades",
    "notes",
]
_TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
)


class SessionClockAlignmentError(ValueError):
    """Raised when session clock diagnostics cannot be computed."""


@dataclass(frozen=True)
class _ClockBar:
    timestamp: datetime
    volume: int
    number_of_trades: int


def run_session_clock_alignment_diagnostics(
    rows: Iterable[dict[str, Any]],
    *,
    expected_timezone: str = "America/New_York",
    local_timezone: str = "Europe/Vilnius",
    session_start_time: str = "09:30:00",
    session_end_time: str = "16:15:00",
    check_time: str = "16:30:00",
) -> list[dict[str, Any]]:
    """Check whether exported timestamps align with the intended session clock."""

    bars = [_clock_bar(row) for row in rows]
    if not bars:
        raise SessionClockAlignmentError("No Sierra export rows were provided")

    expected_zone = ZoneInfo(expected_timezone)
    local_zone = ZoneInfo(local_timezone)
    start = _parse_time(session_start_time, "session_start_time")
    end = _parse_time(session_end_time, "session_end_time")
    check = _parse_time(check_time, "check_time")
    if start >= end:
        raise SessionClockAlignmentError("session_start_time must be before session_end_time")

    grouped: dict[str, list[_ClockBar]] = defaultdict(list)
    for bar in bars:
        grouped[bar.timestamp.date().isoformat()].append(bar)

    return [
        _diagnostic_row(
            trade_date,
            sorted(date_bars, key=lambda bar: bar.timestamp),
            expected_timezone=expected_timezone,
            local_timezone=local_timezone,
            expected_zone=expected_zone,
            local_zone=local_zone,
            start=start,
            end=end,
            check=check,
        )
        for trade_date, date_bars in sorted(grouped.items())
    ]


def _diagnostic_row(
    trade_date: str,
    bars: list[_ClockBar],
    *,
    expected_timezone: str,
    local_timezone: str,
    expected_zone: ZoneInfo,
    local_zone: ZoneInfo,
    start: time,
    end: time,
    check: time,
) -> dict[str, Any]:
    first_bar = bars[0]
    last_bar = bars[-1]
    session_start = datetime.combine(first_bar.timestamp.date(), start).replace(
        tzinfo=expected_zone,
    )
    session_end = datetime.combine(first_bar.timestamp.date(), end).replace(
        tzinfo=expected_zone,
    )
    bins = _five_minute_bins(bars)
    start_bin = _time_bin(start)
    volume_rank = _rank_bin(bins, start_bin, value_index=0)
    trade_rank = _rank_bin(bins, start_bin, value_index=1)
    top_volume_bin, top_volume_values = max(
        bins.items(),
        key=lambda item: item[1][0],
    )
    top_trade_bin, top_trade_values = max(
        bins.items(),
        key=lambda item: item[1][1],
    )
    check_rows = [
        bar
        for bar in bars
        if check <= bar.timestamp.time() < _add_minutes(check, minutes=30)
    ]
    total_volume = sum(bar.volume for bar in bars)

    return {
        "schema_version": 1,
        "trade_date": trade_date,
        "expected_session_timezone": expected_timezone,
        "local_timezone": local_timezone,
        "ny_utc_offset_hours": _format_number(session_start.utcoffset().total_seconds() / 3600),
        "ny_dst_active": str(bool(session_start.dst().total_seconds())).lower(),
        "expected_session_start_time": session_start.strftime("%H:%M:%S %Z"),
        "expected_local_session_start_time": (
            session_start.astimezone(local_zone).strftime("%H:%M:%S %Z")
        ),
        "expected_session_end_time": session_end.strftime("%H:%M:%S %Z"),
        "expected_local_session_end_time": (
            session_end.astimezone(local_zone).strftime("%H:%M:%S %Z")
        ),
        "first_bar_time": first_bar.timestamp.strftime("%H:%M:%S.%f").rstrip("0").rstrip("."),
        "last_bar_time": last_bar.timestamp.strftime("%H:%M:%S.%f").rstrip("0").rstrip("."),
        "first_bar_delay_seconds": _format_number(
            (first_bar.timestamp - session_start.replace(tzinfo=None)).total_seconds(),
        ),
        "last_bar_seconds_before_expected_end": _format_number(
            (session_end.replace(tzinfo=None) - last_bar.timestamp).total_seconds(),
        ),
        "check_time": check.strftime("%H:%M:%S"),
        "check_time_rows": len(check_rows),
        "first_30m_volume_share": _format_number(
            _volume_share(bars, start=start, minutes=30, total_volume=total_volume),
        ),
        "first_60m_volume_share": _format_number(
            _volume_share(bars, start=start, minutes=60, total_volume=total_volume),
        ),
        "session_start_5m_volume": bins.get(start_bin, (0, 0))[0],
        "session_start_5m_volume_rank": volume_rank,
        "session_start_5m_trades": bins.get(start_bin, (0, 0))[1],
        "session_start_5m_trade_rank": trade_rank,
        "top_volume_5m_bin": top_volume_bin,
        "top_volume_5m_volume": top_volume_values[0],
        "top_trade_5m_bin": top_trade_bin,
        "top_trade_5m_trades": top_trade_values[1],
        "notes": _notes(first_bar, session_start, check_rows),
    }


def _clock_bar(row: dict[str, Any]) -> _ClockBar:
    return _ClockBar(
        timestamp=_row_timestamp(row),
        volume=_to_int(_field_value(row, ["Volume", "volume"]), "Volume"),
        number_of_trades=_to_int(
            _field_value(row, ["# of Trades", "Number of Trades", "Trades", "number_of_trades"]),
            "# of Trades",
        ),
    )


def _row_timestamp(row: dict[str, Any]) -> datetime:
    timestamp_value = _first_present(row, ["Date Time", "DateTime", "Timestamp", "timestamp"])
    if timestamp_value:
        return _parse_timestamp(str(timestamp_value))

    date_value = _field_value(row, ["Date", "date"])
    time_value = _field_value(row, ["Time", "time"])
    return _parse_timestamp(f"{date_value} {time_value}")


def _five_minute_bins(bars: list[_ClockBar]) -> dict[str, tuple[int, int]]:
    bins: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for bar in bars:
        key = _time_bin(bar.timestamp.time())
        bins[key][0] += bar.volume
        bins[key][1] += bar.number_of_trades
    return {
        key: (values[0], values[1])
        for key, values in bins.items()
    }


def _rank_bin(
    bins: dict[str, tuple[int, int]],
    selected_bin: str,
    *,
    value_index: int,
) -> int:
    selected_value = bins.get(selected_bin, (0, 0))[value_index]
    return 1 + sum(
        values[value_index] > selected_value
        for values in bins.values()
    )


def _time_bin(value: time) -> str:
    total_minutes = ((value.hour * 60) + value.minute) // 5 * 5
    return f"{total_minutes // 60:02d}:{total_minutes % 60:02d}"


def _volume_share(
    bars: list[_ClockBar],
    *,
    start: time,
    minutes: int,
    total_volume: int,
) -> str:
    if total_volume <= 0:
        return "0"
    end = _add_minutes(start, minutes=minutes)
    selected_volume = sum(
        bar.volume
        for bar in bars
        if start <= bar.timestamp.time() < end
    )
    return _format_number(selected_volume / total_volume)


def _add_minutes(value: time, *, minutes: int) -> time:
    total_minutes = value.hour * 60 + value.minute + minutes
    return time((total_minutes // 60) % 24, total_minutes % 60, value.second)


def _notes(first_bar: _ClockBar, session_start: datetime, check_rows: list[_ClockBar]) -> str:
    delay_seconds = (first_bar.timestamp - session_start.replace(tzinfo=None)).total_seconds()
    if abs(delay_seconds) <= 120 and not check_rows:
        return "first bar aligns with expected New York session start; no rows at check time"
    if check_rows:
        return "rows exist at check time; inspect session/end-time settings"
    return "first bar does not align with expected New York session start"


def _field_value(row: dict[str, Any], names: list[str]) -> Any:
    value = _first_present(row, names)
    if value is None:
        raise SessionClockAlignmentError(
            "Missing Sierra export column; tried aliases: " + ", ".join(names),
        )
    return value


def _first_present(row: dict[str, Any], names: list[str]) -> Any | None:
    for name in names:
        if name in row and str(row[name]).strip() != "":
            return row[name]
    return None


def _parse_time(value: str, field_name: str) -> time:
    try:
        return datetime.strptime(str(value).strip(), "%H:%M:%S").time()
    except ValueError as exc:
        raise SessionClockAlignmentError(f"Invalid {field_name}: {value!r}") from exc


def _parse_timestamp(value: str) -> datetime:
    timestamp_text = _normalize_timestamp_text(value.strip())
    for timestamp_format in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(timestamp_text, timestamp_format)
        except ValueError:
            continue
    raise SessionClockAlignmentError(f"Invalid timestamp: {value!r}")


def _normalize_timestamp_text(value: str) -> str:
    parts = value.split(maxsplit=1)
    if len(parts) != 2 or "-" not in parts[0]:
        return value
    date_parts = parts[0].split("-")
    if len(date_parts) != 3:
        return value
    normalized_date = "-".join(
        [date_parts[0], date_parts[1].zfill(2), date_parts[2].zfill(2)],
    )
    return f"{normalized_date} {parts[1]}"


def _to_int(value: Any, field_name: str) -> int:
    try:
        return int(float(str(value)))
    except ValueError as exc:
        raise SessionClockAlignmentError(
            f"Invalid integer field {field_name}: {value!r}",
        ) from exc


def _format_number(value: Any) -> str:
    return f"{float(value):.8f}".rstrip("0").rstrip(".")
