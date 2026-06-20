"""Feature diagnostics for logged signal outcomes."""

from __future__ import annotations

import re
from datetime import datetime, time
from typing import Any, Iterable


SIGNAL_QUALITY_DIAGNOSTIC_HEADER = [
    "schema_version",
    "diagnostic_id",
    "outcome_id",
    "signal_id",
    "symbol",
    "direction",
    "entry_time",
    "entry_bar_index",
    "entry_hour",
    "minutes_after_rth_open",
    "risk_points",
    "target_distance_points",
    "original_reward_risk",
    "sweep_bar_index",
    "bars_after_sweep",
    "sweep_delta",
    "sweep_abs_delta",
    "sweep_aggression_ratio",
    "confirmation_close_location",
    "max_favorable_r",
    "max_adverse_r",
    "exit_reason",
    "net_usd",
    "notes",
]
_SWEEP_BAR_INDEX_RE = re.compile(r"\bsweep_bar_index=(\d+)\b")
_SWEEP_DELTA_RE = re.compile(r"\bsweep_delta=([-+]?\d+(?:\.\d+)?)\b")
_SWEEP_RATIO_RE = re.compile(r"\bsweep_ratio=([-+]?\d+(?:\.\d+)?)\b")
_CONFIRMATION_CLOSE_LOCATION_RE = re.compile(
    r"\bconfirmation_close_location=([-+]?\d+(?:\.\d+)?)\b",
)
_RTH_OPEN = time(9, 30)
_TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
)


class SignalQualityDiagnosticError(ValueError):
    """Raised when signal quality diagnostics cannot be computed."""


def run_signal_quality_diagnostics(
    *,
    signal_rows: Iterable[dict[str, Any]],
    outcome_rows: Iterable[dict[str, Any]],
    path_diagnostic_rows: Iterable[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Join candidate signal metadata, outcomes, and optional path metrics."""

    signal_by_id = {
        str(row["signal_id"]): row
        for row in signal_rows
        if str(row.get("event_type", "")) == "candidate_signal"
    }
    path_by_outcome_id = {
        str(row["outcome_id"]): row
        for row in (path_diagnostic_rows or [])
    }

    diagnostic_rows: list[dict[str, Any]] = []
    for outcome in outcome_rows:
        signal_id = str(outcome["signal_id"])
        if signal_id not in signal_by_id:
            raise SignalQualityDiagnosticError(
                f"Missing candidate signal row for signal_id={signal_id}",
            )
        signal = signal_by_id[signal_id]
        path_row = path_by_outcome_id.get(str(outcome["outcome_id"]), {})
        diagnostic_rows.append(_diagnostic_row(signal, outcome, path_row))

    return diagnostic_rows


def _diagnostic_row(
    signal: dict[str, Any],
    outcome: dict[str, Any],
    path_row: dict[str, Any],
) -> dict[str, Any]:
    notes = str(signal.get("notes", ""))
    entry_bar_index = _to_int(outcome["entry_bar_index"], "entry_bar_index")
    sweep_bar_index = _parse_note_int(notes, _SWEEP_BAR_INDEX_RE, "sweep_bar_index")
    entry_price = _to_float(outcome["entry_price"], "entry_price")
    stop_price = _to_float(outcome["stop_price"], "stop_price")
    target_price = _to_float(outcome["target_price"], "target_price")
    direction = str(outcome["direction"])
    risk_points = _risk_points(direction, entry_price, stop_price)
    target_distance_points = _target_distance_points(direction, entry_price, target_price)
    entry_time = str(outcome["entry_time"])
    entry_timestamp = _parse_timestamp(entry_time)
    minutes_after_open = _minutes_after_rth_open(entry_timestamp)
    sweep_delta = _parse_note_float(notes, _SWEEP_DELTA_RE, "sweep_delta")
    sweep_ratio = _parse_note_float(notes, _SWEEP_RATIO_RE, "sweep_ratio")
    confirmation_close_location = _parse_note_float(
        notes,
        _CONFIRMATION_CLOSE_LOCATION_RE,
        "confirmation_close_location",
    )

    return {
        "schema_version": 1,
        "diagnostic_id": f"{outcome['outcome_id']}:quality",
        "outcome_id": outcome["outcome_id"],
        "signal_id": outcome["signal_id"],
        "symbol": outcome["symbol"],
        "direction": direction,
        "entry_time": entry_time,
        "entry_bar_index": entry_bar_index,
        "entry_hour": entry_timestamp.hour,
        "minutes_after_rth_open": minutes_after_open,
        "risk_points": _format_number(risk_points),
        "target_distance_points": _format_number(target_distance_points),
        "original_reward_risk": _format_number(
            target_distance_points / risk_points if risk_points else 0.0,
        ),
        "sweep_bar_index": sweep_bar_index,
        "bars_after_sweep": entry_bar_index - sweep_bar_index,
        "sweep_delta": _format_number(sweep_delta),
        "sweep_abs_delta": _format_number(abs(sweep_delta)),
        "sweep_aggression_ratio": _format_number(sweep_ratio),
        "confirmation_close_location": _format_number(confirmation_close_location),
        "max_favorable_r": str(path_row.get("max_favorable_r", "")),
        "max_adverse_r": str(path_row.get("max_adverse_r", "")),
        "exit_reason": outcome["exit_reason"],
        "net_usd": _format_number(_to_float(outcome["net_usd"], "net_usd")),
        "notes": "quality diagnostic from signal notes and outcome/path rows",
    }


def _parse_note_int(notes: str, pattern: re.Pattern[str], field_name: str) -> int:
    match = pattern.search(notes)
    if match is None:
        raise SignalQualityDiagnosticError(f"Missing {field_name} in signal notes: {notes!r}")
    return _to_int(match.group(1), field_name)


def _parse_note_float(notes: str, pattern: re.Pattern[str], field_name: str) -> float:
    match = pattern.search(notes)
    if match is None:
        raise SignalQualityDiagnosticError(f"Missing {field_name} in signal notes: {notes!r}")
    return _to_float(match.group(1), field_name)


def _risk_points(direction: str, entry_price: float, stop_price: float) -> float:
    if direction == "long":
        return entry_price - stop_price
    if direction == "short":
        return stop_price - entry_price
    raise SignalQualityDiagnosticError(f"Unsupported outcome direction: {direction!r}")


def _target_distance_points(direction: str, entry_price: float, target_price: float) -> float:
    if direction == "long":
        return target_price - entry_price
    if direction == "short":
        return entry_price - target_price
    raise SignalQualityDiagnosticError(f"Unsupported outcome direction: {direction!r}")


def _minutes_after_rth_open(timestamp: datetime) -> int:
    return (timestamp.hour * 60 + timestamp.minute) - (_RTH_OPEN.hour * 60 + _RTH_OPEN.minute)


def _parse_timestamp(value: str) -> datetime:
    timestamp_text = _normalize_timestamp_text(value.strip())
    for timestamp_format in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(timestamp_text, timestamp_format)
        except ValueError:
            continue
    raise SignalQualityDiagnosticError(f"Invalid timestamp: {value!r}")


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
        raise SignalQualityDiagnosticError(
            f"Invalid integer field {field_name}: {value!r}",
        ) from exc


def _to_float(value: Any, field_name: str) -> float:
    try:
        return float(str(value))
    except ValueError as exc:
        raise SignalQualityDiagnosticError(
            f"Invalid numeric field {field_name}: {value!r}",
        ) from exc


def _format_number(value: Any) -> str:
    return f"{float(value):.8f}".rstrip("0").rstrip(".")
