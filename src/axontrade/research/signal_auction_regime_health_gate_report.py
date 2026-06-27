"""Auction-regime guard plus health-gate reporting for logged signals."""

from __future__ import annotations

from collections import OrderedDict
from datetime import datetime
from itertools import product
from typing import Any, Iterable

from axontrade.research.signal_health_gate_experiments import evaluate_signal_health_gate


SIGNAL_AUCTION_REGIME_HEALTH_GATE_REPORT_HEADER = [
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
    "maximum_daily_losses",
    "daily_loss_limit_usd",
    "maximum_consecutive_losses",
    "consecutive_loss_pause_trade_dates",
    "maximum_equity_drawdown_usd",
    "drawdown_pause_trade_dates",
    "input_regime_rows",
    "auction_eligible_trades",
    "auction_skipped_trades",
    "auction_skipped_target_hits",
    "auction_skipped_losses",
    "auction_skipped_other_exits",
    "auction_skipped_net_usd",
    "state_warmup_rows",
    "accepted_trades",
    "health_skipped_trades",
    "target_hits",
    "losses",
    "other_exits",
    "health_skipped_target_hits",
    "health_skipped_losses",
    "health_skipped_other_exits",
    "win_rate",
    "net_usd",
    "health_skipped_net_usd",
    "average_net_usd",
    "max_equity_drawdown_usd",
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


class SignalAuctionRegimeHealthGateReportError(ValueError):
    """Raised when the auction-regime/health-gate report cannot be computed."""


def report_signal_auction_regime_health_gate(
    *,
    regime_rows: Iterable[dict[str, Any]],
    selection_rows: Iterable[dict[str, Any]],
    maximum_daily_losses: Iterable[int],
    daily_loss_limits_usd: Iterable[float],
    maximum_consecutive_losses: Iterable[int],
    consecutive_loss_pause_trade_dates: Iterable[int],
    maximum_equity_drawdowns_usd: Iterable[float],
    drawdown_pause_trade_dates: Iterable[int],
    minimum_train_accepted_trades: int = 1,
) -> list[dict[str, Any]]:
    """Stack selected auction-regime rules with train-selected health gates."""

    rows = _sorted_rows(list(regime_rows))
    if minimum_train_accepted_trades <= 0:
        raise SignalAuctionRegimeHealthGateReportError(
            "minimum_train_accepted_trades must be positive",
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
    for train_selection, holdout_selection in _selected_train_holdout_pairs(selection_rows):
        train_dates = _selection_trade_dates(train_selection)
        holdout_dates = _selection_trade_dates(holdout_selection)
        train_base = _filter_rows_by_dates(rows, train_dates)
        holdout_base = _filter_rows_by_dates(rows, holdout_dates)
        train_eligible, train_auction_skipped = _split_auction_selection(
            train_base,
            train_selection,
        )
        holdout_eligible, holdout_auction_skipped = _split_auction_selection(
            holdout_base,
            train_selection,
        )

        best_train = _select_best_train_health_row(
            train_eligible,
            train_selection=train_selection,
            health_configs=health_configs,
            auction_input_row_count=len(train_base),
            auction_skipped_rows=train_auction_skipped,
            minimum_train_accepted_trades=minimum_train_accepted_trades,
        )
        selected_health = _health_config_from_row(best_train)
        holdout_health = evaluate_signal_health_gate(
            train_eligible + holdout_eligible,
            **selected_health,
            report_trade_dates=holdout_dates,
            state_warmup_rows=len(train_eligible),
        )
        holdout_row = _combined_row(
            holdout_health,
            selection=train_selection,
            auction_input_row_count=len(holdout_base),
            auction_skipped_rows=holdout_auction_skipped,
        )
        split_id = str(train_selection["split_id"])
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


def _select_best_train_health_row(
    train_eligible_rows: list[dict[str, Any]],
    *,
    train_selection: dict[str, Any],
    health_configs: list[dict[str, Any]],
    auction_input_row_count: int,
    auction_skipped_rows: list[dict[str, Any]],
    minimum_train_accepted_trades: int,
) -> dict[str, Any]:
    best_row: dict[str, Any] | None = None
    for health_config in health_configs:
        candidate = _combined_row(
            evaluate_signal_health_gate(train_eligible_rows, **health_config),
            selection=train_selection,
            auction_input_row_count=auction_input_row_count,
            auction_skipped_rows=auction_skipped_rows,
        )
        if int(candidate["accepted_trades"]) < minimum_train_accepted_trades:
            continue
        if best_row is None or _selection_score(candidate) > _selection_score(best_row):
            best_row = candidate

    if best_row is None:
        raise SignalAuctionRegimeHealthGateReportError(
            "No train health-gate experiments met "
            f"minimum_train_accepted_trades={minimum_train_accepted_trades}",
        )
    return best_row


def _combined_row(
    health_row: dict[str, Any],
    *,
    selection: dict[str, Any],
    auction_input_row_count: int,
    auction_skipped_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    auction_skipped = _summary(auction_skipped_rows)
    experiment_id = (
        f"signal_auction_regime_health_gate:strategy={health_row['strategy_id']}:"
        f"direction={selection['direction_filter']}:"
        f"max_rr={selection['max_original_reward_risk']}:"
        f"minutes={selection['min_minutes_after_rth_open']}-"
        f"{selection['max_minutes_after_rth_open']}:"
        f"max_session_range={selection['max_session_range_points']}:"
        f"max_fade_edge={selection['max_fade_edge_score']}:"
        f"max_vwap_stretch={selection['max_vwap_stretch_points']}:"
        f"max_open_stretch={selection['max_open_stretch_points']}:"
        f"max_daily_losses={health_row['maximum_daily_losses']}:"
        f"daily_loss={health_row['daily_loss_limit_usd']}:"
        f"max_consecutive_losses={health_row['maximum_consecutive_losses']}:"
        f"consecutive_pause_dates={health_row['consecutive_loss_pause_trade_dates']}:"
        f"max_drawdown={health_row['maximum_equity_drawdown_usd']}:"
        f"drawdown_pause_dates={health_row['drawdown_pause_trade_dates']}"
    )
    net_usd = _to_float(health_row["net_usd"], "net_usd")
    health_skipped_net = _to_float(health_row["skipped_net_usd"], "skipped_net_usd")
    total_candidate_net = net_usd + health_skipped_net + auction_skipped["net_usd"]
    return {
        "schema_version": 1,
        "experiment_id": experiment_id,
        "strategy_id": health_row["strategy_id"],
        "direction_filter": selection["direction_filter"],
        "max_original_reward_risk": selection["max_original_reward_risk"],
        "min_minutes_after_rth_open": selection["min_minutes_after_rth_open"],
        "max_minutes_after_rth_open": selection["max_minutes_after_rth_open"],
        "max_session_range_points": selection["max_session_range_points"],
        "max_fade_edge_score": selection["max_fade_edge_score"],
        "max_vwap_stretch_points": selection["max_vwap_stretch_points"],
        "max_open_stretch_points": selection["max_open_stretch_points"],
        "maximum_daily_losses": health_row["maximum_daily_losses"],
        "daily_loss_limit_usd": health_row["daily_loss_limit_usd"],
        "maximum_consecutive_losses": health_row["maximum_consecutive_losses"],
        "consecutive_loss_pause_trade_dates": (
            health_row["consecutive_loss_pause_trade_dates"]
        ),
        "maximum_equity_drawdown_usd": health_row["maximum_equity_drawdown_usd"],
        "drawdown_pause_trade_dates": health_row["drawdown_pause_trade_dates"],
        "input_regime_rows": auction_input_row_count,
        "auction_eligible_trades": health_row["input_diagnostic_rows"],
        "auction_skipped_trades": auction_skipped["total_trades"],
        "auction_skipped_target_hits": auction_skipped["target_hits"],
        "auction_skipped_losses": auction_skipped["losses"],
        "auction_skipped_other_exits": auction_skipped["other_exits"],
        "auction_skipped_net_usd": _format_number(auction_skipped["net_usd"]),
        "state_warmup_rows": health_row["state_warmup_rows"],
        "accepted_trades": health_row["accepted_trades"],
        "health_skipped_trades": health_row["skipped_trades"],
        "target_hits": health_row["target_hits"],
        "losses": health_row["losses"],
        "other_exits": health_row["other_exits"],
        "health_skipped_target_hits": health_row["skipped_target_hits"],
        "health_skipped_losses": health_row["skipped_losses"],
        "health_skipped_other_exits": health_row["skipped_other_exits"],
        "win_rate": health_row["win_rate"],
        "net_usd": health_row["net_usd"],
        "health_skipped_net_usd": health_row["skipped_net_usd"],
        "average_net_usd": health_row["average_net_usd"],
        "max_equity_drawdown_usd": health_row["max_equity_drawdown_usd"],
        "total_candidate_net_usd": _format_number(total_candidate_net),
        "long_trades": health_row["long_trades"],
        "short_trades": health_row["short_trades"],
        "notes": (
            "selected auction-regime guard first, then train-selected "
            "closed-trade health gate on auction-eligible rows"
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
            raise SignalAuctionRegimeHealthGateReportError(
                "Expected exactly one selected train row and one selected "
                f"holdout row for split_id={split_id!r}",
            )
        pairs.append((train_rows[0], holdout_rows[0]))
    if not pairs:
        raise SignalAuctionRegimeHealthGateReportError(
            "No selected train/holdout auction-regime rows found",
        )
    return pairs


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
        str(row["max_session_range_points"]),
        str(row["max_fade_edge_score"]),
        str(row["max_vwap_stretch_points"]),
        str(row["max_open_stretch_points"]),
        str(row["maximum_daily_losses"]),
        str(row["daily_loss_limit_usd"]),
        str(row["maximum_consecutive_losses"]),
        str(row["consecutive_loss_pause_trade_dates"]),
        str(row["maximum_equity_drawdown_usd"]),
        str(row["drawdown_pause_trade_dates"]),
    )


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
            for key in SIGNAL_AUCTION_REGIME_HEALTH_GATE_REPORT_HEADER
            if key not in {"schema_version", "split_id", "sample", "selected_on_train", "trade_dates"}
        },
    )
    return tagged


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


def _trade_date(row: dict[str, Any]) -> str:
    return _parse_timestamp(str(row["entry_time"])).date().isoformat()


def _parse_timestamp(value: str) -> datetime:
    timestamp_text = _normalize_timestamp_text(value.strip())
    for timestamp_format in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(timestamp_text, timestamp_format)
        except ValueError:
            continue
    raise SignalAuctionRegimeHealthGateReportError(f"Invalid timestamp: {value!r}")


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
        raise SignalAuctionRegimeHealthGateReportError(
            f"{field_name} must contain at least one value",
        )
    if any(value <= 0 for value in grid):
        raise SignalAuctionRegimeHealthGateReportError(f"{field_name} values must be positive")
    return grid


def _normalize_positive_int_grid(values: Iterable[int], field_name: str) -> list[int]:
    grid = [int(value) for value in values]
    if not grid:
        raise SignalAuctionRegimeHealthGateReportError(
            f"{field_name} must contain at least one value",
        )
    if any(value <= 0 for value in grid):
        raise SignalAuctionRegimeHealthGateReportError(f"{field_name} values must be positive")
    return grid


def _normalize_nonnegative_int_grid(values: Iterable[int], field_name: str) -> list[int]:
    grid = [int(value) for value in values]
    if not grid:
        raise SignalAuctionRegimeHealthGateReportError(
            f"{field_name} must contain at least one value",
        )
    if any(value < 0 for value in grid):
        raise SignalAuctionRegimeHealthGateReportError(
            f"{field_name} values must be nonnegative",
        )
    return grid


def _to_float(value: Any, field_name: str) -> float:
    try:
        return float(str(value))
    except ValueError as exc:
        raise SignalAuctionRegimeHealthGateReportError(
            f"Invalid numeric field {field_name}: {value!r}",
        ) from exc


def _format_number(value: Any) -> str:
    return f"{float(value):.8f}".rstrip("0").rstrip(".")
