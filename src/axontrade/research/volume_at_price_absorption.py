"""Volume-at-price diagnostics for liquidity sweep absorption candidates."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable


VAP_ABSORPTION_DIAGNOSTIC_HEADER = [
    "schema_version",
    "diagnostic_id",
    "outcome_id",
    "signal_id",
    "symbol",
    "direction",
    "entry_bar_index",
    "sweep_bar_index",
    "sweep_extreme_price",
    "zone_low_price",
    "zone_high_price",
    "zone_levels",
    "zone_bid_volume",
    "zone_ask_volume",
    "zone_delta",
    "zone_aggression_ratio",
    "extreme_bid_volume",
    "extreme_ask_volume",
    "extreme_delta",
    "extreme_aggression_ratio",
    "level_absorption_pass",
    "exit_reason",
    "net_usd",
    "notes",
]
_SWEEP_BAR_INDEX_RE = re.compile(r"\bsweep_bar_index=(\d+)\b")


class VolumeAtPriceAbsorptionError(ValueError):
    """Raised when volume-at-price absorption diagnostics cannot be computed."""


@dataclass(frozen=True)
class VolumeAtPriceLevel:
    symbol: str
    bar_index: int
    price: float
    bid_volume: float
    ask_volume: float

    @property
    def delta(self) -> float:
        return self.ask_volume - self.bid_volume


def run_vap_absorption_diagnostics(
    *,
    outcome_rows: Iterable[dict[str, Any]],
    signal_rows: Iterable[dict[str, Any]],
    vap_rows: Iterable[dict[str, Any]],
    sweep_zone_points: float = 1.0,
    stop_buffer_points: float = 0.25,
    minimum_zone_aggression_ratio: float = 1.25,
    minimum_zone_volume: float = 0.0,
) -> list[dict[str, Any]]:
    """Annotate evaluated absorption outcomes with swept-level VAP metrics."""

    if sweep_zone_points < 0:
        raise VolumeAtPriceAbsorptionError("sweep_zone_points must be nonnegative")
    if stop_buffer_points < 0:
        raise VolumeAtPriceAbsorptionError("stop_buffer_points must be nonnegative")
    if minimum_zone_aggression_ratio < 1:
        raise VolumeAtPriceAbsorptionError("minimum_zone_aggression_ratio must be at least 1")
    if minimum_zone_volume < 0:
        raise VolumeAtPriceAbsorptionError("minimum_zone_volume must be nonnegative")

    signal_by_id = {
        str(row["signal_id"]): row
        for row in signal_rows
        if str(row.get("event_type", "")) == "candidate_signal"
    }
    vap_by_bar = _index_vap_rows(vap_rows)

    diagnostic_rows: list[dict[str, Any]] = []
    for outcome in outcome_rows:
        signal_id = str(outcome["signal_id"])
        if signal_id not in signal_by_id:
            raise VolumeAtPriceAbsorptionError(f"Missing signal row for outcome signal_id={signal_id}")

        signal = signal_by_id[signal_id]
        direction = str(outcome["direction"])
        symbol = str(outcome["symbol"])
        sweep_bar_index = _parse_sweep_bar_index(signal)
        sweep_extreme_price = _sweep_extreme_price(
            direction=direction,
            stop_price=_to_float(outcome["stop_price"], "stop_price"),
            stop_buffer_points=stop_buffer_points,
        )
        zone_low, zone_high = _sweep_zone(
            direction=direction,
            sweep_extreme_price=sweep_extreme_price,
            sweep_zone_points=sweep_zone_points,
        )
        levels = [
            level
            for level in vap_by_bar.get((symbol, sweep_bar_index), [])
            if zone_low <= level.price <= zone_high
        ]
        metrics = _level_metrics(levels, direction=direction, extreme_price=sweep_extreme_price)
        level_absorption_pass = _level_absorption_pass(
            metrics,
            direction=direction,
            minimum_zone_aggression_ratio=minimum_zone_aggression_ratio,
            minimum_zone_volume=minimum_zone_volume,
        )

        diagnostic_rows.append(
            {
                "schema_version": 1,
                "diagnostic_id": f"{signal_id}:vap_absorption",
                "outcome_id": outcome["outcome_id"],
                "signal_id": signal_id,
                "symbol": symbol,
                "direction": direction,
                "entry_bar_index": outcome["entry_bar_index"],
                "sweep_bar_index": sweep_bar_index,
                "sweep_extreme_price": _format_number(sweep_extreme_price),
                "zone_low_price": _format_number(zone_low),
                "zone_high_price": _format_number(zone_high),
                "zone_levels": metrics["zone_levels"],
                "zone_bid_volume": _format_number(metrics["zone_bid_volume"]),
                "zone_ask_volume": _format_number(metrics["zone_ask_volume"]),
                "zone_delta": _format_number(metrics["zone_delta"]),
                "zone_aggression_ratio": _format_number(metrics["zone_aggression_ratio"]),
                "extreme_bid_volume": _format_number(metrics["extreme_bid_volume"]),
                "extreme_ask_volume": _format_number(metrics["extreme_ask_volume"]),
                "extreme_delta": _format_number(metrics["extreme_delta"]),
                "extreme_aggression_ratio": _format_number(metrics["extreme_aggression_ratio"]),
                "level_absorption_pass": str(level_absorption_pass).lower(),
                "exit_reason": outcome["exit_reason"],
                "net_usd": _format_number(_to_float(outcome["net_usd"], "net_usd")),
                "notes": (
                    "sweep-zone VAP diagnostics; "
                    f"sweep_zone_points={_format_number(sweep_zone_points)}; "
                    f"minimum_zone_aggression_ratio={_format_number(minimum_zone_aggression_ratio)}; "
                    f"minimum_zone_volume={_format_number(minimum_zone_volume)}"
                ),
            },
        )

    return diagnostic_rows


def summarize_vap_absorption_diagnostics(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Summarize VAP diagnostics by level_absorption_pass bucket."""

    diagnostics = list(rows)
    summaries = []
    for bucket in ("true", "false"):
        bucket_rows = [
            row
            for row in diagnostics
            if str(row["level_absorption_pass"]) == bucket
        ]
        trades = len(bucket_rows)
        wins = sum(str(row["exit_reason"]) == "target_hit" for row in bucket_rows)
        losses = sum(str(row["exit_reason"]) in {"stop_hit", "ambiguous_stop_first"} for row in bucket_rows)
        net_usd = sum(_to_float(row["net_usd"], "net_usd") for row in bucket_rows)
        summaries.append(
            {
                "level_absorption_pass": bucket,
                "trades": trades,
                "target_hits": wins,
                "losses": losses,
                "win_rate": _format_number(wins / trades if trades else 0.0),
                "net_usd": _format_number(net_usd),
                "average_net_usd": _format_number(net_usd / trades if trades else 0.0),
            },
        )
    return summaries


def _index_vap_rows(rows: Iterable[dict[str, Any]]) -> dict[tuple[str, int], list[VolumeAtPriceLevel]]:
    indexed: dict[tuple[str, int], list[VolumeAtPriceLevel]] = defaultdict(list)
    for row in rows:
        level = VolumeAtPriceLevel(
            symbol=str(row["symbol"]),
            bar_index=_to_int(row["bar_index"], "bar_index"),
            price=_to_float(row["price"], "price"),
            bid_volume=_to_float(row["bid_volume"], "bid_volume"),
            ask_volume=_to_float(row["ask_volume"], "ask_volume"),
        )
        indexed[(level.symbol, level.bar_index)].append(level)
    return indexed


def _parse_sweep_bar_index(signal_row: dict[str, Any]) -> int:
    notes = str(signal_row.get("notes", ""))
    match = _SWEEP_BAR_INDEX_RE.search(notes)
    if match is None:
        raise VolumeAtPriceAbsorptionError(
            f"Signal row does not include sweep_bar_index in notes: {signal_row.get('signal_id')}",
        )
    return int(match.group(1))


def _sweep_extreme_price(
    *,
    direction: str,
    stop_price: float,
    stop_buffer_points: float,
) -> float:
    if direction == "short":
        return stop_price - stop_buffer_points
    if direction == "long":
        return stop_price + stop_buffer_points
    raise VolumeAtPriceAbsorptionError(f"Unsupported direction: {direction}")


def _sweep_zone(
    *,
    direction: str,
    sweep_extreme_price: float,
    sweep_zone_points: float,
) -> tuple[float, float]:
    if direction == "short":
        return sweep_extreme_price - sweep_zone_points, sweep_extreme_price
    if direction == "long":
        return sweep_extreme_price, sweep_extreme_price + sweep_zone_points
    raise VolumeAtPriceAbsorptionError(f"Unsupported direction: {direction}")


def _level_metrics(
    levels: list[VolumeAtPriceLevel],
    *,
    direction: str,
    extreme_price: float,
) -> dict[str, float | int]:
    zone_bid_volume = sum(level.bid_volume for level in levels)
    zone_ask_volume = sum(level.ask_volume for level in levels)
    extreme_levels = [
        level
        for level in levels
        if abs(level.price - extreme_price) < 0.0000001
    ]
    extreme_bid_volume = sum(level.bid_volume for level in extreme_levels)
    extreme_ask_volume = sum(level.ask_volume for level in extreme_levels)
    if direction == "short":
        zone_aggression_ratio = _safe_ratio(zone_ask_volume, zone_bid_volume)
        extreme_aggression_ratio = _safe_ratio(extreme_ask_volume, extreme_bid_volume)
    elif direction == "long":
        zone_aggression_ratio = _safe_ratio(zone_bid_volume, zone_ask_volume)
        extreme_aggression_ratio = _safe_ratio(extreme_bid_volume, extreme_ask_volume)
    else:
        raise VolumeAtPriceAbsorptionError(f"Unsupported direction: {direction}")

    return {
        "zone_levels": len(levels),
        "zone_bid_volume": zone_bid_volume,
        "zone_ask_volume": zone_ask_volume,
        "zone_delta": zone_ask_volume - zone_bid_volume,
        "zone_aggression_ratio": zone_aggression_ratio,
        "extreme_bid_volume": extreme_bid_volume,
        "extreme_ask_volume": extreme_ask_volume,
        "extreme_delta": extreme_ask_volume - extreme_bid_volume,
        "extreme_aggression_ratio": extreme_aggression_ratio,
    }


def _level_absorption_pass(
    metrics: dict[str, float | int],
    *,
    direction: str,
    minimum_zone_aggression_ratio: float,
    minimum_zone_volume: float,
) -> bool:
    if int(metrics["zone_levels"]) <= 0:
        return False
    zone_volume = float(metrics["zone_bid_volume"]) + float(metrics["zone_ask_volume"])
    if zone_volume < minimum_zone_volume:
        return False
    zone_delta = float(metrics["zone_delta"])
    zone_ratio = float(metrics["zone_aggression_ratio"])
    if direction == "short":
        return zone_delta > 0 and zone_ratio >= minimum_zone_aggression_ratio
    if direction == "long":
        return zone_delta < 0 and zone_ratio >= minimum_zone_aggression_ratio
    raise VolumeAtPriceAbsorptionError(f"Unsupported direction: {direction}")


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return float("inf") if numerator > 0 else 0.0
    return numerator / denominator


def _to_int(value: Any, field_name: str) -> int:
    try:
        return int(str(value))
    except ValueError as exc:
        raise VolumeAtPriceAbsorptionError(f"Invalid integer field {field_name}: {value!r}") from exc


def _to_float(value: Any, field_name: str) -> float:
    try:
        return float(str(value))
    except ValueError as exc:
        raise VolumeAtPriceAbsorptionError(f"Invalid numeric field {field_name}: {value!r}") from exc


def _format_number(value: Any) -> str:
    return f"{float(value):.8f}".rstrip("0").rstrip(".")
