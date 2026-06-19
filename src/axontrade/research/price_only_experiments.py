"""Parameter experiments for the price-only VWAP/opening-range baseline."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from itertools import product
from typing import Any, Iterable

from axontrade.research.price_only_baseline import (
    evaluate_price_only_vwap_reclaim,
    load_price_only_baseline_config,
)
from axontrade.research.trade_outcomes import (
    evaluate_trade_outcomes,
    summarize_trade_outcomes,
)


PRICE_ONLY_PARAMETER_SWEEP_HEADER = [
    "schema_version",
    "experiment_id",
    "strategy_id",
    "direction_filter",
    "target_r_multiple",
    "stop_buffer_points",
    "minimum_opening_range_width_points",
    "signal_rows",
    "candidate_signals",
    "rejected_signals",
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


class PriceOnlyExperimentError(ValueError):
    """Raised when a price-only experiment definition is invalid."""


ALLOWED_DIRECTION_FILTERS = ("all", "long", "short")


def run_price_only_parameter_sweep(
    normalized_rows: Iterable[dict[str, Any]],
    *,
    target_r_multiples: Iterable[float],
    stop_buffer_points: Iterable[float],
    minimum_opening_range_width_points: Iterable[float],
    direction_filters: Iterable[str] = ("all",),
    instrument_root: str | None = None,
    slippage_ticks_per_side: int | None = None,
    base_config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Run aggregate outcome experiments over a small parameter grid."""

    rows = list(normalized_rows)
    targets = _normalize_positive_grid(target_r_multiples, "target_r_multiples")
    stop_buffers = _normalize_nonnegative_grid(stop_buffer_points, "stop_buffer_points")
    min_widths = _normalize_nonnegative_grid(
        minimum_opening_range_width_points,
        "minimum_opening_range_width_points",
    )
    directions = _normalize_direction_filters(direction_filters)
    config_template = load_price_only_baseline_config() if base_config is None else base_config

    experiment_rows: list[dict[str, Any]] = []
    for target_r, stop_buffer, min_width, direction_filter in product(
        targets,
        stop_buffers,
        min_widths,
        directions,
    ):
        config = deepcopy(config_template)
        config["rules"]["target_r_multiple"] = target_r
        config["rules"]["stop_buffer_points"] = stop_buffer
        config["rules"]["minimum_opening_range_width_points"] = min_width

        signal_rows = evaluate_price_only_vwap_reclaim(rows, config)
        outcome_signal_rows = _filter_signal_rows_by_direction(signal_rows, direction_filter)
        outcome_rows = evaluate_trade_outcomes(
            rows,
            outcome_signal_rows,
            instrument_root=instrument_root,
            slippage_ticks_per_side=slippage_ticks_per_side,
        )
        experiment_rows.append(
            _experiment_row(
                config,
                signal_rows,
                outcome_rows,
                target_r=target_r,
                stop_buffer=stop_buffer,
                min_width=min_width,
                direction_filter=direction_filter,
            ),
        )

    return experiment_rows


def _experiment_row(
    config: dict[str, Any],
    signal_rows: list[dict[str, Any]],
    outcome_rows: list[dict[str, Any]],
    *,
    target_r: float,
    stop_buffer: float,
    min_width: float,
    direction_filter: str,
) -> dict[str, Any]:
    signal_counts = Counter(str(row["event_type"]) for row in signal_rows)
    direction_counts = Counter(str(row["direction"]) for row in outcome_rows)
    summary = summarize_trade_outcomes(outcome_rows)
    experiment_id = (
        f"{config['strategy_id']}:"
        f"direction={direction_filter}:"
        f"target_r={_format_number(target_r)}:"
        f"stop_buffer={_format_number(stop_buffer)}:"
        f"min_or_width={_format_number(min_width)}"
    )

    return {
        "schema_version": 1,
        "experiment_id": experiment_id,
        "strategy_id": config["strategy_id"],
        "direction_filter": direction_filter,
        "target_r_multiple": _format_number(target_r),
        "stop_buffer_points": _format_number(stop_buffer),
        "minimum_opening_range_width_points": _format_number(min_width),
        "signal_rows": len(signal_rows),
        "candidate_signals": signal_counts.get("candidate_signal", 0),
        "rejected_signals": signal_counts.get("rejected_signal", 0),
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
        "notes": "price-only parameter sweep aggregate",
    }


def _normalize_positive_grid(values: Iterable[float], field_name: str) -> list[float]:
    grid = _normalize_grid(values, field_name)
    if any(value <= 0 for value in grid):
        raise PriceOnlyExperimentError(f"{field_name} values must be positive")
    return grid


def _normalize_nonnegative_grid(values: Iterable[float], field_name: str) -> list[float]:
    grid = _normalize_grid(values, field_name)
    if any(value < 0 for value in grid):
        raise PriceOnlyExperimentError(f"{field_name} values must be nonnegative")
    return grid


def _normalize_grid(values: Iterable[float], field_name: str) -> list[float]:
    grid = [float(value) for value in values]
    if not grid:
        raise PriceOnlyExperimentError(f"{field_name} must contain at least one value")
    return grid


def _normalize_direction_filters(values: Iterable[str]) -> list[str]:
    filters = [str(value).strip().lower() for value in values if str(value).strip()]
    if not filters:
        raise PriceOnlyExperimentError("direction_filters must contain at least one value")
    invalid = [value for value in filters if value not in ALLOWED_DIRECTION_FILTERS]
    if invalid:
        raise PriceOnlyExperimentError(
            "direction_filters contains unsupported values: " + ", ".join(invalid),
        )
    return filters


def _filter_signal_rows_by_direction(
    signal_rows: list[dict[str, Any]],
    direction_filter: str,
) -> list[dict[str, Any]]:
    if direction_filter == "all":
        return signal_rows
    return [
        row
        for row in signal_rows
        if row["event_type"] != "candidate_signal" or row["direction"] == direction_filter
    ]


def _format_number(value: Any) -> str:
    return f"{float(value):.8f}".rstrip("0").rstrip(".")
