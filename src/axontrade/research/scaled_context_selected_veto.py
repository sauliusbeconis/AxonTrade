"""Selected-trade audit and second-stage veto checks for scaled context filters."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from math import sqrt
from statistics import pstdev
from typing import Any, Iterable

from axontrade.research.scaled_context_filter_experiments import (
    scaled_context_row_passes_filter,
)


SCALED_CONTEXT_SELECTED_TRADE_AUDIT_HEADER = [
    "schema_version",
    "audit_id",
    "split_id",
    "sample",
    "trade_dates",
    "selected_context_experiment_id",
    "outcome_id",
    "signal_id",
    "symbol",
    "direction",
    "entry_time",
    "entry_bar_index",
    "exit_reason",
    "net_usd",
    "minutes_after_rth_open",
    "directional_open_distance_points",
    "directional_opening_range_breakout_points",
    "continuation_edge_score",
    "opening_range_continuation_edge_score",
    "lookback_directional_move_points",
    "lookback_efficiency_ratio",
    "lookback_choppiness_score",
    "signal_abs_delta_sum_to_average_abs_delta",
    "entry_volume_to_average_volume",
    "entry_trades_to_average_trades",
    "entry_volume_to_session_average_volume",
    "lookback_volume_to_session_average_volume",
    "risk_to_average_bar_range",
    "runner_target_to_average_bar_range",
    "notes",
]
SCALED_CONTEXT_SELECTED_VETO_WALK_FORWARD_HEADER = [
    "schema_version",
    "split_id",
    "sample",
    "selected_on_train",
    "trade_dates",
    "selected_context_experiment_id",
    "veto_id",
    "veto_name",
    "veto_field",
    "veto_operator",
    "veto_threshold",
    "minimum_kept_train_trades",
    "selected_input_trades",
    "kept_trades",
    "vetoed_trades",
    "runner_target_hits",
    "full_stops",
    "runner_stop_exits",
    "other_exits",
    "positive_net_trades",
    "positive_net_rate",
    "net_usd",
    "average_net_usd",
    "average_net_usd_lower_bound",
    "unvetoed_net_usd",
    "veto_net_improvement_usd",
    "long_trades",
    "short_trades",
    "notes",
]
_TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
)
_RUNNER_TARGET_REASONS = {"runner_target_hit"}
_FULL_STOP_REASONS = {"full_stop_hit", "ambiguous_full_stop_first"}
_RUNNER_STOP_REASONS = {
    "runner_initial_stop_hit",
    "runner_breakeven_stop_hit",
    "ambiguous_runner_stop_first",
}
_AUDIT_FEATURE_FIELDS = SCALED_CONTEXT_SELECTED_TRADE_AUDIT_HEADER[14:-1]


class ScaledContextSelectedVetoError(ValueError):
    """Raised when selected context rows cannot be audited or vetoed."""


@dataclass(frozen=True)
class VetoRule:
    """One second-stage selected-trade keep rule."""

    name: str
    field: str
    operator: str
    threshold: float

    @property
    def veto_id(self) -> str:
        if self.name == "none":
            return "selected_veto:none"
        return (
            "selected_veto:"
            f"name={self.name}:"
            f"field={self.field}:"
            f"op={self.operator}:"
            f"threshold={_format_number(self.threshold)}"
        )


def audit_scaled_context_selected_trades(
    *,
    context_rows: Iterable[dict[str, Any]],
    selection_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Emit one audit row per trade selected by each walk-forward split row."""

    rows = _sorted_context_rows(list(context_rows))
    audit_rows: list[dict[str, Any]] = []
    for selection in selection_rows:
        selected_rows = _selected_context_rows(rows, selection)
        for row in selected_rows:
            audit_rows.append(_audit_row(row, selection))
    return audit_rows


def run_scaled_context_selected_veto_walk_forward(
    *,
    context_rows: Iterable[dict[str, Any]],
    selection_rows: Iterable[dict[str, Any]],
    minimum_kept_train_trades: int,
    min_directional_open_distance_points: Iterable[float],
    min_directional_opening_range_breakout_points: Iterable[float],
    min_continuation_edge_scores: Iterable[float],
    min_opening_range_continuation_edge_scores: Iterable[float],
    min_lookback_directional_move_points: Iterable[float],
    min_lookback_efficiency_ratios: Iterable[float],
    max_signal_abs_delta_sum_to_average_abs_deltas: Iterable[float],
    max_entry_volume_to_average_volumes: Iterable[float],
    max_entry_volume_to_session_average_volumes: Iterable[float],
    max_risk_to_average_bar_ranges: Iterable[float],
) -> list[dict[str, Any]]:
    """Select a simple train-side veto and apply it to selected holdout trades."""

    if minimum_kept_train_trades <= 0:
        raise ScaledContextSelectedVetoError("minimum_kept_train_trades must be positive")

    rows = _sorted_context_rows(list(context_rows))
    veto_rules = _veto_rules(
        min_directional_open_distance_points=min_directional_open_distance_points,
        min_directional_opening_range_breakout_points=(
            min_directional_opening_range_breakout_points
        ),
        min_continuation_edge_scores=min_continuation_edge_scores,
        min_opening_range_continuation_edge_scores=(
            min_opening_range_continuation_edge_scores
        ),
        min_lookback_directional_move_points=min_lookback_directional_move_points,
        min_lookback_efficiency_ratios=min_lookback_efficiency_ratios,
        max_signal_abs_delta_sum_to_average_abs_deltas=(
            max_signal_abs_delta_sum_to_average_abs_deltas
        ),
        max_entry_volume_to_average_volumes=max_entry_volume_to_average_volumes,
        max_entry_volume_to_session_average_volumes=(
            max_entry_volume_to_session_average_volumes
        ),
        max_risk_to_average_bar_ranges=max_risk_to_average_bar_ranges,
    )

    split_rows: list[dict[str, Any]] = []
    for train_selection, holdout_selection in _selected_train_holdout_pairs(selection_rows):
        train_rows = _selected_context_rows(rows, train_selection)
        holdout_rows = _selected_context_rows(rows, holdout_selection)
        selected_veto = _select_best_train_veto(
            train_rows,
            veto_rules,
            minimum_kept_train_trades=minimum_kept_train_trades,
        )
        split_rows.append(
            _summary_row(
                split_selection=train_selection,
                selected_veto=selected_veto,
                rows=train_rows,
                sample="train",
                minimum_kept_train_trades=minimum_kept_train_trades,
            ),
        )
        split_rows.append(
            _summary_row(
                split_selection=holdout_selection,
                selected_veto=selected_veto,
                rows=holdout_rows,
                sample="holdout",
                minimum_kept_train_trades=minimum_kept_train_trades,
            ),
        )
    return split_rows


def _selected_context_rows(
    rows: list[dict[str, Any]],
    selection_row: dict[str, Any],
) -> list[dict[str, Any]]:
    dates = _selection_trade_dates(selection_row)
    return [
        row
        for row in rows
        if _trade_date(row) in dates and scaled_context_row_passes_filter(row, selection_row)
    ]


def _audit_row(row: dict[str, Any], selection: dict[str, Any]) -> dict[str, Any]:
    audit = {
        "schema_version": 1,
        "audit_id": f"{selection['split_id']}:{selection['sample']}:{row['outcome_id']}",
        "split_id": selection["split_id"],
        "sample": selection["sample"],
        "trade_dates": selection["trade_dates"],
        "selected_context_experiment_id": selection["experiment_id"],
        "outcome_id": row["outcome_id"],
        "signal_id": row["signal_id"],
        "symbol": row["symbol"],
        "direction": row["direction"],
        "entry_time": row["entry_time"],
        "entry_bar_index": row["entry_bar_index"],
        "exit_reason": row["exit_reason"],
        "net_usd": row["net_usd"],
    }
    audit.update({field: row.get(field, "") for field in _AUDIT_FEATURE_FIELDS})
    audit["notes"] = "trade selected by context-filter walk-forward row"
    return audit


def _selected_train_holdout_pairs(
    selection_rows: Iterable[dict[str, Any]],
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    by_split: dict[str, dict[str, dict[str, Any]]] = {}
    for row in selection_rows:
        if str(row.get("selected_on_train", "")).lower() != "true":
            continue
        by_split.setdefault(str(row["split_id"]), {})[str(row["sample"])] = row

    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for split_id in sorted(by_split, key=_split_sort_key):
        split_rows = by_split[split_id]
        if "train" not in split_rows or "holdout" not in split_rows:
            raise ScaledContextSelectedVetoError(
                f"Missing train/holdout selected rows for split_id={split_id}",
            )
        pairs.append((split_rows["train"], split_rows["holdout"]))
    return pairs


def _veto_rules(
    *,
    min_directional_open_distance_points: Iterable[float],
    min_directional_opening_range_breakout_points: Iterable[float],
    min_continuation_edge_scores: Iterable[float],
    min_opening_range_continuation_edge_scores: Iterable[float],
    min_lookback_directional_move_points: Iterable[float],
    min_lookback_efficiency_ratios: Iterable[float],
    max_signal_abs_delta_sum_to_average_abs_deltas: Iterable[float],
    max_entry_volume_to_average_volumes: Iterable[float],
    max_entry_volume_to_session_average_volumes: Iterable[float],
    max_risk_to_average_bar_ranges: Iterable[float],
) -> list[VetoRule]:
    rules = [VetoRule("none", "none", "none", 0.0)]
    rules.extend(
        _min_rules(
            "min_directional_open_distance_points",
            "directional_open_distance_points",
            min_directional_open_distance_points,
        ),
    )
    rules.extend(
        _min_rules(
            "min_directional_opening_range_breakout_points",
            "directional_opening_range_breakout_points",
            min_directional_opening_range_breakout_points,
        ),
    )
    rules.extend(_min_rules("min_continuation_edge_score", "continuation_edge_score", min_continuation_edge_scores))
    rules.extend(
        _min_rules(
            "min_opening_range_continuation_edge_score",
            "opening_range_continuation_edge_score",
            min_opening_range_continuation_edge_scores,
        ),
    )
    rules.extend(
        _min_rules(
            "min_lookback_directional_move_points",
            "lookback_directional_move_points",
            min_lookback_directional_move_points,
        ),
    )
    rules.extend(
        _min_rules(
            "min_lookback_efficiency_ratio",
            "lookback_efficiency_ratio",
            min_lookback_efficiency_ratios,
        ),
    )
    rules.extend(
        _max_rules(
            "max_signal_abs_delta_sum_to_average_abs_delta",
            "signal_abs_delta_sum_to_average_abs_delta",
            max_signal_abs_delta_sum_to_average_abs_deltas,
        ),
    )
    rules.extend(
        _max_rules(
            "max_entry_volume_to_average_volume",
            "entry_volume_to_average_volume",
            max_entry_volume_to_average_volumes,
        ),
    )
    rules.extend(
        _max_rules(
            "max_entry_volume_to_session_average_volume",
            "entry_volume_to_session_average_volume",
            max_entry_volume_to_session_average_volumes,
        ),
    )
    rules.extend(
        _max_rules(
            "max_risk_to_average_bar_range",
            "risk_to_average_bar_range",
            max_risk_to_average_bar_ranges,
        ),
    )
    return rules


def _min_rules(name: str, field: str, values: Iterable[float]) -> list[VetoRule]:
    return [VetoRule(name, field, ">=", float(value)) for value in values]


def _max_rules(name: str, field: str, values: Iterable[float]) -> list[VetoRule]:
    return [VetoRule(name, field, "<=", float(value)) for value in values]


def _select_best_train_veto(
    rows: list[dict[str, Any]],
    veto_rules: list[VetoRule],
    *,
    minimum_kept_train_trades: int,
) -> VetoRule:
    original_net = _net_usd(rows)
    eligible: list[tuple[float, float, float, int, str, VetoRule]] = []
    for rule in veto_rules:
        kept_rows = _apply_veto(rows, rule)
        if len(kept_rows) < minimum_kept_train_trades:
            continue
        eligible.append(
            (
                _average_net_lower_bound(kept_rows),
                _net_usd(kept_rows) - original_net,
                _net_usd(kept_rows),
                len(kept_rows),
                rule.veto_id,
                rule,
            ),
        )
    if not eligible:
        raise ScaledContextSelectedVetoError(
            f"No veto rule met minimum_kept_train_trades={minimum_kept_train_trades}",
        )
    return max(eligible)[-1]


def _summary_row(
    *,
    split_selection: dict[str, Any],
    selected_veto: VetoRule,
    rows: list[dict[str, Any]],
    sample: str,
    minimum_kept_train_trades: int,
) -> dict[str, Any]:
    kept_rows = _apply_veto(rows, selected_veto)
    summary = _summary(kept_rows)
    unvetoed_net = _net_usd(rows)
    direction_counts = Counter(str(row["direction"]) for row in kept_rows)
    return {
        "schema_version": 1,
        "split_id": split_selection["split_id"],
        "sample": sample,
        "selected_on_train": "true",
        "trade_dates": split_selection["trade_dates"],
        "selected_context_experiment_id": split_selection["experiment_id"],
        "veto_id": selected_veto.veto_id,
        "veto_name": selected_veto.name,
        "veto_field": selected_veto.field,
        "veto_operator": selected_veto.operator,
        "veto_threshold": _format_number(selected_veto.threshold),
        "minimum_kept_train_trades": minimum_kept_train_trades,
        "selected_input_trades": len(rows),
        "kept_trades": summary["total_trades"],
        "vetoed_trades": len(rows) - summary["total_trades"],
        "runner_target_hits": summary["runner_target_hits"],
        "full_stops": summary["full_stops"],
        "runner_stop_exits": summary["runner_stop_exits"],
        "other_exits": summary["other_exits"],
        "positive_net_trades": summary["positive_net_trades"],
        "positive_net_rate": _format_number(summary["positive_net_rate"]),
        "net_usd": _format_number(summary["net_usd"]),
        "average_net_usd": _format_number(summary["average_net_usd"]),
        "average_net_usd_lower_bound": _format_number(_average_net_lower_bound(kept_rows)),
        "unvetoed_net_usd": _format_number(unvetoed_net),
        "veto_net_improvement_usd": _format_number(summary["net_usd"] - unvetoed_net),
        "long_trades": direction_counts.get("long", 0),
        "short_trades": direction_counts.get("short", 0),
        "notes": "second-stage single-feature veto selected on train rows only",
    }


def _apply_veto(rows: list[dict[str, Any]], veto_rule: VetoRule) -> list[dict[str, Any]]:
    if veto_rule.name == "none":
        return rows
    if veto_rule.operator == ">=":
        return [
            row
            for row in rows
            if _to_float_or_default(row, veto_rule.field, float("-inf")) >= veto_rule.threshold
        ]
    if veto_rule.operator == "<=":
        return [
            row
            for row in rows
            if _to_float_or_default(row, veto_rule.field, float("inf")) <= veto_rule.threshold
        ]
    raise ScaledContextSelectedVetoError(
        f"Unsupported veto operator: {veto_rule.operator}",
    )


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    runner_targets = sum(str(row["exit_reason"]) in _RUNNER_TARGET_REASONS for row in rows)
    full_stops = sum(str(row["exit_reason"]) in _FULL_STOP_REASONS for row in rows)
    runner_stops = sum(str(row["exit_reason"]) in _RUNNER_STOP_REASONS for row in rows)
    net_usd = _net_usd(rows)
    positive = sum(_to_float(row["net_usd"], "net_usd") > 0 for row in rows)
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


def _average_net_lower_bound(rows: list[dict[str, Any]]) -> float:
    values = [_to_float(row["net_usd"], "net_usd") for row in rows]
    if not values:
        return 0.0
    average = sum(values) / len(values)
    if len(values) == 1:
        return average
    return average - pstdev(values) / sqrt(len(values))


def _net_usd(rows: list[dict[str, Any]]) -> float:
    return sum(_to_float(row["net_usd"], "net_usd") for row in rows)


def _selection_trade_dates(selection_row: dict[str, Any]) -> set[str]:
    return {
        value.strip()
        for value in str(selection_row["trade_dates"]).split(";")
        if value.strip()
    }


def _sorted_context_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: (_trade_date(row), _parse_timestamp(str(row["entry_time"]))))


def _trade_date(row: dict[str, Any]) -> str:
    return _parse_timestamp(str(row["entry_time"])).date().isoformat()


def _split_sort_key(split_id: str) -> tuple[int, str]:
    marker = "window="
    if marker in split_id:
        suffix = split_id.split(marker, maxsplit=1)[1].split(":", maxsplit=1)[0]
        try:
            return int(suffix), split_id
        except ValueError:
            pass
    return 0, split_id


def _parse_timestamp(value: str) -> datetime:
    timestamp_text = _normalize_timestamp_text(value.strip())
    for timestamp_format in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(timestamp_text, timestamp_format)
        except ValueError:
            continue
    raise ScaledContextSelectedVetoError(f"Invalid timestamp: {value!r}")


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


def _to_float(value: Any, field_name: str) -> float:
    try:
        return float(str(value))
    except ValueError as exc:
        raise ScaledContextSelectedVetoError(
            f"Invalid numeric field {field_name}: {value!r}",
        ) from exc


def _to_float_or_default(row: dict[str, Any], field_name: str, default: float) -> float:
    value = row.get(field_name)
    if value is None or str(value).strip() == "":
        return default
    return _to_float(value, field_name)


def _format_number(value: Any) -> str:
    return f"{float(value):.8f}".rstrip("0").rstrip(".")
