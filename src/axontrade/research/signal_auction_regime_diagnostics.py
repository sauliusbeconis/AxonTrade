"""Auction-regime diagnostics for logged signal quality rows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable


SIGNAL_AUCTION_REGIME_DIAGNOSTIC_HEADER = [
    "schema_version",
    "regime_id",
    "diagnostic_id",
    "outcome_id",
    "signal_id",
    "symbol",
    "direction",
    "entry_time",
    "entry_bar_index",
    "minutes_after_rth_open",
    "risk_points",
    "target_distance_points",
    "original_reward_risk",
    "sweep_abs_delta",
    "session_open_price",
    "entry_close_price",
    "entry_vwap",
    "session_high_so_far",
    "session_low_so_far",
    "session_range_points",
    "entry_position_in_session_range",
    "fade_edge_score",
    "direction_aware_vwap_stretch_points",
    "direction_aware_open_stretch_points",
    "opening_range_high",
    "opening_range_low",
    "opening_range_points",
    "opening_range_edge_score",
    "direction_aware_outside_opening_range_points",
    "exit_reason",
    "net_usd",
    "notes",
]
_TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
)


class SignalAuctionRegimeDiagnosticError(ValueError):
    """Raised when auction-regime diagnostics cannot be computed."""


@dataclass(frozen=True)
class AuctionRegimeBar:
    timestamp: str
    parsed_timestamp: datetime
    symbol: str
    bar_index: int
    open: float
    high: float
    low: float
    close: float
    vwap: float
    opening_range_high: float
    opening_range_low: float


def run_signal_auction_regime_diagnostics(
    *,
    bar_rows: Iterable[dict[str, Any]],
    quality_diagnostic_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compute pre-entry auction-state diagnostics for quality rows."""

    bars_by_symbol_date = _bars_by_symbol_date(bar_rows)
    return [
        _regime_row(row, bars_by_symbol_date)
        for row in quality_diagnostic_rows
    ]


def _regime_row(
    row: dict[str, Any],
    bars_by_symbol_date: dict[tuple[str, str], list[AuctionRegimeBar]],
) -> dict[str, Any]:
    symbol = str(row["symbol"])
    direction = str(row["direction"])
    entry_time = str(row["entry_time"])
    entry_timestamp = _parse_timestamp(entry_time)
    entry_bar_index = _to_int(row["entry_bar_index"], "entry_bar_index")
    key = (symbol, entry_timestamp.date().isoformat())
    same_day_bars = bars_by_symbol_date.get(key, [])
    if not same_day_bars:
        raise SignalAuctionRegimeDiagnosticError(
            f"No auction-regime bars found for symbol={symbol} date={key[1]}",
        )

    entry_bar = _find_entry_bar(same_day_bars, entry_bar_index)
    if entry_bar is None:
        raise SignalAuctionRegimeDiagnosticError(
            f"No entry auction-regime bar found for signal_id={row['signal_id']} "
            f"entry_bar_index={entry_bar_index}",
        )
    bars_so_far = [
        bar
        for bar in same_day_bars
        if bar.bar_index <= entry_bar_index
    ]
    if not bars_so_far:
        raise SignalAuctionRegimeDiagnosticError(
            f"No pre-entry auction-regime bars found for signal_id={row['signal_id']}",
        )

    session_open = same_day_bars[0].open
    session_high = max(bar.high for bar in bars_so_far)
    session_low = min(bar.low for bar in bars_so_far)
    session_range = session_high - session_low
    entry_position = _ratio_or_zero(entry_bar.close - session_low, session_range)
    fade_edge_score = _direction_aware_edge_score(
        direction=direction,
        range_position=entry_position,
    )
    opening_range = entry_bar.opening_range_high - entry_bar.opening_range_low
    opening_range_position = _ratio_or_zero(
        entry_bar.close - entry_bar.opening_range_low,
        opening_range,
    )

    return {
        "schema_version": 1,
        "regime_id": f"{row['diagnostic_id']}:auction_regime",
        "diagnostic_id": row["diagnostic_id"],
        "outcome_id": row["outcome_id"],
        "signal_id": row["signal_id"],
        "symbol": symbol,
        "direction": direction,
        "entry_time": entry_time,
        "entry_bar_index": entry_bar_index,
        "minutes_after_rth_open": row["minutes_after_rth_open"],
        "risk_points": row["risk_points"],
        "target_distance_points": row["target_distance_points"],
        "original_reward_risk": row["original_reward_risk"],
        "sweep_abs_delta": row["sweep_abs_delta"],
        "session_open_price": _format_number(session_open),
        "entry_close_price": _format_number(entry_bar.close),
        "entry_vwap": _format_number(entry_bar.vwap),
        "session_high_so_far": _format_number(session_high),
        "session_low_so_far": _format_number(session_low),
        "session_range_points": _format_number(session_range),
        "entry_position_in_session_range": _format_number(entry_position),
        "fade_edge_score": _format_number(fade_edge_score),
        "direction_aware_vwap_stretch_points": _format_number(
            _direction_aware_stretch(
                direction=direction,
                reference_price=entry_bar.vwap,
                entry_price=entry_bar.close,
            ),
        ),
        "direction_aware_open_stretch_points": _format_number(
            _direction_aware_stretch(
                direction=direction,
                reference_price=session_open,
                entry_price=entry_bar.close,
            ),
        ),
        "opening_range_high": _format_number(entry_bar.opening_range_high),
        "opening_range_low": _format_number(entry_bar.opening_range_low),
        "opening_range_points": _format_number(opening_range),
        "opening_range_edge_score": _format_number(
            _direction_aware_edge_score(
                direction=direction,
                range_position=opening_range_position,
            ),
        ),
        "direction_aware_outside_opening_range_points": _format_number(
            _direction_aware_outside_opening_range(
                direction=direction,
                entry_price=entry_bar.close,
                opening_range_high=entry_bar.opening_range_high,
                opening_range_low=entry_bar.opening_range_low,
            ),
        ),
        "exit_reason": row["exit_reason"],
        "net_usd": row["net_usd"],
        "notes": "pre-entry auction regime diagnostic from orderflow bar export",
    }


def _direction_aware_edge_score(*, direction: str, range_position: float) -> float:
    if direction == "long":
        return 1.0 - range_position
    if direction == "short":
        return range_position
    raise SignalAuctionRegimeDiagnosticError(f"Unsupported direction: {direction}")


def _direction_aware_stretch(
    *,
    direction: str,
    reference_price: float,
    entry_price: float,
) -> float:
    if direction == "long":
        return reference_price - entry_price
    if direction == "short":
        return entry_price - reference_price
    raise SignalAuctionRegimeDiagnosticError(f"Unsupported direction: {direction}")


def _direction_aware_outside_opening_range(
    *,
    direction: str,
    entry_price: float,
    opening_range_high: float,
    opening_range_low: float,
) -> float:
    if direction == "long":
        return max(0.0, opening_range_low - entry_price)
    if direction == "short":
        return max(0.0, entry_price - opening_range_high)
    raise SignalAuctionRegimeDiagnosticError(f"Unsupported direction: {direction}")


def _bars_by_symbol_date(rows: Iterable[dict[str, Any]]) -> dict[tuple[str, str], list[AuctionRegimeBar]]:
    grouped: dict[tuple[str, str], list[AuctionRegimeBar]] = {}
    for row in rows:
        bar = _auction_regime_bar(row)
        grouped.setdefault(
            (bar.symbol, bar.parsed_timestamp.date().isoformat()),
            [],
        ).append(bar)
    for bars in grouped.values():
        bars.sort(key=lambda bar: (bar.bar_index, bar.parsed_timestamp))
    return grouped


def _auction_regime_bar(row: dict[str, Any]) -> AuctionRegimeBar:
    timestamp = str(row["timestamp"])
    return AuctionRegimeBar(
        timestamp=timestamp,
        parsed_timestamp=_parse_timestamp(timestamp),
        symbol=str(row["symbol"]),
        bar_index=_to_int(row["bar_index"], "bar_index"),
        open=_to_float(row["open"], "open"),
        high=_to_float(row["high"], "high"),
        low=_to_float(row["low"], "low"),
        close=_to_float(row["close"], "close"),
        vwap=_to_float(row["vwap"], "vwap"),
        opening_range_high=_to_float(row["opening_range_high"], "opening_range_high"),
        opening_range_low=_to_float(row["opening_range_low"], "opening_range_low"),
    )


def _find_entry_bar(
    bars: list[AuctionRegimeBar],
    entry_bar_index: int,
) -> AuctionRegimeBar | None:
    matching_bars = [bar for bar in bars if bar.bar_index == entry_bar_index]
    if not matching_bars:
        return None
    return matching_bars[0]


def _ratio_or_zero(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _parse_timestamp(value: str) -> datetime:
    timestamp_text = _normalize_timestamp_text(value.strip())
    for timestamp_format in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(timestamp_text, timestamp_format)
        except ValueError:
            continue
    raise SignalAuctionRegimeDiagnosticError(f"Invalid timestamp: {value!r}")


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
        return int(str(value))
    except ValueError as exc:
        raise SignalAuctionRegimeDiagnosticError(
            f"Invalid integer field {field_name}: {value!r}",
        ) from exc


def _to_float(value: Any, field_name: str) -> float:
    try:
        return float(str(value))
    except ValueError as exc:
        raise SignalAuctionRegimeDiagnosticError(
            f"Invalid numeric field {field_name}: {value!r}",
        ) from exc


def _format_number(value: float) -> str:
    return f"{value:.8f}".rstrip("0").rstrip(".")
