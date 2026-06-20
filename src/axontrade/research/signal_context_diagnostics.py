"""Context diagnostics for logged signal quality rows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from statistics import mean
from typing import Any, Iterable


SIGNAL_CONTEXT_DIAGNOSTIC_HEADER = [
    "schema_version",
    "context_id",
    "diagnostic_id",
    "outcome_id",
    "signal_id",
    "symbol",
    "direction",
    "entry_time",
    "entry_bar_index",
    "lookback_bars",
    "lookback_bars_available",
    "minutes_after_rth_open",
    "risk_points",
    "target_distance_points",
    "original_reward_risk",
    "sweep_abs_delta",
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
    "target_distance_to_average_bar_range",
    "sweep_abs_delta_to_average_abs_delta",
    "entry_volume_to_average_volume",
    "entry_trades_to_average_trades",
    "entry_abs_delta_to_average_abs_delta",
    "exit_reason",
    "net_usd",
    "notes",
]
_TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
)


class SignalContextDiagnosticError(ValueError):
    """Raised when signal context diagnostics cannot be computed."""


@dataclass(frozen=True)
class ContextBar:
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


def run_signal_context_diagnostics(
    *,
    bar_rows: Iterable[dict[str, Any]],
    quality_diagnostic_rows: Iterable[dict[str, Any]],
    lookback_bars: int = 50,
) -> list[dict[str, Any]]:
    """Compute rolling volatility/activity context for quality diagnostic rows."""

    if lookback_bars <= 0:
        raise SignalContextDiagnosticError("lookback_bars must be positive")

    bars_by_symbol_date = _bars_by_symbol_date(bar_rows)
    return [
        _context_row(row, bars_by_symbol_date, lookback_bars=lookback_bars)
        for row in quality_diagnostic_rows
    ]


def _context_row(
    row: dict[str, Any],
    bars_by_symbol_date: dict[tuple[str, str], list[ContextBar]],
    *,
    lookback_bars: int,
) -> dict[str, Any]:
    symbol = str(row["symbol"])
    entry_time = str(row["entry_time"])
    entry_timestamp = _parse_timestamp(entry_time)
    entry_bar_index = _to_int(row["entry_bar_index"], "entry_bar_index")
    key = (symbol, entry_timestamp.date().isoformat())
    same_day_bars = bars_by_symbol_date.get(key, [])
    if not same_day_bars:
        raise SignalContextDiagnosticError(
            f"No context bars found for symbol={symbol} date={key[1]}",
        )

    previous_bars = [
        bar
        for bar in same_day_bars
        if bar.bar_index < entry_bar_index
    ][-lookback_bars:]
    entry_bar = _find_entry_bar(same_day_bars, entry_bar_index)
    if not previous_bars:
        raise SignalContextDiagnosticError(
            f"No previous context bars found for signal_id={row['signal_id']}",
        )
    if entry_bar is None:
        raise SignalContextDiagnosticError(
            f"No entry context bar found for signal_id={row['signal_id']} "
            f"entry_bar_index={entry_bar_index}",
        )

    average_bar_range = mean(bar.bar_range for bar in previous_bars)
    average_volume = _mean_optional(bar.volume for bar in previous_bars)
    average_trades = _mean_optional(bar.trades for bar in previous_bars)
    average_abs_delta = _mean_optional(bar.abs_delta for bar in previous_bars)
    risk_points = _to_float(row["risk_points"], "risk_points")
    target_distance_points = _to_float(row["target_distance_points"], "target_distance_points")
    sweep_abs_delta = _to_float(row["sweep_abs_delta"], "sweep_abs_delta")
    entry_abs_delta = entry_bar.abs_delta

    return {
        "schema_version": 1,
        "context_id": f"{row['diagnostic_id']}:context:{lookback_bars}",
        "diagnostic_id": row["diagnostic_id"],
        "outcome_id": row["outcome_id"],
        "signal_id": row["signal_id"],
        "symbol": symbol,
        "direction": row["direction"],
        "entry_time": entry_time,
        "entry_bar_index": entry_bar_index,
        "lookback_bars": lookback_bars,
        "lookback_bars_available": len(previous_bars),
        "minutes_after_rth_open": row["minutes_after_rth_open"],
        "risk_points": _format_number(risk_points),
        "target_distance_points": _format_number(target_distance_points),
        "original_reward_risk": row["original_reward_risk"],
        "sweep_abs_delta": _format_number(sweep_abs_delta),
        "lookback_range_points": _format_number(
            max(bar.high for bar in previous_bars) - min(bar.low for bar in previous_bars),
        ),
        "average_bar_range_points": _format_optional(average_bar_range),
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
        "target_distance_to_average_bar_range": _format_optional(
            _ratio_or_none(target_distance_points, average_bar_range),
        ),
        "sweep_abs_delta_to_average_abs_delta": _format_optional(
            _ratio_or_none(sweep_abs_delta, average_abs_delta),
        ),
        "entry_volume_to_average_volume": _format_optional(
            _ratio_or_none(entry_bar.volume, average_volume),
        ),
        "entry_trades_to_average_trades": _format_optional(
            _ratio_or_none(entry_bar.trades, average_trades),
        ),
        "entry_abs_delta_to_average_abs_delta": _format_optional(
            _ratio_or_none(entry_abs_delta, average_abs_delta),
        ),
        "exit_reason": row["exit_reason"],
        "net_usd": row["net_usd"],
        "notes": "rolling pre-entry volatility/activity context from orderflow bar export",
    }


def _bars_by_symbol_date(rows: Iterable[dict[str, Any]]) -> dict[tuple[str, str], list[ContextBar]]:
    grouped: dict[tuple[str, str], list[ContextBar]] = {}
    for row in rows:
        bar = _context_bar(row)
        grouped.setdefault(
            (bar.symbol, bar.parsed_timestamp.date().isoformat()),
            [],
        ).append(bar)
    for bars in grouped.values():
        bars.sort(key=lambda bar: (bar.bar_index, bar.parsed_timestamp))
    return grouped


def _context_bar(row: dict[str, Any]) -> ContextBar:
    timestamp = str(row["timestamp"])
    bid_volume = _optional_float(row.get("bid_volume"), "bid_volume")
    ask_volume = _optional_float(row.get("ask_volume"), "ask_volume")
    volume = _optional_float(row.get("volume"), "volume")
    if volume is None and bid_volume is not None and ask_volume is not None:
        volume = bid_volume + ask_volume
    delta = _optional_float(row.get("delta"), "delta")
    if delta is None and bid_volume is not None and ask_volume is not None:
        delta = ask_volume - bid_volume

    return ContextBar(
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


def _find_entry_bar(bars: list[ContextBar], entry_bar_index: int) -> ContextBar | None:
    matching_bars = [bar for bar in bars if bar.bar_index == entry_bar_index]
    if not matching_bars:
        return None
    return matching_bars[0]


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
    raise SignalContextDiagnosticError(f"Invalid timestamp: {value!r}")


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
        raise SignalContextDiagnosticError(
            f"Invalid integer field {field_name}: {value!r}",
        ) from exc


def _to_float(value: Any, field_name: str) -> float:
    try:
        return float(str(value))
    except ValueError as exc:
        raise SignalContextDiagnosticError(
            f"Invalid numeric field {field_name}: {value!r}",
        ) from exc


def _format_optional(value: float | None) -> str:
    return "" if value is None else _format_number(value)


def _format_number(value: float) -> str:
    return f"{value:.8f}".rstrip("0").rstrip(".")
