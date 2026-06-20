"""Post-signal experiments for liquidity sweep absorption outcomes."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any, Iterable

from axontrade.research.trade_outcomes import summarize_trade_outcomes


ABSORPTION_REWARD_RISK_SWEEP_HEADER = [
    "schema_version",
    "split_id",
    "sample",
    "selected_on_train",
    "trade_dates",
    "experiment_id",
    "strategy_id",
    "direction_filter",
    "minimum_reward_risk",
    "input_trades",
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


class AbsorptionExperimentError(ValueError):
    """Raised when an absorption experiment definition is invalid."""


def run_absorption_reward_risk_sweep(
    outcome_rows: Iterable[dict[str, Any]],
    *,
    minimum_reward_risks: Iterable[float],
    direction_filters: Iterable[str] = ("all",),
) -> list[dict[str, Any]]:
    """Sweep minimum reward/risk filters over already evaluated outcomes."""

    rows = list(outcome_rows)
    thresholds = _normalize_nonnegative_grid(minimum_reward_risks, "minimum_reward_risks")
    directions = _normalize_direction_filters(direction_filters)
    return [
        _experiment_row(
            rows,
            minimum_reward_risk=minimum_reward_risk,
            direction_filter=direction_filter,
            sample="all",
            split_id="aggregate",
            selected_experiment_id="",
            trade_dates=_sorted_trade_dates(rows),
        )
        for minimum_reward_risk in thresholds
        for direction_filter in directions
    ]


def run_absorption_reward_risk_train_holdout_sweep(
    outcome_rows: Iterable[dict[str, Any]],
    *,
    train_date_count: int,
    minimum_reward_risks: Iterable[float],
    direction_filters: Iterable[str] = ("all",),
) -> list[dict[str, Any]]:
    """Run a chronological train/holdout reward/risk threshold sweep."""

    rows = list(outcome_rows)
    dates = _sorted_trade_dates(rows)
    if train_date_count <= 0 or train_date_count >= len(dates):
        raise AbsorptionExperimentError(
            "train_date_count must be greater than zero and less than the number of trade dates",
        )

    train_dates = dates[:train_date_count]
    holdout_dates = dates[train_date_count:]
    train_rows = _filter_rows_by_dates(rows, train_dates)
    holdout_rows = _filter_rows_by_dates(rows, holdout_dates)

    train_sweep = run_absorption_reward_risk_sweep(
        train_rows,
        minimum_reward_risks=minimum_reward_risks,
        direction_filters=direction_filters,
    )
    best_train = max(train_sweep, key=lambda row: float(row["net_usd"]), default=None)
    selected_experiment_id = "" if best_train is None else str(best_train["experiment_id"])
    split_id = f"chronological_train_dates={len(train_dates)}_holdout_dates={len(holdout_dates)}"

    thresholds = _normalize_nonnegative_grid(minimum_reward_risks, "minimum_reward_risks")
    directions = _normalize_direction_filters(direction_filters)
    return [
        *[
            _tag_split_row(
                row,
                sample="train",
                selected_experiment_id=selected_experiment_id,
                split_id=split_id,
                trade_dates=train_dates,
            )
            for row in train_sweep
        ],
        *[
            _experiment_row(
                holdout_rows,
                minimum_reward_risk=minimum_reward_risk,
                direction_filter=direction_filter,
                sample="holdout",
                split_id=split_id,
                selected_experiment_id=selected_experiment_id,
                trade_dates=holdout_dates,
            )
            for minimum_reward_risk in thresholds
            for direction_filter in directions
        ],
    ]


def run_absorption_reward_risk_walk_forward_sweep(
    outcome_rows: Iterable[dict[str, Any]],
    *,
    train_date_count: int,
    holdout_date_count: int,
    minimum_reward_risks: Iterable[float],
    direction_filters: Iterable[str] = ("all",),
    minimum_train_trades: int = 1,
) -> list[dict[str, Any]]:
    """Run rolling chronological reward/risk threshold windows by trade date."""

    rows = list(outcome_rows)
    dates = _sorted_trade_dates(rows)
    if train_date_count <= 0:
        raise AbsorptionExperimentError("train_date_count must be positive")
    if holdout_date_count <= 0:
        raise AbsorptionExperimentError("holdout_date_count must be positive")
    if minimum_train_trades <= 0:
        raise AbsorptionExperimentError("minimum_train_trades must be positive")
    if train_date_count + holdout_date_count > len(dates):
        raise AbsorptionExperimentError(
            "train_date_count plus holdout_date_count must not exceed the number of trade dates",
        )

    sweep_kwargs = {
        "minimum_reward_risks": minimum_reward_risks,
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

        train_sweep = run_absorption_reward_risk_sweep(train_rows, **sweep_kwargs)
        holdout_sweep = run_absorption_reward_risk_sweep(holdout_rows, **sweep_kwargs)
        best_train = _select_best_train_row(
            train_sweep,
            minimum_train_trades=minimum_train_trades,
        )
        matching_holdout = _find_experiment_row(
            holdout_sweep,
            str(best_train["experiment_id"]),
        )
        split_id = (
            f"walk_forward_window={window_index + 1}:"
            f"train_dates={len(train_dates)}:"
            f"holdout_dates={len(holdout_dates)}"
        )

        split_rows.append(
            _tag_split_row(
                best_train,
                sample="train",
                selected_experiment_id=str(best_train["experiment_id"]),
                split_id=split_id,
                trade_dates=train_dates,
            ),
        )
        split_rows.append(
            _tag_split_row(
                matching_holdout,
                sample="holdout",
                selected_experiment_id=str(best_train["experiment_id"]),
                split_id=split_id,
                trade_dates=holdout_dates,
            ),
        )

    return split_rows


def _experiment_row(
    rows: list[dict[str, Any]],
    *,
    minimum_reward_risk: float,
    direction_filter: str,
    sample: str,
    split_id: str,
    selected_experiment_id: str,
    trade_dates: list[str],
) -> dict[str, Any]:
    filtered_rows = _filter_outcomes(
        rows,
        minimum_reward_risk=minimum_reward_risk,
        direction_filter=direction_filter,
    )
    summary = summarize_trade_outcomes(filtered_rows)
    direction_counts = Counter(str(row["direction"]) for row in filtered_rows)
    experiment_id = (
        "liquidity_sweep_absorption_reward_risk:"
        f"direction={direction_filter}:"
        f"min_reward_risk={_format_number(minimum_reward_risk)}"
    )

    return {
        "schema_version": 1,
        "split_id": split_id,
        "sample": sample,
        "selected_on_train": str(experiment_id == selected_experiment_id).lower(),
        "trade_dates": ";".join(trade_dates),
        "experiment_id": experiment_id,
        "strategy_id": "liquidity_sweep_absorption_reversal",
        "direction_filter": direction_filter,
        "minimum_reward_risk": _format_number(minimum_reward_risk),
        "input_trades": len(rows),
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
        "notes": "post-signal reward/risk filter over absorption outcomes",
    }


def _tag_split_row(
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


def _find_experiment_row(rows: list[dict[str, Any]], experiment_id: str) -> dict[str, Any]:
    for row in rows:
        if str(row["experiment_id"]) == experiment_id:
            return row
    raise AbsorptionExperimentError(f"Missing matching holdout experiment row: {experiment_id}")


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
        raise AbsorptionExperimentError(
            f"No train experiments met minimum_train_trades={minimum_train_trades}",
        )
    return max(eligible_rows, key=lambda row: float(row["net_usd"]))


def _filter_outcomes(
    rows: list[dict[str, Any]],
    *,
    minimum_reward_risk: float,
    direction_filter: str,
) -> list[dict[str, Any]]:
    return [
        row
        for row in rows
        if (direction_filter == "all" or str(row["direction"]) == direction_filter)
        and _reward_risk(row) >= minimum_reward_risk
    ]


def _reward_risk(row: dict[str, Any]) -> float:
    entry_price = _to_float(row["entry_price"], "entry_price")
    stop_price = _to_float(row["stop_price"], "stop_price")
    target_price = _to_float(row["target_price"], "target_price")
    risk_points = abs(entry_price - stop_price)
    if risk_points <= 0:
        return 0.0
    return abs(target_price - entry_price) / risk_points


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
    raise AbsorptionExperimentError(f"Invalid timestamp: {value!r}")


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


def _normalize_nonnegative_grid(values: Iterable[float], field_name: str) -> list[float]:
    grid = [float(value) for value in values]
    if not grid:
        raise AbsorptionExperimentError(f"{field_name} must contain at least one value")
    if any(value < 0 for value in grid):
        raise AbsorptionExperimentError(f"{field_name} values must be nonnegative")
    return grid


def _normalize_direction_filters(values: Iterable[str]) -> list[str]:
    filters = [str(value).strip().lower() for value in values if str(value).strip()]
    if not filters:
        raise AbsorptionExperimentError("direction_filters must contain at least one value")
    invalid = [value for value in filters if value not in _ALLOWED_DIRECTION_FILTERS]
    if invalid:
        raise AbsorptionExperimentError(
            "direction_filters contains unsupported values: " + ", ".join(invalid),
        )
    return filters


def _to_float(value: Any, field_name: str) -> float:
    try:
        return float(str(value))
    except ValueError as exc:
        raise AbsorptionExperimentError(f"Invalid numeric field {field_name}: {value!r}") from exc


def _format_number(value: Any) -> str:
    return f"{float(value):.8f}".rstrip("0").rstrip(".")
