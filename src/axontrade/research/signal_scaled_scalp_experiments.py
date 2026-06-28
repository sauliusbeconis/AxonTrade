"""Scaled two-contract scalp exit experiments for logged signal rows."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from itertools import product
from typing import Any, Iterable

from axontrade.research.trade_outcomes import (
    OutcomeBar,
    OutcomeCosts,
    _bars_by_symbol,
    _following_bars_for_signal,
    _format_number,
    _gross_points,
    _load_outcome_costs,
    _normalize_bar,
    _parse_timestamp,
    _to_float,
    _to_int,
)


SIGNAL_SCALED_SCALP_SWEEP_HEADER = [
    "schema_version",
    "experiment_id",
    "strategy_id",
    "direction_filter",
    "first_target_points",
    "stop_points",
    "runner_target_points",
    "runner_stop_mode",
    "input_signal_rows",
    "input_candidates",
    "evaluated_trades",
    "full_stops",
    "first_target_hits",
    "runner_target_hits",
    "runner_stop_exits",
    "end_of_session_exits",
    "other_exits",
    "positive_net_trades",
    "positive_net_rate",
    "gross_usd",
    "net_usd",
    "average_net_usd",
    "long_trades",
    "short_trades",
    "notes",
]
SIGNAL_SCALED_SCALP_WALK_FORWARD_HEADER = [
    "schema_version",
    "split_id",
    "sample",
    "selected_on_train",
    "trade_dates",
    *SIGNAL_SCALED_SCALP_SWEEP_HEADER[1:],
]
_TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
)
_ALLOWED_DIRECTION_FILTERS = ("all", "long", "short")
_ALLOWED_RUNNER_STOP_MODES = ("initial", "breakeven")
_FULL_STOP_REASONS = {"full_stop_hit", "ambiguous_full_stop_first"}
_RUNNER_STOP_REASONS = {
    "runner_initial_stop_hit",
    "runner_breakeven_stop_hit",
    "ambiguous_runner_stop_first",
}
_RUNNER_TARGET_REASONS = {"runner_target_hit"}
_END_OF_SESSION_REASONS = {"end_of_session", "no_following_bar"}


class SignalScaledScalpExperimentError(ValueError):
    """Raised when a scaled scalp experiment cannot be evaluated."""


@dataclass(frozen=True)
class _PreparedScaledScalpSignal:
    signal: dict[str, Any]
    symbol: str
    direction: str
    entry_bar_index: int
    entry_time: str
    entry_timestamp: datetime
    entry_price: float
    following_bars: list[OutcomeBar]
    resolved_match_mode: str


def evaluate_signal_scaled_scalp_outcomes(
    bars: Iterable[dict[str, Any]],
    signal_rows: Iterable[dict[str, Any]],
    *,
    first_target_points: float,
    stop_points: float,
    runner_target_points: float,
    runner_stop_mode: str = "breakeven",
    direction_filter: str = "all",
    instrument_root: str | None = None,
    slippage_ticks_per_side: int | None = None,
    slippage_ticks_per_contract: float | None = None,
    entry_match_mode: str = "auto",
) -> list[dict[str, Any]]:
    """Evaluate logged candidates as a two-contract scalp with one runner."""

    if entry_match_mode not in {"bar_index", "timestamp", "auto"}:
        raise SignalScaledScalpExperimentError(
            "entry_match_mode must be one of: bar_index, timestamp, auto",
        )
    first_target = _normalize_positive_value(first_target_points, "first_target_points")
    stop = _normalize_positive_value(stop_points, "stop_points")
    runner_target = _normalize_positive_value(runner_target_points, "runner_target_points")
    if runner_target <= first_target:
        raise SignalScaledScalpExperimentError(
            "runner_target_points must be greater than first_target_points",
        )
    runner_mode = _normalize_runner_stop_mode(runner_stop_mode)
    direction = _normalize_direction_filter(direction_filter)
    slippage_ticks = _normalize_optional_nonnegative_value(
        slippage_ticks_per_contract,
        "slippage_ticks_per_contract",
    )

    normalized_bars = _normalize_bars(bars)
    candidate_signals = _candidate_signals(list(signal_rows), direction_filter=direction)
    if not candidate_signals:
        return []

    costs = _load_outcome_costs(
        candidate_signals,
        instrument_root=instrument_root,
        slippage_ticks_per_side=slippage_ticks_per_side,
        cost_config=None,
        instrument_config=None,
    )
    bars_by_symbol = _bars_by_symbol(normalized_bars)
    prepared_signals = _prepare_scaled_scalp_signal_contexts(
        candidate_signals,
        bars_by_symbol,
        entry_match_mode=entry_match_mode,
    )
    return _evaluate_prepared_scaled_scalp_contexts(
        prepared_signals,
        costs,
        first_target_points=first_target,
        stop_points=stop,
        runner_target_points=runner_target,
        runner_stop_mode=runner_mode,
        slippage_ticks_per_contract=slippage_ticks,
    )


def run_signal_scaled_scalp_sweep(
    bars: Iterable[dict[str, Any]],
    signal_rows: Iterable[dict[str, Any]],
    *,
    first_target_points_values: Iterable[float],
    stop_points_values: Iterable[float],
    runner_target_points_values: Iterable[float],
    runner_stop_modes: Iterable[str] = ("breakeven",),
    direction_filters: Iterable[str] = ("all",),
    instrument_root: str | None = None,
    slippage_ticks_per_side: int | None = None,
    slippage_ticks_per_contract: float | None = None,
    entry_match_mode: str = "auto",
) -> list[dict[str, Any]]:
    """Sweep two-contract scalp exit parameters over logged candidates."""

    normalized_bars = _normalize_bars(bars)
    rows = list(signal_rows)
    parameter_sets = _valid_parameter_sets(
        first_target_points_values,
        stop_points_values,
        runner_target_points_values,
        runner_stop_modes,
    )
    directions = _normalize_direction_filters(direction_filters)
    slippage_ticks = _normalize_optional_nonnegative_value(
        slippage_ticks_per_contract,
        "slippage_ticks_per_contract",
    )
    all_candidates = _candidate_signals(rows, direction_filter="all")
    candidate_signals_by_direction = {
        direction: _candidate_signals(rows, direction_filter=direction)
        for direction in directions
    }
    costs = (
        _load_outcome_costs(
            all_candidates,
            instrument_root=instrument_root,
            slippage_ticks_per_side=slippage_ticks_per_side,
            cost_config=None,
            instrument_config=None,
        )
        if all_candidates
        else None
    )
    bars_by_symbol = _bars_by_symbol(normalized_bars)
    all_contexts = _prepare_scaled_scalp_signal_contexts(
        all_candidates,
        bars_by_symbol,
        entry_match_mode=entry_match_mode,
    )
    contexts_by_direction = {
        "all": all_contexts,
        "long": [context for context in all_contexts if context.direction == "long"],
        "short": [context for context in all_contexts if context.direction == "short"],
    }

    experiment_rows: list[dict[str, Any]] = []
    for (first_target, stop, runner_target, runner_mode), direction_filter in product(
        parameter_sets,
        directions,
    ):
        selected_candidates = candidate_signals_by_direction[direction_filter]
        outcomes = (
            _evaluate_prepared_scaled_scalp_contexts(
                contexts_by_direction[direction_filter],
                costs,
                first_target_points=first_target,
                stop_points=stop,
                runner_target_points=runner_target,
                runner_stop_mode=runner_mode,
                slippage_ticks_per_contract=slippage_ticks,
            )
            if selected_candidates and costs is not None
            else []
        )
        experiment_rows.append(
            _experiment_row(
                rows,
                outcomes,
                first_target_points=first_target,
                stop_points=stop,
                runner_target_points=runner_target,
                runner_stop_mode=runner_mode,
                direction_filter=direction_filter,
            ),
        )
    return experiment_rows


def run_signal_scaled_scalp_walk_forward_sweep(
    bars: Iterable[dict[str, Any]],
    signal_rows: Iterable[dict[str, Any]],
    *,
    train_date_count: int,
    holdout_date_count: int,
    first_target_points_values: Iterable[float],
    stop_points_values: Iterable[float],
    runner_target_points_values: Iterable[float],
    runner_stop_modes: Iterable[str] = ("breakeven",),
    direction_filters: Iterable[str] = ("all",),
    minimum_train_trades: int = 1,
    instrument_root: str | None = None,
    slippage_ticks_per_side: int | None = None,
    slippage_ticks_per_contract: float | None = None,
    entry_match_mode: str = "auto",
) -> list[dict[str, Any]]:
    """Run rolling selection of two-contract scalp exit parameters."""

    normalized_bars = _normalize_bars(bars)
    rows = list(signal_rows)
    dates = _sorted_candidate_dates(rows)
    if train_date_count <= 0:
        raise SignalScaledScalpExperimentError("train_date_count must be positive")
    if holdout_date_count <= 0:
        raise SignalScaledScalpExperimentError("holdout_date_count must be positive")
    if minimum_train_trades <= 0:
        raise SignalScaledScalpExperimentError("minimum_train_trades must be positive")
    if train_date_count + holdout_date_count > len(dates):
        raise SignalScaledScalpExperimentError(
            "train_date_count plus holdout_date_count must not exceed "
            "the number of candidate trade dates",
        )

    first_targets = _normalize_positive_grid(
        first_target_points_values,
        "first_target_points_values",
    )
    stops = _normalize_positive_grid(stop_points_values, "stop_points_values")
    runner_targets = _normalize_positive_grid(
        runner_target_points_values,
        "runner_target_points_values",
    )
    runner_modes = _normalize_runner_stop_modes(runner_stop_modes)
    directions = _normalize_direction_filters(direction_filters)
    slippage_ticks = _normalize_optional_nonnegative_value(
        slippage_ticks_per_contract,
        "slippage_ticks_per_contract",
    )
    split_rows: list[dict[str, Any]] = []
    max_start = len(dates) - train_date_count - holdout_date_count + 1
    for window_index in range(max_start):
        train_dates = dates[window_index:window_index + train_date_count]
        holdout_dates = dates[
            window_index + train_date_count:
            window_index + train_date_count + holdout_date_count
        ]
        train_sweep = run_signal_scaled_scalp_sweep(
            _filter_bars_by_dates(normalized_bars, train_dates),
            _filter_signal_rows_by_dates(rows, train_dates),
            first_target_points_values=first_targets,
            stop_points_values=stops,
            runner_target_points_values=runner_targets,
            runner_stop_modes=runner_modes,
            direction_filters=directions,
            instrument_root=instrument_root,
            slippage_ticks_per_side=slippage_ticks_per_side,
            slippage_ticks_per_contract=slippage_ticks,
            entry_match_mode=entry_match_mode,
        )
        best_train = _select_best_train_row(
            train_sweep,
            minimum_train_trades=minimum_train_trades,
        )
        holdout_sweep = run_signal_scaled_scalp_sweep(
            _filter_bars_by_dates(normalized_bars, holdout_dates),
            _filter_signal_rows_by_dates(rows, holdout_dates),
            first_target_points_values=first_targets,
            stop_points_values=stops,
            runner_target_points_values=runner_targets,
            runner_stop_modes=runner_modes,
            direction_filters=directions,
            instrument_root=instrument_root,
            slippage_ticks_per_side=slippage_ticks_per_side,
            slippage_ticks_per_contract=slippage_ticks,
            entry_match_mode=entry_match_mode,
        )
        matching_holdout = _find_matching_selection_row(holdout_sweep, best_train)
        split_id = (
            f"scaled_scalp_walk_forward_window={window_index + 1}:"
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


def _evaluate_one_signal_with_scaled_scalp(
    signal: dict[str, Any],
    bars_by_symbol: dict[str, list[OutcomeBar]],
    costs: OutcomeCosts,
    *,
    first_target_points: float,
    stop_points: float,
    runner_target_points: float,
    runner_stop_mode: str,
    entry_match_mode: str,
    slippage_ticks_per_contract: float | None = None,
) -> dict[str, Any]:
    context = _prepare_one_scaled_scalp_signal_context(
        signal,
        bars_by_symbol,
        entry_match_mode=entry_match_mode,
    )
    return _evaluate_prepared_scaled_scalp_context(
        context,
        costs,
        first_target_points=first_target_points,
        stop_points=stop_points,
        runner_target_points=runner_target_points,
        runner_stop_mode=runner_stop_mode,
        slippage_ticks_per_contract=slippage_ticks_per_contract,
    )


def _evaluate_prepared_scaled_scalp_context(
    context: _PreparedScaledScalpSignal,
    costs: OutcomeCosts,
    *,
    first_target_points: float,
    stop_points: float,
    runner_target_points: float,
    runner_stop_mode: str,
    slippage_ticks_per_contract: float | None,
) -> dict[str, Any]:
    stop_price = _price_at_offset(
        context.direction,
        entry_price=context.entry_price,
        points=-stop_points,
    )
    first_target_price = _price_at_offset(
        context.direction,
        entry_price=context.entry_price,
        points=first_target_points,
    )
    runner_target_price = _price_at_offset(
        context.direction,
        entry_price=context.entry_price,
        points=runner_target_points,
    )

    exit_bar, leg1_exit_price, runner_exit_price, exit_reason, first_hit = (
        _find_scaled_scalp_exit(
            context.following_bars,
            direction=context.direction,
            entry_price=context.entry_price,
            stop_price=stop_price,
            first_target_price=first_target_price,
            runner_target_price=runner_target_price,
            runner_stop_mode=runner_stop_mode,
        )
    )
    exit_bar_index = (
        exit_bar.bar_index
        if exit_bar is not None
        else context.entry_bar_index
    )
    exit_time = exit_bar.timestamp if exit_bar is not None else context.entry_time
    if context.resolved_match_mode == "timestamp" and exit_bar is not None:
        holding_bars = context.following_bars.index(exit_bar) + 1
    else:
        holding_bars = max(0, exit_bar_index - context.entry_bar_index)

    leg1_points = _gross_points(context.direction, context.entry_price, leg1_exit_price)
    runner_points = _gross_points(
        context.direction,
        context.entry_price,
        runner_exit_price,
    )
    gross_points = leg1_points + runner_points
    gross_usd = gross_points * costs.point_value_usd
    commission_usd = costs.commission_round_turn_usd * 2
    slippage_usd = _scaled_scalp_slippage_usd(
        costs,
        contract_count=2,
        slippage_ticks_per_contract=slippage_ticks_per_contract,
    )
    net_usd = gross_usd - commission_usd - slippage_usd

    signal = context.signal
    outcome_id = f"{signal['signal_id']}:{exit_reason}:{exit_bar_index}"
    return {
        "schema_version": 1,
        "outcome_id": outcome_id,
        "event_key": signal["event_key"],
        "signal_id": signal["signal_id"],
        "symbol": context.symbol,
        "direction": context.direction,
        "entry_bar_index": context.entry_bar_index,
        "exit_bar_index": exit_bar_index,
        "entry_time": context.entry_time,
        "exit_time": exit_time,
        "entry_price": _format_number(context.entry_price),
        "stop_price": _format_number(stop_price),
        "first_target_price": _format_number(first_target_price),
        "runner_target_price": _format_number(runner_target_price),
        "leg1_exit_price": _format_number(leg1_exit_price),
        "runner_exit_price": _format_number(runner_exit_price),
        "exit_reason": exit_reason,
        "first_target_hit": str(first_hit).lower(),
        "holding_bars": holding_bars,
        "gross_points": _format_number(gross_points),
        "gross_usd": _format_number(gross_usd),
        "commission_usd": _format_number(commission_usd),
        "slippage_usd": _format_number(slippage_usd),
        "net_usd": _format_number(net_usd),
        "notes": (
            f"{costs.instrument_root} two-contract scaled scalp; "
            f"first_target_points={_format_number(first_target_points)}; "
            f"stop_points={_format_number(stop_points)}; "
            f"runner_target_points={_format_number(runner_target_points)}; "
            f"runner_stop_mode={runner_stop_mode}; "
            f"slippage_ticks_per_contract="
            f"{_format_optional_number(slippage_ticks_per_contract)}; "
            f"entry_match_mode={context.resolved_match_mode}"
        ),
    }


def _evaluate_prepared_scaled_scalp_contexts(
    prepared_signals: list[_PreparedScaledScalpSignal],
    costs: OutcomeCosts,
    *,
    first_target_points: float,
    stop_points: float,
    runner_target_points: float,
    runner_stop_mode: str,
    slippage_ticks_per_contract: float | None,
) -> list[dict[str, Any]]:
    return [
        _evaluate_prepared_scaled_scalp_context(
            context,
            costs,
            first_target_points=first_target_points,
            stop_points=stop_points,
            runner_target_points=runner_target_points,
            runner_stop_mode=runner_stop_mode,
            slippage_ticks_per_contract=slippage_ticks_per_contract,
        )
        for context in prepared_signals
    ]


def _prepare_scaled_scalp_signal_contexts(
    candidate_signals: list[dict[str, Any]],
    bars_by_symbol: dict[str, list[OutcomeBar]],
    *,
    entry_match_mode: str,
) -> list[_PreparedScaledScalpSignal]:
    return [
        _prepare_one_scaled_scalp_signal_context(
            signal,
            bars_by_symbol,
            entry_match_mode=entry_match_mode,
        )
        for signal in candidate_signals
    ]


def _prepare_one_scaled_scalp_signal_context(
    signal: dict[str, Any],
    bars_by_symbol: dict[str, list[OutcomeBar]],
    *,
    entry_match_mode: str,
) -> _PreparedScaledScalpSignal:
    symbol = str(signal.get("symbol", ""))
    direction = str(signal.get("direction", ""))
    if direction not in {"long", "short"}:
        raise SignalScaledScalpExperimentError(
            f"Unsupported candidate direction: {direction!r}",
        )

    entry_bar_index = _to_int(signal.get("bar_index"), "bar_index")
    entry_time = str(signal.get("bar_start_time") or signal.get("generated_at") or "")
    entry_timestamp = _parse_timestamp(entry_time)
    following_bars, resolved_match_mode = _following_bars_for_signal(
        bars_by_symbol.get(symbol, []),
        entry_bar_index=entry_bar_index,
        entry_timestamp=entry_timestamp,
        entry_match_mode=entry_match_mode,
    )
    return _PreparedScaledScalpSignal(
        signal=signal,
        symbol=symbol,
        direction=direction,
        entry_bar_index=entry_bar_index,
        entry_time=entry_time,
        entry_timestamp=entry_timestamp,
        entry_price=_to_float(signal.get("signal_price"), "signal_price"),
        following_bars=following_bars,
        resolved_match_mode=resolved_match_mode,
    )


def _find_scaled_scalp_exit(
    bars: list[OutcomeBar],
    *,
    direction: str,
    entry_price: float,
    stop_price: float,
    first_target_price: float,
    runner_target_price: float,
    runner_stop_mode: str,
) -> tuple[OutcomeBar | None, float, float, str, bool]:
    if not bars:
        return None, entry_price, entry_price, "no_following_bar", False

    first_target_hit = False
    leg1_exit_price = entry_price
    runner_stop_price = stop_price
    for bar in bars:
        if not first_target_hit:
            stop_hit = _stop_hit(direction, bar, stop_price)
            first_hit = _target_hit(direction, bar, first_target_price)
            if stop_hit and first_hit:
                return bar, stop_price, stop_price, "ambiguous_full_stop_first", False
            if stop_hit:
                return bar, stop_price, stop_price, "full_stop_hit", False
            if first_hit:
                first_target_hit = True
                leg1_exit_price = first_target_price
                runner_stop_price = (
                    entry_price
                    if runner_stop_mode == "breakeven"
                    else stop_price
                )
                runner_exit = _runner_exit_in_bar(
                    bar,
                    direction=direction,
                    runner_stop_price=runner_stop_price,
                    runner_target_price=runner_target_price,
                    runner_stop_mode=runner_stop_mode,
                )
                if runner_exit is not None:
                    runner_exit_price, exit_reason = runner_exit
                    return bar, leg1_exit_price, runner_exit_price, exit_reason, True
                continue

        runner_exit = _runner_exit_in_bar(
            bar,
            direction=direction,
            runner_stop_price=runner_stop_price,
            runner_target_price=runner_target_price,
            runner_stop_mode=runner_stop_mode,
        )
        if runner_exit is not None:
            runner_exit_price, exit_reason = runner_exit
            return bar, leg1_exit_price, runner_exit_price, exit_reason, True

    final_bar = bars[-1]
    final_price = final_bar.close
    if first_target_hit:
        return final_bar, leg1_exit_price, final_price, "end_of_session", True
    return final_bar, final_price, final_price, "end_of_session", False


def _runner_exit_in_bar(
    bar: OutcomeBar,
    *,
    direction: str,
    runner_stop_price: float,
    runner_target_price: float,
    runner_stop_mode: str,
) -> tuple[float, str] | None:
    stop_hit = _stop_hit(direction, bar, runner_stop_price)
    target_hit = _target_hit(direction, bar, runner_target_price)
    if stop_hit and target_hit:
        return runner_stop_price, "ambiguous_runner_stop_first"
    if stop_hit:
        if runner_stop_mode == "breakeven":
            return runner_stop_price, "runner_breakeven_stop_hit"
        return runner_stop_price, "runner_initial_stop_hit"
    if target_hit:
        return runner_target_price, "runner_target_hit"
    return None


def _price_at_offset(direction: str, *, entry_price: float, points: float) -> float:
    if direction == "long":
        return entry_price + points
    if direction == "short":
        return entry_price - points
    raise SignalScaledScalpExperimentError(f"Unsupported candidate direction: {direction!r}")


def _stop_hit(direction: str, bar: OutcomeBar, stop_price: float) -> bool:
    if direction == "long":
        return bar.low <= stop_price
    return bar.high >= stop_price


def _target_hit(direction: str, bar: OutcomeBar, target_price: float) -> bool:
    if direction == "long":
        return bar.high >= target_price
    return bar.low <= target_price


def _candidate_signals(
    signal_rows: list[dict[str, Any]],
    *,
    direction_filter: str,
) -> list[dict[str, Any]]:
    candidates = [
        row
        for row in signal_rows
        if str(row.get("event_type", "")) == "candidate_signal"
    ]
    if direction_filter == "all":
        return candidates
    return [row for row in candidates if str(row.get("direction", "")) == direction_filter]


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
        raise SignalScaledScalpExperimentError(
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
    raise SignalScaledScalpExperimentError(
        "Missing matching holdout scaled scalp row for "
        f"selection={selected_key}",
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
            for key in SIGNAL_SCALED_SCALP_SWEEP_HEADER
            if key != "schema_version"
        },
    )
    return tagged


def _selection_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        str(row["direction_filter"]),
        str(row["first_target_points"]),
        str(row["stop_points"]),
        str(row["runner_target_points"]),
        str(row["runner_stop_mode"]),
    )


def _experiment_row(
    all_signal_rows: list[dict[str, Any]],
    outcome_rows: list[dict[str, Any]],
    *,
    first_target_points: float,
    stop_points: float,
    runner_target_points: float,
    runner_stop_mode: str,
    direction_filter: str,
) -> dict[str, Any]:
    summary = _scaled_scalp_outcome_summary(outcome_rows)
    direction_counts = Counter(str(row["direction"]) for row in outcome_rows)
    candidate_rows = _candidate_signals(
        all_signal_rows,
        direction_filter=direction_filter,
    )
    strategy_id = _strategy_id(candidate_rows)
    experiment_id = (
        f"signal_scaled_scalp:strategy={strategy_id}:"
        f"direction={direction_filter}:"
        f"first_target_points={_format_number(first_target_points)}:"
        f"stop_points={_format_number(stop_points)}:"
        f"runner_target_points={_format_number(runner_target_points)}:"
        f"runner_stop_mode={runner_stop_mode}"
    )
    return {
        "schema_version": 1,
        "experiment_id": experiment_id,
        "strategy_id": strategy_id,
        "direction_filter": direction_filter,
        "first_target_points": _format_number(first_target_points),
        "stop_points": _format_number(stop_points),
        "runner_target_points": _format_number(runner_target_points),
        "runner_stop_mode": runner_stop_mode,
        "input_signal_rows": len(all_signal_rows),
        "input_candidates": len(candidate_rows),
        "evaluated_trades": summary["total_trades"],
        "full_stops": summary["full_stops"],
        "first_target_hits": summary["first_target_hits"],
        "runner_target_hits": summary["runner_target_hits"],
        "runner_stop_exits": summary["runner_stop_exits"],
        "end_of_session_exits": summary["end_of_session_exits"],
        "other_exits": summary["other_exits"],
        "positive_net_trades": summary["positive_net_trades"],
        "positive_net_rate": _format_number(summary["positive_net_rate"]),
        "gross_usd": _format_number(summary["gross_usd"]),
        "net_usd": _format_number(summary["net_usd"]),
        "average_net_usd": _format_number(summary["average_net_usd"]),
        "long_trades": direction_counts.get("long", 0),
        "short_trades": direction_counts.get("short", 0),
        "notes": (
            "two-contract post-signal scalp: one contract exits at first target, "
            "one runner uses selected stop mode and runner target"
        ),
    }


def _scaled_scalp_outcome_summary(outcomes: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(outcomes)
    full_stops = sum(row["exit_reason"] in _FULL_STOP_REASONS for row in outcomes)
    first_target_hits = sum(str(row["first_target_hit"]).lower() == "true" for row in outcomes)
    runner_target_hits = sum(row["exit_reason"] in _RUNNER_TARGET_REASONS for row in outcomes)
    runner_stop_exits = sum(row["exit_reason"] in _RUNNER_STOP_REASONS for row in outcomes)
    end_of_session_exits = sum(row["exit_reason"] in _END_OF_SESSION_REASONS for row in outcomes)
    positive_net_trades = sum(_to_float(row["net_usd"], "net_usd") > 0 for row in outcomes)
    gross_usd = sum(_to_float(row["gross_usd"], "gross_usd") for row in outcomes)
    net_usd = sum(_to_float(row["net_usd"], "net_usd") for row in outcomes)
    known_exits = full_stops + runner_target_hits + runner_stop_exits + end_of_session_exits
    return {
        "total_trades": total,
        "full_stops": full_stops,
        "first_target_hits": first_target_hits,
        "runner_target_hits": runner_target_hits,
        "runner_stop_exits": runner_stop_exits,
        "end_of_session_exits": end_of_session_exits,
        "other_exits": total - known_exits,
        "positive_net_trades": positive_net_trades,
        "positive_net_rate": positive_net_trades / total if total else 0.0,
        "gross_usd": gross_usd,
        "net_usd": net_usd,
        "average_net_usd": net_usd / total if total else 0.0,
    }


def _scaled_scalp_slippage_usd(
    costs: OutcomeCosts,
    *,
    contract_count: int,
    slippage_ticks_per_contract: float | None,
) -> float:
    if slippage_ticks_per_contract is None:
        return costs.slippage_round_turn_usd * contract_count
    return slippage_ticks_per_contract * costs.tick_value_usd * contract_count


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
    bars: list[dict[str, Any] | OutcomeBar],
    dates: list[str],
) -> list[dict[str, Any] | OutcomeBar]:
    allowed_dates = set(dates)
    return [
        row
        for row in bars
        if _bar_trade_date(row) in allowed_dates
    ]


def _normalize_bars(bars: Iterable[dict[str, Any] | OutcomeBar]) -> list[OutcomeBar]:
    return [
        row if isinstance(row, OutcomeBar) else _normalize_bar(row)
        for row in bars
    ]


def _bar_trade_date(row: dict[str, Any] | OutcomeBar) -> str:
    if isinstance(row, OutcomeBar):
        return row.parsed_timestamp.date().isoformat()
    return _parse_trade_date(str(row["timestamp"]))


def _parse_trade_date(value: str) -> str:
    timestamp_text = _normalize_timestamp_text(value.strip())
    for timestamp_format in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(timestamp_text, timestamp_format).date().isoformat()
        except ValueError:
            continue
    raise SignalScaledScalpExperimentError(f"Invalid timestamp: {value!r}")


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


def _valid_parameter_sets(
    first_target_points_values: Iterable[float],
    stop_points_values: Iterable[float],
    runner_target_points_values: Iterable[float],
    runner_stop_modes: Iterable[str],
) -> list[tuple[float, float, float, str]]:
    first_targets = _normalize_positive_grid(
        first_target_points_values,
        "first_target_points_values",
    )
    stops = _normalize_positive_grid(stop_points_values, "stop_points_values")
    runner_targets = _normalize_positive_grid(
        runner_target_points_values,
        "runner_target_points_values",
    )
    runner_modes = _normalize_runner_stop_modes(runner_stop_modes)
    parameter_sets = [
        (first_target, stop, runner_target, runner_mode)
        for first_target, stop, runner_target, runner_mode in product(
            first_targets,
            stops,
            runner_targets,
            runner_modes,
        )
        if runner_target > first_target
    ]
    if not parameter_sets:
        raise SignalScaledScalpExperimentError(
            "runner_target_points_values must include values above first_target_points_values",
        )
    return parameter_sets


def _normalize_positive_value(value: float, field_name: str) -> float:
    numeric_value = float(value)
    if numeric_value <= 0:
        raise SignalScaledScalpExperimentError(f"{field_name} must be positive")
    return numeric_value


def _normalize_positive_grid(values: Iterable[float], field_name: str) -> list[float]:
    grid = [float(value) for value in values]
    if not grid:
        raise SignalScaledScalpExperimentError(f"{field_name} must contain at least one value")
    if any(value <= 0 for value in grid):
        raise SignalScaledScalpExperimentError(f"{field_name} values must be positive")
    return grid


def _normalize_optional_nonnegative_value(
    value: float | None,
    field_name: str,
) -> float | None:
    if value is None:
        return None
    numeric_value = float(value)
    if numeric_value < 0:
        raise SignalScaledScalpExperimentError(f"{field_name} must be nonnegative")
    return numeric_value


def _normalize_direction_filter(value: str) -> str:
    direction = value.strip().lower()
    if direction not in _ALLOWED_DIRECTION_FILTERS:
        raise SignalScaledScalpExperimentError(
            "direction_filter must be one of: " + ", ".join(_ALLOWED_DIRECTION_FILTERS),
        )
    return direction


def _normalize_direction_filters(values: Iterable[str]) -> list[str]:
    filters = [str(value).strip().lower() for value in values if str(value).strip()]
    if not filters:
        raise SignalScaledScalpExperimentError("direction_filters must contain at least one value")
    invalid = [value for value in filters if value not in _ALLOWED_DIRECTION_FILTERS]
    if invalid:
        raise SignalScaledScalpExperimentError(
            "direction_filters contains unsupported values: " + ", ".join(invalid),
        )
    return filters


def _normalize_runner_stop_mode(value: str) -> str:
    mode = value.strip().lower()
    if mode not in _ALLOWED_RUNNER_STOP_MODES:
        raise SignalScaledScalpExperimentError(
            "runner_stop_mode must be one of: " + ", ".join(_ALLOWED_RUNNER_STOP_MODES),
        )
    return mode


def _normalize_runner_stop_modes(values: Iterable[str]) -> list[str]:
    modes = [str(value).strip().lower() for value in values if str(value).strip()]
    if not modes:
        raise SignalScaledScalpExperimentError("runner_stop_modes must contain at least one value")
    invalid = [value for value in modes if value not in _ALLOWED_RUNNER_STOP_MODES]
    if invalid:
        raise SignalScaledScalpExperimentError(
            "runner_stop_modes contains unsupported values: " + ", ".join(invalid),
        )
    return modes


def _format_optional_number(value: float | None) -> str:
    if value is None:
        return "round_turn_default"
    return _format_number(value)
