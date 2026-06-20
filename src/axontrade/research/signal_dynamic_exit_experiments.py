"""Dynamic exit experiments for logged signal rows."""

from __future__ import annotations

from collections import Counter
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


SIGNAL_BREAKEVEN_STOP_SWEEP_HEADER = [
    "schema_version",
    "experiment_id",
    "strategy_id",
    "direction_filter",
    "target_r_multiple",
    "breakeven_trigger_r",
    "input_signal_rows",
    "input_candidates",
    "evaluated_trades",
    "target_hits",
    "losses",
    "breakeven_exits",
    "other_exits",
    "win_rate",
    "gross_usd",
    "net_usd",
    "average_net_usd",
    "long_trades",
    "short_trades",
    "notes",
]
SIGNAL_BREAKEVEN_STOP_WALK_FORWARD_HEADER = [
    "schema_version",
    "split_id",
    "sample",
    "selected_on_train",
    "trade_dates",
    "experiment_id",
    "strategy_id",
    "direction_filter",
    "target_r_multiple",
    "breakeven_trigger_r",
    "input_signal_rows",
    "input_candidates",
    "evaluated_trades",
    "target_hits",
    "losses",
    "breakeven_exits",
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
_BREAKEVEN_EXIT_REASONS = {
    "breakeven_stop_hit",
    "ambiguous_breakeven_stop_first",
}
_LOSS_EXIT_REASONS = {"stop_hit", "ambiguous_stop_first"}


class SignalDynamicExitExperimentError(ValueError):
    """Raised when a dynamic exit experiment cannot be evaluated."""


def evaluate_signal_breakeven_stop_outcomes(
    bars: Iterable[dict[str, Any]],
    signal_rows: Iterable[dict[str, Any]],
    *,
    target_r_multiple: float,
    breakeven_trigger_r: float,
    direction_filter: str = "all",
    instrument_root: str | None = None,
    slippage_ticks_per_side: int | None = None,
    entry_match_mode: str = "auto",
) -> list[dict[str, Any]]:
    """Evaluate logged candidates with a fixed target and breakeven stop move."""

    if entry_match_mode not in {"bar_index", "timestamp", "auto"}:
        raise SignalDynamicExitExperimentError(
            "entry_match_mode must be one of: bar_index, timestamp, auto",
        )
    target_r = _normalize_positive_value(target_r_multiple, "target_r_multiple")
    trigger_r = _normalize_positive_value(breakeven_trigger_r, "breakeven_trigger_r")
    _validate_breakeven_pair(target_r, trigger_r)
    direction = _normalize_direction_filter(direction_filter)

    normalized_bars = [_normalize_bar(row) for row in bars]
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
    return [
        _evaluate_one_signal_with_breakeven_stop(
            signal,
            bars_by_symbol,
            costs,
            target_r=target_r,
            breakeven_trigger_r=trigger_r,
            entry_match_mode=entry_match_mode,
        )
        for signal in candidate_signals
    ]


def run_signal_breakeven_stop_sweep(
    bars: Iterable[dict[str, Any]],
    signal_rows: Iterable[dict[str, Any]],
    *,
    target_r_multiples: Iterable[float],
    breakeven_trigger_r_multiples: Iterable[float],
    direction_filters: Iterable[str] = ("all",),
    instrument_root: str | None = None,
    slippage_ticks_per_side: int | None = None,
    entry_match_mode: str = "auto",
) -> list[dict[str, Any]]:
    """Sweep target R and breakeven stop trigger R over logged candidates."""

    normalized_bars = list(bars)
    rows = list(signal_rows)
    parameter_pairs = _valid_parameter_pairs(
        target_r_multiples,
        breakeven_trigger_r_multiples,
    )
    directions = _normalize_direction_filters(direction_filters)

    experiment_rows: list[dict[str, Any]] = []
    for (target_r, trigger_r), direction_filter in product(parameter_pairs, directions):
        outcomes = evaluate_signal_breakeven_stop_outcomes(
            normalized_bars,
            rows,
            target_r_multiple=target_r,
            breakeven_trigger_r=trigger_r,
            direction_filter=direction_filter,
            instrument_root=instrument_root,
            slippage_ticks_per_side=slippage_ticks_per_side,
            entry_match_mode=entry_match_mode,
        )
        experiment_rows.append(
            _experiment_row(
                rows,
                outcomes,
                target_r=target_r,
                breakeven_trigger_r=trigger_r,
                direction_filter=direction_filter,
            ),
        )

    return experiment_rows


def run_signal_breakeven_stop_walk_forward_sweep(
    bars: Iterable[dict[str, Any]],
    signal_rows: Iterable[dict[str, Any]],
    *,
    train_date_count: int,
    holdout_date_count: int,
    target_r_multiples: Iterable[float],
    breakeven_trigger_r_multiples: Iterable[float],
    direction_filters: Iterable[str] = ("all",),
    minimum_train_trades: int = 1,
    instrument_root: str | None = None,
    slippage_ticks_per_side: int | None = None,
    entry_match_mode: str = "auto",
) -> list[dict[str, Any]]:
    """Run rolling selection of target R and breakeven trigger R."""

    normalized_bars = list(bars)
    rows = list(signal_rows)
    dates = _sorted_candidate_dates(rows)
    if train_date_count <= 0:
        raise SignalDynamicExitExperimentError("train_date_count must be positive")
    if holdout_date_count <= 0:
        raise SignalDynamicExitExperimentError("holdout_date_count must be positive")
    if minimum_train_trades <= 0:
        raise SignalDynamicExitExperimentError("minimum_train_trades must be positive")
    if train_date_count + holdout_date_count > len(dates):
        raise SignalDynamicExitExperimentError(
            "train_date_count plus holdout_date_count must not exceed "
            "the number of candidate trade dates",
        )

    targets = _normalize_positive_grid(target_r_multiples, "target_r_multiples")
    triggers = _normalize_positive_grid(
        breakeven_trigger_r_multiples,
        "breakeven_trigger_r_multiples",
    )
    directions = _normalize_direction_filters(direction_filters)
    split_rows: list[dict[str, Any]] = []
    max_start = len(dates) - train_date_count - holdout_date_count + 1
    for window_index in range(max_start):
        train_dates = dates[window_index:window_index + train_date_count]
        holdout_dates = dates[
            window_index + train_date_count:
            window_index + train_date_count + holdout_date_count
        ]
        train_sweep = run_signal_breakeven_stop_sweep(
            _filter_bars_by_dates(normalized_bars, train_dates),
            _filter_signal_rows_by_dates(rows, train_dates),
            target_r_multiples=targets,
            breakeven_trigger_r_multiples=triggers,
            direction_filters=directions,
            instrument_root=instrument_root,
            slippage_ticks_per_side=slippage_ticks_per_side,
            entry_match_mode=entry_match_mode,
        )
        best_train = _select_best_train_row(
            train_sweep,
            minimum_train_trades=minimum_train_trades,
        )
        holdout_sweep = run_signal_breakeven_stop_sweep(
            _filter_bars_by_dates(normalized_bars, holdout_dates),
            _filter_signal_rows_by_dates(rows, holdout_dates),
            target_r_multiples=targets,
            breakeven_trigger_r_multiples=triggers,
            direction_filters=directions,
            instrument_root=instrument_root,
            slippage_ticks_per_side=slippage_ticks_per_side,
            entry_match_mode=entry_match_mode,
        )
        matching_holdout = _find_matching_selection_row(holdout_sweep, best_train)
        split_id = (
            f"breakeven_stop_walk_forward_window={window_index + 1}:"
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


def _evaluate_one_signal_with_breakeven_stop(
    signal: dict[str, Any],
    bars_by_symbol: dict[str, list[OutcomeBar]],
    costs: OutcomeCosts,
    *,
    target_r: float,
    breakeven_trigger_r: float,
    entry_match_mode: str,
) -> dict[str, Any]:
    symbol = str(signal.get("symbol", ""))
    direction = str(signal.get("direction", ""))
    if direction not in {"long", "short"}:
        raise SignalDynamicExitExperimentError(
            f"Unsupported candidate direction: {direction!r}",
        )

    entry_bar_index = _to_int(signal.get("bar_index"), "bar_index")
    entry_time = str(signal.get("bar_start_time") or signal.get("generated_at") or "")
    entry_timestamp = _parse_timestamp(entry_time)
    entry_price = _to_float(signal.get("signal_price"), "signal_price")
    stop_price = _to_float(signal.get("stop_price"), "stop_price")
    risk_points = _risk_points(direction, entry_price, stop_price)
    if risk_points <= 0:
        raise SignalDynamicExitExperimentError(
            f"Candidate has nonpositive risk distance: {signal.get('signal_id')}",
        )

    target_price = _target_price(
        direction,
        entry_price=entry_price,
        risk_points=risk_points,
        target_r=target_r,
    )
    breakeven_trigger_price = _target_price(
        direction,
        entry_price=entry_price,
        risk_points=risk_points,
        target_r=breakeven_trigger_r,
    )
    following_bars, resolved_match_mode = _following_bars_for_signal(
        bars_by_symbol.get(symbol, []),
        entry_bar_index=entry_bar_index,
        entry_timestamp=entry_timestamp,
        entry_match_mode=entry_match_mode,
    )
    exit_bar, exit_price, exit_reason = _find_breakeven_stop_exit(
        following_bars,
        direction=direction,
        entry_price=entry_price,
        initial_stop_price=stop_price,
        target_price=target_price,
        breakeven_trigger_price=breakeven_trigger_price,
    )
    exit_bar_index = exit_bar.bar_index if exit_bar is not None else entry_bar_index
    exit_time = exit_bar.timestamp if exit_bar is not None else entry_time
    if resolved_match_mode == "timestamp" and exit_bar is not None:
        holding_bars = following_bars.index(exit_bar) + 1
    else:
        holding_bars = max(0, exit_bar_index - entry_bar_index)

    gross_points = _gross_points(direction, entry_price, exit_price)
    r_multiple = gross_points / risk_points if risk_points else 0.0
    gross_usd = gross_points * costs.point_value_usd
    net_usd = gross_usd - costs.commission_round_turn_usd - costs.slippage_round_turn_usd

    outcome_id = f"{signal['signal_id']}:{exit_reason}:{exit_bar_index}"
    return {
        "schema_version": 1,
        "outcome_id": outcome_id,
        "event_key": signal["event_key"],
        "signal_id": signal["signal_id"],
        "symbol": symbol,
        "direction": direction,
        "entry_bar_index": entry_bar_index,
        "exit_bar_index": exit_bar_index,
        "entry_time": entry_time,
        "exit_time": exit_time,
        "entry_price": _format_number(entry_price),
        "stop_price": _format_number(stop_price),
        "target_price": _format_number(target_price),
        "exit_price": _format_number(exit_price),
        "exit_reason": exit_reason,
        "holding_bars": holding_bars,
        "gross_points": _format_number(gross_points),
        "gross_usd": _format_number(gross_usd),
        "commission_usd": _format_number(costs.commission_round_turn_usd),
        "slippage_usd": _format_number(costs.slippage_round_turn_usd),
        "net_usd": _format_number(net_usd),
        "r_multiple": _format_number(r_multiple),
        "notes": (
            f"{costs.instrument_root} dynamic breakeven stop scan; "
            f"target_r={_format_number(target_r)}; "
            f"breakeven_trigger_r={_format_number(breakeven_trigger_r)}; "
            f"entry_match_mode={resolved_match_mode}"
        ),
    }


def _find_breakeven_stop_exit(
    bars: list[OutcomeBar],
    *,
    direction: str,
    entry_price: float,
    initial_stop_price: float,
    target_price: float,
    breakeven_trigger_price: float,
) -> tuple[OutcomeBar | None, float, str]:
    if not bars:
        return None, entry_price, "no_following_bar"

    breakeven_armed = False
    active_stop_price = initial_stop_price
    for bar in bars:
        target_hit = _target_hit(direction, bar, target_price)
        stop_hit = _stop_hit(direction, bar, active_stop_price)

        if breakeven_armed:
            if stop_hit and target_hit:
                return bar, entry_price, "ambiguous_breakeven_stop_first"
            if stop_hit:
                return bar, entry_price, "breakeven_stop_hit"
            if target_hit:
                return bar, target_price, "target_hit"
            continue

        if stop_hit and target_hit:
            return bar, initial_stop_price, "ambiguous_stop_first"
        if stop_hit:
            return bar, initial_stop_price, "stop_hit"

        trigger_hit = _target_hit(direction, bar, breakeven_trigger_price)
        if trigger_hit:
            breakeven_armed = True
            active_stop_price = entry_price
            breakeven_hit = _stop_hit(direction, bar, entry_price)
            if breakeven_hit and target_hit:
                return bar, entry_price, "ambiguous_breakeven_stop_first"
            if breakeven_hit:
                return bar, entry_price, "breakeven_stop_hit"
        if target_hit:
            return bar, target_price, "target_hit"

    final_bar = bars[-1]
    return final_bar, final_bar.close, "end_of_session"


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
        raise SignalDynamicExitExperimentError(
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
    raise SignalDynamicExitExperimentError(
        "Missing matching holdout breakeven stop row for "
        f"direction={selected_key[0]} "
        f"target_r={selected_key[1]} "
        f"breakeven_trigger_r={selected_key[2]}",
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
            for key in SIGNAL_BREAKEVEN_STOP_SWEEP_HEADER
            if key != "schema_version"
        },
    )
    return tagged


def _selection_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(row["direction_filter"]),
        str(row["target_r_multiple"]),
        str(row["breakeven_trigger_r"]),
    )


def _experiment_row(
    all_signal_rows: list[dict[str, Any]],
    outcome_rows: list[dict[str, Any]],
    *,
    target_r: float,
    breakeven_trigger_r: float,
    direction_filter: str,
) -> dict[str, Any]:
    summary = _dynamic_outcome_summary(outcome_rows)
    direction_counts = Counter(str(row["direction"]) for row in outcome_rows)
    candidate_rows = _candidate_signals(
        all_signal_rows,
        direction_filter=direction_filter,
    )
    strategy_id = _strategy_id(candidate_rows)
    experiment_id = (
        f"signal_breakeven_stop:strategy={strategy_id}:"
        f"direction={direction_filter}:"
        f"target_r={_format_number(target_r)}:"
        f"breakeven_trigger_r={_format_number(breakeven_trigger_r)}"
    )

    return {
        "schema_version": 1,
        "experiment_id": experiment_id,
        "strategy_id": strategy_id,
        "direction_filter": direction_filter,
        "target_r_multiple": _format_number(target_r),
        "breakeven_trigger_r": _format_number(breakeven_trigger_r),
        "input_signal_rows": len(all_signal_rows),
        "input_candidates": len(candidate_rows),
        "evaluated_trades": summary["total_trades"],
        "target_hits": summary["target_hits"],
        "losses": summary["losses"],
        "breakeven_exits": summary["breakeven_exits"],
        "other_exits": summary["other_exits"],
        "win_rate": _format_number(summary["win_rate"]),
        "gross_usd": _format_number(summary["gross_usd"]),
        "net_usd": _format_number(summary["net_usd"]),
        "average_net_usd": _format_number(summary["average_net_usd"]),
        "long_trades": direction_counts.get("long", 0),
        "short_trades": direction_counts.get("short", 0),
        "notes": (
            "post-signal dynamic exit sweep using logged entry/stop, "
            "replacement target R, and breakeven stop trigger"
        ),
    }


def _dynamic_outcome_summary(outcomes: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(outcomes)
    target_hits = sum(row["exit_reason"] == "target_hit" for row in outcomes)
    losses = sum(row["exit_reason"] in _LOSS_EXIT_REASONS for row in outcomes)
    breakeven_exits = sum(
        row["exit_reason"] in _BREAKEVEN_EXIT_REASONS
        for row in outcomes
    )
    gross_usd = sum(_to_float(row["gross_usd"], "gross_usd") for row in outcomes)
    net_usd = sum(_to_float(row["net_usd"], "net_usd") for row in outcomes)
    return {
        "total_trades": total,
        "target_hits": target_hits,
        "losses": losses,
        "breakeven_exits": breakeven_exits,
        "other_exits": total - target_hits - losses - breakeven_exits,
        "win_rate": target_hits / total if total else 0.0,
        "gross_usd": gross_usd,
        "net_usd": net_usd,
        "average_net_usd": net_usd / total if total else 0.0,
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


def _risk_points(direction: str, entry_price: float, stop_price: float) -> float:
    if direction == "long":
        return entry_price - stop_price
    if direction == "short":
        return stop_price - entry_price
    raise SignalDynamicExitExperimentError(f"Unsupported candidate direction: {direction!r}")


def _target_price(
    direction: str,
    *,
    entry_price: float,
    risk_points: float,
    target_r: float,
) -> float:
    if direction == "long":
        return entry_price + (risk_points * target_r)
    if direction == "short":
        return entry_price - (risk_points * target_r)
    raise SignalDynamicExitExperimentError(f"Unsupported candidate direction: {direction!r}")


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
    raise SignalDynamicExitExperimentError(f"Invalid timestamp: {value!r}")


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


def _valid_parameter_pairs(
    target_r_multiples: Iterable[float],
    breakeven_trigger_r_multiples: Iterable[float],
) -> list[tuple[float, float]]:
    targets = _normalize_positive_grid(target_r_multiples, "target_r_multiples")
    triggers = _normalize_positive_grid(
        breakeven_trigger_r_multiples,
        "breakeven_trigger_r_multiples",
    )
    pairs = [
        (target_r, trigger_r)
        for target_r, trigger_r in product(targets, triggers)
        if trigger_r < target_r
    ]
    if not pairs:
        raise SignalDynamicExitExperimentError(
            "At least one breakeven trigger R must be below a target R",
        )
    return pairs


def _validate_breakeven_pair(target_r: float, breakeven_trigger_r: float) -> None:
    if breakeven_trigger_r >= target_r:
        raise SignalDynamicExitExperimentError(
            "breakeven_trigger_r must be below target_r_multiple",
        )


def _normalize_positive_grid(values: Iterable[float], field_name: str) -> list[float]:
    grid = [float(value) for value in values]
    if not grid:
        raise SignalDynamicExitExperimentError(f"{field_name} must contain at least one value")
    if any(value <= 0 for value in grid):
        raise SignalDynamicExitExperimentError(f"{field_name} values must be positive")
    return grid


def _normalize_positive_value(value: float, field_name: str) -> float:
    normalized = float(value)
    if normalized <= 0:
        raise SignalDynamicExitExperimentError(f"{field_name} must be positive")
    return normalized


def _normalize_direction_filters(values: Iterable[str]) -> list[str]:
    filters = [str(value).strip().lower() for value in values if str(value).strip()]
    if not filters:
        raise SignalDynamicExitExperimentError(
            "direction_filters must contain at least one value",
        )
    return [_normalize_direction_filter(value) for value in filters]


def _normalize_direction_filter(value: str) -> str:
    direction_filter = str(value).strip().lower()
    if direction_filter not in _ALLOWED_DIRECTION_FILTERS:
        raise SignalDynamicExitExperimentError(
            f"Unsupported direction filter: {direction_filter}",
        )
    return direction_filter

