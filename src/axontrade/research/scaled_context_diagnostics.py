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
    "entry_open_price",
    "entry_close_price",
    "entry_bar_volume",
    "entry_bar_trades",
    "entry_bar_delta",
    "risk_to_average_bar_range",
    "runner_target_to_average_bar_range",
    "signal_abs_delta_sum_to_average_abs_delta",
    "entry_volume_to_average_volume",
    "entry_trades_to_average_trades",
    "entry_abs_delta_to_average_abs_delta",
    "session_open_price",
    "session_high_so_far",
    "session_low_so_far",
    "session_range_points",
    "entry_position_in_session_range",
    "continuation_edge_score",
    "fade_edge_score",
    "directional_open_distance_points",
    "opening_range_high",
    "opening_range_low",
    "opening_range_points",
    "entry_position_in_opening_range",
    "opening_range_continuation_edge_score",
    "opening_range_fade_edge_score",
    "directional_opening_range_breakout_points",
    "lookback_directional_move_points",
    "lookback_efficiency_ratio",
    "lookback_choppiness_score",
    "session_bars_so_far",
    "session_average_volume",
    "session_average_trades",
    "entry_volume_to_session_average_volume",
    "entry_trades_to_session_average_trades",
    "lookback_volume_to_session_average_volume",
    "lookback_trades_to_session_average_trades",
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
    open: float
    high: float
    low: float
    close: float
    volume: float | None
    trades: float | None
    delta: float | None
    opening_range_high: float | None = None
    opening_range_low: float | None = None

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
    bars_so_far = [
        bar
        for bar in same_day_bars
        if bar.bar_index <= entry_bar_index
    ]
    if not bars_so_far:
        raise ScaledContextDiagnosticError(
            f"No session context bars found for signal_id={signal_id}",
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
    session_open = bars_so_far[0].open
    session_high = max(bar.high for bar in bars_so_far)
    session_low = min(bar.low for bar in bars_so_far)
    session_range = session_high - session_low
    session_position = _ratio_or_none(entry_bar.close - session_low, session_range)
    continuation_edge_score = _direction_aware_continuation_edge_score(
        direction=str(row["direction"]),
        range_position=session_position,
    )
    fade_edge_score = _direction_aware_fade_edge_score(
        direction=str(row["direction"]),
        range_position=session_position,
    )
    opening_range_high = entry_bar.opening_range_high
    opening_range_low = entry_bar.opening_range_low
    if opening_range_high is None or opening_range_low is None:
        opening_range_high, opening_range_low = _computed_opening_range(same_day_bars)
    opening_range_points = _range_or_none(opening_range_high, opening_range_low)
    opening_range_position = _ratio_or_none(
        None if opening_range_low is None else entry_bar.close - opening_range_low,
        opening_range_points,
    )
    directional_opening_range_breakout = _direction_aware_opening_range_breakout(
        direction=str(row["direction"]),
        entry_price=entry_bar.close,
        opening_range_high=opening_range_high,
        opening_range_low=opening_range_low,
    )
    session_average_volume = _mean_optional(bar.volume for bar in bars_so_far)
    session_average_trades = _mean_optional(bar.trades for bar in bars_so_far)
    lookback_volume = _mean_optional(bar.volume for bar in previous_bars)
    lookback_trades = _mean_optional(bar.trades for bar in previous_bars)
    lookback_directional_move = _direction_aware_price_move(
        direction=str(row["direction"]),
        start_price=previous_bars[0].close,
        end_price=entry_bar.close,
    )
    lookback_efficiency = _lookback_efficiency_ratio([*previous_bars, entry_bar])
    lookback_choppiness = None if lookback_efficiency is None else 1.0 - lookback_efficiency

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
        "entry_open_price": _format_number(entry_bar.open),
        "entry_close_price": _format_number(entry_bar.close),
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
        "session_open_price": _format_number(session_open),
        "session_high_so_far": _format_number(session_high),
        "session_low_so_far": _format_number(session_low),
        "session_range_points": _format_number(session_range),
        "entry_position_in_session_range": _format_optional(session_position),
        "continuation_edge_score": _format_optional(continuation_edge_score),
        "fade_edge_score": _format_optional(fade_edge_score),
        "directional_open_distance_points": _format_number(
            _direction_aware_price_move(
                direction=str(row["direction"]),
                start_price=session_open,
                end_price=entry_bar.close,
            ),
        ),
        "opening_range_high": _format_optional(opening_range_high),
        "opening_range_low": _format_optional(opening_range_low),
        "opening_range_points": _format_optional(opening_range_points),
        "entry_position_in_opening_range": _format_optional(opening_range_position),
        "opening_range_continuation_edge_score": _format_optional(
            _direction_aware_continuation_edge_score(
                direction=str(row["direction"]),
                range_position=opening_range_position,
            ),
        ),
        "opening_range_fade_edge_score": _format_optional(
            _direction_aware_fade_edge_score(
                direction=str(row["direction"]),
                range_position=opening_range_position,
            ),
        ),
        "directional_opening_range_breakout_points": _format_optional(
            directional_opening_range_breakout,
        ),
        "lookback_directional_move_points": _format_number(lookback_directional_move),
        "lookback_efficiency_ratio": _format_optional(lookback_efficiency),
        "lookback_choppiness_score": _format_optional(lookback_choppiness),
        "session_bars_so_far": len(bars_so_far),
        "session_average_volume": _format_optional(session_average_volume),
        "session_average_trades": _format_optional(session_average_trades),
        "entry_volume_to_session_average_volume": _format_optional(
            _ratio_or_none(entry_bar.volume, session_average_volume),
        ),
        "entry_trades_to_session_average_trades": _format_optional(
            _ratio_or_none(entry_bar.trades, session_average_trades),
        ),
        "lookback_volume_to_session_average_volume": _format_optional(
            _ratio_or_none(lookback_volume, session_average_volume),
        ),
        "lookback_trades_to_session_average_trades": _format_optional(
            _ratio_or_none(lookback_trades, session_average_trades),
        ),
        "exit_reason": row["exit_reason"],
        "first_target_hit": row["first_target_hit"],
        "net_usd": row["net_usd"],
        "notes": (
            "pre-entry normalized context and session-regime state for fixed "
            "scaled-scalp outcome row"
        ),
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
        open=_to_float(row["open"], "open"),
        high=_to_float(row["high"], "high"),
        low=_to_float(row["low"], "low"),
        close=_to_float(row["close"], "close"),
        volume=volume,
        trades=_optional_float(row.get("number_of_trades"), "number_of_trades"),
        delta=delta,
        opening_range_high=_optional_float(
            row.get("opening_range_high"),
            "opening_range_high",
        ),
        opening_range_low=_optional_float(
            row.get("opening_range_low"),
            "opening_range_low",
        ),
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


def _computed_opening_range(bars: list[_ContextBar]) -> tuple[float | None, float | None]:
    opening_range_bars = [bar for bar in bars if _is_opening_range_timestamp(bar.parsed_timestamp)]
    if not opening_range_bars:
        return None, None
    return (
        max(bar.high for bar in opening_range_bars),
        min(bar.low for bar in opening_range_bars),
    )


def _is_opening_range_timestamp(timestamp: datetime) -> bool:
    minutes = timestamp.hour * 60 + timestamp.minute
    return (_RTH_OPEN_HOUR * 60 + _RTH_OPEN_MINUTE) <= minutes < 10 * 60


def _range_or_none(high: float | None, low: float | None) -> float | None:
    if high is None or low is None:
        return None
    return high - low


def _direction_aware_price_move(
    *,
    direction: str,
    start_price: float,
    end_price: float,
) -> float:
    if direction == "long":
        return end_price - start_price
    if direction == "short":
        return start_price - end_price
    raise ScaledContextDiagnosticError(f"Unsupported direction: {direction}")


def _direction_aware_continuation_edge_score(
    *,
    direction: str,
    range_position: float | None,
) -> float | None:
    if range_position is None:
        return None
    if direction == "long":
        return range_position
    if direction == "short":
        return 1.0 - range_position
    raise ScaledContextDiagnosticError(f"Unsupported direction: {direction}")


def _direction_aware_fade_edge_score(
    *,
    direction: str,
    range_position: float | None,
) -> float | None:
    if range_position is None:
        return None
    if direction == "long":
        return 1.0 - range_position
    if direction == "short":
        return range_position
    raise ScaledContextDiagnosticError(f"Unsupported direction: {direction}")


def _direction_aware_opening_range_breakout(
    *,
    direction: str,
    entry_price: float,
    opening_range_high: float | None,
    opening_range_low: float | None,
) -> float | None:
    if opening_range_high is None or opening_range_low is None:
        return None
    if direction == "long":
        return entry_price - opening_range_high
    if direction == "short":
        return opening_range_low - entry_price
    raise ScaledContextDiagnosticError(f"Unsupported direction: {direction}")


def _lookback_efficiency_ratio(bars: list[_ContextBar]) -> float | None:
    if len(bars) < 2:
        return None
    path_distance = sum(
        abs(current.close - previous.close)
        for previous, current in zip(bars, bars[1:], strict=False)
    )
    if path_distance == 0:
        return 0.0
    direct_distance = abs(bars[-1].close - bars[0].close)
    return direct_distance / path_distance


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
