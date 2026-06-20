"""Target-placement experiments for logged signal rows."""

from __future__ import annotations

from collections import Counter
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
