"""Guard reporting for selected auction-regime filter rows."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable


SIGNAL_AUCTION_REGIME_GUARD_REPORT_HEADER = [
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
    "max_session_range_points",
    "max_fade_edge_score",
    "max_vwap_stretch_points",
    "max_open_stretch_points",
    "input_regime_rows",
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
    "total_net_usd",
    "long_trades",
    "short_trades",
    "skipped_long_trades",
    "skipped_short_trades",
    "notes",
]
_TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
)
_LOSS_EXIT_REASONS = {"stop_hit", "ambiguous_stop_first"}


class SignalAuctionRegimeGuardReportError(ValueError):
    """Raised when auction-regime guard reporting cannot be computed."""


def report_signal_auction_regime_guard(
    *,
    regime_rows: Iterable[dict[str, Any]],
    selection_rows: Iterable[dict[str, Any]],
    selected_only: bool = True,
) -> list[dict[str, Any]]:
    """Report accepted/skipped outcomes for selected auction-regime rules."""

    diagnostics = list(regime_rows)
    selections = [
        row
        for row in selection_rows
        if not selected_only or str(row["selected_on_train"]) == "true"
    ]
    return [
        _guard_row(diagnostics, selection)
        for selection in selections
    ]


def _guard_row(
    diagnostics: list[dict[str, Any]],
    selection: dict[str, Any],
) -> dict[str, Any]:
    trade_dates = _selection_trade_dates(selection)
    input_rows = [
        row
        for row in diagnostics
        if _trade_date(row) in trade_dates
    ]
    accepted_rows = [
        row
        for row in input_rows
        if _passes_selection(row, selection)
    ]
    accepted_ids = {str(row["signal_id"]) for row in accepted_rows}
    skipped_rows = [
        row
        for row in input_rows
        if str(row["signal_id"]) not in accepted_ids
    ]
    accepted_summary = _summary(accepted_rows)
    skipped_summary = _summary(skipped_rows)

    return {
        "schema_version": 1,
        "split_id": selection["split_id"],
        "sample": selection["sample"],
        "selected_on_train": selection["selected_on_train"],
        "trade_dates": selection["trade_dates"],
        "experiment_id": selection["experiment_id"],
        "strategy_id": selection["strategy_id"],
        "direction_filter": selection["direction_filter"],
        "max_original_reward_risk": selection["max_original_reward_risk"],
        "min_minutes_after_rth_open": selection["min_minutes_after_rth_open"],
        "max_minutes_after_rth_open": selection["max_minutes_after_rth_open"],
        "max_session_range_points": selection["max_session_range_points"],
        "max_fade_edge_score": selection["max_fade_edge_score"],
        "max_vwap_stretch_points": selection["max_vwap_stretch_points"],
        "max_open_stretch_points": selection["max_open_stretch_points"],
        "input_regime_rows": len(input_rows),
        "accepted_trades": accepted_summary["total_trades"],
        "skipped_trades": skipped_summary["total_trades"],
        "target_hits": accepted_summary["target_hits"],
        "losses": accepted_summary["losses"],
        "other_exits": accepted_summary["other_exits"],
        "skipped_target_hits": skipped_summary["target_hits"],
        "skipped_losses": skipped_summary["losses"],
        "skipped_other_exits": skipped_summary["other_exits"],
        "win_rate": _format_number(accepted_summary["win_rate"]),
        "net_usd": _format_number(accepted_summary["net_usd"]),
        "skipped_net_usd": _format_number(skipped_summary["net_usd"]),
        "total_net_usd": _format_number(
            accepted_summary["net_usd"] + skipped_summary["net_usd"],
        ),
        "long_trades": _direction_count(accepted_rows, "long"),
        "short_trades": _direction_count(accepted_rows, "short"),
        "skipped_long_trades": _direction_count(skipped_rows, "long"),
        "skipped_short_trades": _direction_count(skipped_rows, "short"),
        "notes": "accepted/skipped report for selected auction-regime guard rule",
    }


def _passes_selection(row: dict[str, Any], selection: dict[str, Any]) -> bool:
    direction_filter = str(selection["direction_filter"])
    if direction_filter != "all" and str(row["direction"]) != direction_filter:
        return False
    if _to_float(row["original_reward_risk"], "original_reward_risk") > _to_float(
        selection["max_original_reward_risk"],
        "max_original_reward_risk",
    ):
        return False
    minutes = _to_float(row["minutes_after_rth_open"], "minutes_after_rth_open")
    if minutes < _to_float(selection["min_minutes_after_rth_open"], "min_minutes_after_rth_open"):
        return False
    if minutes > _to_float(selection["max_minutes_after_rth_open"], "max_minutes_after_rth_open"):
        return False
    if _to_float(row["session_range_points"], "session_range_points") > _to_float(
        selection["max_session_range_points"],
        "max_session_range_points",
    ):
        return False
    if _to_float(row["fade_edge_score"], "fade_edge_score") > _to_float(
        selection["max_fade_edge_score"],
        "max_fade_edge_score",
    ):
        return False
    if _to_float(
        row["direction_aware_vwap_stretch_points"],
        "direction_aware_vwap_stretch_points",
    ) > _to_float(selection["max_vwap_stretch_points"], "max_vwap_stretch_points"):
        return False
    return _to_float(
        row["direction_aware_open_stretch_points"],
        "direction_aware_open_stretch_points",
    ) <= _to_float(selection["max_open_stretch_points"], "max_open_stretch_points")


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    target_hits = sum(str(row["exit_reason"]) == "target_hit" for row in rows)
    losses = sum(str(row["exit_reason"]) in _LOSS_EXIT_REASONS for row in rows)
    net_usd = sum(_to_float(row["net_usd"], "net_usd") for row in rows)
    return {
        "total_trades": total,
        "target_hits": target_hits,
        "losses": losses,
        "other_exits": total - target_hits - losses,
        "win_rate": target_hits / total if total else 0.0,
        "net_usd": net_usd,
    }


def _selection_trade_dates(selection: dict[str, Any]) -> set[str]:
    return {
        part.strip()
        for part in str(selection["trade_dates"]).split(";")
        if part.strip()
    }


def _direction_count(rows: list[dict[str, Any]], direction: str) -> int:
    return sum(str(row["direction"]) == direction for row in rows)


def _trade_date(row: dict[str, Any]) -> str:
    return _parse_timestamp(str(row["entry_time"])).date().isoformat()


def _parse_timestamp(value: str) -> datetime:
    timestamp_text = _normalize_timestamp_text(value.strip())
    for timestamp_format in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(timestamp_text, timestamp_format)
        except ValueError:
            continue
    raise SignalAuctionRegimeGuardReportError(f"Invalid timestamp: {value!r}")


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
        raise SignalAuctionRegimeGuardReportError(
            f"Invalid numeric field {field_name}: {value!r}",
        ) from exc


def _format_number(value: float) -> str:
    return f"{value:.8f}".rstrip("0").rstrip(".")
