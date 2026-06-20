from __future__ import annotations

import pytest

from axontrade.research import (
    NEWS_ANNOTATION_FIELDS,
    NEWS_EVENT_CSV_HEADER,
    NewsExclusionError,
    annotate_rows_with_news_blackouts,
    filter_news_blackout_rows,
)


def test_annotates_rows_inside_news_blackout() -> None:
    rows = annotate_rows_with_news_blackouts(
        [
            {
                "signal_id": "signal-1",
                "entry_time": "2026-06-19 09:27:00",
            },
            {
                "signal_id": "signal-2",
                "entry_time": "2026-06-19 10:00:00",
            },
        ],
        [
            {
                "event_id": "event-1",
                "event_time": "2026-06-19 09:30:00",
                "event_name": "Employment Situation",
                "currency": "USD",
                "impact": "high",
                "blackout_before_minutes": "5",
                "blackout_after_minutes": "10",
            },
        ],
    )

    assert NEWS_EVENT_CSV_HEADER[0] == "schema_version"
    assert "in_news_blackout" in NEWS_ANNOTATION_FIELDS
    assert rows[0]["in_news_blackout"] == "true"
    assert rows[0]["matched_news_event_id"] == "event-1"
    assert rows[0]["matched_news_event_name"] == "Employment Situation"
    assert rows[0]["minutes_from_news_event"] == "-3"
    assert rows[0]["news_blackout_before_minutes"] == "5"
    assert rows[0]["news_blackout_after_minutes"] == "10"
    assert rows[1]["in_news_blackout"] == "false"
    assert rows[1]["matched_news_event_id"] == ""


def test_annotates_rows_with_default_blackout_window() -> None:
    rows = annotate_rows_with_news_blackouts(
        [{"signal_id": "signal-1", "entry_time": "2026-06-19 09:20:00"}],
        [{"event_id": "event-1", "event_time": "2026-06-19 09:30:00"}],
        default_blackout_before_minutes=10,
        default_blackout_after_minutes=0,
    )

    assert rows[0]["in_news_blackout"] == "true"
    assert rows[0]["news_blackout_before_minutes"] == "10"
    assert rows[0]["news_blackout_after_minutes"] == "0"


def test_filters_news_blackout_rows() -> None:
    rows = filter_news_blackout_rows(
        [
            {"signal_id": "signal-1", "in_news_blackout": "true"},
            {"signal_id": "signal-2", "in_news_blackout": "false"},
        ],
    )

    assert rows == [{"signal_id": "signal-2", "in_news_blackout": "false"}]


def test_filter_requires_annotation_by_default() -> None:
    with pytest.raises(NewsExclusionError, match="in_news_blackout"):
        filter_news_blackout_rows([{"signal_id": "signal-1"}])


def test_annotate_requires_timestamp_field() -> None:
    with pytest.raises(NewsExclusionError, match="timestamp field"):
        annotate_rows_with_news_blackouts(
            [{"signal_id": "signal-1"}],
            [{"event_id": "event-1", "event_time": "2026-06-19 09:30:00"}],
        )
