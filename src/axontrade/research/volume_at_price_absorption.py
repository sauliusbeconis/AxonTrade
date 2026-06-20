"""Volume-at-price diagnostics for liquidity sweep absorption candidates."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from itertools import product
from typing import Any, Iterable


VAP_ABSORPTION_DIAGNOSTIC_HEADER = [
    "schema_version",
    "diagnostic_id",
    "outcome_id",
    "signal_id",
    "symbol",
    "direction",
    "entry_time",
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
VAP_ABSORPTION_THRESHOLD_SWEEP_HEADER = [
    "schema_version",
    "split_id",
    "sample",
    "selected_on_train",
    "trade_dates",
    "experiment_id",
    "strategy_id",
    "direction_filter",
    "minimum_zone_aggression_ratio",
    "minimum_zone_volume",
    "input_trades",
    "evaluated_trades",
    "target_hits",
    "losses",
    "other_exits",
    "win_rate",
    "net_usd",
    "average_net_usd",
    "long_trades",
    "short_trades",
    "notes",
]
_SWEEP_BAR_INDEX_RE = re.compile(r"\bsweep_bar_index=(\d+)\b")
_TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
)
_ALLOWED_DIRECTION_FILTERS = ("all", "long", "short")


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
                "entry_time": outcome["entry_time"],
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


def run_vap_absorption_threshold_sweep(
    diagnostic_rows: Iterable[dict[str, Any]],
    *,
    minimum_zone_aggression_ratios: Iterable[float],
    minimum_zone_volumes: Iterable[float],
    direction_filters: Iterable[str] = ("all",),
) -> list[dict[str, Any]]:
    """Sweep VAP threshold filters over existing diagnostic rows."""

    rows = list(diagnostic_rows)
    ratios = _normalize_minimum_ratios(minimum_zone_aggression_ratios)
    volumes = _normalize_nonnegative_grid(minimum_zone_volumes, "minimum_zone_volumes")
    directions = _normalize_direction_filters(direction_filters)
    return [
        _threshold_experiment_row(
            rows,
            minimum_zone_aggression_ratio=minimum_zone_aggression_ratio,
            minimum_zone_volume=minimum_zone_volume,
            direction_filter=direction_filter,
            sample="all",
            split_id="aggregate",
            selected_experiment_id="",
            trade_dates=_sorted_trade_dates(rows),
        )
        for minimum_zone_aggression_ratio, minimum_zone_volume, direction_filter in product(
            ratios,
            volumes,
            directions,
        )
    ]


def run_vap_absorption_threshold_train_holdout_sweep(
    diagnostic_rows: Iterable[dict[str, Any]],
    *,
    train_date_count: int,
    minimum_zone_aggression_ratios: Iterable[float],
    minimum_zone_volumes: Iterable[float],
    direction_filters: Iterable[str] = ("all",),
    minimum_train_trades: int = 1,
) -> list[dict[str, Any]]:
    """Run a chronological train/holdout VAP threshold sweep."""

    rows = list(diagnostic_rows)
    dates = _sorted_trade_dates(rows)
    if train_date_count <= 0 or train_date_count >= len(dates):
        raise VolumeAtPriceAbsorptionError(
            "train_date_count must be greater than zero and less than the number of trade dates",
        )
    if minimum_train_trades <= 0:
        raise VolumeAtPriceAbsorptionError("minimum_train_trades must be positive")

    train_dates = dates[:train_date_count]
    holdout_dates = dates[train_date_count:]
    train_rows = _filter_rows_by_dates(rows, train_dates)
    holdout_rows = _filter_rows_by_dates(rows, holdout_dates)
    train_sweep = run_vap_absorption_threshold_sweep(
        train_rows,
        minimum_zone_aggression_ratios=minimum_zone_aggression_ratios,
        minimum_zone_volumes=minimum_zone_volumes,
        direction_filters=direction_filters,
    )
    selected_train = _select_best_threshold_row(
        train_sweep,
        minimum_train_trades=minimum_train_trades,
    )
    selected_experiment_id = str(selected_train["experiment_id"])
    split_id = f"chronological_train_dates={len(train_dates)}_holdout_dates={len(holdout_dates)}"
    ratios = _normalize_minimum_ratios(minimum_zone_aggression_ratios)
    volumes = _normalize_nonnegative_grid(minimum_zone_volumes, "minimum_zone_volumes")
    directions = _normalize_direction_filters(direction_filters)

    return [
        *[
            _tag_threshold_split_row(
                row,
                sample="train",
                selected_experiment_id=selected_experiment_id,
                split_id=split_id,
                trade_dates=train_dates,
            )
            for row in train_sweep
        ],
        *[
            _threshold_experiment_row(
                holdout_rows,
                minimum_zone_aggression_ratio=minimum_zone_aggression_ratio,
                minimum_zone_volume=minimum_zone_volume,
                direction_filter=direction_filter,
                sample="holdout",
                split_id=split_id,
                selected_experiment_id=selected_experiment_id,
                trade_dates=holdout_dates,
            )
            for minimum_zone_aggression_ratio, minimum_zone_volume, direction_filter in product(
                ratios,
                volumes,
                directions,
            )
        ],
    ]


def run_vap_absorption_threshold_walk_forward_sweep(
    diagnostic_rows: Iterable[dict[str, Any]],
    *,
    train_date_count: int,
    holdout_date_count: int,
    minimum_zone_aggression_ratios: Iterable[float],
    minimum_zone_volumes: Iterable[float],
    direction_filters: Iterable[str] = ("all",),
    minimum_train_trades: int = 1,
) -> list[dict[str, Any]]:
    """Run rolling chronological VAP threshold windows by trade date."""

    rows = list(diagnostic_rows)
    dates = _sorted_trade_dates(rows)
    if train_date_count <= 0:
        raise VolumeAtPriceAbsorptionError("train_date_count must be positive")
    if holdout_date_count <= 0:
        raise VolumeAtPriceAbsorptionError("holdout_date_count must be positive")
    if minimum_train_trades <= 0:
        raise VolumeAtPriceAbsorptionError("minimum_train_trades must be positive")
    if train_date_count + holdout_date_count > len(dates):
        raise VolumeAtPriceAbsorptionError(
            "train_date_count plus holdout_date_count must not exceed the number of trade dates",
        )

    sweep_kwargs = {
        "minimum_zone_aggression_ratios": minimum_zone_aggression_ratios,
        "minimum_zone_volumes": minimum_zone_volumes,
        "direction_filters": direction_filters,
    }

    split_rows: list[dict[str, Any]] = []
    max_start = len(dates) - train_date_count - holdout_date_count + 1
    for window_index in range(max_start):
        train_dates = dates[window_index:window_index + train_date_count]
        holdout_dates = dates[
            window_index + train_date_count:
            window_index + train_date_count + holdout_date_count
        ]
        train_rows = _filter_rows_by_dates(rows, train_dates)
        holdout_rows = _filter_rows_by_dates(rows, holdout_dates)

        train_sweep = run_vap_absorption_threshold_sweep(train_rows, **sweep_kwargs)
        holdout_sweep = run_vap_absorption_threshold_sweep(holdout_rows, **sweep_kwargs)
        best_train = _select_best_threshold_row(
            train_sweep,
            minimum_train_trades=minimum_train_trades,
        )
        matching_holdout = _find_threshold_experiment_row(
            holdout_sweep,
            str(best_train["experiment_id"]),
        )
        split_id = (
            f"walk_forward_window={window_index + 1}:"
            f"train_dates={len(train_dates)}:"
            f"holdout_dates={len(holdout_dates)}"
        )

        split_rows.append(
            _tag_threshold_split_row(
                best_train,
                sample="train",
                selected_experiment_id=str(best_train["experiment_id"]),
                split_id=split_id,
                trade_dates=train_dates,
            ),
        )
        split_rows.append(
            _tag_threshold_split_row(
                matching_holdout,
                sample="holdout",
                selected_experiment_id=str(best_train["experiment_id"]),
                split_id=split_id,
                trade_dates=holdout_dates,
            ),
        )

    return split_rows


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


def _threshold_experiment_row(
    rows: list[dict[str, Any]],
    *,
    minimum_zone_aggression_ratio: float,
    minimum_zone_volume: float,
    direction_filter: str,
    sample: str,
    split_id: str,
    selected_experiment_id: str,
    trade_dates: list[str],
) -> dict[str, Any]:
    filtered_rows = _filter_threshold_rows(
        rows,
        minimum_zone_aggression_ratio=minimum_zone_aggression_ratio,
        minimum_zone_volume=minimum_zone_volume,
        direction_filter=direction_filter,
    )
    trades = len(filtered_rows)
    wins = sum(str(row["exit_reason"]) == "target_hit" for row in filtered_rows)
    losses = sum(
        str(row["exit_reason"]) in {"stop_hit", "ambiguous_stop_first"}
        for row in filtered_rows
    )
    net_usd = sum(_to_float(row["net_usd"], "net_usd") for row in filtered_rows)
    experiment_id = (
        "liquidity_sweep_vap_absorption_threshold:"
        f"direction={direction_filter}:"
        f"min_zone_ratio={_format_number(minimum_zone_aggression_ratio)}:"
        f"min_zone_volume={_format_number(minimum_zone_volume)}"
    )

    return {
        "schema_version": 1,
        "split_id": split_id,
        "sample": sample,
        "selected_on_train": str(experiment_id == selected_experiment_id).lower(),
        "trade_dates": ";".join(trade_dates),
        "experiment_id": experiment_id,
        "strategy_id": "liquidity_sweep_vap_absorption_reversal",
        "direction_filter": direction_filter,
        "minimum_zone_aggression_ratio": _format_number(minimum_zone_aggression_ratio),
        "minimum_zone_volume": _format_number(minimum_zone_volume),
        "input_trades": len(rows),
        "evaluated_trades": trades,
        "target_hits": wins,
        "losses": losses,
        "other_exits": trades - wins - losses,
        "win_rate": _format_number(wins / trades if trades else 0.0),
        "net_usd": _format_number(net_usd),
        "average_net_usd": _format_number(net_usd / trades if trades else 0.0),
        "long_trades": sum(str(row["direction"]) == "long" for row in filtered_rows),
        "short_trades": sum(str(row["direction"]) == "short" for row in filtered_rows),
        "notes": "post-diagnostic VAP threshold sweep",
    }


def _tag_threshold_split_row(
    row: dict[str, Any],
    *,
    sample: str,
    selected_experiment_id: str,
    split_id: str,
    trade_dates: list[str],
) -> dict[str, Any]:
    tagged = dict(row)
    tagged["split_id"] = split_id
    tagged["sample"] = sample
    tagged["selected_on_train"] = str(row["experiment_id"] == selected_experiment_id).lower()
    tagged["trade_dates"] = ";".join(trade_dates)
    return tagged


def _filter_threshold_rows(
    rows: list[dict[str, Any]],
    *,
    minimum_zone_aggression_ratio: float,
    minimum_zone_volume: float,
    direction_filter: str,
) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if (direction_filter == "all" or str(row["direction"]) == direction_filter)
        and _diagnostic_threshold_pass(
            row,
            minimum_zone_aggression_ratio=minimum_zone_aggression_ratio,
            minimum_zone_volume=minimum_zone_volume,
        )
    ]


def _diagnostic_threshold_pass(
    row: dict[str, Any],
    *,
    minimum_zone_aggression_ratio: float,
    minimum_zone_volume: float,
) -> bool:
    metrics = {
        "zone_levels": _to_int(row["zone_levels"], "zone_levels"),
        "zone_bid_volume": _to_float(row["zone_bid_volume"], "zone_bid_volume"),
        "zone_ask_volume": _to_float(row["zone_ask_volume"], "zone_ask_volume"),
        "zone_delta": _to_float(row["zone_delta"], "zone_delta"),
        "zone_aggression_ratio": _to_float(row["zone_aggression_ratio"], "zone_aggression_ratio"),
    }
    return _level_absorption_pass(
        metrics,
        direction=str(row["direction"]),
        minimum_zone_aggression_ratio=minimum_zone_aggression_ratio,
        minimum_zone_volume=minimum_zone_volume,
    )


def _select_best_threshold_row(
    rows: list[dict[str, Any]],
    *,
    minimum_train_trades: int,
) -> dict[str, Any]:
    eligible_rows = [
        row
        for row in rows
        if int(row["evaluated_trades"]) >= minimum_train_trades
    ]
    if not eligible_rows:
        raise VolumeAtPriceAbsorptionError(
            f"No train experiments met minimum_train_trades={minimum_train_trades}",
        )
    return max(eligible_rows, key=lambda row: float(row["net_usd"]))


def _find_threshold_experiment_row(rows: list[dict[str, Any]], experiment_id: str) -> dict[str, Any]:
    for row in rows:
        if str(row["experiment_id"]) == experiment_id:
            return row
    raise VolumeAtPriceAbsorptionError(f"Missing matching holdout experiment row: {experiment_id}")


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


def _sorted_trade_dates(rows: list[dict[str, Any]]) -> list[str]:
    return sorted({_parse_trade_date(row["entry_time"]) for row in rows})


def _filter_rows_by_dates(rows: list[dict[str, Any]], dates: list[str]) -> list[dict[str, Any]]:
    allowed_dates = set(dates)
    return [
        row
        for row in rows
        if _parse_trade_date(row["entry_time"]) in allowed_dates
    ]


def _parse_trade_date(value: Any) -> str:
    timestamp_text = _normalize_timestamp_text(str(value).strip())
    for timestamp_format in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(timestamp_text, timestamp_format).date().isoformat()
        except ValueError:
            continue
    raise VolumeAtPriceAbsorptionError(f"Invalid timestamp: {value!r}")


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


def _normalize_minimum_ratios(values: Iterable[float]) -> list[float]:
    grid = _normalize_nonnegative_grid(values, "minimum_zone_aggression_ratios")
    if any(value < 1 for value in grid):
        raise VolumeAtPriceAbsorptionError("minimum_zone_aggression_ratios values must be at least 1")
    return grid


def _normalize_nonnegative_grid(values: Iterable[float], field_name: str) -> list[float]:
    grid = [float(value) for value in values]
    if not grid:
        raise VolumeAtPriceAbsorptionError(f"{field_name} must contain at least one value")
    if any(value < 0 for value in grid):
        raise VolumeAtPriceAbsorptionError(f"{field_name} values must be nonnegative")
    return grid


def _normalize_direction_filters(values: Iterable[str]) -> list[str]:
    filters = [str(value).strip().lower() for value in values if str(value).strip()]
    if not filters:
        raise VolumeAtPriceAbsorptionError("direction_filters must contain at least one value")
    invalid = [value for value in filters if value not in _ALLOWED_DIRECTION_FILTERS]
    if invalid:
        raise VolumeAtPriceAbsorptionError(
            "direction_filters contains unsupported values: " + ", ".join(invalid),
        )
    return filters
