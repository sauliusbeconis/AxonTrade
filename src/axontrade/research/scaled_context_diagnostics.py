"""Rolling context diagnostics for fixed scaled-scalp outcome rows."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from statistics import mean
from typing import Any, Iterable


SCALED_CONTEXT_DIAGNOSTIC_HEADER = [
    "schema_version",
    "context_id",
    "outcome_id",
    "event_key",
    "signal_id",
    "symbol",
    "direction",
    "entry_time",
    "entry_bar_index",
    "lookback_bars",
    "lookback_bars_available",
    "minutes_after_rth_open",
    "entry_price",
    "stop_price",
    "first_target_price",
    "runner_target_price",
    "risk_points",
    "first_target_points",
    "runner_target_points",
    "runner_reward_risk",
    "signal_price_move",
    "signal_delta_sum",
    "signal_abs_delta_sum",
    "lookback_range_points",
    "average_bar_range_points",
    "average_volume",
    "average_trades",
    "average_abs_delta",
    "entry_bar_range_points",
    "entry_bar_volume",
    "entry_bar_trades",
    "entry_bar_delta",
    "risk_to_average_bar_range",
    "runner_target_to_average_bar_range",
    "signal_abs_delta_sum_to_average_abs_delta",
    "entry_volume_to_average_volume",
    "entry_trades_to_average_trades",
    "entry_abs_delta_to_average_abs_delta",
    "exit_reason",
    "first_target_hit",
    "net_usd",
    "notes",
]
_TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
)
_RTH_OPEN_HOUR = 9
_RTH_OPEN_MINUTE = 30


class ScaledContextDiagnosticError(ValueError):
    """Raised when scaled context diagnostics cannot be computed."""


@dataclass(frozen=True)
class _ContextBar:
    timestamp: str
    parsed_timestamp: datetime
    symbol: str
    bar_index: int
    high: float
    low: float
    volume: float | None
    trades: float | None
    delta: float | None

    @property
    def bar_range(self) -> float:
        return self.high - self.low

    @property
    def abs_delta(self) -> float | None:
        return None if self.delta is None else abs(self.delta)


@dataclass(frozen=True)
class _SignalNotes:
    price_move: float | None = None
    delta_sum: float | None = None


def run_scaled_outcome_context_diagnostics(
    *,
    bar_rows: Iterable[dict[str, Any]],
    scaled_outcome_rows: Iterable[dict[str, Any]],
    signal_rows: Iterable[dict[str, Any]] = (),
    lookback_bars: int = 20,
) -> list[dict[str, Any]]:
    """Compute pre-entry rolling context for fixed scaled-scalp outcomes."""

    if lookback_bars <= 0:
        raise ScaledContextDiagnosticError("lookback_bars must be positive")

    bars_by_symbol_date = _bars_by_symbol_date(bar_rows)
    notes_by_signal_id = _signal_notes_by_id(signal_rows)
    return [
        _context_row(
            row,
            bars_by_symbol_date,
            notes_by_signal_id,
            lookback_bars=lookback_bars,
        )
        for row in scaled_outcome_rows
    ]


def _context_row(
    row: dict[str, Any],
    bars_by_symbol_date: dict[tuple[str, str], list[_ContextBar]],
    notes_by_signal_id: dict[str, _SignalNotes],
    *,
    lookback_bars: int,
) -> dict[str, Any]:
    symbol = str(row["symbol"])
    signal_id = str(row["signal_id"])
    entry_time = str(row["entry_time"])
    entry_timestamp = _parse_timestamp(entry_time)
    entry_bar_index = _to_int(row["entry_bar_index"], "entry_bar_index")
    same_day_bars = bars_by_symbol_date.get((symbol, entry_timestamp.date().isoformat()), [])
    if not same_day_bars:
        raise ScaledContextDiagnosticError(
            f"No context bars found for symbol={symbol} date={entry_timestamp.date().isoformat()}",
        )

    previous_bars = [
        bar
        for bar in same_day_bars
        if bar.bar_index < entry_bar_index
    ][-lookback_bars:]
    entry_bar = _find_entry_bar(same_day_bars, entry_bar_index)
    if not previous_bars:
        raise ScaledContextDiagnosticError(
            f"No previous context bars found for signal_id={signal_id}",
        )
    if entry_bar is None:
        raise ScaledContextDiagnosticError(
            f"No entry context bar found for signal_id={signal_id} "
            f"entry_bar_index={entry_bar_index}",
        )

    entry_price = _to_float(row["entry_price"], "entry_price")
    stop_price = _to_float(row["stop_price"], "stop_price")
    first_target_price = _to_float(row["first_target_price"], "first_target_price")
    runner_target_price = _to_float(row["runner_target_price"], "runner_target_price")
    risk_points = abs(entry_price - stop_price)
    first_target_points = abs(first_target_price - entry_price)
    runner_target_points = abs(runner_target_price - entry_price)
    average_bar_range = mean(bar.bar_range for bar in previous_bars)
    average_volume = _mean_optional(bar.volume for bar in previous_bars)
    average_trades = _mean_optional(bar.trades for bar in previous_bars)
    average_abs_delta = _mean_optional(bar.abs_delta for bar in previous_bars)
    signal_notes = notes_by_signal_id.get(signal_id, _SignalNotes())
    signal_abs_delta_sum = (
        None if signal_notes.delta_sum is None else abs(signal_notes.delta_sum)
    )

    return {
        "schema_version": 1,
        "context_id": f"{row['outcome_id']}:scaled_context:{lookback_bars}",
        "outcome_id": row["outcome_id"],
        "event_key": row["event_key"],
        "signal_id": signal_id,
        "symbol": symbol,
        "direction": row["direction"],
        "entry_time": entry_time,
        "entry_bar_index": entry_bar_index,
        "lookback_bars": lookback_bars,
        "lookback_bars_available": len(previous_bars),
        "minutes_after_rth_open": _format_number(_minutes_after_rth_open(entry_timestamp)),
        "entry_price": _format_number(entry_price),
        "stop_price": _format_number(stop_price),
        "first_target_price": _format_number(first_target_price),
        "runner_target_price": _format_number(runner_target_price),
        "risk_points": _format_number(risk_points),
        "first_target_points": _format_number(first_target_points),
        "runner_target_points": _format_number(runner_target_points),
        "runner_reward_risk": _format_optional(_ratio_or_none(runner_target_points, risk_points)),
        "signal_price_move": _format_optional(signal_notes.price_move),
        "signal_delta_sum": _format_optional(signal_notes.delta_sum),
        "signal_abs_delta_sum": _format_optional(signal_abs_delta_sum),
        "lookback_range_points": _format_number(
            max(bar.high for bar in previous_bars) - min(bar.low for bar in previous_bars),
        ),
        "average_bar_range_points": _format_number(average_bar_range),
        "average_volume": _format_optional(average_volume),
        "average_trades": _format_optional(average_trades),
        "average_abs_delta": _format_optional(average_abs_delta),
        "entry_bar_range_points": _format_number(entry_bar.bar_range),
        "entry_bar_volume": _format_optional(entry_bar.volume),
        "entry_bar_trades": _format_optional(entry_bar.trades),
        "entry_bar_delta": _format_optional(entry_bar.delta),
        "risk_to_average_bar_range": _format_optional(
            _ratio_or_none(risk_points, average_bar_range),
        ),
        "runner_target_to_average_bar_range": _format_optional(
            _ratio_or_none(runner_target_points, average_bar_range),
        ),
        "signal_abs_delta_sum_to_average_abs_delta": _format_optional(
            _ratio_or_none(signal_abs_delta_sum, average_abs_delta),
        ),
        "entry_volume_to_average_volume": _format_optional(
            _ratio_or_none(entry_bar.volume, average_volume),
        ),
        "entry_trades_to_average_trades": _format_optional(
            _ratio_or_none(entry_bar.trades, average_trades),
        ),
        "entry_abs_delta_to_average_abs_delta": _format_optional(
            _ratio_or_none(entry_bar.abs_delta, average_abs_delta),
        ),
        "exit_reason": row["exit_reason"],
        "first_target_hit": row["first_target_hit"],
        "net_usd": row["net_usd"],
        "notes": "pre-entry normalized context for fixed scaled-scalp outcome row",
    }


def _bars_by_symbol_date(rows: Iterable[dict[str, Any]]) -> dict[tuple[str, str], list[_ContextBar]]:
    grouped: dict[tuple[str, str], list[_ContextBar]] = {}
    for row in rows:
        bar = _context_bar(row)
        grouped.setdefault(
            (bar.symbol, bar.parsed_timestamp.date().isoformat()),
            [],
        ).append(bar)
    for bars in grouped.values():
        bars.sort(key=lambda bar: (bar.bar_index, bar.parsed_timestamp))
    return grouped


def _context_bar(row: dict[str, Any]) -> _ContextBar:
    timestamp = str(row["timestamp"])
    bid_volume = _optional_float(row.get("bid_volume"), "bid_volume")
    ask_volume = _optional_float(row.get("ask_volume"), "ask_volume")
    volume = _optional_float(row.get("volume"), "volume")
    if volume is None and bid_volume is not None and ask_volume is not None:
        volume = bid_volume + ask_volume
    delta = _optional_float(row.get("delta"), "delta")
    if delta is None and bid_volume is not None and ask_volume is not None:
        delta = ask_volume - bid_volume

    return _ContextBar(
        timestamp=timestamp,
        parsed_timestamp=_parse_timestamp(timestamp),
        symbol=str(row["symbol"]),
        bar_index=_to_int(row["bar_index"], "bar_index"),
        high=_to_float(row["high"], "high"),
        low=_to_float(row["low"], "low"),
        volume=volume,
        trades=_optional_float(row.get("number_of_trades"), "number_of_trades"),
        delta=delta,
    )


def _signal_notes_by_id(rows: Iterable[dict[str, Any]]) -> dict[str, _SignalNotes]:
    notes_by_id = {}
    for row in rows:
        signal_id = str(row.get("signal_id", ""))
        if not signal_id:
            continue
        notes_by_id[signal_id] = _parse_signal_notes(str(row.get("notes", "")))
    return notes_by_id


def _parse_signal_notes(notes: str) -> _SignalNotes:
    return _SignalNotes(
        price_move=_extract_note_number(notes, "price_move"),
        delta_sum=_extract_note_number(notes, "delta_sum"),
    )


def _extract_note_number(notes: str, field_name: str) -> float | None:
    match = re.search(rf"(?:^|;\s*){re.escape(field_name)}=([-+]?\d+(?:\.\d+)?)", notes)
    if match is None:
        return None
    return float(match.group(1))


def _find_entry_bar(bars: list[_ContextBar], entry_bar_index: int) -> _ContextBar | None:
    matching_bars = [bar for bar in bars if bar.bar_index == entry_bar_index]
    return matching_bars[0] if matching_bars else None


def _minutes_after_rth_open(timestamp: datetime) -> float:
    return (
        timestamp.hour * 60
        + timestamp.minute
        + timestamp.second / 60
        - (_RTH_OPEN_HOUR * 60 + _RTH_OPEN_MINUTE)
    )


def _mean_optional(values: Iterable[float | None]) -> float | None:
    numeric_values = [value for value in values if value is not None]
    return mean(numeric_values) if numeric_values else None


def _ratio_or_none(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None
    return numerator / denominator


def _parse_timestamp(value: str) -> datetime:
    timestamp_text = _normalize_timestamp_text(value.strip())
    for timestamp_format in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(timestamp_text, timestamp_format)
        except ValueError:
            continue
    raise ScaledContextDiagnosticError(f"Invalid timestamp: {value!r}")


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
    return _to_float(value, field_name)


def _to_int(value: Any, field_name: str) -> int:
    try:
        return int(str(value))
    except ValueError as exc:
        raise ScaledContextDiagnosticError(
            f"Invalid integer field {field_name}: {value!r}",
        ) from exc


def _to_float(value: Any, field_name: str) -> float:
    try:
        return float(str(value))
    except ValueError as exc:
        raise ScaledContextDiagnosticError(
            f"Invalid numeric field {field_name}: {value!r}",
        ) from exc


def _format_optional(value: float | None) -> str:
    return "" if value is None else _format_number(value)


def _format_number(value: float) -> str:
    return f"{value:.8f}".rstrip("0").rstrip(".")
