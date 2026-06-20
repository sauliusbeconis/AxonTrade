"""Conservative stop/target outcome evaluation for research signals."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from axontrade.config import load_yaml


DEFAULT_COST_CONFIG = "config/research/default_costs.yaml"
DEFAULT_INSTRUMENT_CONFIG_DIR = "config/instruments"
TRADE_OUTCOME_CSV_HEADER = [
    "schema_version",
    "outcome_id",
    "event_key",
    "signal_id",
    "symbol",
    "direction",
    "entry_bar_index",
    "exit_bar_index",
    "entry_time",
    "exit_time",
    "entry_price",
    "stop_price",
    "target_price",
    "exit_price",
    "exit_reason",
    "holding_bars",
    "gross_points",
    "gross_usd",
    "commission_usd",
    "slippage_usd",
    "net_usd",
    "r_multiple",
    "notes",
]
TRADE_OUTCOME_DAILY_CSV_HEADER = [
    "schema_version",
    "trade_date",
    "trades",
    "target_hits",
    "losses",
    "other_exits",
    "win_rate",
    "gross_usd",
    "net_usd",
    "average_net_usd",
    "long_trades",
    "short_trades",
    "average_holding_bars",
    "cumulative_net_usd",
    "peak_to_date_net_usd",
    "drawdown_usd",
    "notes",
]
TRADE_PATH_DIAGNOSTIC_CSV_HEADER = [
    "schema_version",
    "diagnostic_id",
    "outcome_id",
    "signal_id",
    "symbol",
    "direction",
    "entry_time",
    "exit_time",
    "entry_bar_index",
    "exit_bar_index",
    "entry_price",
    "stop_price",
    "target_price",
    "exit_reason",
    "scanned_bars",
    "risk_points",
    "target_distance_points",
    "max_favorable_points",
    "max_favorable_r",
    "max_adverse_points",
    "max_adverse_r",
    "first_target_bar_index",
    "first_target_time",
    "first_stop_bar_index",
    "first_stop_time",
    "bars_to_max_favorable",
    "bars_to_max_adverse",
    "diagnostic_label",
    "notes",
]
_TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
)
_ENTRY_VALIDATION_RECOVERY = (
    "Export fresh bars from the same Sierra chart/timezone as the signal log."
)


class TradeOutcomeError(ValueError):
    """Raised when a trade-outcome input cannot be evaluated."""


@dataclass(frozen=True)
class OutcomeBar:
    timestamp: str
    parsed_timestamp: datetime
    symbol: str
    bar_index: int
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class OutcomeCosts:
    instrument_root: str
    tick_size: float
    tick_value_usd: float
    point_value_usd: float
    commission_per_side_usd: float
    slippage_ticks_per_side: int

    @property
    def commission_round_turn_usd(self) -> float:
        return self.commission_per_side_usd * 2

    @property
    def slippage_round_turn_usd(self) -> float:
        return self.slippage_ticks_per_side * 2 * self.tick_value_usd


def load_signal_rows_csv(path: str | Path) -> list[dict[str, str]]:
    """Load signal-log CSV rows from disk."""

    csv_path = Path(path)
    with csv_path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def evaluate_trade_outcomes(
    bars: Iterable[dict[str, Any]],
    signal_rows: Iterable[dict[str, Any]],
    *,
    instrument_root: str | None = None,
    slippage_ticks_per_side: int | None = None,
    cost_config: dict[str, Any] | None = None,
    instrument_config: dict[str, Any] | None = None,
    entry_match_mode: str = "bar_index",
) -> list[dict[str, Any]]:
    """Evaluate candidate signals against later same-session bars.

    This model assumes entry at the signal row's close-derived signal price and
    then scans subsequent bars on the same symbol/date. If a later bar touches
    both stop and target, the stop is chosen first as the conservative outcome.
    """

    if entry_match_mode not in {"bar_index", "timestamp", "auto"}:
        raise TradeOutcomeError("entry_match_mode must be one of: bar_index, timestamp, auto")

    normalized_bars = [_normalize_bar(row) for row in bars]
    candidate_signals = [
        row for row in signal_rows if str(row.get("event_type", "")) == "candidate_signal"
    ]
    if not candidate_signals:
        return []

    costs = _load_outcome_costs(
        candidate_signals,
        instrument_root=instrument_root,
        slippage_ticks_per_side=slippage_ticks_per_side,
        cost_config=cost_config,
        instrument_config=instrument_config,
    )
    bars_by_symbol = _bars_by_symbol(normalized_bars)

    outcomes: list[dict[str, Any]] = []
    for signal in candidate_signals:
        outcome = _evaluate_one_signal(
            signal,
            bars_by_symbol,
            costs,
            entry_match_mode=entry_match_mode,
        )
        outcomes.append(outcome)
    return outcomes


def validate_signal_entries_against_bars(
    bars: Iterable[dict[str, Any]],
    signal_rows: Iterable[dict[str, Any]],
    *,
    maximum_time_difference_seconds: float = 300.0,
    maximum_price_difference_points: float = 0.25,
) -> list[dict[str, Any]]:
    """Validate that candidate signal entries line up with exported bar rows."""

    if maximum_time_difference_seconds < 0:
        raise TradeOutcomeError("maximum_time_difference_seconds must be nonnegative")
    if maximum_price_difference_points < 0:
        raise TradeOutcomeError("maximum_price_difference_points must be nonnegative")

    normalized_bars = [_normalize_bar(row) for row in bars]
    bars_by_symbol = _bars_by_symbol(normalized_bars)
    candidate_signals = [
        row for row in signal_rows if str(row.get("event_type", "")) == "candidate_signal"
    ]
    diagnostics: list[dict[str, Any]] = []
    for signal in candidate_signals:
        symbol = str(signal.get("symbol", ""))
        entry_time = str(signal.get("bar_start_time") or signal.get("generated_at") or "")
        entry_timestamp = _parse_timestamp(entry_time)
        entry_price = _to_float(signal.get("signal_price"), "signal_price")
        same_day_bars = [
            bar
            for bar in bars_by_symbol.get(symbol, [])
            if bar.parsed_timestamp.date() == entry_timestamp.date()
        ]
        if not same_day_bars:
            raise TradeOutcomeError(
                f"No exported bars found for signal_id={signal.get('signal_id')} "
                f"symbol={symbol} date={entry_timestamp.date().isoformat()}. "
                f"{_ENTRY_VALIDATION_RECOVERY}",
            )

        nearest_bar = min(
            same_day_bars,
            key=lambda bar: (
                abs((bar.parsed_timestamp - entry_timestamp).total_seconds()),
                abs(bar.close - entry_price),
            ),
        )
        time_difference_seconds = abs(
            (nearest_bar.parsed_timestamp - entry_timestamp).total_seconds(),
        )
        price_difference_points = abs(nearest_bar.close - entry_price)
        if time_difference_seconds > maximum_time_difference_seconds:
            raise TradeOutcomeError(
                f"Nearest export bar for signal_id={signal.get('signal_id')} is "
                f"{time_difference_seconds:.3f}s away, above "
                f"maximum_time_difference_seconds={maximum_time_difference_seconds}. "
                f"{_ENTRY_VALIDATION_RECOVERY}",
            )
        if price_difference_points > maximum_price_difference_points:
            raise TradeOutcomeError(
                f"Nearest export bar for signal_id={signal.get('signal_id')} has "
                f"close/entry difference {price_difference_points:.8f}, above "
                f"maximum_price_difference_points={maximum_price_difference_points}. "
                f"{_ENTRY_VALIDATION_RECOVERY}",
            )

        diagnostics.append(
            {
                "signal_id": signal["signal_id"],
                "symbol": symbol,
                "entry_time": entry_time,
                "entry_price": _format_number(entry_price),
                "nearest_bar_index": nearest_bar.bar_index,
                "nearest_bar_time": nearest_bar.timestamp,
                "nearest_bar_close": _format_number(nearest_bar.close),
                "time_difference_seconds": _format_number(time_difference_seconds),
                "price_difference_points": _format_number(price_difference_points),
            },
        )

    return diagnostics


def diagnose_trade_paths(
    bars: Iterable[dict[str, Any]],
    outcome_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Measure MFE/MAE and first stop/target touch for evaluated outcomes."""

    normalized_bars = [_normalize_bar(row) for row in bars]
    bars_by_symbol = _bars_by_symbol(normalized_bars)
    return [
        _diagnose_one_trade_path(outcome, bars_by_symbol)
        for outcome in outcome_rows
    ]


def summarize_trade_outcomes(outcomes: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Summarize a list of trade outcome rows."""

    outcome_rows = list(outcomes)
    total = len(outcome_rows)
    wins = sum(row["exit_reason"] == "target_hit" for row in outcome_rows)
    losses = sum(
        row["exit_reason"] in {"stop_hit", "ambiguous_stop_first"}
        for row in outcome_rows
    )
    net_usd = sum(_to_float(row["net_usd"], "net_usd") for row in outcome_rows)
    gross_usd = sum(_to_float(row["gross_usd"], "gross_usd") for row in outcome_rows)

    return {
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "other_exits": total - wins - losses,
        "win_rate": wins / total if total else 0.0,
        "gross_usd": gross_usd,
        "net_usd": net_usd,
        "average_net_usd": net_usd / total if total else 0.0,
    }


def summarize_trade_outcomes_by_day(
    outcomes: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Summarize outcome rows by entry trade date with cumulative drawdown."""

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in outcomes:
        trade_date = _parse_timestamp(str(row["entry_time"])).date().isoformat()
        grouped.setdefault(trade_date, []).append(row)

    daily_rows: list[dict[str, Any]] = []
    cumulative_net_usd = 0.0
    peak_to_date_net_usd = 0.0
    for trade_date in sorted(grouped):
        day_outcomes = grouped[trade_date]
        summary = summarize_trade_outcomes(day_outcomes)
        net_usd = _to_float(summary["net_usd"], "net_usd")
        cumulative_net_usd += net_usd
        peak_to_date_net_usd = max(peak_to_date_net_usd, cumulative_net_usd)
        drawdown_usd = cumulative_net_usd - peak_to_date_net_usd
        long_trades = sum(row["direction"] == "long" for row in day_outcomes)
        short_trades = sum(row["direction"] == "short" for row in day_outcomes)
        holding_bars = sum(_to_int(row["holding_bars"], "holding_bars") for row in day_outcomes)

        daily_rows.append(
            {
                "schema_version": 1,
                "trade_date": trade_date,
                "trades": summary["total_trades"],
                "target_hits": summary["wins"],
                "losses": summary["losses"],
                "other_exits": summary["other_exits"],
                "win_rate": _format_number(summary["win_rate"]),
                "gross_usd": _format_number(summary["gross_usd"]),
                "net_usd": _format_number(net_usd),
                "average_net_usd": _format_number(summary["average_net_usd"]),
                "long_trades": long_trades,
                "short_trades": short_trades,
                "average_holding_bars": _format_number(holding_bars / len(day_outcomes)),
                "cumulative_net_usd": _format_number(cumulative_net_usd),
                "peak_to_date_net_usd": _format_number(peak_to_date_net_usd),
                "drawdown_usd": _format_number(drawdown_usd),
                "notes": "daily aggregate by entry date",
            },
        )

    return daily_rows


def _diagnose_one_trade_path(
    outcome: dict[str, Any],
    bars_by_symbol: dict[str, list[OutcomeBar]],
) -> dict[str, Any]:
    symbol = str(outcome["symbol"])
    direction = str(outcome["direction"])
    if direction not in {"long", "short"}:
        raise TradeOutcomeError(f"Unsupported outcome direction: {direction!r}")

    entry_bar_index = _to_int(outcome["entry_bar_index"], "entry_bar_index")
    exit_bar_index = _to_int(outcome["exit_bar_index"], "exit_bar_index")
    entry_time = str(outcome["entry_time"])
    exit_time = str(outcome["exit_time"])
    entry_timestamp = _parse_timestamp(entry_time)
    exit_timestamp = _parse_timestamp(exit_time)
    entry_price = _to_float(outcome["entry_price"], "entry_price")
    stop_price = _to_float(outcome["stop_price"], "stop_price")
    target_price = _to_float(outcome["target_price"], "target_price")

    path_bars = _path_bars_for_outcome(
        bars_by_symbol.get(symbol, []),
        entry_bar_index=entry_bar_index,
        exit_bar_index=exit_bar_index,
        entry_timestamp=entry_timestamp,
        exit_timestamp=exit_timestamp,
    )
    risk_points = _risk_points(direction, entry_price, stop_price)
    target_distance_points = _target_distance_points(direction, entry_price, target_price)
    if risk_points <= 0:
        raise TradeOutcomeError(f"Outcome has nonpositive risk distance: {outcome['outcome_id']}")

    metrics = _trade_path_metrics(
        path_bars,
        direction=direction,
        entry_price=entry_price,
        stop_price=stop_price,
        target_price=target_price,
        risk_points=risk_points,
        entry_bar_index=entry_bar_index,
    )

    return {
        "schema_version": 1,
        "diagnostic_id": f"{outcome['outcome_id']}:path",
        "outcome_id": outcome["outcome_id"],
        "signal_id": outcome["signal_id"],
        "symbol": symbol,
        "direction": direction,
        "entry_time": entry_time,
        "exit_time": exit_time,
        "entry_bar_index": entry_bar_index,
        "exit_bar_index": exit_bar_index,
        "entry_price": _format_number(entry_price),
        "stop_price": _format_number(stop_price),
        "target_price": _format_number(target_price),
        "exit_reason": outcome["exit_reason"],
        "scanned_bars": len(path_bars),
        "risk_points": _format_number(risk_points),
        "target_distance_points": _format_number(target_distance_points),
        "max_favorable_points": _format_number(metrics["max_favorable_points"]),
        "max_favorable_r": _format_number(metrics["max_favorable_points"] / risk_points),
        "max_adverse_points": _format_number(metrics["max_adverse_points"]),
        "max_adverse_r": _format_number(metrics["max_adverse_points"] / risk_points),
        "first_target_bar_index": metrics["first_target_bar_index"],
        "first_target_time": metrics["first_target_time"],
        "first_stop_bar_index": metrics["first_stop_bar_index"],
        "first_stop_time": metrics["first_stop_time"],
        "bars_to_max_favorable": metrics["bars_to_max_favorable"],
        "bars_to_max_adverse": metrics["bars_to_max_adverse"],
        "diagnostic_label": metrics["diagnostic_label"],
        "notes": "path diagnostic from first bar after entry through evaluated exit",
    }


def _path_bars_for_outcome(
    bars: list[OutcomeBar],
    *,
    entry_bar_index: int,
    exit_bar_index: int,
    entry_timestamp: datetime,
    exit_timestamp: datetime,
) -> list[OutcomeBar]:
    same_day_bars = [
        bar
        for bar in bars
        if bar.parsed_timestamp.date() == entry_timestamp.date()
    ]
    if exit_bar_index > entry_bar_index:
        by_index = [
            bar
            for bar in same_day_bars
            if entry_bar_index < bar.bar_index <= exit_bar_index
        ]
        if by_index:
            return by_index

    return [
        bar
        for bar in same_day_bars
        if entry_timestamp < bar.parsed_timestamp <= exit_timestamp
    ]


def _trade_path_metrics(
    bars: list[OutcomeBar],
    *,
    direction: str,
    entry_price: float,
    stop_price: float,
    target_price: float,
    risk_points: float,
    entry_bar_index: int,
) -> dict[str, Any]:
    max_favorable_points = 0.0
    max_adverse_points = 0.0
    first_target_bar: OutcomeBar | None = None
    first_stop_bar: OutcomeBar | None = None
    max_favorable_bar: OutcomeBar | None = None
    max_adverse_bar: OutcomeBar | None = None

    for bar in bars:
        if direction == "long":
            favorable_points = max(0.0, bar.high - entry_price)
            adverse_points = max(0.0, entry_price - bar.low)
            target_hit = bar.high >= target_price
            stop_hit = bar.low <= stop_price
        else:
            favorable_points = max(0.0, entry_price - bar.low)
            adverse_points = max(0.0, bar.high - entry_price)
            target_hit = bar.low <= target_price
            stop_hit = bar.high >= stop_price

        if favorable_points > max_favorable_points:
            max_favorable_points = favorable_points
            max_favorable_bar = bar
        if adverse_points > max_adverse_points:
            max_adverse_points = adverse_points
            max_adverse_bar = bar
        if target_hit and first_target_bar is None:
            first_target_bar = bar
        if stop_hit and first_stop_bar is None:
            first_stop_bar = bar

    return {
        "max_favorable_points": max_favorable_points,
        "max_adverse_points": max_adverse_points,
        "first_target_bar_index": _bar_index_or_blank(first_target_bar),
        "first_target_time": _bar_time_or_blank(first_target_bar),
        "first_stop_bar_index": _bar_index_or_blank(first_stop_bar),
        "first_stop_time": _bar_time_or_blank(first_stop_bar),
        "bars_to_max_favorable": _bars_to_bar(max_favorable_bar, entry_bar_index),
        "bars_to_max_adverse": _bars_to_bar(max_adverse_bar, entry_bar_index),
        "diagnostic_label": _trade_path_label(first_target_bar, first_stop_bar),
        "risk_points": risk_points,
    }


def _trade_path_label(
    first_target_bar: OutcomeBar | None,
    first_stop_bar: OutcomeBar | None,
) -> str:
    if first_target_bar is None and first_stop_bar is None:
        return "neither_stop_nor_target_reached"
    if first_target_bar is None:
        return "stop_reached_target_not_reached"
    if first_stop_bar is None:
        return "target_reached_stop_not_reached"
    if first_target_bar.bar_index == first_stop_bar.bar_index:
        return "stop_and_target_same_bar"
    if first_stop_bar.bar_index < first_target_bar.bar_index:
        return "stop_before_target"
    return "target_before_stop"


def _risk_points(direction: str, entry_price: float, stop_price: float) -> float:
    if direction == "long":
        return entry_price - stop_price
    return stop_price - entry_price


def _target_distance_points(direction: str, entry_price: float, target_price: float) -> float:
    if direction == "long":
        return target_price - entry_price
    return entry_price - target_price


def _bar_index_or_blank(bar: OutcomeBar | None) -> int | str:
    return "" if bar is None else bar.bar_index


def _bar_time_or_blank(bar: OutcomeBar | None) -> str:
    return "" if bar is None else bar.timestamp


def _bars_to_bar(bar: OutcomeBar | None, entry_bar_index: int) -> int | str:
    return "" if bar is None else max(0, bar.bar_index - entry_bar_index)


def _evaluate_one_signal(
    signal: dict[str, Any],
    bars_by_symbol: dict[str, list[OutcomeBar]],
    costs: OutcomeCosts,
    *,
    entry_match_mode: str,
) -> dict[str, Any]:
    symbol = str(signal.get("symbol", ""))
    direction = str(signal.get("direction", ""))
    if direction not in {"long", "short"}:
        raise TradeOutcomeError(f"Unsupported candidate direction: {direction!r}")

    entry_bar_index = _to_int(signal.get("bar_index"), "bar_index")
    entry_time = str(signal.get("bar_start_time") or signal.get("generated_at") or "")
    entry_timestamp = _parse_timestamp(entry_time)
    entry_price = _to_float(signal.get("signal_price"), "signal_price")
    stop_price = _to_float(signal.get("stop_price"), "stop_price")
    target_price = _to_float(signal.get("target_price"), "target_price")

    following_bars, resolved_match_mode = _following_bars_for_signal(
        bars_by_symbol.get(symbol, []),
        entry_bar_index=entry_bar_index,
        entry_timestamp=entry_timestamp,
        entry_match_mode=entry_match_mode,
    )
    exit_bar, exit_price, exit_reason = _find_exit(
        following_bars,
        direction=direction,
        stop_price=stop_price,
        target_price=target_price,
        fallback_price=entry_price,
    )
    exit_bar_index = exit_bar.bar_index if exit_bar is not None else entry_bar_index
    exit_time = exit_bar.timestamp if exit_bar is not None else entry_time
    if resolved_match_mode == "timestamp" and exit_bar is not None:
        holding_bars = following_bars.index(exit_bar) + 1
    else:
        holding_bars = max(0, exit_bar_index - entry_bar_index)

    gross_points = _gross_points(direction, entry_price, exit_price)
    risk_points = abs(entry_price - stop_price)
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
            f"{costs.instrument_root} conservative stop/target scan; "
            f"entry_match_mode={resolved_match_mode}"
        ),
    }


def _following_bars_for_signal(
    bars: list[OutcomeBar],
    *,
    entry_bar_index: int,
    entry_timestamp: datetime,
    entry_match_mode: str,
) -> tuple[list[OutcomeBar], str]:
    same_day_bars = [
        bar
        for bar in bars
        if bar.parsed_timestamp.date() == entry_timestamp.date()
    ]
    if entry_match_mode == "bar_index":
        return (
            [bar for bar in same_day_bars if bar.bar_index > entry_bar_index],
            "bar_index",
        )
    if entry_match_mode == "timestamp":
        return (
            [bar for bar in same_day_bars if bar.parsed_timestamp > entry_timestamp],
            "timestamp",
        )

    by_bar_index = [bar for bar in same_day_bars if bar.bar_index > entry_bar_index]
    if by_bar_index:
        return by_bar_index, "bar_index"
    return (
        [bar for bar in same_day_bars if bar.parsed_timestamp > entry_timestamp],
        "timestamp",
    )


def _find_exit(
    bars: list[OutcomeBar],
    *,
    direction: str,
    stop_price: float,
    target_price: float,
    fallback_price: float,
) -> tuple[OutcomeBar | None, float, str]:
    if not bars:
        return None, fallback_price, "no_following_bar"

    for bar in bars:
        if direction == "long":
            stop_hit = bar.low <= stop_price
            target_hit = bar.high >= target_price
        else:
            stop_hit = bar.high >= stop_price
            target_hit = bar.low <= target_price

        if stop_hit and target_hit:
            return bar, stop_price, "ambiguous_stop_first"
        if stop_hit:
            return bar, stop_price, "stop_hit"
        if target_hit:
            return bar, target_price, "target_hit"

    final_bar = bars[-1]
    return final_bar, final_bar.close, "end_of_session"


def _load_outcome_costs(
    signal_rows: list[dict[str, Any]],
    *,
    instrument_root: str | None,
    slippage_ticks_per_side: int | None,
    cost_config: dict[str, Any] | None,
    instrument_config: dict[str, Any] | None,
) -> OutcomeCosts:
    loaded_cost_config = load_yaml(DEFAULT_COST_CONFIG) if cost_config is None else cost_config
    loaded_instrument_config = instrument_config
    resolved_root = instrument_root.upper() if instrument_root else None

    if resolved_root is None:
        known_roots = set(loaded_cost_config.get("commissions", {}).keys())
        if loaded_instrument_config is not None:
            known_roots.add(str(loaded_instrument_config["symbol"]))
        resolved_root = _infer_instrument_root(str(signal_rows[0]["symbol"]), known_roots)

    if loaded_instrument_config is None:
        loaded_instrument_config = load_yaml(
            f"{DEFAULT_INSTRUMENT_CONFIG_DIR}/{resolved_root}.yaml",
        )

    cost_commissions = loaded_cost_config.get("commissions", {})
    commission_config = cost_commissions.get(resolved_root, {})
    commission_per_side = commission_config.get(
        "commission_per_side_usd",
        loaded_instrument_config["default_commission_per_side_usd"],
    )
    slippage_ticks = (
        slippage_ticks_per_side
        if slippage_ticks_per_side is not None
        else int(loaded_cost_config["slippage"]["default_ticks_per_side"])
    )
    if slippage_ticks < 0:
        raise TradeOutcomeError("slippage_ticks_per_side must be nonnegative")

    return OutcomeCosts(
        instrument_root=resolved_root,
        tick_size=_to_float(loaded_instrument_config["tick_size"], "tick_size"),
        tick_value_usd=_to_float(loaded_instrument_config["tick_value_usd"], "tick_value_usd"),
        point_value_usd=_to_float(loaded_instrument_config["point_value_usd"], "point_value_usd"),
        commission_per_side_usd=_to_float(commission_per_side, "commission_per_side_usd"),
        slippage_ticks_per_side=slippage_ticks,
    )


def _infer_instrument_root(symbol: str, known_roots: set[str]) -> str:
    root_letters = re.match(r"[A-Za-z]+", symbol)
    if root_letters is None:
        raise TradeOutcomeError(f"Cannot infer instrument root from symbol: {symbol!r}")

    symbol_prefix = root_letters.group(0).upper()
    for root in sorted(known_roots, key=len, reverse=True):
        root_text = root.upper()
        if symbol_prefix.startswith(root_text):
            return root_text
    raise TradeOutcomeError(f"Cannot match symbol {symbol!r} to a known instrument root")


def _bars_by_symbol(bars: list[OutcomeBar]) -> dict[str, list[OutcomeBar]]:
    grouped: dict[str, list[OutcomeBar]] = {}
    for bar in bars:
        grouped.setdefault(bar.symbol, []).append(bar)
    for symbol_bars in grouped.values():
        symbol_bars.sort(key=lambda bar: (bar.parsed_timestamp, bar.bar_index))
    return grouped


def _normalize_bar(row: dict[str, Any]) -> OutcomeBar:
    timestamp = str(row["timestamp"])
    return OutcomeBar(
        timestamp=timestamp,
        parsed_timestamp=_parse_timestamp(timestamp),
        symbol=str(row["symbol"]),
        bar_index=_to_int(row["bar_index"], "bar_index"),
        high=_to_float(row["high"], "high"),
        low=_to_float(row["low"], "low"),
        close=_to_float(row["close"], "close"),
    )


def _gross_points(direction: str, entry_price: float, exit_price: float) -> float:
    if direction == "long":
        return exit_price - entry_price
    return entry_price - exit_price


def _parse_timestamp(value: str) -> datetime:
    timestamp_text = value.strip()
    for timestamp_format in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(timestamp_text, timestamp_format)
        except ValueError:
            continue
    raise TradeOutcomeError(f"Invalid timestamp: {value!r}")


def _to_int(value: Any, field_name: str) -> int:
    try:
        return int(str(value))
    except ValueError as exc:
        raise TradeOutcomeError(f"Invalid integer field {field_name}: {value!r}") from exc


def _to_float(value: Any, field_name: str) -> float:
    try:
        return float(str(value))
    except ValueError as exc:
        raise TradeOutcomeError(f"Invalid numeric field {field_name}: {value!r}") from exc


def _format_number(value: float) -> str:
    return f"{value:.8f}".rstrip("0").rstrip(".")
