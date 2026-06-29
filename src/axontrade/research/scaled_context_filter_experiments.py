"""Walk-forward filters over scaled-outcome context diagnostics."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from itertools import product
from math import sqrt
from statistics import pstdev
from typing import Any, Iterable


SCALED_CONTEXT_FILTER_SWEEP_HEADER = [
    "schema_version",
    "experiment_id",
    "strategy_id",
    "direction_filter",
    "min_minutes_after_rth_open",
    "max_minutes_after_rth_open",
    "max_risk_to_average_bar_range",
    "max_runner_target_to_average_bar_range",
    "min_signal_abs_delta_sum_to_average_abs_delta",
    "max_signal_abs_delta_sum_to_average_abs_delta",
    "min_entry_volume_to_average_volume",
    "min_entry_trades_to_average_trades",
    "min_continuation_edge_score",
    "min_opening_range_continuation_edge_score",
    "min_directional_opening_range_breakout_points",
    "min_lookback_efficiency_ratio",
    "max_lookback_choppiness_score",
    "min_entry_volume_to_session_average_volume",
    "min_lookback_volume_to_session_average_volume",
    "input_context_rows",
    "evaluated_trades",
    "runner_target_hits",
    "full_stops",
    "runner_stop_exits",
    "other_exits",
    "positive_net_trades",
    "positive_net_rate",
    "net_usd",
    "average_net_usd",
    "average_net_usd_lower_bound",
    "unfiltered_net_usd",
    "participation_rate",
    "filter_net_improvement_usd",
    "long_trades",
    "short_trades",
    "notes",
]
SCALED_CONTEXT_FILTER_WALK_FORWARD_HEADER = [
    "schema_version",
    "split_id",
    "sample",
    "selected_on_train",
    "trade_dates",
    *SCALED_CONTEXT_FILTER_SWEEP_HEADER[1:],
]
_TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
)
_ALLOWED_DIRECTION_FILTERS = ("all", "long", "short")
_FULL_STOP_REASONS = {"full_stop_hit", "ambiguous_full_stop_first"}
_RUNNER_STOP_REASONS = {
    "runner_initial_stop_hit",
    "runner_breakeven_stop_hit",
    "ambiguous_runner_stop_first",
}
_RUNNER_TARGET_REASONS = {"runner_target_hit"}
_ALLOWED_SELECTION_OBJECTIVES = ("net", "efficiency")


class ScaledContextFilterExperimentError(ValueError):
    """Raised when a scaled context filter experiment cannot be evaluated."""


def run_scaled_context_filter_sweep(
    context_rows: Iterable[dict[str, Any]],
    *,
    min_minutes_after_rth_open_values: Iterable[float],
    max_minutes_after_rth_open_values: Iterable[float],
    max_risk_to_average_bar_ranges: Iterable[float],
    max_runner_target_to_average_bar_ranges: Iterable[float],
    min_signal_abs_delta_sum_to_average_abs_deltas: Iterable[float],
    max_signal_abs_delta_sum_to_average_abs_deltas: Iterable[float],
    min_entry_volume_to_average_volumes: Iterable[float],
    min_entry_trades_to_average_trades: Iterable[float],
    min_continuation_edge_scores: Iterable[float] = (0,),
    min_opening_range_continuation_edge_scores: Iterable[float] = (0,),
    min_directional_opening_range_breakout_points_values: Iterable[float] = (-999999,),
    min_lookback_efficiency_ratios: Iterable[float] = (0,),
    max_lookback_choppiness_scores: Iterable[float] = (1,),
    min_entry_volume_to_session_average_volumes: Iterable[float] = (0,),
    min_lookback_volume_to_session_average_volumes: Iterable[float] = (0,),
    direction_filters: Iterable[str] = ("all",),
) -> list[dict[str, Any]]:
    """Sweep entry-known normalized context filters for scaled outcomes."""

    rows = list(context_rows)
    time_windows = _valid_time_windows(
        min_minutes_after_rth_open_values,
        max_minutes_after_rth_open_values,
    )
    max_risk_ranges = _normalize_positive_grid(
        max_risk_to_average_bar_ranges,
        "max_risk_to_average_bar_ranges",
    )
    max_runner_ranges = _normalize_positive_grid(
        max_runner_target_to_average_bar_ranges,
        "max_runner_target_to_average_bar_ranges",
    )
    min_signal_delta_ratios = _normalize_nonnegative_grid(
        min_signal_abs_delta_sum_to_average_abs_deltas,
        "min_signal_abs_delta_sum_to_average_abs_deltas",
    )
    max_signal_delta_ratios = _normalize_positive_grid(
        max_signal_abs_delta_sum_to_average_abs_deltas,
        "max_signal_abs_delta_sum_to_average_abs_deltas",
    )
    signal_delta_windows = [
        (minimum, maximum)
        for minimum, maximum in product(min_signal_delta_ratios, max_signal_delta_ratios)
        if minimum <= maximum
    ]
    if not signal_delta_windows:
        raise ScaledContextFilterExperimentError(
            "At least one min/max signal delta ratio window must be valid",
        )
    min_volume_ratios = _normalize_nonnegative_grid(
        min_entry_volume_to_average_volumes,
        "min_entry_volume_to_average_volumes",
    )
    min_trade_ratios = _normalize_nonnegative_grid(
        min_entry_trades_to_average_trades,
        "min_entry_trades_to_average_trades",
    )
    min_continuation_edges = _normalize_zero_to_one_grid(
        min_continuation_edge_scores,
        "min_continuation_edge_scores",
    )
    min_opening_range_continuation_edges = _normalize_zero_to_one_grid(
        min_opening_range_continuation_edge_scores,
        "min_opening_range_continuation_edge_scores",
    )
    min_opening_range_breakouts = _normalize_float_grid(
        min_directional_opening_range_breakout_points_values,
        "min_directional_opening_range_breakout_points_values",
    )
    min_efficiency_ratios = _normalize_zero_to_one_grid(
        min_lookback_efficiency_ratios,
        "min_lookback_efficiency_ratios",
    )
    max_choppiness_scores = _normalize_zero_to_one_grid(
        max_lookback_choppiness_scores,
        "max_lookback_choppiness_scores",
    )
    min_session_volume_ratios = _normalize_nonnegative_grid(
        min_entry_volume_to_session_average_volumes,
        "min_entry_volume_to_session_average_volumes",
    )
    min_lookback_session_volume_ratios = _normalize_nonnegative_grid(
        min_lookback_volume_to_session_average_volumes,
        "min_lookback_volume_to_session_average_volumes",
    )
    directions = _normalize_direction_filters(direction_filters)

    experiment_rows: list[dict[str, Any]] = []
    for (
        (min_minutes, max_minutes),
        max_risk_range,
        max_runner_range,
        (min_signal_delta_ratio, max_signal_delta_ratio),
        min_volume_ratio,
        min_trade_ratio,
        min_continuation_edge,
        min_opening_range_continuation_edge,
        min_opening_range_breakout,
        min_efficiency_ratio,
        max_choppiness_score,
        min_session_volume_ratio,
        min_lookback_session_volume_ratio,
        direction_filter,
    ) in product(
        time_windows,
        max_risk_ranges,
        max_runner_ranges,
        signal_delta_windows,
        min_volume_ratios,
        min_trade_ratios,
        min_continuation_edges,
        min_opening_range_continuation_edges,
        min_opening_range_breakouts,
        min_efficiency_ratios,
        max_choppiness_scores,
        min_session_volume_ratios,
        min_lookback_session_volume_ratios,
        directions,
    ):
        filtered_rows = _filter_rows(
            rows,
            direction_filter=direction_filter,
            min_minutes_after_rth_open=min_minutes,
            max_minutes_after_rth_open=max_minutes,
            max_risk_to_average_bar_range=max_risk_range,
            max_runner_target_to_average_bar_range=max_runner_range,
            min_signal_abs_delta_sum_to_average_abs_delta=min_signal_delta_ratio,
            max_signal_abs_delta_sum_to_average_abs_delta=max_signal_delta_ratio,
            min_entry_volume_to_average_volume=min_volume_ratio,
            min_entry_trades_to_average_trades=min_trade_ratio,
            min_continuation_edge_score=min_continuation_edge,
            min_opening_range_continuation_edge_score=min_opening_range_continuation_edge,
            min_directional_opening_range_breakout_points=min_opening_range_breakout,
            min_lookback_efficiency_ratio=min_efficiency_ratio,
            max_lookback_choppiness_score=max_choppiness_score,
            min_entry_volume_to_session_average_volume=min_session_volume_ratio,
            min_lookback_volume_to_session_average_volume=min_lookback_session_volume_ratio,
        )
        experiment_rows.append(
            _experiment_row(
                rows,
                filtered_rows,
                direction_filter=direction_filter,
                min_minutes_after_rth_open=min_minutes,
                max_minutes_after_rth_open=max_minutes,
                max_risk_to_average_bar_range=max_risk_range,
                max_runner_target_to_average_bar_range=max_runner_range,
                min_signal_abs_delta_sum_to_average_abs_delta=min_signal_delta_ratio,
                max_signal_abs_delta_sum_to_average_abs_delta=max_signal_delta_ratio,
                min_entry_volume_to_average_volume=min_volume_ratio,
                min_entry_trades_to_average_trades=min_trade_ratio,
                min_continuation_edge_score=min_continuation_edge,
                min_opening_range_continuation_edge_score=(
                    min_opening_range_continuation_edge
                ),
                min_directional_opening_range_breakout_points=min_opening_range_breakout,
                min_lookback_efficiency_ratio=min_efficiency_ratio,
                max_lookback_choppiness_score=max_choppiness_score,
                min_entry_volume_to_session_average_volume=min_session_volume_ratio,
                min_lookback_volume_to_session_average_volume=(
                    min_lookback_session_volume_ratio
                ),
            ),
        )
    return experiment_rows


def run_scaled_context_filter_walk_forward_sweep(
    context_rows: Iterable[dict[str, Any]],
    *,
    train_date_count: int,
    holdout_date_count: int,
    min_minutes_after_rth_open_values: Iterable[float],
    max_minutes_after_rth_open_values: Iterable[float],
    max_risk_to_average_bar_ranges: Iterable[float],
    max_runner_target_to_average_bar_ranges: Iterable[float],
    min_signal_abs_delta_sum_to_average_abs_deltas: Iterable[float],
    max_signal_abs_delta_sum_to_average_abs_deltas: Iterable[float],
    min_entry_volume_to_average_volumes: Iterable[float],
    min_entry_trades_to_average_trades: Iterable[float],
    min_continuation_edge_scores: Iterable[float] = (0,),
    min_opening_range_continuation_edge_scores: Iterable[float] = (0,),
    min_directional_opening_range_breakout_points_values: Iterable[float] = (-999999,),
    min_lookback_efficiency_ratios: Iterable[float] = (0,),
    max_lookback_choppiness_scores: Iterable[float] = (1,),
    min_entry_volume_to_session_average_volumes: Iterable[float] = (0,),
    min_lookback_volume_to_session_average_volumes: Iterable[float] = (0,),
    direction_filters: Iterable[str] = ("all",),
    minimum_train_trades: int = 1,
    window_step_date_count: int = 1,
    selection_objective: str = "net",
) -> list[dict[str, Any]]:
    """Run rolling selection of scaled context filters by trade date."""

    rows = list(context_rows)
    dates = _sorted_trade_dates(rows)
    if train_date_count <= 0:
        raise ScaledContextFilterExperimentError("train_date_count must be positive")
    if holdout_date_count <= 0:
        raise ScaledContextFilterExperimentError("holdout_date_count must be positive")
    if minimum_train_trades <= 0:
        raise ScaledContextFilterExperimentError("minimum_train_trades must be positive")
    if window_step_date_count <= 0:
        raise ScaledContextFilterExperimentError("window_step_date_count must be positive")
    objective = _normalize_selection_objective(selection_objective)
    if train_date_count + holdout_date_count > len(dates):
        raise ScaledContextFilterExperimentError(
            "train_date_count plus holdout_date_count must not exceed "
            "the number of candidate trade dates",
        )

    split_rows: list[dict[str, Any]] = []
    max_start = len(dates) - train_date_count - holdout_date_count + 1
    for window_index in range(0, max_start, window_step_date_count):
        train_dates = dates[window_index:window_index + train_date_count]
        holdout_dates = dates[
            window_index + train_date_count:
            window_index + train_date_count + holdout_date_count
        ]
        train_sweep = run_scaled_context_filter_sweep(
            _filter_rows_by_dates(rows, train_dates),
            min_minutes_after_rth_open_values=min_minutes_after_rth_open_values,
            max_minutes_after_rth_open_values=max_minutes_after_rth_open_values,
            max_risk_to_average_bar_ranges=max_risk_to_average_bar_ranges,
            max_runner_target_to_average_bar_ranges=max_runner_target_to_average_bar_ranges,
            min_signal_abs_delta_sum_to_average_abs_deltas=(
                min_signal_abs_delta_sum_to_average_abs_deltas
            ),
            max_signal_abs_delta_sum_to_average_abs_deltas=(
                max_signal_abs_delta_sum_to_average_abs_deltas
            ),
            min_entry_volume_to_average_volumes=min_entry_volume_to_average_volumes,
            min_entry_trades_to_average_trades=min_entry_trades_to_average_trades,
            min_continuation_edge_scores=min_continuation_edge_scores,
            min_opening_range_continuation_edge_scores=(
                min_opening_range_continuation_edge_scores
            ),
            min_directional_opening_range_breakout_points_values=(
                min_directional_opening_range_breakout_points_values
            ),
            min_lookback_efficiency_ratios=min_lookback_efficiency_ratios,
            max_lookback_choppiness_scores=max_lookback_choppiness_scores,
            min_entry_volume_to_session_average_volumes=(
                min_entry_volume_to_session_average_volumes
            ),
            min_lookback_volume_to_session_average_volumes=(
                min_lookback_volume_to_session_average_volumes
            ),
            direction_filters=direction_filters,
        )
        best_train = _select_best_train_row(
            train_sweep,
            minimum_train_trades=minimum_train_trades,
            selection_objective=objective,
        )
        holdout_sweep = run_scaled_context_filter_sweep(
            _filter_rows_by_dates(rows, holdout_dates),
            min_minutes_after_rth_open_values=min_minutes_after_rth_open_values,
            max_minutes_after_rth_open_values=max_minutes_after_rth_open_values,
            max_risk_to_average_bar_ranges=max_risk_to_average_bar_ranges,
            max_runner_target_to_average_bar_ranges=max_runner_target_to_average_bar_ranges,
            min_signal_abs_delta_sum_to_average_abs_deltas=(
                min_signal_abs_delta_sum_to_average_abs_deltas
            ),
            max_signal_abs_delta_sum_to_average_abs_deltas=(
                max_signal_abs_delta_sum_to_average_abs_deltas
            ),
            min_entry_volume_to_average_volumes=min_entry_volume_to_average_volumes,
            min_entry_trades_to_average_trades=min_entry_trades_to_average_trades,
            min_continuation_edge_scores=min_continuation_edge_scores,
            min_opening_range_continuation_edge_scores=(
                min_opening_range_continuation_edge_scores
            ),
            min_directional_opening_range_breakout_points_values=(
                min_directional_opening_range_breakout_points_values
            ),
            min_lookback_efficiency_ratios=min_lookback_efficiency_ratios,
            max_lookback_choppiness_scores=max_lookback_choppiness_scores,
            min_entry_volume_to_session_average_volumes=(
                min_entry_volume_to_session_average_volumes
            ),
            min_lookback_volume_to_session_average_volumes=(
                min_lookback_volume_to_session_average_volumes
            ),
            direction_filters=direction_filters,
        )
        matching_holdout = _find_matching_selection_row(holdout_sweep, best_train)
        split_id = (
            f"scaled_context_filter_walk_forward_window={window_index + 1}:"
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
    min_minutes_after_rth_open: float,
    max_minutes_after_rth_open: float,
    max_risk_to_average_bar_range: float,
    max_runner_target_to_average_bar_range: float,
    min_signal_abs_delta_sum_to_average_abs_delta: float,
    max_signal_abs_delta_sum_to_average_abs_delta: float,
    min_entry_volume_to_average_volume: float,
    min_entry_trades_to_average_trades: float,
    min_continuation_edge_score: float,
    min_opening_range_continuation_edge_score: float,
    min_directional_opening_range_breakout_points: float,
    min_lookback_efficiency_ratio: float,
    max_lookback_choppiness_score: float,
    min_entry_volume_to_session_average_volume: float,
    min_lookback_volume_to_session_average_volume: float,
) -> list[dict[str, Any]]:
    filtered_rows: list[dict[str, Any]] = []
    for row in rows:
        direction = str(row["direction"])
        if direction_filter != "all" and direction != direction_filter:
            continue
        minutes = _to_float(row["minutes_after_rth_open"], "minutes_after_rth_open")
        if minutes < min_minutes_after_rth_open or minutes > max_minutes_after_rth_open:
            continue
        if (
            _to_float(row["risk_to_average_bar_range"], "risk_to_average_bar_range")
            > max_risk_to_average_bar_range
        ):
            continue
        if (
            _to_float(
                row["runner_target_to_average_bar_range"],
                "runner_target_to_average_bar_range",
            )
            > max_runner_target_to_average_bar_range
        ):
            continue
        signal_ratio = _to_float(
            row["signal_abs_delta_sum_to_average_abs_delta"],
            "signal_abs_delta_sum_to_average_abs_delta",
        )
        if (
            signal_ratio < min_signal_abs_delta_sum_to_average_abs_delta
            or signal_ratio > max_signal_abs_delta_sum_to_average_abs_delta
        ):
            continue
        if (
            _to_float(row["entry_volume_to_average_volume"], "entry_volume_to_average_volume")
            < min_entry_volume_to_average_volume
        ):
            continue
        if (
            _to_float(row["entry_trades_to_average_trades"], "entry_trades_to_average_trades")
            < min_entry_trades_to_average_trades
        ):
            continue
        if (
            _to_float_or_default(row, "continuation_edge_score", 0.0)
            < min_continuation_edge_score
        ):
            continue
        if (
            _to_float_or_default(row, "opening_range_continuation_edge_score", 0.0)
            < min_opening_range_continuation_edge_score
        ):
            continue
        if (
            _to_float_or_default(row, "directional_opening_range_breakout_points", -999999.0)
            < min_directional_opening_range_breakout_points
        ):
            continue
        if (
            _to_float_or_default(row, "lookback_efficiency_ratio", 0.0)
            < min_lookback_efficiency_ratio
        ):
            continue
        if (
            _to_float_or_default(row, "lookback_choppiness_score", 1.0)
            > max_lookback_choppiness_score
        ):
            continue
        if (
            _to_float_or_default(row, "entry_volume_to_session_average_volume", 0.0)
            < min_entry_volume_to_session_average_volume
        ):
            continue
        if (
            _to_float_or_default(row, "lookback_volume_to_session_average_volume", 0.0)
            < min_lookback_volume_to_session_average_volume
        ):
            continue
        filtered_rows.append(row)
    return filtered_rows


def _experiment_row(
    all_rows: list[dict[str, Any]],
    filtered_rows: list[dict[str, Any]],
    *,
    direction_filter: str,
    min_minutes_after_rth_open: float,
    max_minutes_after_rth_open: float,
    max_risk_to_average_bar_range: float,
    max_runner_target_to_average_bar_range: float,
    min_signal_abs_delta_sum_to_average_abs_delta: float,
    max_signal_abs_delta_sum_to_average_abs_delta: float,
    min_entry_volume_to_average_volume: float,
    min_entry_trades_to_average_trades: float,
    min_continuation_edge_score: float,
    min_opening_range_continuation_edge_score: float,
    min_directional_opening_range_breakout_points: float,
    min_lookback_efficiency_ratio: float,
    max_lookback_choppiness_score: float,
    min_entry_volume_to_session_average_volume: float,
    min_lookback_volume_to_session_average_volume: float,
) -> dict[str, Any]:
    summary = _summary(filtered_rows)
    all_summary = _summary(all_rows)
    direction_counts = Counter(str(row["direction"]) for row in filtered_rows)
    strategy_id = _strategy_id(filtered_rows)
    experiment_id = (
        f"scaled_context_filter:strategy={strategy_id}:"
        f"direction={direction_filter}:"
        f"minutes={_format_number(min_minutes_after_rth_open)}-"
        f"{_format_number(max_minutes_after_rth_open)}:"
        f"max_risk_avg_range={_format_number(max_risk_to_average_bar_range)}:"
        f"max_runner_avg_range={_format_number(max_runner_target_to_average_bar_range)}:"
        f"signal_delta_avg={_format_number(min_signal_abs_delta_sum_to_average_abs_delta)}-"
        f"{_format_number(max_signal_abs_delta_sum_to_average_abs_delta)}:"
        f"min_volume_avg={_format_number(min_entry_volume_to_average_volume)}:"
        f"min_trades_avg={_format_number(min_entry_trades_to_average_trades)}:"
        f"min_cont_edge={_format_number(min_continuation_edge_score)}:"
        f"min_or_cont_edge={_format_number(min_opening_range_continuation_edge_score)}:"
        f"min_or_breakout={_format_number(min_directional_opening_range_breakout_points)}:"
        f"min_efficiency={_format_number(min_lookback_efficiency_ratio)}:"
        f"max_chop={_format_number(max_lookback_choppiness_score)}:"
        f"min_entry_session_volume={_format_number(min_entry_volume_to_session_average_volume)}:"
        f"min_lookback_session_volume={_format_number(min_lookback_volume_to_session_average_volume)}"
    )
    return {
        "schema_version": 1,
        "experiment_id": experiment_id,
        "strategy_id": strategy_id,
        "direction_filter": direction_filter,
        "min_minutes_after_rth_open": _format_number(min_minutes_after_rth_open),
        "max_minutes_after_rth_open": _format_number(max_minutes_after_rth_open),
        "max_risk_to_average_bar_range": _format_number(max_risk_to_average_bar_range),
        "max_runner_target_to_average_bar_range": _format_number(
            max_runner_target_to_average_bar_range,
        ),
        "min_signal_abs_delta_sum_to_average_abs_delta": _format_number(
            min_signal_abs_delta_sum_to_average_abs_delta,
        ),
        "max_signal_abs_delta_sum_to_average_abs_delta": _format_number(
            max_signal_abs_delta_sum_to_average_abs_delta,
        ),
        "min_entry_volume_to_average_volume": _format_number(min_entry_volume_to_average_volume),
        "min_entry_trades_to_average_trades": _format_number(min_entry_trades_to_average_trades),
        "min_continuation_edge_score": _format_number(min_continuation_edge_score),
        "min_opening_range_continuation_edge_score": _format_number(
            min_opening_range_continuation_edge_score,
        ),
        "min_directional_opening_range_breakout_points": _format_number(
            min_directional_opening_range_breakout_points,
        ),
        "min_lookback_efficiency_ratio": _format_number(min_lookback_efficiency_ratio),
        "max_lookback_choppiness_score": _format_number(max_lookback_choppiness_score),
        "min_entry_volume_to_session_average_volume": _format_number(
            min_entry_volume_to_session_average_volume,
        ),
        "min_lookback_volume_to_session_average_volume": _format_number(
            min_lookback_volume_to_session_average_volume,
        ),
        "input_context_rows": len(all_rows),
        "evaluated_trades": summary["total_trades"],
        "runner_target_hits": summary["runner_target_hits"],
        "full_stops": summary["full_stops"],
        "runner_stop_exits": summary["runner_stop_exits"],
        "other_exits": summary["other_exits"],
        "positive_net_trades": summary["positive_net_trades"],
        "positive_net_rate": _format_number(summary["positive_net_rate"]),
        "net_usd": _format_number(summary["net_usd"]),
        "average_net_usd": _format_number(summary["average_net_usd"]),
        "average_net_usd_lower_bound": _format_number(_average_net_lower_bound(filtered_rows)),
        "unfiltered_net_usd": _format_number(all_summary["net_usd"]),
        "participation_rate": _format_number(
            summary["total_trades"] / len(all_rows) if all_rows else 0.0,
        ),
        "filter_net_improvement_usd": _format_number(
            summary["net_usd"] - all_summary["net_usd"],
        ),
        "long_trades": direction_counts.get("long", 0),
        "short_trades": direction_counts.get("short", 0),
        "notes": (
            "scaled context filter sweep; uses only entry-known normalized "
            "volatility, activity, and session-regime fields"
        ),
    }


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    runner_targets = sum(str(row["exit_reason"]) in _RUNNER_TARGET_REASONS for row in rows)
    full_stops = sum(str(row["exit_reason"]) in _FULL_STOP_REASONS for row in rows)
    runner_stops = sum(str(row["exit_reason"]) in _RUNNER_STOP_REASONS for row in rows)
    positive = sum(_to_float(row["net_usd"], "net_usd") > 0 for row in rows)
    net_usd = sum(_to_float(row["net_usd"], "net_usd") for row in rows)
    return {
        "total_trades": total,
        "runner_target_hits": runner_targets,
        "full_stops": full_stops,
        "runner_stop_exits": runner_stops,
        "other_exits": total - runner_targets - full_stops - runner_stops,
        "positive_net_trades": positive,
        "positive_net_rate": positive / total if total else 0.0,
        "net_usd": net_usd,
        "average_net_usd": net_usd / total if total else 0.0,
    }


def _select_best_train_row(
    rows: list[dict[str, Any]],
    *,
    minimum_train_trades: int,
    selection_objective: str,
) -> dict[str, Any]:
    eligible_rows = [
        row
        for row in rows
        if int(row["evaluated_trades"]) >= minimum_train_trades
    ]
    if not eligible_rows:
        raise ScaledContextFilterExperimentError(
            f"No train experiments met minimum_train_trades={minimum_train_trades}",
        )
    if selection_objective == "net":
        return max(
            eligible_rows,
            key=lambda row: (
                float(row["net_usd"]),
                float(row["positive_net_rate"]),
                int(row["evaluated_trades"]),
            ),
        )
    if selection_objective == "efficiency":
        return max(
            eligible_rows,
            key=lambda row: (
                float(row["average_net_usd_lower_bound"]),
                float(row["filter_net_improvement_usd"]),
                float(row["average_net_usd"]),
                float(row["positive_net_rate"]),
                int(row["evaluated_trades"]),
            ),
        )
    raise ScaledContextFilterExperimentError(
        f"Unsupported selection_objective: {selection_objective}",
    )


def _find_matching_selection_row(
    rows: list[dict[str, Any]],
    selected_row: dict[str, Any],
) -> dict[str, Any]:
    selected_key = _selection_key(selected_row)
    for row in rows:
        if _selection_key(row) == selected_key:
            return row
    raise ScaledContextFilterExperimentError(
        "Missing matching holdout scaled context filter row for "
        f"selection_key={selected_key}",
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
            for key in SCALED_CONTEXT_FILTER_SWEEP_HEADER
            if key != "schema_version"
        },
    )
    return tagged


def _selection_key(row: dict[str, Any]) -> tuple[str, ...]:
    return (
        str(row["direction_filter"]),
        str(row["min_minutes_after_rth_open"]),
        str(row["max_minutes_after_rth_open"]),
        str(row["max_risk_to_average_bar_range"]),
        str(row["max_runner_target_to_average_bar_range"]),
        str(row["min_signal_abs_delta_sum_to_average_abs_delta"]),
        str(row["max_signal_abs_delta_sum_to_average_abs_delta"]),
        str(row["min_entry_volume_to_average_volume"]),
        str(row["min_entry_trades_to_average_trades"]),
        str(row["min_continuation_edge_score"]),
        str(row["min_opening_range_continuation_edge_score"]),
        str(row["min_directional_opening_range_breakout_points"]),
        str(row["min_lookback_efficiency_ratio"]),
        str(row["max_lookback_choppiness_score"]),
        str(row["min_entry_volume_to_session_average_volume"]),
        str(row["min_lookback_volume_to_session_average_volume"]),
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
    raise ScaledContextFilterExperimentError(f"Invalid timestamp: {value!r}")


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
        raise ScaledContextFilterExperimentError(
            "At least one min/max minute window must be valid",
        )
    return windows


def _normalize_positive_grid(values: Iterable[float], field_name: str) -> list[float]:
    grid = [float(value) for value in values]
    if not grid:
        raise ScaledContextFilterExperimentError(f"{field_name} must contain at least one value")
    if any(value <= 0 for value in grid):
        raise ScaledContextFilterExperimentError(f"{field_name} values must be positive")
    return grid


def _normalize_nonnegative_grid(values: Iterable[float], field_name: str) -> list[float]:
    grid = [float(value) for value in values]
    if not grid:
        raise ScaledContextFilterExperimentError(f"{field_name} must contain at least one value")
    if any(value < 0 for value in grid):
        raise ScaledContextFilterExperimentError(f"{field_name} values must be nonnegative")
    return grid


def _normalize_float_grid(values: Iterable[float], field_name: str) -> list[float]:
    grid = [float(value) for value in values]
    if not grid:
        raise ScaledContextFilterExperimentError(f"{field_name} must contain at least one value")
    return grid


def _normalize_zero_to_one_grid(values: Iterable[float], field_name: str) -> list[float]:
    grid = _normalize_float_grid(values, field_name)
    if any(value < 0 or value > 1 for value in grid):
        raise ScaledContextFilterExperimentError(
            f"{field_name} values must be between 0 and 1",
        )
    return grid


def _normalize_direction_filters(values: Iterable[str]) -> list[str]:
    filters = [str(value).strip().lower() for value in values if str(value).strip()]
    if not filters:
        raise ScaledContextFilterExperimentError(
            "direction_filters must contain at least one value",
        )
    invalid = [value for value in filters if value not in _ALLOWED_DIRECTION_FILTERS]
    if invalid:
        raise ScaledContextFilterExperimentError(
            "direction_filters contains unsupported values: " + ", ".join(invalid),
        )
    return filters


def _normalize_selection_objective(value: str) -> str:
    objective = str(value).strip().lower()
    if objective not in _ALLOWED_SELECTION_OBJECTIVES:
        raise ScaledContextFilterExperimentError(
            "selection_objective must be one of: "
            + ", ".join(_ALLOWED_SELECTION_OBJECTIVES),
        )
    return objective


def _to_float(value: Any, field_name: str) -> float:
    try:
        return float(str(value))
    except ValueError as exc:
        raise ScaledContextFilterExperimentError(
            f"Invalid numeric field {field_name}: {value!r}",
        ) from exc


def _to_float_or_default(row: dict[str, Any], field_name: str, default: float) -> float:
    value = row.get(field_name)
    if value is None or str(value).strip() == "":
        return default
    return _to_float(value, field_name)


def _average_net_lower_bound(rows: list[dict[str, Any]]) -> float:
    values = [_to_float(row["net_usd"], "net_usd") for row in rows]
    if not values:
        return 0.0
    average = sum(values) / len(values)
    if len(values) == 1:
        return average
    return average - pstdev(values) / sqrt(len(values))


def _format_number(value: Any) -> str:
    return f"{float(value):.8f}".rstrip("0").rstrip(".")
