"""Scheduled-news blackout annotation for research rows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Iterable


NEWS_EVENT_CSV_HEADER = [
    "schema_version",
    "event_id",
    "event_time",
    "event_name",
    "currency",
    "impact",
    "blackout_before_minutes",
    "blackout_after_minutes",
    "source",
    "notes",
]
NEWS_ANNOTATION_FIELDS = [
    "in_news_blackout",
    "matched_news_event_id",
    "matched_news_event_time",
    "matched_news_event_name",
    "matched_news_event_currency",
    "matched_news_event_impact",
    "minutes_from_news_event",
    "news_blackout_before_minutes",
    "news_blackout_after_minutes",
    "news_notes",
]
_TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
)


class NewsExclusionError(ValueError):
    """Raised when scheduled-news annotation cannot be computed."""


@dataclass(frozen=True)
class NewsEvent:
    event_id: str
    event_time: str
    parsed_time: datetime
    event_name: str
    currency: str
    impact: str
    blackout_before_minutes: float
    blackout_after_minutes: float

    def contains(self, timestamp: datetime) -> bool:
        start = self.parsed_time - timedelta(minutes=self.blackout_before_minutes)
        end = self.parsed_time + timedelta(minutes=self.blackout_after_minutes)
        return start <= timestamp <= end

    def minutes_from(self, timestamp: datetime) -> float:
        return (timestamp - self.parsed_time).total_seconds() / 60.0


def annotate_rows_with_news_blackouts(
    rows: Iterable[dict[str, Any]],
    news_event_rows: Iterable[dict[str, Any]],
    *,
    timestamp_field: str = "entry_time",
    default_blackout_before_minutes: float = 10.0,
    default_blackout_after_minutes: float = 15.0,
) -> list[dict[str, Any]]:
    """Append scheduled-news blackout fields to research rows."""

    events = _normalize_news_events(
        news_event_rows,
        default_blackout_before_minutes=default_blackout_before_minutes,
        default_blackout_after_minutes=default_blackout_after_minutes,
    )
    return [
        _annotate_row(row, events, timestamp_field=timestamp_field)
        for row in rows
    ]


def filter_news_blackout_rows(
    rows: Iterable[dict[str, Any]],
    *,
    require_annotation: bool = True,
) -> list[dict[str, Any]]:
    """Remove rows marked inside a scheduled-news blackout."""

    filtered_rows: list[dict[str, Any]] = []
    for row in rows:
        if "in_news_blackout" not in row:
            if require_annotation:
                raise NewsExclusionError(
                    "Rows must include in_news_blackout before news exclusion can be applied",
                )
            filtered_rows.append(row)
            continue
        if str(row.get("in_news_blackout", "")).strip().lower() == "true":
            continue
        filtered_rows.append(row)
    return filtered_rows


def _annotate_row(
    row: dict[str, Any],
    events: list[NewsEvent],
    *,
    timestamp_field: str,
) -> dict[str, Any]:
    if timestamp_field not in row:
        raise NewsExclusionError(f"Missing timestamp field in row: {timestamp_field}")

    timestamp = _parse_timestamp(str(row[timestamp_field]))
    matching_events = [event for event in events if event.contains(timestamp)]
    annotated = dict(row)
    if not matching_events:
        annotated.update(_blank_annotation())
        return annotated

    matched_event = min(matching_events, key=lambda event: abs(event.minutes_from(timestamp)))
    annotated.update(
        {
            "in_news_blackout": "true",
            "matched_news_event_id": matched_event.event_id,
            "matched_news_event_time": matched_event.event_time,
            "matched_news_event_name": matched_event.event_name,
            "matched_news_event_currency": matched_event.currency,
            "matched_news_event_impact": matched_event.impact,
            "minutes_from_news_event": _format_number(matched_event.minutes_from(timestamp)),
            "news_blackout_before_minutes": _format_number(
                matched_event.blackout_before_minutes,
            ),
            "news_blackout_after_minutes": _format_number(
                matched_event.blackout_after_minutes,
            ),
            "news_notes": "inside scheduled-news blackout window",
        },
    )
    return annotated


def _blank_annotation() -> dict[str, str]:
    return {
        "in_news_blackout": "false",
        "matched_news_event_id": "",
        "matched_news_event_time": "",
        "matched_news_event_name": "",
        "matched_news_event_currency": "",
        "matched_news_event_impact": "",
        "minutes_from_news_event": "",
        "news_blackout_before_minutes": "",
        "news_blackout_after_minutes": "",
        "news_notes": "outside scheduled-news blackout windows",
    }


def _normalize_news_events(
    rows: Iterable[dict[str, Any]],
    *,
    default_blackout_before_minutes: float,
    default_blackout_after_minutes: float,
) -> list[NewsEvent]:
    if default_blackout_before_minutes < 0:
        raise NewsExclusionError("default_blackout_before_minutes must be nonnegative")
    if default_blackout_after_minutes < 0:
        raise NewsExclusionError("default_blackout_after_minutes must be nonnegative")

    events: list[NewsEvent] = []
    for row_number, row in enumerate(rows, start=1):
        try:
            events.append(
                _normalize_news_event(
                    row,
                    default_blackout_before_minutes=default_blackout_before_minutes,
                    default_blackout_after_minutes=default_blackout_after_minutes,
                ),
            )
        except NewsExclusionError as exc:
            raise NewsExclusionError(f"News event row {row_number}: {exc}") from exc
    return sorted(events, key=lambda event: event.parsed_time)


def _normalize_news_event(
    row: dict[str, Any],
    *,
    default_blackout_before_minutes: float,
    default_blackout_after_minutes: float,
) -> NewsEvent:
    event_time = _optional_text(row.get("event_time"))
    if event_time == "":
        raise NewsExclusionError("News event row missing event_time")
    event_id = _optional_text(row.get("event_id")) or event_time
    before = _optional_float(row.get("blackout_before_minutes"), "blackout_before_minutes")
    after = _optional_float(row.get("blackout_after_minutes"), "blackout_after_minutes")
    before = default_blackout_before_minutes if before is None else before
    after = default_blackout_after_minutes if after is None else after
    if before < 0 or after < 0:
        raise NewsExclusionError("News event blackout minutes must be nonnegative")

    return NewsEvent(
        event_id=event_id,
        event_time=event_time,
        parsed_time=_parse_timestamp(event_time),
        event_name=_optional_text(row.get("event_name")),
        currency=_optional_text(row.get("currency")),
        impact=_optional_text(row.get("impact")),
        blackout_before_minutes=before,
        blackout_after_minutes=after,
    )


def _parse_timestamp(value: str) -> datetime:
    timestamp_text = _normalize_timestamp_text(value.strip())
    for timestamp_format in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(timestamp_text, timestamp_format)
        except ValueError:
            continue
    raise NewsExclusionError(f"Invalid timestamp: {value!r}")


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


def _optional_float(value: Any, field_name: str) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(str(value))
    except ValueError as exc:
        raise NewsExclusionError(f"Invalid numeric field {field_name}: {value!r}") from exc


def _optional_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _format_number(value: float) -> str:
    return f"{value:.8f}".rstrip("0").rstrip(".")
