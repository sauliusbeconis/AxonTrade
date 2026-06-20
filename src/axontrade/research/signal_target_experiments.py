"""Target-placement experiments for logged signal rows."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from itertools import product
from typing import Any, Iterable

from axontrade.research.trade_outcomes import (
    evaluate_trade_outcomes,
    summarize_trade_outcomes,
)


SIGNAL_TARGET_R_SWEEP_HEADER = [
    "schema_version",
    "experiment_id",
    "strategy_id",
    "direction_filter",
    "target_r_multiple",
    "input_signal_rows",
    "input_candidates",
    "evaluated_trades",
    "target_hits",
    "losses",
    "other_exits",
    "win_rate",
    "gross_usd",
    "net_usd",
    "average_net_usd",
    "long_trades",
    "short_trades",
    "notes",
]
SIGNAL_TARGET_R_WALK_FORWARD_SWEEP_HEADER = [
    "schema_version",
    "split_id",
    "sample",
    "selected_on_train",
    "trade_dates",
    "experiment_id",
    "strategy_id",
    "direction_filter",
    "target_r_multiple",
    "input_signal_rows",
    "input_candidates",
    "evaluated_trades",
    "target_hits",
    "losses",
    "other_exits",
    "win_rate",
    "gross_usd",
    "net_usd",
    "average_net_usd",
    "long_trades",
    "short_trades",
    "notes",
]
_TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
)
_ALLOWED_DIRECTION_FILTERS = ("all", "long", "short")


class SignalTargetExperimentError(ValueError):
    """Raised when a signal target experiment cannot be evaluated."""


def run_signal_target_r_sweep(
    bars: Iterable[dict[str, Any]],
    signal_rows: Iterable[dict[str, Any]],
    *,
    target_r_multiples: Iterable[float],
    direction_filters: Iterable[str] = ("all",),
    instrument_root: str | None = None,
    slippage_ticks_per_side: int | None = None,
    entry_match_mode: str = "auto",
) -> list[dict[str, Any]]:
    """Sweep replacement target prices over logged candidate signal rows."""

    normalized_bars = list(bars)
    rows = list(signal_rows)
    targets = _normalize_positive_grid(target_r_multiples, "target_r_multiples")
    directions = _normalize_direction_filters(direction_filters)

    experiment_rows: list[dict[str, Any]] = []
    for target_r, direction_filter in product(targets, directions):
        adjusted_signals = _signals_with_target_r(
            rows,
            target_r=target_r,
            direction_filter=direction_filter,
        )
        outcome_rows = evaluate_trade_outcomes(
            normalized_bars,
            adjusted_signals,
            instrument_root=instrument_root,
            slippage_ticks_per_side=slippage_ticks_per_side,
            entry_match_mode=entry_match_mode,
        )
        experiment_rows.append(
            _experiment_row(
                rows,
                adjusted_signals,
                outcome_rows,
                target_r=target_r,
                direction_filter=direction_filter,
            ),
        )

    return experiment_rows


def run_signal_target_r_walk_forward_sweep(
    bars: Iterable[dict[str, Any]],
    signal_rows: Iterable[dict[str, Any]],
    *,
    train_date_count: int,
    holdout_date_count: int,
    target_r_multiples: Iterable[float],
    direction_filters: Iterable[str] = ("all",),
    minimum_train_trades: int = 1,
    instrument_root: str | None = None,
    slippage_ticks_per_side: int | None = None,
    entry_match_mode: str = "auto",
) -> list[dict[str, Any]]:
    """Run rolling target R selection by candidate-signal trade date."""

    normalized_bars = list(bars)
    rows = list(signal_rows)
    dates = _sorted_candidate_dates(rows)
    if train_date_count <= 0:
        raise SignalTargetExperimentError("train_date_count must be positive")
    if holdout_date_count <= 0:
        raise SignalTargetExperimentError("holdout_date_count must be positive")
    if minimum_train_trades <= 0:
        raise SignalTargetExperimentError("minimum_train_trades must be positive")
    if train_date_count + holdout_date_count > len(dates):
        raise SignalTargetExperimentError(
            "train_date_count plus holdout_date_count must not exceed "
            "the number of candidate trade dates",
        )

    targets = _normalize_positive_grid(target_r_multiples, "target_r_multiples")
    directions = _normalize_direction_filters(direction_filters)
    split_rows: list[dict[str, Any]] = []
    max_start = len(dates) - train_date_count - holdout_date_count + 1
    for window_index in range(max_start):
        train_dates = dates[window_index:window_index + train_date_count]
        holdout_dates = dates[
            window_index + train_date_count:
            window_index + train_date_count + holdout_date_count
        ]
        train_sweep = run_signal_target_r_sweep(
            _filter_bars_by_dates(normalized_bars, train_dates),
            _filter_signal_rows_by_dates(rows, train_dates),
            target_r_multiples=targets,
            direction_filters=directions,
            instrument_root=instrument_root,
            slippage_ticks_per_side=slippage_ticks_per_side,
            entry_match_mode=entry_match_mode,
        )
        best_train = _select_best_train_row(
            train_sweep,
            minimum_train_trades=minimum_train_trades,
        )
        holdout_sweep = run_signal_target_r_sweep(
            _filter_bars_by_dates(normalized_bars, holdout_dates),
            _filter_signal_rows_by_dates(rows, holdout_dates),
            target_r_multiples=targets,
            direction_filters=directions,
            instrument_root=instrument_root,
            slippage_ticks_per_side=slippage_ticks_per_side,
            entry_match_mode=entry_match_mode,
        )
        matching_holdout = _find_matching_selection_row(holdout_sweep, best_train)
        split_id = (
            f"signal_target_walk_forward_window={window_index + 1}:"
            f"train_dates={len(train_dates)}:"
            f"holdout_dates={len(holdout_dates)}"
        )
        split_rows.append(
            _tag_split_row(
                best_train,
                sample="train",
                selected_row=best_train,
                split_id=split_id,
                trade_dates=train_dates,
            ),
        )
        split_rows.append(
            _tag_split_row(
                matching_holdout,
                sample="holdout",
                selected_row=best_train,
                split_id=split_id,
                trade_dates=holdout_dates,
            ),
        )

    return split_rows


def _signals_with_target_r(
    signal_rows: list[dict[str, Any]],
    *,
    target_r: float,
    direction_filter: str,
) -> list[dict[str, Any]]:
    adjusted_rows: list[dict[str, Any]] = []
    for row in signal_rows:
        if str(row.get("event_type", "")) != "candidate_signal":
            continue
        direction = str(row["direction"])
        if direction_filter != "all" and direction != direction_filter:
            continue
        adjusted_rows.append(_candidate_with_target_r(row, target_r=target_r))
    return adjusted_rows


def _select_best_train_row(
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
        raise SignalTargetExperimentError(
            f"No train experiments met minimum_train_trades={minimum_train_trades}",
        )
    return max(eligible_rows, key=lambda row: float(row["net_usd"]))


def _find_matching_selection_row(
    rows: list[dict[str, Any]],
    selected_row: dict[str, Any],
) -> dict[str, Any]:
    selected_key = _selection_key(selected_row)
    for row in rows:
        if _selection_key(row) == selected_key:
            return row
    raise SignalTargetExperimentError(
        "Missing matching holdout target R row for "
        f"direction={selected_key[0]} target_r={selected_key[1]}",
    )


def _tag_split_row(
    row: dict[str, Any],
    *,
    sample: str,
    selected_row: dict[str, Any],
    split_id: str,
    trade_dates: list[str],
) -> dict[str, Any]:
    tagged = {
        "schema_version": 1,
        "split_id": split_id,
        "sample": sample,
        "selected_on_train": str(_selection_key(row) == _selection_key(selected_row)).lower(),
        "trade_dates": ";".join(trade_dates),
    }
    tagged.update(
        {
            key: row[key]
            for key in SIGNAL_TARGET_R_SWEEP_HEADER
            if key != "schema_version"
        },
    )
    return tagged


def _selection_key(row: dict[str, Any]) -> tuple[str, str]:
    return str(row["direction_filter"]), str(row["target_r_multiple"])


def _candidate_with_target_r(row: dict[str, Any], *, target_r: float) -> dict[str, Any]:
    direction = str(row["direction"])
    entry_price = _to_float(row["signal_price"], "signal_price")
    stop_price = _to_float(row["stop_price"], "stop_price")
    if direction == "long":
        risk_points = entry_price - stop_price
        target_price = entry_price + (risk_points * target_r)
    elif direction == "short":
        risk_points = stop_price - entry_price
        target_price = entry_price - (risk_points * target_r)
    else:
        raise SignalTargetExperimentError(f"Unsupported candidate direction: {direction!r}")

    if risk_points <= 0:
        raise SignalTargetExperimentError(
            f"Candidate has nonpositive risk distance: {row.get('signal_id')}",
        )

    adjusted = dict(row)
    adjusted["target_price"] = _format_number(target_price)
    return adjusted


def _experiment_row(
    all_signal_rows: list[dict[str, Any]],
    adjusted_signals: list[dict[str, Any]],
    outcome_rows: list[dict[str, Any]],
    *,
    target_r: float,
    direction_filter: str,
) -> dict[str, Any]:
    summary = summarize_trade_outcomes(outcome_rows)
    direction_counts = Counter(str(row["direction"]) for row in outcome_rows)
    strategy_id = _strategy_id(adjusted_signals)
    experiment_id = (
        f"signal_target_r:strategy={strategy_id}:"
        f"direction={direction_filter}:"
        f"target_r={_format_number(target_r)}"
    )

    return {
        "schema_version": 1,
        "experiment_id": experiment_id,
        "strategy_id": strategy_id,
        "direction_filter": direction_filter,
        "target_r_multiple": _format_number(target_r),
        "input_signal_rows": len(all_signal_rows),
        "input_candidates": len(adjusted_signals),
        "evaluated_trades": summary["total_trades"],
        "target_hits": summary["wins"],
        "losses": summary["losses"],
        "other_exits": summary["other_exits"],
        "win_rate": _format_number(summary["win_rate"]),
        "gross_usd": _format_number(summary["gross_usd"]),
        "net_usd": _format_number(summary["net_usd"]),
        "average_net_usd": _format_number(summary["average_net_usd"]),
        "long_trades": direction_counts.get("long", 0),
        "short_trades": direction_counts.get("short", 0),
        "notes": "post-signal target R-multiple sweep using logged entry and stop",
    }


def _strategy_id(signal_rows: list[dict[str, Any]]) -> str:
    strategy_ids = sorted(
        {
            str(row.get("strategy_id", "unknown") or "unknown")
            for row in signal_rows
        },
    )
    if not strategy_ids:
        return "none"
    if len(strategy_ids) == 1:
        return strategy_ids[0]
    return "mixed"


def _sorted_candidate_dates(signal_rows: list[dict[str, Any]]) -> list[str]:
    return sorted(
        {
            _parse_trade_date(str(row.get("bar_start_time") or row.get("generated_at") or ""))
            for row in signal_rows
            if str(row.get("event_type", "")) == "candidate_signal"
        },
    )


def _filter_signal_rows_by_dates(
    signal_rows: list[dict[str, Any]],
    dates: list[str],
) -> list[dict[str, Any]]:
    allowed_dates = set(dates)
    return [
        row
        for row in signal_rows
        if _parse_trade_date(str(row.get("bar_start_time") or row.get("generated_at") or ""))
        in allowed_dates
    ]


def _filter_bars_by_dates(
    bars: list[dict[str, Any]],
    dates: list[str],
) -> list[dict[str, Any]]:
    allowed_dates = set(dates)
    return [
        row
        for row in bars
        if _parse_trade_date(str(row["timestamp"])) in allowed_dates
    ]


def _parse_trade_date(value: str) -> str:
    timestamp_text = _normalize_timestamp_text(value.strip())
    for timestamp_format in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(timestamp_text, timestamp_format).date().isoformat()
        except ValueError:
            continue
    raise SignalTargetExperimentError(f"Invalid timestamp: {value!r}")


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


def _normalize_positive_grid(values: Iterable[float], field_name: str) -> list[float]:
    grid = [float(value) for value in values]
    if not grid:
        raise SignalTargetExperimentError(f"{field_name} must contain at least one value")
    if any(value <= 0 for value in grid):
        raise SignalTargetExperimentError(f"{field_name} values must be positive")
    return grid


def _normalize_direction_filters(values: Iterable[str]) -> list[str]:
    filters = [str(value).strip().lower() for value in values if str(value).strip()]
    if not filters:
        raise SignalTargetExperimentError("direction_filters must contain at least one value")
    invalid = [value for value in filters if value not in _ALLOWED_DIRECTION_FILTERS]
    if invalid:
        raise SignalTargetExperimentError(
            "direction_filters contains unsupported values: " + ", ".join(invalid),
        )
    return filters


def _to_float(value: Any, field_name: str) -> float:
    try:
        return float(str(value))
    except ValueError as exc:
        raise SignalTargetExperimentError(
            f"Invalid numeric field {field_name}: {value!r}",
        ) from exc


def _format_number(value: Any) -> str:
    return f"{float(value):.8f}".rstrip("0").rstrip(".")
