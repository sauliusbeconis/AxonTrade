"""Strategy health-gate experiments for logged signal outcomes."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from itertools import product
from typing import Any, Iterable


SIGNAL_HEALTH_GATE_SWEEP_HEADER = [
    "schema_version",
    "experiment_id",
    "strategy_id",
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
SIGNAL_HEALTH_GATE_WALK_FORWARD_HEADER = [
    "schema_version",
    "split_id",
    "sample",
    "selected_on_train",
    "trade_dates",
    "experiment_id",
    "strategy_id",
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
_LOSS_EXIT_REASONS = {"stop_hit", "ambiguous_stop_first"}


class SignalHealthGateExperimentError(ValueError):
    """Raised when a strategy health-gate experiment cannot be evaluated."""


@dataclass(frozen=True)
class HealthGateConfig:
    maximum_daily_losses: int
    daily_loss_limit_usd: float
    maximum_consecutive_losses: int
    consecutive_loss_pause_trade_dates: int
    maximum_equity_drawdown_usd: float
    drawdown_pause_trade_dates: int


@dataclass
class _HealthState:
    current_date: str | None = None
    daily_net_usd: float = 0.0
    daily_losses: int = 0
    block_rest_of_day: bool = False
    pause_trade_dates_remaining: int = 0
    current_date_is_paused: bool = False
    consecutive_losses: int = 0
    cumulative_net_usd: float = 0.0
    peak_net_usd: float = 0.0


def run_signal_health_gate_sweep(
    diagnostic_rows: Iterable[dict[str, Any]],
    *,
    maximum_daily_losses: Iterable[int],
    daily_loss_limits_usd: Iterable[float],
    maximum_consecutive_losses: Iterable[int],
    consecutive_loss_pause_trade_dates: Iterable[int],
    maximum_equity_drawdowns_usd: Iterable[float],
    drawdown_pause_trade_dates: Iterable[int],
) -> list[dict[str, Any]]:
    """Sweep realized-outcome health gates over logged signal diagnostics."""

    rows = _sorted_rows(list(diagnostic_rows))
    configs = _health_gate_configs(
        maximum_daily_losses=maximum_daily_losses,
        daily_loss_limits_usd=daily_loss_limits_usd,
        maximum_consecutive_losses=maximum_consecutive_losses,
        consecutive_loss_pause_trade_dates=consecutive_loss_pause_trade_dates,
        maximum_equity_drawdowns_usd=maximum_equity_drawdowns_usd,
        drawdown_pause_trade_dates=drawdown_pause_trade_dates,
    )
    return [
        _experiment_row(
            rows,
            config=config,
            report_dates=None,
            state_warmup_rows=0,
        )
        for config in configs
    ]


def run_signal_health_gate_walk_forward_sweep(
    diagnostic_rows: Iterable[dict[str, Any]],
    *,
    train_date_count: int,
    holdout_date_count: int,
    maximum_daily_losses: Iterable[int],
    daily_loss_limits_usd: Iterable[float],
    maximum_consecutive_losses: Iterable[int],
    consecutive_loss_pause_trade_dates: Iterable[int],
    maximum_equity_drawdowns_usd: Iterable[float],
    drawdown_pause_trade_dates: Iterable[int],
    minimum_train_accepted_trades: int = 1,
) -> list[dict[str, Any]]:
    """Run rolling selection of realized-outcome health gates by trade date."""

    rows = _sorted_rows(list(diagnostic_rows))
    dates = _sorted_trade_dates(rows)
    if train_date_count <= 0:
        raise SignalHealthGateExperimentError("train_date_count must be positive")
    if holdout_date_count <= 0:
        raise SignalHealthGateExperimentError("holdout_date_count must be positive")
    if minimum_train_accepted_trades <= 0:
        raise SignalHealthGateExperimentError("minimum_train_accepted_trades must be positive")
    if train_date_count + holdout_date_count > len(dates):
        raise SignalHealthGateExperimentError(
            "train_date_count plus holdout_date_count must not exceed "
            "the number of candidate trade dates",
        )

    configs = _health_gate_configs(
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
        train_rows = _filter_rows_by_dates(rows, train_dates)
        holdout_rows = _filter_rows_by_dates(rows, holdout_dates)
        train_sweep = [
            _experiment_row(
                train_rows,
                config=config,
                report_dates=None,
                state_warmup_rows=0,
            )
            for config in configs
        ]
        best_train = _select_best_train_row(
            train_sweep,
            minimum_train_accepted_trades=minimum_train_accepted_trades,
        )
        selected_config = _config_from_row(best_train)
        holdout_with_warmup = _experiment_row(
            train_rows + holdout_rows,
            config=selected_config,
            report_dates=holdout_dates,
            state_warmup_rows=len(train_rows),
        )
        split_id = (
            f"health_gate_walk_forward_window={window_index + 1}:"
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
                holdout_with_warmup,
                sample="holdout",
                selected_row=best_train,
                split_id=split_id,
                trade_dates=holdout_dates,
            ),
        )

    return split_rows


def _experiment_row(
    rows: list[dict[str, Any]],
    *,
    config: HealthGateConfig,
    report_dates: list[str] | None,
    state_warmup_rows: int,
) -> dict[str, Any]:
    report_date_set = None if report_dates is None else set(report_dates)
    summary = _simulate(rows, config=config, report_date_set=report_date_set)
    strategy_id = _strategy_id(rows)
    experiment_id = (
        f"signal_health_gate:strategy={strategy_id}:"
        f"max_daily_losses={config.maximum_daily_losses}:"
        f"daily_loss={_format_number(config.daily_loss_limit_usd)}:"
        f"max_consecutive_losses={config.maximum_consecutive_losses}:"
        f"consecutive_pause_dates={config.consecutive_loss_pause_trade_dates}:"
        f"max_drawdown={_format_number(config.maximum_equity_drawdown_usd)}:"
        f"drawdown_pause_dates={config.drawdown_pause_trade_dates}"
    )
    accepted_trades = int(summary["accepted_trades"])
    net_usd = float(summary["net_usd"])

    return {
        "schema_version": 1,
        "experiment_id": experiment_id,
        "strategy_id": strategy_id,
        "maximum_daily_losses": config.maximum_daily_losses,
        "daily_loss_limit_usd": _format_number(config.daily_loss_limit_usd),
        "maximum_consecutive_losses": config.maximum_consecutive_losses,
        "consecutive_loss_pause_trade_dates": config.consecutive_loss_pause_trade_dates,
        "maximum_equity_drawdown_usd": _format_number(config.maximum_equity_drawdown_usd),
        "drawdown_pause_trade_dates": config.drawdown_pause_trade_dates,
        "input_diagnostic_rows": summary["input_diagnostic_rows"],
        "state_warmup_rows": state_warmup_rows,
        "accepted_trades": accepted_trades,
        "skipped_trades": summary["skipped_trades"],
        "target_hits": summary["target_hits"],
        "losses": summary["losses"],
        "other_exits": summary["other_exits"],
        "skipped_target_hits": summary["skipped_target_hits"],
        "skipped_losses": summary["skipped_losses"],
        "skipped_other_exits": summary["skipped_other_exits"],
        "win_rate": _format_number(summary["win_rate"]),
        "net_usd": _format_number(net_usd),
        "skipped_net_usd": _format_number(summary["skipped_net_usd"]),
        "average_net_usd": _format_number(net_usd / accepted_trades if accepted_trades else 0.0),
        "max_equity_drawdown_usd": _format_number(summary["max_equity_drawdown_usd"]),
        "long_trades": summary["long_trades"],
        "short_trades": summary["short_trades"],
        "notes": (
            "health gate sweep over realized signal outcomes; gates use only "
            "closed accepted trades and reset drawdown baseline after a drawdown pause"
        ),
    }


def _simulate(
    rows: list[dict[str, Any]],
    *,
    config: HealthGateConfig,
    report_date_set: set[str] | None,
) -> dict[str, Any]:
    state = _HealthState()
    accepted_rows: list[dict[str, Any]] = []
    skipped_rows: list[dict[str, Any]] = []
    reported_cumulative_net = 0.0
    reported_peak_net = 0.0
    reported_max_drawdown = 0.0

    for row in rows:
        trade_date = _trade_date(row)
        if trade_date != state.current_date:
            _start_trade_date(state, trade_date)
        is_reported = report_date_set is None or trade_date in report_date_set
        is_blocked = state.current_date_is_paused or state.block_rest_of_day
        if is_blocked:
            if is_reported:
                skipped_rows.append(row)
            continue

        net_usd = _to_float(row["net_usd"], "net_usd")
        state.daily_net_usd += net_usd
        state.cumulative_net_usd += net_usd
        state.peak_net_usd = max(state.peak_net_usd, state.cumulative_net_usd)
        state_drawdown = state.cumulative_net_usd - state.peak_net_usd
        is_losing_trade = net_usd < 0
        if is_losing_trade:
            state.daily_losses += 1
            state.consecutive_losses += 1
        else:
            state.consecutive_losses = 0

        if is_reported:
            accepted_rows.append(row)
            reported_cumulative_net += net_usd
            reported_peak_net = max(reported_peak_net, reported_cumulative_net)
            reported_max_drawdown = min(
                reported_max_drawdown,
                reported_cumulative_net - reported_peak_net,
            )

        _apply_post_trade_gates(state, config, state_drawdown=state_drawdown)

    accepted_summary = _outcome_summary(accepted_rows)
    skipped_summary = _outcome_summary(skipped_rows)
    direction_counts = Counter(str(row["direction"]) for row in accepted_rows)
    return {
        "input_diagnostic_rows": (
            len(rows)
            if report_date_set is None
            else sum(1 for row in rows if _trade_date(row) in report_date_set)
        ),
        "accepted_trades": accepted_summary["total_trades"],
        "skipped_trades": skipped_summary["total_trades"],
        "target_hits": accepted_summary["target_hits"],
        "losses": accepted_summary["losses"],
        "other_exits": accepted_summary["other_exits"],
        "skipped_target_hits": skipped_summary["target_hits"],
        "skipped_losses": skipped_summary["losses"],
        "skipped_other_exits": skipped_summary["other_exits"],
        "win_rate": accepted_summary["win_rate"],
        "net_usd": accepted_summary["net_usd"],
        "skipped_net_usd": skipped_summary["net_usd"],
        "max_equity_drawdown_usd": reported_max_drawdown,
        "long_trades": direction_counts.get("long", 0),
        "short_trades": direction_counts.get("short", 0),
    }


def _start_trade_date(state: _HealthState, trade_date: str) -> None:
    state.current_date = trade_date
    state.daily_net_usd = 0.0
    state.daily_losses = 0
    state.block_rest_of_day = False
    state.current_date_is_paused = state.pause_trade_dates_remaining > 0
    if state.current_date_is_paused:
        state.pause_trade_dates_remaining -= 1


def _apply_post_trade_gates(
    state: _HealthState,
    config: HealthGateConfig,
    *,
    state_drawdown: float,
) -> None:
    if state.daily_losses >= config.maximum_daily_losses:
        state.block_rest_of_day = True
    if state.daily_net_usd <= -config.daily_loss_limit_usd:
        state.block_rest_of_day = True
    if state.consecutive_losses >= config.maximum_consecutive_losses:
        state.block_rest_of_day = True
        state.pause_trade_dates_remaining = max(
            state.pause_trade_dates_remaining,
            config.consecutive_loss_pause_trade_dates,
        )
        state.consecutive_losses = 0
    if state_drawdown <= -config.maximum_equity_drawdown_usd:
        state.block_rest_of_day = True
        state.pause_trade_dates_remaining = max(
            state.pause_trade_dates_remaining,
            config.drawdown_pause_trade_dates,
        )
        state.peak_net_usd = state.cumulative_net_usd


def _outcome_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
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
    }


def _health_gate_configs(
    *,
    maximum_daily_losses: Iterable[int],
    daily_loss_limits_usd: Iterable[float],
    maximum_consecutive_losses: Iterable[int],
    consecutive_loss_pause_trade_dates: Iterable[int],
    maximum_equity_drawdowns_usd: Iterable[float],
    drawdown_pause_trade_dates: Iterable[int],
) -> list[HealthGateConfig]:
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
        HealthGateConfig(
            maximum_daily_losses=daily_loss_count,
            daily_loss_limit_usd=daily_loss_limit,
            maximum_consecutive_losses=consecutive_loss_count,
            consecutive_loss_pause_trade_dates=consecutive_pause,
            maximum_equity_drawdown_usd=drawdown,
            drawdown_pause_trade_dates=drawdown_pause,
        )
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


def _select_best_train_row(
    rows: list[dict[str, Any]],
    *,
    minimum_train_accepted_trades: int,
) -> dict[str, Any]:
    eligible_rows = [
        row
        for row in rows
        if int(row["accepted_trades"]) >= minimum_train_accepted_trades
    ]
    if not eligible_rows:
        raise SignalHealthGateExperimentError(
            "No train experiments met "
            f"minimum_train_accepted_trades={minimum_train_accepted_trades}",
        )
    return max(
        eligible_rows,
        key=lambda row: (
            float(row["net_usd"]),
            -float(row["max_equity_drawdown_usd"]),
            int(row["accepted_trades"]),
        ),
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
            for key in SIGNAL_HEALTH_GATE_SWEEP_HEADER
            if key != "schema_version"
        },
    )
    return tagged


def _config_from_row(row: dict[str, Any]) -> HealthGateConfig:
    return HealthGateConfig(
        maximum_daily_losses=int(row["maximum_daily_losses"]),
        daily_loss_limit_usd=_to_float(row["daily_loss_limit_usd"], "daily_loss_limit_usd"),
        maximum_consecutive_losses=int(row["maximum_consecutive_losses"]),
        consecutive_loss_pause_trade_dates=int(row["consecutive_loss_pause_trade_dates"]),
        maximum_equity_drawdown_usd=_to_float(
            row["maximum_equity_drawdown_usd"],
            "maximum_equity_drawdown_usd",
        ),
        drawdown_pause_trade_dates=int(row["drawdown_pause_trade_dates"]),
    )


def _selection_key(row: dict[str, Any]) -> tuple[str, ...]:
    return (
        str(row["maximum_daily_losses"]),
        str(row["daily_loss_limit_usd"]),
        str(row["maximum_consecutive_losses"]),
        str(row["consecutive_loss_pause_trade_dates"]),
        str(row["maximum_equity_drawdown_usd"]),
        str(row["drawdown_pause_trade_dates"]),
    )


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
    raise SignalHealthGateExperimentError(f"Invalid timestamp: {value!r}")


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


def _normalize_positive_grid(values: Iterable[float], field_name: str) -> list[float]:
    grid = [float(value) for value in values]
    if not grid:
        raise SignalHealthGateExperimentError(f"{field_name} must contain at least one value")
    if any(value <= 0 for value in grid):
        raise SignalHealthGateExperimentError(f"{field_name} values must be positive")
    return grid


def _normalize_positive_int_grid(values: Iterable[int], field_name: str) -> list[int]:
    grid = [int(value) for value in values]
    if not grid:
        raise SignalHealthGateExperimentError(f"{field_name} must contain at least one value")
    if any(value <= 0 for value in grid):
        raise SignalHealthGateExperimentError(f"{field_name} values must be positive")
    return grid


def _normalize_nonnegative_int_grid(values: Iterable[int], field_name: str) -> list[int]:
    grid = [int(value) for value in values]
    if not grid:
        raise SignalHealthGateExperimentError(f"{field_name} must contain at least one value")
    if any(value < 0 for value in grid):
        raise SignalHealthGateExperimentError(f"{field_name} values must be nonnegative")
    return grid


def _to_float(value: Any, field_name: str) -> float:
    try:
        return float(str(value))
    except ValueError as exc:
        raise SignalHealthGateExperimentError(
            f"Invalid numeric field {field_name}: {value!r}",
        ) from exc


def _format_number(value: Any) -> str:
    return f"{float(value):.8f}".rstrip("0").rstrip(".")
