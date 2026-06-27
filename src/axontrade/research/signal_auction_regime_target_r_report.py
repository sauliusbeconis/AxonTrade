"""Auction-regime guard plus target-R reporting for logged signals."""

from __future__ import annotations

from collections import OrderedDict
from datetime import datetime
from typing import Any, Iterable

from axontrade.research.signal_target_experiments import run_signal_target_r_sweep


SIGNAL_AUCTION_REGIME_TARGET_R_REPORT_HEADER = [
    "schema_version",
    "split_id",
    "sample",
    "selected_on_train",
    "trade_dates",
    "experiment_id",
    "strategy_id",
    "auction_direction_filter",
    "max_original_reward_risk",
    "min_minutes_after_rth_open",
    "max_minutes_after_rth_open",
    "max_session_range_points",
    "max_fade_edge_score",
    "max_vwap_stretch_points",
    "max_open_stretch_points",
    "target_direction_filter",
    "target_r_multiple",
    "input_regime_rows",
    "auction_eligible_trades",
    "auction_skipped_trades",
    "auction_skipped_target_hits",
    "auction_skipped_losses",
    "auction_skipped_other_exits",
    "auction_skipped_net_usd",
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
    "total_candidate_net_usd",
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


class SignalAuctionRegimeTargetReportError(ValueError):
    """Raised when the auction-regime/target-R report cannot be computed."""


def report_signal_auction_regime_target_r(
    *,
    bars: Iterable[dict[str, Any]],
    signal_rows: Iterable[dict[str, Any]],
    regime_rows: Iterable[dict[str, Any]],
    selection_rows: Iterable[dict[str, Any]],
    target_r_multiples: Iterable[float],
    direction_filters: Iterable[str] = ("all",),
    minimum_train_trades: int = 1,
    instrument_root: str | None = None,
    slippage_ticks_per_side: int | None = None,
    entry_match_mode: str = "auto",
) -> list[dict[str, Any]]:
    """Stack selected auction-regime rules with train-selected target R."""

    normalized_bars = list(bars)
    signals = list(signal_rows)
    diagnostics = _sorted_rows(list(regime_rows))
    targets = _normalize_positive_grid(target_r_multiples, "target_r_multiples")
    directions = _normalize_direction_filters(direction_filters)
    if minimum_train_trades <= 0:
        raise SignalAuctionRegimeTargetReportError("minimum_train_trades must be positive")

    split_rows: list[dict[str, Any]] = []
    for train_selection, holdout_selection in _selected_train_holdout_pairs(selection_rows):
        train_dates = _selection_trade_dates(train_selection)
        holdout_dates = _selection_trade_dates(holdout_selection)
        train_base = _filter_rows_by_dates(diagnostics, train_dates)
        holdout_base = _filter_rows_by_dates(diagnostics, holdout_dates)
        train_eligible, train_auction_skipped = _split_auction_selection(
            train_base,
            train_selection,
        )
        holdout_eligible, holdout_auction_skipped = _split_auction_selection(
            holdout_base,
            train_selection,
        )

        train_signals = _signals_for_regime_rows(signals, train_eligible)
        best_train = _select_best_train_target_row(
            run_signal_target_r_sweep(
                _filter_bars_by_dates(normalized_bars, train_dates),
                train_signals,
                target_r_multiples=targets,
                direction_filters=directions,
                instrument_root=instrument_root,
                slippage_ticks_per_side=slippage_ticks_per_side,
                entry_match_mode=entry_match_mode,
            ),
            minimum_train_trades=minimum_train_trades,
        )
        holdout_signals = _signals_for_regime_rows(signals, holdout_eligible)
        holdout_sweep = run_signal_target_r_sweep(
            _filter_bars_by_dates(normalized_bars, holdout_dates),
            holdout_signals,
            target_r_multiples=targets,
            direction_filters=directions,
            instrument_root=instrument_root,
            slippage_ticks_per_side=slippage_ticks_per_side,
            entry_match_mode=entry_match_mode,
        )
        matching_holdout = _find_matching_target_row(holdout_sweep, best_train)
        split_id = str(train_selection["split_id"])
        split_rows.append(
            _tag_split_row(
                _combined_row(
                    best_train,
                    selection=train_selection,
                    auction_input_row_count=len(train_base),
                    auction_eligible_row_count=len(train_eligible),
                    auction_skipped_rows=train_auction_skipped,
                ),
                sample="train",
                selected_row=best_train,
                split_id=split_id,
                trade_dates=train_dates,
            ),
        )
        split_rows.append(
            _tag_split_row(
                _combined_row(
                    matching_holdout,
                    selection=train_selection,
                    auction_input_row_count=len(holdout_base),
                    auction_eligible_row_count=len(holdout_eligible),
                    auction_skipped_rows=holdout_auction_skipped,
                ),
                sample="holdout",
                selected_row=best_train,
                split_id=split_id,
                trade_dates=holdout_dates,
            ),
        )

    return split_rows


def _select_best_train_target_row(
    target_rows: list[dict[str, Any]],
    *,
    minimum_train_trades: int,
) -> dict[str, Any]:
    eligible_rows = [
        row
        for row in target_rows
        if int(row["evaluated_trades"]) >= minimum_train_trades
    ]
    if not eligible_rows:
        raise SignalAuctionRegimeTargetReportError(
            f"No train target-R experiments met minimum_train_trades={minimum_train_trades}",
        )
    return max(eligible_rows, key=lambda row: float(row["net_usd"]))


def _combined_row(
    target_row: dict[str, Any],
    *,
    selection: dict[str, Any],
    auction_input_row_count: int,
    auction_eligible_row_count: int,
    auction_skipped_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    auction_skipped = _summary(auction_skipped_rows)
    net_usd = _to_float(target_row["net_usd"], "net_usd")
    total_candidate_net = net_usd + auction_skipped["net_usd"]
    experiment_id = (
        f"signal_auction_regime_target_r:strategy={target_row['strategy_id']}:"
        f"auction_direction={selection['direction_filter']}:"
        f"max_rr={selection['max_original_reward_risk']}:"
        f"minutes={selection['min_minutes_after_rth_open']}-"
        f"{selection['max_minutes_after_rth_open']}:"
        f"max_session_range={selection['max_session_range_points']}:"
        f"max_fade_edge={selection['max_fade_edge_score']}:"
        f"max_vwap_stretch={selection['max_vwap_stretch_points']}:"
        f"max_open_stretch={selection['max_open_stretch_points']}:"
        f"target_direction={target_row['direction_filter']}:"
        f"target_r={target_row['target_r_multiple']}"
    )
    return {
        "schema_version": 1,
        "experiment_id": experiment_id,
        "strategy_id": target_row["strategy_id"],
        "auction_direction_filter": selection["direction_filter"],
        "max_original_reward_risk": selection["max_original_reward_risk"],
        "min_minutes_after_rth_open": selection["min_minutes_after_rth_open"],
        "max_minutes_after_rth_open": selection["max_minutes_after_rth_open"],
        "max_session_range_points": selection["max_session_range_points"],
        "max_fade_edge_score": selection["max_fade_edge_score"],
        "max_vwap_stretch_points": selection["max_vwap_stretch_points"],
        "max_open_stretch_points": selection["max_open_stretch_points"],
        "target_direction_filter": target_row["direction_filter"],
        "target_r_multiple": target_row["target_r_multiple"],
        "input_regime_rows": auction_input_row_count,
        "auction_eligible_trades": auction_eligible_row_count,
        "auction_skipped_trades": auction_skipped["total_trades"],
        "auction_skipped_target_hits": auction_skipped["target_hits"],
        "auction_skipped_losses": auction_skipped["losses"],
        "auction_skipped_other_exits": auction_skipped["other_exits"],
        "auction_skipped_net_usd": _format_number(auction_skipped["net_usd"]),
        "input_signal_rows": target_row["input_signal_rows"],
        "input_candidates": target_row["input_candidates"],
        "evaluated_trades": target_row["evaluated_trades"],
        "target_hits": target_row["target_hits"],
        "losses": target_row["losses"],
        "other_exits": target_row["other_exits"],
        "win_rate": target_row["win_rate"],
        "gross_usd": target_row["gross_usd"],
        "net_usd": target_row["net_usd"],
        "average_net_usd": target_row["average_net_usd"],
        "total_candidate_net_usd": _format_number(total_candidate_net),
        "long_trades": target_row["long_trades"],
        "short_trades": target_row["short_trades"],
        "notes": (
            "selected auction-regime guard first, then train-selected target R "
            "on auction-eligible logged candidates"
        ),
    }


def _selected_train_holdout_pairs(
    selection_rows: Iterable[dict[str, Any]],
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    grouped: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for row in selection_rows:
        if str(row.get("selected_on_train", "")).lower() != "true":
            continue
        grouped.setdefault(str(row["split_id"]), []).append(row)

    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for split_id, rows in grouped.items():
        train_rows = [row for row in rows if str(row["sample"]) == "train"]
        holdout_rows = [row for row in rows if str(row["sample"]) == "holdout"]
        if len(train_rows) != 1 or len(holdout_rows) != 1:
            raise SignalAuctionRegimeTargetReportError(
                "Expected exactly one selected train row and one selected "
                f"holdout row for split_id={split_id!r}",
            )
        pairs.append((train_rows[0], holdout_rows[0]))
    if not pairs:
        raise SignalAuctionRegimeTargetReportError(
            "No selected train/holdout auction-regime rows found",
        )
    return pairs


def _find_matching_target_row(
    rows: list[dict[str, Any]],
    selected_row: dict[str, Any],
) -> dict[str, Any]:
    selected_key = _target_selection_key(selected_row)
    for row in rows:
        if _target_selection_key(row) == selected_key:
            return row
    raise SignalAuctionRegimeTargetReportError(
        "Missing matching holdout target-R row for "
        f"target_selection={selected_key}",
    )


def _split_auction_selection(
    rows: list[dict[str, Any]],
    selection: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    accepted_rows: list[dict[str, Any]] = []
    skipped_rows: list[dict[str, Any]] = []
    for row in rows:
        if _passes_selection(row, selection):
            accepted_rows.append(row)
        else:
            skipped_rows.append(row)
    return accepted_rows, skipped_rows


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


def _signals_for_regime_rows(
    signal_rows: list[dict[str, Any]],
    regime_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    allowed_signal_ids = {str(row["signal_id"]) for row in regime_rows}
    return [
        row
        for row in signal_rows
        if str(row.get("signal_id", "")) in allowed_signal_ids
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
        "selected_on_train": str(_target_selection_key(row) == _target_selection_key(selected_row)).lower(),
        "trade_dates": ";".join(trade_dates),
    }
    tagged.update(
        {
            key: row[key]
            for key in SIGNAL_AUCTION_REGIME_TARGET_R_REPORT_HEADER
            if key not in {"schema_version", "split_id", "sample", "selected_on_train", "trade_dates"}
        },
    )
    return tagged


def _target_selection_key(row: dict[str, Any]) -> tuple[str, str]:
    direction_filter = row.get("target_direction_filter", row.get("direction_filter"))
    return str(direction_filter), str(row["target_r_multiple"])


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
        "net_usd": net_usd,
    }


def _selection_trade_dates(selection: dict[str, Any]) -> list[str]:
    return [
        part.strip()
        for part in str(selection["trade_dates"]).split(";")
        if part.strip()
    ]


def _sorted_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: (_parse_timestamp(str(row["entry_time"])), str(row["signal_id"])))


def _filter_rows_by_dates(rows: list[dict[str, Any]], dates: list[str]) -> list[dict[str, Any]]:
    allowed_dates = set(dates)
    return [row for row in rows if _trade_date(row) in allowed_dates]


def _filter_bars_by_dates(bars: list[dict[str, Any]], dates: list[str]) -> list[dict[str, Any]]:
    allowed_dates = set(dates)
    return [
        row
        for row in bars
        if _parse_timestamp(str(row["timestamp"])).date().isoformat() in allowed_dates
    ]


def _trade_date(row: dict[str, Any]) -> str:
    return _parse_timestamp(str(row["entry_time"])).date().isoformat()


def _parse_timestamp(value: str) -> datetime:
    timestamp_text = _normalize_timestamp_text(value.strip())
    for timestamp_format in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(timestamp_text, timestamp_format)
        except ValueError:
            continue
    raise SignalAuctionRegimeTargetReportError(f"Invalid timestamp: {value!r}")


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
        raise SignalAuctionRegimeTargetReportError(
            f"{field_name} must contain at least one value",
        )
    if any(value <= 0 for value in grid):
        raise SignalAuctionRegimeTargetReportError(f"{field_name} values must be positive")
    return grid


def _normalize_direction_filters(values: Iterable[str]) -> list[str]:
    filters = [str(value).strip().lower() for value in values if str(value).strip()]
    if not filters:
        raise SignalAuctionRegimeTargetReportError(
            "direction_filters must contain at least one value",
        )
    invalid = [value for value in filters if value not in {"all", "long", "short"}]
    if invalid:
        raise SignalAuctionRegimeTargetReportError(
            "direction_filters contains unsupported values: " + ", ".join(invalid),
        )
    return filters


def _to_float(value: Any, field_name: str) -> float:
    try:
        return float(str(value))
    except ValueError as exc:
        raise SignalAuctionRegimeTargetReportError(
            f"Invalid numeric field {field_name}: {value!r}",
        ) from exc


def _format_number(value: Any) -> str:
    return f"{float(value):.8f}".rstrip("0").rstrip(".")
