"""Entry-quality filter experiments for logged signal diagnostics."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from itertools import product
from typing import Any, Iterable


SIGNAL_QUALITY_FILTER_SWEEP_HEADER = [
    "schema_version",
    "experiment_id",
    "strategy_id",
    "direction_filter",
    "max_original_reward_risk",
    "min_minutes_after_rth_open",
    "max_minutes_after_rth_open",
    "max_sweep_abs_delta",
    "input_diagnostic_rows",
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
SIGNAL_QUALITY_FILTER_WALK_FORWARD_HEADER = [
    "schema_version",
    "split_id",
    "sample",
    "selected_on_train",
    "trade_dates",
    "experiment_id",
    "strategy_id",
    "direction_filter",
    "max_original_reward_risk",
    "min_minutes_after_rth_open",
    "max_minutes_after_rth_open",
    "max_sweep_abs_delta",
    "input_diagnostic_rows",
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
_TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
)
_ALLOWED_DIRECTION_FILTERS = ("all", "long", "short")
_LOSS_EXIT_REASONS = {"stop_hit", "ambiguous_stop_first"}


class SignalQualityFilterExperimentError(ValueError):
    """Raised when a signal quality filter experiment cannot be evaluated."""


def run_signal_quality_filter_sweep(
    diagnostic_rows: Iterable[dict[str, Any]],
    *,
    max_original_reward_risks: Iterable[float],
    min_minutes_after_rth_open_values: Iterable[float],
    max_minutes_after_rth_open_values: Iterable[float],
    max_sweep_abs_deltas: Iterable[float],
    direction_filters: Iterable[str] = ("all",),
) -> list[dict[str, Any]]:
    """Sweep simple entry-known filters over signal quality diagnostics."""

    rows = list(diagnostic_rows)
    max_reward_risks = _normalize_positive_grid(
        max_original_reward_risks,
        "max_original_reward_risks",
    )
    time_windows = _valid_time_windows(
        min_minutes_after_rth_open_values,
        max_minutes_after_rth_open_values,
    )
    max_sweeps = _normalize_positive_grid(max_sweep_abs_deltas, "max_sweep_abs_deltas")
    directions = _normalize_direction_filters(direction_filters)

    experiment_rows: list[dict[str, Any]] = []
    for max_rr, (min_minutes, max_minutes), max_sweep, direction_filter in product(
        max_reward_risks,
        time_windows,
        max_sweeps,
        directions,
    ):
        filtered_rows = _filter_rows(
            rows,
            direction_filter=direction_filter,
            max_original_reward_risk=max_rr,
            min_minutes_after_rth_open=min_minutes,
            max_minutes_after_rth_open=max_minutes,
            max_sweep_abs_delta=max_sweep,
        )
        experiment_rows.append(
            _experiment_row(
                rows,
                filtered_rows,
                direction_filter=direction_filter,
                max_original_reward_risk=max_rr,
                min_minutes_after_rth_open=min_minutes,
                max_minutes_after_rth_open=max_minutes,
                max_sweep_abs_delta=max_sweep,
            ),
        )

    return experiment_rows


def run_signal_quality_filter_walk_forward_sweep(
    diagnostic_rows: Iterable[dict[str, Any]],
    *,
    train_date_count: int,
    holdout_date_count: int,
    max_original_reward_risks: Iterable[float],
    min_minutes_after_rth_open_values: Iterable[float],
    max_minutes_after_rth_open_values: Iterable[float],
    max_sweep_abs_deltas: Iterable[float],
    direction_filters: Iterable[str] = ("all",),
    minimum_train_trades: int = 1,
) -> list[dict[str, Any]]:
    """Run rolling selection of entry-quality filters by trade date."""

    rows = list(diagnostic_rows)
    dates = _sorted_trade_dates(rows)
    if train_date_count <= 0:
        raise SignalQualityFilterExperimentError("train_date_count must be positive")
    if holdout_date_count <= 0:
        raise SignalQualityFilterExperimentError("holdout_date_count must be positive")
    if minimum_train_trades <= 0:
        raise SignalQualityFilterExperimentError("minimum_train_trades must be positive")
    if train_date_count + holdout_date_count > len(dates):
        raise SignalQualityFilterExperimentError(
            "train_date_count plus holdout_date_count must not exceed "
            "the number of candidate trade dates",
        )

    max_reward_risks = _normalize_positive_grid(
        max_original_reward_risks,
        "max_original_reward_risks",
    )
    min_minutes = _normalize_nonnegative_grid(
        min_minutes_after_rth_open_values,
        "min_minutes_after_rth_open_values",
    )
    max_minutes = _normalize_nonnegative_grid(
        max_minutes_after_rth_open_values,
        "max_minutes_after_rth_open_values",
    )
    max_sweeps = _normalize_positive_grid(max_sweep_abs_deltas, "max_sweep_abs_deltas")
    directions = _normalize_direction_filters(direction_filters)

    split_rows: list[dict[str, Any]] = []
    max_start = len(dates) - train_date_count - holdout_date_count + 1
    for window_index in range(max_start):
        train_dates = dates[window_index:window_index + train_date_count]
        holdout_dates = dates[
            window_index + train_date_count:
            window_index + train_date_count + holdout_date_count
        ]
        train_sweep = run_signal_quality_filter_sweep(
            _filter_rows_by_dates(rows, train_dates),
            max_original_reward_risks=max_reward_risks,
            min_minutes_after_rth_open_values=min_minutes,
            max_minutes_after_rth_open_values=max_minutes,
            max_sweep_abs_deltas=max_sweeps,
            direction_filters=directions,
        )
        best_train = _select_best_train_row(
            train_sweep,
            minimum_train_trades=minimum_train_trades,
        )
        holdout_sweep = run_signal_quality_filter_sweep(
            _filter_rows_by_dates(rows, holdout_dates),
            max_original_reward_risks=max_reward_risks,
            min_minutes_after_rth_open_values=min_minutes,
            max_minutes_after_rth_open_values=max_minutes,
            max_sweep_abs_deltas=max_sweeps,
            direction_filters=directions,
        )
        matching_holdout = _find_matching_selection_row(holdout_sweep, best_train)
        split_id = (
            f"quality_filter_walk_forward_window={window_index + 1}:"
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


def _filter_rows(
    rows: list[dict[str, Any]],
    *,
    direction_filter: str,
    max_original_reward_risk: float,
    min_minutes_after_rth_open: float,
    max_minutes_after_rth_open: float,
    max_sweep_abs_delta: float,
) -> list[dict[str, Any]]:
    filtered_rows: list[dict[str, Any]] = []
    for row in rows:
        direction = str(row["direction"])
        if direction_filter != "all" and direction != direction_filter:
            continue
        if _to_float(row["original_reward_risk"], "original_reward_risk") > max_original_reward_risk:
            continue
        minutes = _to_float(row["minutes_after_rth_open"], "minutes_after_rth_open")
        if minutes < min_minutes_after_rth_open or minutes > max_minutes_after_rth_open:
            continue
        if _to_float(row["sweep_abs_delta"], "sweep_abs_delta") > max_sweep_abs_delta:
            continue
        filtered_rows.append(row)
    return filtered_rows


def _experiment_row(
    all_rows: list[dict[str, Any]],
    filtered_rows: list[dict[str, Any]],
    *,
    direction_filter: str,
    max_original_reward_risk: float,
    min_minutes_after_rth_open: float,
    max_minutes_after_rth_open: float,
    max_sweep_abs_delta: float,
) -> dict[str, Any]:
    summary = _summary(filtered_rows)
    direction_counts = Counter(str(row["direction"]) for row in filtered_rows)
    strategy_id = _strategy_id(filtered_rows)
    experiment_id = (
        f"signal_quality_filter:strategy={strategy_id}:"
        f"direction={direction_filter}:"
        f"max_rr={_format_number(max_original_reward_risk)}:"
        f"minutes={_format_number(min_minutes_after_rth_open)}-"
        f"{_format_number(max_minutes_after_rth_open)}:"
        f"max_sweep_abs_delta={_format_number(max_sweep_abs_delta)}"
    )

    return {
        "schema_version": 1,
        "experiment_id": experiment_id,
        "strategy_id": strategy_id,
        "direction_filter": direction_filter,
        "max_original_reward_risk": _format_number(max_original_reward_risk),
        "min_minutes_after_rth_open": _format_number(min_minutes_after_rth_open),
        "max_minutes_after_rth_open": _format_number(max_minutes_after_rth_open),
        "max_sweep_abs_delta": _format_number(max_sweep_abs_delta),
        "input_diagnostic_rows": len(all_rows),
        "evaluated_trades": summary["total_trades"],
        "target_hits": summary["target_hits"],
        "losses": summary["losses"],
        "other_exits": summary["other_exits"],
        "win_rate": _format_number(summary["win_rate"]),
        "net_usd": _format_number(summary["net_usd"]),
        "average_net_usd": _format_number(summary["average_net_usd"]),
        "long_trades": direction_counts.get("long", 0),
        "short_trades": direction_counts.get("short", 0),
        "notes": (
            "entry-quality filter sweep over original outcome diagnostics; "
            "uses only entry-known diagnostic fields"
        ),
    }


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    target_hits = sum(row["exit_reason"] == "target_hit" for row in rows)
    losses = sum(row["exit_reason"] in _LOSS_EXIT_REASONS for row in rows)
    net_usd = sum(_to_float(row["net_usd"], "net_usd") for row in rows)
    return {
        "total_trades": total,
        "target_hits": target_hits,
        "losses": losses,
        "other_exits": total - target_hits - losses,
        "win_rate": target_hits / total if total else 0.0,
        "net_usd": net_usd,
        "average_net_usd": net_usd / total if total else 0.0,
    }


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
        raise SignalQualityFilterExperimentError(
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
    raise SignalQualityFilterExperimentError(
        "Missing matching holdout quality filter row for "
        f"direction={selected_key[0]} "
        f"max_rr={selected_key[1]} "
        f"minutes={selected_key[2]}-{selected_key[3]} "
        f"max_sweep_abs_delta={selected_key[4]}",
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
            for key in SIGNAL_QUALITY_FILTER_SWEEP_HEADER
            if key != "schema_version"
        },
    )
    return tagged


def _selection_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(row["direction_filter"]),
        str(row["max_original_reward_risk"]),
        str(row["min_minutes_after_rth_open"]),
        str(row["max_minutes_after_rth_open"]),
        str(row["max_sweep_abs_delta"]),
    )


def _strategy_id(rows: list[dict[str, Any]]) -> str:
    strategy_ids = sorted(
        {
            _extract_strategy_id(str(row.get("signal_id", "")), str(row.get("symbol", "")))
            for row in rows
        },
    )
    if not strategy_ids:
        return "none"
    if len(strategy_ids) == 1:
        return strategy_ids[0]
    return "mixed"


def _extract_strategy_id(signal_id: str, symbol: str) -> str:
    marker = f"_{symbol}_"
    if symbol and marker in signal_id:
        return signal_id.split(marker, maxsplit=1)[0]
    if "_" in signal_id:
        return signal_id.rsplit("_", maxsplit=1)[0]
    return signal_id or "unknown"


def _sorted_trade_dates(rows: list[dict[str, Any]]) -> list[str]:
    return sorted({_trade_date(row) for row in rows})


def _filter_rows_by_dates(
    rows: list[dict[str, Any]],
    dates: list[str],
) -> list[dict[str, Any]]:
    allowed_dates = set(dates)
    return [row for row in rows if _trade_date(row) in allowed_dates]


def _trade_date(row: dict[str, Any]) -> str:
    return _parse_timestamp(str(row["entry_time"])).date().isoformat()


def _parse_timestamp(value: str) -> datetime:
    timestamp_text = _normalize_timestamp_text(value.strip())
    for timestamp_format in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(timestamp_text, timestamp_format)
        except ValueError:
            continue
    raise SignalQualityFilterExperimentError(f"Invalid timestamp: {value!r}")


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


def _valid_time_windows(
    min_values: Iterable[float],
    max_values: Iterable[float],
) -> list[tuple[float, float]]:
    minimums = _normalize_nonnegative_grid(
        min_values,
        "min_minutes_after_rth_open_values",
    )
    maximums = _normalize_nonnegative_grid(
        max_values,
        "max_minutes_after_rth_open_values",
    )
    windows = [
        (minimum, maximum)
        for minimum, maximum in product(minimums, maximums)
        if minimum <= maximum
    ]
    if not windows:
        raise SignalQualityFilterExperimentError(
            "At least one min/max minute window must be valid",
        )
    return windows


def _normalize_positive_grid(values: Iterable[float], field_name: str) -> list[float]:
    grid = [float(value) for value in values]
    if not grid:
        raise SignalQualityFilterExperimentError(f"{field_name} must contain at least one value")
    if any(value <= 0 for value in grid):
        raise SignalQualityFilterExperimentError(f"{field_name} values must be positive")
    return grid


def _normalize_nonnegative_grid(values: Iterable[float], field_name: str) -> list[float]:
    grid = [float(value) for value in values]
    if not grid:
        raise SignalQualityFilterExperimentError(f"{field_name} must contain at least one value")
    if any(value < 0 for value in grid):
        raise SignalQualityFilterExperimentError(f"{field_name} values must be nonnegative")
    return grid


def _normalize_direction_filters(values: Iterable[str]) -> list[str]:
    filters = [str(value).strip().lower() for value in values if str(value).strip()]
    if not filters:
        raise SignalQualityFilterExperimentError(
            "direction_filters must contain at least one value",
        )
    invalid = [value for value in filters if value not in _ALLOWED_DIRECTION_FILTERS]
    if invalid:
        raise SignalQualityFilterExperimentError(
            "direction_filters contains unsupported values: " + ", ".join(invalid),
        )
    return filters


def _to_float(value: Any, field_name: str) -> float:
    try:
        return float(str(value))
    except ValueError as exc:
        raise SignalQualityFilterExperimentError(
            f"Invalid numeric field {field_name}: {value!r}",
        ) from exc


def _format_number(value: Any) -> str:
    return f"{float(value):.8f}".rstrip("0").rstrip(".")
