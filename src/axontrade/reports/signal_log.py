"""Markdown reporting for Sierra-generated AxonTrade signal logs."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from axontrade.research import validate_signal_log_rows


def write_signal_log_report(
    path: str | Path,
    signal_rows: Iterable[dict[str, Any]],
    *,
    source: str,
) -> str:
    """Render and write a Markdown report for signal-log rows."""

    report = render_signal_log_report(signal_rows, source=source)
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    return report


def render_signal_log_report(
    signal_rows: Iterable[dict[str, Any]],
    *,
    source: str,
) -> str:
    """Render a deterministic Markdown summary from signal-log rows."""

    rows = validate_signal_log_rows(signal_rows)
    event_counts = Counter(str(row["event_type"]) for row in rows)
    rejection_counts = Counter(
        str(row["rejection_reason"])
        for row in rows
        if str(row["event_type"]) == "rejected_signal"
    )
    direction_counts = Counter(
        str(row["direction"])
        for row in rows
        if str(row["event_type"]) == "candidate_signal"
    )
    symbol_counts = Counter(str(row["symbol"]) for row in rows)
    strategy_counts = Counter(str(row["strategy_id"]) for row in rows)
    date_times = [_normalize_timestamp(row["bar_start_time"]) for row in rows]
    sorted_date_times = sorted(date_times)
    date_counts = Counter(timestamp.split(" ")[0] for timestamp in date_times)
    candidates = sorted(
        [
            row
            for row in rows
            if str(row["event_type"]) == "candidate_signal"
        ],
        key=lambda row: _normalize_timestamp(row["bar_start_time"]),
    )

    lines = [
        "# Sierra Signal Log Report",
        "",
        "This report summarizes indicator-only Sierra Chart signal-log rows.",
        "It is research-only and does not imply a tradable strategy.",
        "",
        "## Source",
        "",
        f"- Signal log: `{source}`",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Total rows | {len(rows)} |",
        f"| Candidate signals | {event_counts.get('candidate_signal', 0)} |",
        f"| Rejected signals | {event_counts.get('rejected_signal', 0)} |",
        f"| First row bar time | {_first_or_none(date_times)} |",
        f"| Last row bar time | {_last_or_none(date_times)} |",
        f"| Earliest bar time | {_first_or_none(sorted_date_times)} |",
        f"| Latest bar time | {_last_or_none(sorted_date_times)} |",
        "",
        "## Symbols",
        "",
        _counter_table(symbol_counts, "Symbol"),
        "",
        "## Strategy IDs",
        "",
        _counter_table(strategy_counts, "Strategy ID"),
        "",
        "## Event Types",
        "",
        _counter_table(event_counts, "Event type"),
        "",
        "## Dates",
        "",
        _counter_table(date_counts, "Date"),
        "",
        "## Candidate Directions",
        "",
        _counter_table(direction_counts, "Direction"),
        "",
        "## Rejection Reasons",
        "",
        _counter_table(rejection_counts, "Rejection reason"),
        "",
        "## Candidates",
        "",
        _candidate_table(candidates),
        "",
        "## Interpretation",
        "",
        _interpretation(len(rows), len(candidates)),
        "",
    ]
    return "\n".join(lines)


def _counter_table(counter: Counter[str], label: str) -> str:
    if not counter:
        return f"| {label} | Count |\n| --- | ---: |\n| none | 0 |"

    rows = [f"| {label} | Count |", "| --- | ---: |"]
    for key, value in sorted(counter.items()):
        rows.append(f"| {key} | {value} |")
    return "\n".join(rows)


def _candidate_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return (
            "| Time | Symbol | Direction | Entry | Stop | Target | Notes |\n"
            "| --- | --- | --- | ---: | ---: | ---: | --- |\n"
            "| none | none | none | 0 | 0 | 0 | none |"
        )

    lines = [
        "| Time | Symbol | Direction | Entry | Stop | Target | Notes |",
        "| --- | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in rows:
        lines.append(
            "| "
            f"{_normalize_timestamp(row['bar_start_time'])} | "
            f"{row['symbol']} | "
            f"{row['direction']} | "
            f"{row['signal_price']} | "
            f"{row['stop_price']} | "
            f"{row['target_price']} | "
            f"{_escape_table_text(str(row['notes']))} |",
        )
    return "\n".join(lines)


def _interpretation(row_count: int, candidate_count: int) -> str:
    if row_count == 0:
        return "No signal-log rows were available."
    if candidate_count == 0:
        return "The overlay ran but did not emit candidate signals in this sample."
    return (
        "The overlay emitted candidate rows. Evaluate outcomes separately before "
        "treating any candidate as strategy evidence."
    )


def _normalize_timestamp(value: Any) -> str:
    return " ".join(str(value).split())


def _first_or_none(values: list[str]) -> str:
    return values[0] if values else "none"


def _last_or_none(values: list[str]) -> str:
    return values[-1] if values else "none"


def _escape_table_text(value: str) -> str:
    return value.replace("|", "\\|")
