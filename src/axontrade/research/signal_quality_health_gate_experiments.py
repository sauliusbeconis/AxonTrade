"""Combined entry-quality and health-gate experiments for logged signals."""

from __future__ import annotations

from datetime import datetime
from itertools import product
from typing import Any, Iterable

from axontrade.research.signal_health_gate_experiments import evaluate_signal_health_gate


SIGNAL_QUALITY_HEALTH_GATE_WALK_FORWARD_HEADER = [
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
    "maximum_daily_losses",
    "daily_loss_limit_usd",
    "maximum_consecutive_losses",
    "consecutive_loss_pause_trade_dates",
    "maximum_equity_drawdown_usd",
    "drawdown_pause_trade_dates",
    "input_diagnostic_rows",
    "state_warmup_rows",
    "accepted_trades",
    "skipped_trades",
    "target_hits",
    "losses",
    "other_exits",
    "skipped_target_hits",
    "skipped_losses",
    "skipped_other_exits",
    "win_rate",
    "net_usd",
    "skipped_net_usd",
    "average_net_usd",
    "max_equity_drawdown_usd",
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


class SignalQualityHealthGateExperimentError(ValueError):
    """Raised when a combined quality/health-gate experiment cannot run."""


def run_signal_quality_health_gate_walk_forward_sweep(
    diagnostic_rows: Iterable[dict[str, Any]],
    *,
    train_date_count: int,
    holdout_date_count: int,
    max_original_reward_risks: Iterable[float],
    min_minutes_after_rth_open_values: Iterable[float],
    max_minutes_after_rth_open_values: Iterable[float],
    max_sweep_abs_deltas: Iterable[float],
    maximum_daily_losses: Iterable[int],
    daily_loss_limits_usd: Iterable[float],
    maximum_consecutive_losses: Iterable[int],
    consecutive_loss_pause_trade_dates: Iterable[int],
    maximum_equity_drawdowns_usd: Iterable[float],
    drawdown_pause_trade_dates: Iterable[int],
    direction_filters: Iterable[str] = ("all",),
    minimum_train_accepted_trades: int = 1,
) -> list[dict[str, Any]]:
    """Select an entry-quality filter plus health gate on rolling train dates."""

    rows = _sorted_rows(list(diagnostic_rows))
    dates = _sorted_trade_dates(rows)
    if train_date_count <= 0:
        raise SignalQualityHealthGateExperimentError("train_date_count must be positive")
    if holdout_date_count <= 0:
        raise SignalQualityHealthGateExperimentError("holdout_date_count must be positive")
    if minimum_train_accepted_trades <= 0:
        raise SignalQualityHealthGateExperimentError(
            "minimum_train_accepted_trades must be positive",
        )
    if train_date_count + holdout_date_count > len(dates):
        raise SignalQualityHealthGateExperimentError(
            "train_date_count plus holdout_date_count must not exceed "
            "the number of candidate trade dates",
        )

    quality_configs = _quality_configs(
        max_original_reward_risks=max_original_reward_risks,
        min_minutes_after_rth_open_values=min_minutes_after_rth_open_values,
        max_minutes_after_rth_open_values=max_minutes_after_rth_open_values,
        max_sweep_abs_deltas=max_sweep_abs_deltas,
        direction_filters=direction_filters,
    )
    health_configs = _health_configs(
        maximum_daily_losses=maximum_daily_losses,
        daily_loss_limits_usd=daily_loss_limits_usd,
        maximum_consecutive_losses=maximum_consecutive_losses,
        consecutive_loss_pause_trade_dates=consecutive_loss_pause_trade_dates,
        maximum_equity_drawdowns_usd=maximum_equity_drawdowns_usd,
        drawdown_pause_trade_dates=drawdown_pause_trade_dates,
    )

    split_rows: list[dict[str, Any]] = []
    max_start = len(dates) - train_date_count - holdout_date_count + 1
    for window_index in range(max_start):
        train_dates = dates[window_index:window_index + train_date_count]
        holdout_dates = dates[
            window_index + train_date_count:
            window_index + train_date_count + holdout_date_count
        ]
        train_base = _filter_rows_by_dates(rows, train_dates)
        best_train = _select_best_train_row(
            train_base,
            quality_configs=quality_configs,
            health_configs=health_configs,
            minimum_train_accepted_trades=minimum_train_accepted_trades,
        )
        selected_quality = _quality_config_from_row(best_train)
        train_filtered = _filter_rows(train_base, selected_quality)
        holdout_base = _filter_rows_by_dates(rows, holdout_dates)
        holdout_filtered = _filter_rows(holdout_base, selected_quality)
        selected_health = _health_config_from_row(best_train)
        holdout_row = _combined_row(
            evaluate_signal_health_gate(
                train_filtered + holdout_filtered,
                **selected_health,
                report_trade_dates=holdout_dates,
                state_warmup_rows=len(train_filtered),
            ),
            selected_quality,
        )

        split_id = (
            f"quality_health_gate_walk_forward_window={window_index + 1}:"
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
                holdout_row,
                sample="holdout",
                selected_row=best_train,
                split_id=split_id,
                trade_dates=holdout_dates,
            ),
        )

    return split_rows


def _select_best_train_row(
    train_rows: list[dict[str, Any]],
    *,
    quality_configs: list[dict[str, Any]],
    health_configs: list[dict[str, Any]],
    minimum_train_accepted_trades: int,
) -> dict[str, Any]:
    best_row: dict[str, Any] | None = None
    for quality_config in quality_configs:
        filtered_rows = _filter_rows(train_rows, quality_config)
        if len(filtered_rows) < minimum_train_accepted_trades:
            continue
        for health_config in health_configs:
            candidate = _combined_row(
                evaluate_signal_health_gate(filtered_rows, **health_config),
                quality_config,
            )
            if int(candidate["accepted_trades"]) < minimum_train_accepted_trades:
                continue
            if best_row is None or _selection_score(candidate) > _selection_score(best_row):
                best_row = candidate

    if best_row is None:
        raise SignalQualityHealthGateExperimentError(
            "No train experiments met "
            f"minimum_train_accepted_trades={minimum_train_accepted_trades}",
        )
    return best_row


def _combined_row(
    health_row: dict[str, Any],
    quality_config: dict[str, Any],
) -> dict[str, Any]:
    experiment_id = (
        f"signal_quality_health_gate:strategy={health_row['strategy_id']}:"
        f"direction={quality_config['direction_filter']}:"
        f"max_rr={_format_number(quality_config['max_original_reward_risk'])}:"
        f"minutes={_format_number(quality_config['min_minutes_after_rth_open'])}-"
        f"{_format_number(quality_config['max_minutes_after_rth_open'])}:"
        f"max_sweep_abs_delta={_format_number(quality_config['max_sweep_abs_delta'])}:"
        f"max_daily_losses={health_row['maximum_daily_losses']}:"
        f"daily_loss={health_row['daily_loss_limit_usd']}:"
        f"max_consecutive_losses={health_row['maximum_consecutive_losses']}:"
        f"consecutive_pause_dates={health_row['consecutive_loss_pause_trade_dates']}:"
        f"max_drawdown={health_row['maximum_equity_drawdown_usd']}:"
        f"drawdown_pause_dates={health_row['drawdown_pause_trade_dates']}"
    )
    return {
        "schema_version": 1,
        "experiment_id": experiment_id,
        "strategy_id": health_row["strategy_id"],
        "direction_filter": quality_config["direction_filter"],
        "max_original_reward_risk": _format_number(
            quality_config["max_original_reward_risk"],
        ),
        "min_minutes_after_rth_open": _format_number(
            quality_config["min_minutes_after_rth_open"],
        ),
        "max_minutes_after_rth_open": _format_number(
            quality_config["max_minutes_after_rth_open"],
        ),
        "max_sweep_abs_delta": _format_number(quality_config["max_sweep_abs_delta"]),
        "maximum_daily_losses": health_row["maximum_daily_losses"],
        "daily_loss_limit_usd": health_row["daily_loss_limit_usd"],
        "maximum_consecutive_losses": health_row["maximum_consecutive_losses"],
        "consecutive_loss_pause_trade_dates": (
            health_row["consecutive_loss_pause_trade_dates"]
        ),
        "maximum_equity_drawdown_usd": health_row["maximum_equity_drawdown_usd"],
        "drawdown_pause_trade_dates": health_row["drawdown_pause_trade_dates"],
        "input_diagnostic_rows": health_row["input_diagnostic_rows"],
        "state_warmup_rows": health_row["state_warmup_rows"],
        "accepted_trades": health_row["accepted_trades"],
        "skipped_trades": health_row["skipped_trades"],
        "target_hits": health_row["target_hits"],
        "losses": health_row["losses"],
        "other_exits": health_row["other_exits"],
        "skipped_target_hits": health_row["skipped_target_hits"],
        "skipped_losses": health_row["skipped_losses"],
        "skipped_other_exits": health_row["skipped_other_exits"],
        "win_rate": health_row["win_rate"],
        "net_usd": health_row["net_usd"],
        "skipped_net_usd": health_row["skipped_net_usd"],
        "average_net_usd": health_row["average_net_usd"],
        "max_equity_drawdown_usd": health_row["max_equity_drawdown_usd"],
        "long_trades": health_row["long_trades"],
        "short_trades": health_row["short_trades"],
        "notes": (
            "joint walk-forward selection of entry-quality filter and "
            "closed-trade health gate"
        ),
    }


def _filter_rows(
    rows: list[dict[str, Any]],
    quality_config: dict[str, Any],
) -> list[dict[str, Any]]:
    filtered_rows: list[dict[str, Any]] = []
    for row in rows:
        direction_filter = str(quality_config["direction_filter"])
        if direction_filter != "all" and str(row["direction"]) != direction_filter:
            continue
        if (
            _to_float(row["original_reward_risk"], "original_reward_risk")
            > float(quality_config["max_original_reward_risk"])
        ):
            continue
        minutes = _to_float(row["minutes_after_rth_open"], "minutes_after_rth_open")
        if minutes < float(quality_config["min_minutes_after_rth_open"]):
            continue
        if minutes > float(quality_config["max_minutes_after_rth_open"]):
            continue
        if (
            _to_float(row["sweep_abs_delta"], "sweep_abs_delta")
            > float(quality_config["max_sweep_abs_delta"])
        ):
            continue
        filtered_rows.append(row)
    return filtered_rows


def _quality_configs(
    *,
    max_original_reward_risks: Iterable[float],
    min_minutes_after_rth_open_values: Iterable[float],
    max_minutes_after_rth_open_values: Iterable[float],
    max_sweep_abs_deltas: Iterable[float],
    direction_filters: Iterable[str],
) -> list[dict[str, Any]]:
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
    configs: list[dict[str, Any]] = []
    for direction, max_rr, min_minute, max_minute, max_sweep in product(
        directions,
        max_reward_risks,
        min_minutes,
        max_minutes,
        max_sweeps,
    ):
        if min_minute > max_minute:
            continue
        configs.append(
            {
                "direction_filter": direction,
                "max_original_reward_risk": max_rr,
                "min_minutes_after_rth_open": min_minute,
                "max_minutes_after_rth_open": max_minute,
                "max_sweep_abs_delta": max_sweep,
            },
        )
    if not configs:
        raise SignalQualityHealthGateExperimentError(
            "At least one min/max minute window must be valid",
        )
    return configs


def _health_configs(
    *,
    maximum_daily_losses: Iterable[int],
    daily_loss_limits_usd: Iterable[float],
    maximum_consecutive_losses: Iterable[int],
    consecutive_loss_pause_trade_dates: Iterable[int],
    maximum_equity_drawdowns_usd: Iterable[float],
    drawdown_pause_trade_dates: Iterable[int],
) -> list[dict[str, Any]]:
    daily_losses = _normalize_positive_int_grid(maximum_daily_losses, "maximum_daily_losses")
    daily_loss_limits = _normalize_positive_grid(daily_loss_limits_usd, "daily_loss_limits_usd")
    consecutive_losses = _normalize_positive_int_grid(
        maximum_consecutive_losses,
        "maximum_consecutive_losses",
    )
    consecutive_pauses = _normalize_nonnegative_int_grid(
        consecutive_loss_pause_trade_dates,
        "consecutive_loss_pause_trade_dates",
    )
    drawdowns = _normalize_positive_grid(
        maximum_equity_drawdowns_usd,
        "maximum_equity_drawdowns_usd",
    )
    drawdown_pauses = _normalize_nonnegative_int_grid(
        drawdown_pause_trade_dates,
        "drawdown_pause_trade_dates",
    )
    return [
        {
            "maximum_daily_losses": daily_loss_count,
            "daily_loss_limit_usd": daily_loss_limit,
            "maximum_consecutive_losses": consecutive_loss_count,
            "consecutive_loss_pause_trade_dates": consecutive_pause,
            "maximum_equity_drawdown_usd": drawdown,
            "drawdown_pause_trade_dates": drawdown_pause,
        }
        for (
            daily_loss_count,
            daily_loss_limit,
            consecutive_loss_count,
            consecutive_pause,
            drawdown,
            drawdown_pause,
        ) in product(
            daily_losses,
            daily_loss_limits,
            consecutive_losses,
            consecutive_pauses,
            drawdowns,
            drawdown_pauses,
        )
    ]


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
            for key in SIGNAL_QUALITY_HEALTH_GATE_WALK_FORWARD_HEADER
            if key not in {"schema_version", "split_id", "sample", "selected_on_train", "trade_dates"}
        },
    )
    return tagged


def _selection_score(row: dict[str, Any]) -> tuple[float, float, int]:
    return (
        float(row["net_usd"]),
        float(row["win_rate"]),
        int(row["accepted_trades"]),
    )


def _selection_key(row: dict[str, Any]) -> tuple[str, ...]:
    return (
        str(row["direction_filter"]),
        str(row["max_original_reward_risk"]),
        str(row["min_minutes_after_rth_open"]),
        str(row["max_minutes_after_rth_open"]),
        str(row["max_sweep_abs_delta"]),
        str(row["maximum_daily_losses"]),
        str(row["daily_loss_limit_usd"]),
        str(row["maximum_consecutive_losses"]),
        str(row["consecutive_loss_pause_trade_dates"]),
        str(row["maximum_equity_drawdown_usd"]),
        str(row["drawdown_pause_trade_dates"]),
    )


def _quality_config_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "direction_filter": str(row["direction_filter"]),
        "max_original_reward_risk": _to_float(
            row["max_original_reward_risk"],
            "max_original_reward_risk",
        ),
        "min_minutes_after_rth_open": _to_float(
            row["min_minutes_after_rth_open"],
            "min_minutes_after_rth_open",
        ),
        "max_minutes_after_rth_open": _to_float(
            row["max_minutes_after_rth_open"],
            "max_minutes_after_rth_open",
        ),
        "max_sweep_abs_delta": _to_float(row["max_sweep_abs_delta"], "max_sweep_abs_delta"),
    }


def _health_config_from_row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "maximum_daily_losses": int(row["maximum_daily_losses"]),
        "daily_loss_limit_usd": _to_float(row["daily_loss_limit_usd"], "daily_loss_limit_usd"),
        "maximum_consecutive_losses": int(row["maximum_consecutive_losses"]),
        "consecutive_loss_pause_trade_dates": int(row["consecutive_loss_pause_trade_dates"]),
        "maximum_equity_drawdown_usd": _to_float(
            row["maximum_equity_drawdown_usd"],
            "maximum_equity_drawdown_usd",
        ),
        "drawdown_pause_trade_dates": int(row["drawdown_pause_trade_dates"]),
    }


def _sorted_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: (_parse_timestamp(str(row["entry_time"])), str(row["signal_id"])))


def _sorted_trade_dates(rows: list[dict[str, Any]]) -> list[str]:
    return sorted({_trade_date(row) for row in rows})


def _filter_rows_by_dates(rows: list[dict[str, Any]], dates: list[str]) -> list[dict[str, Any]]:
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
    raise SignalQualityHealthGateExperimentError(f"Invalid timestamp: {value!r}")


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
        raise SignalQualityHealthGateExperimentError(f"{field_name} must contain at least one value")
    if any(value <= 0 for value in grid):
        raise SignalQualityHealthGateExperimentError(f"{field_name} values must be positive")
    return grid


def _normalize_nonnegative_grid(values: Iterable[float], field_name: str) -> list[float]:
    grid = [float(value) for value in values]
    if not grid:
        raise SignalQualityHealthGateExperimentError(f"{field_name} must contain at least one value")
    if any(value < 0 for value in grid):
        raise SignalQualityHealthGateExperimentError(f"{field_name} values must be nonnegative")
    return grid


def _normalize_positive_int_grid(values: Iterable[int], field_name: str) -> list[int]:
    grid = [int(value) for value in values]
    if not grid:
        raise SignalQualityHealthGateExperimentError(f"{field_name} must contain at least one value")
    if any(value <= 0 for value in grid):
        raise SignalQualityHealthGateExperimentError(f"{field_name} values must be positive")
    return grid


def _normalize_nonnegative_int_grid(values: Iterable[int], field_name: str) -> list[int]:
    grid = [int(value) for value in values]
    if not grid:
        raise SignalQualityHealthGateExperimentError(f"{field_name} must contain at least one value")
    if any(value < 0 for value in grid):
        raise SignalQualityHealthGateExperimentError(f"{field_name} values must be nonnegative")
    return grid


def _normalize_direction_filters(values: Iterable[str]) -> list[str]:
    filters = [str(value).strip().lower() for value in values if str(value).strip()]
    if not filters:
        raise SignalQualityHealthGateExperimentError(
            "direction_filters must contain at least one value",
        )
    invalid = [value for value in filters if value not in _ALLOWED_DIRECTION_FILTERS]
    if invalid:
        raise SignalQualityHealthGateExperimentError(
            "direction_filters contains unsupported values: " + ", ".join(invalid),
        )
    return filters


def _to_float(value: Any, field_name: str) -> float:
    try:
        return float(str(value))
    except ValueError as exc:
        raise SignalQualityHealthGateExperimentError(
            f"Invalid numeric field {field_name}: {value!r}",
        ) from exc


def _format_number(value: Any) -> str:
    return f"{float(value):.8f}".rstrip("0").rstrip(".")
