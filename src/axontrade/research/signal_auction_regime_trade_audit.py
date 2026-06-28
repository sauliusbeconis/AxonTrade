"""Trade-level audit rows for selected auction-regime stacks."""

from __future__ import annotations

from collections import Counter, OrderedDict, defaultdict
from typing import Any, Iterable

from axontrade.research.signal_auction_regime_breakeven_report import (
    _filter_bars_by_dates as _filter_breakeven_bars_by_dates,
    _filter_rows_by_dates as _filter_breakeven_rows_by_dates,
    _normalize_direction_filters as _normalize_breakeven_direction_filters,
    _normalize_positive_grid as _normalize_breakeven_positive_grid,
    _passes_selection as _passes_breakeven_selection,
    _select_best_train_exit_row,
    _selected_train_holdout_pairs as _selected_breakeven_train_holdout_pairs,
    _selection_trade_dates as _breakeven_selection_trade_dates,
    _signals_for_regime_rows as _breakeven_signals_for_regime_rows,
    _sorted_rows as _sort_breakeven_rows,
)
from axontrade.research.signal_auction_regime_target_r_report import (
    _filter_bars_by_dates as _filter_target_bars_by_dates,
    _filter_rows_by_dates as _filter_target_rows_by_dates,
    _normalize_direction_filters as _normalize_target_direction_filters,
    _normalize_positive_grid as _normalize_target_positive_grid,
    _passes_selection as _passes_target_selection,
    _select_best_train_target_row,
    _selected_train_holdout_pairs as _selected_target_train_holdout_pairs,
    _selection_trade_dates as _target_selection_trade_dates,
    _signals_for_regime_rows as _target_signals_for_regime_rows,
    _sorted_rows as _sort_target_rows,
)
from axontrade.research.signal_dynamic_exit_experiments import (
    evaluate_signal_breakeven_stop_outcomes,
    run_signal_breakeven_stop_sweep,
)
from axontrade.research.signal_target_experiments import (
    _signals_with_target_r,
    run_signal_target_r_sweep,
)
from axontrade.research.trade_outcomes import evaluate_trade_outcomes


SIGNAL_AUCTION_REGIME_TRADE_AUDIT_HEADER = [
    "schema_version",
    "split_id",
    "sample",
    "selected_on_train",
    "trade_dates",
    "stack_type",
    "trade_date",
    "sample_signal_occurrence",
    "sample_duplicate_signal",
    "signal_id",
    "symbol",
    "direction",
    "decision",
    "entry_time",
    "selected_direction_filter",
    "selected_target_r_multiple",
    "selected_breakeven_trigger_r",
    "auction_direction_filter",
    "max_original_reward_risk",
    "min_minutes_after_rth_open",
    "max_minutes_after_rth_open",
    "max_session_range_points",
    "max_fade_edge_score",
    "max_vwap_stretch_points",
    "max_open_stretch_points",
    "original_reward_risk",
    "minutes_after_rth_open",
    "session_range_points",
    "fade_edge_score",
    "direction_aware_vwap_stretch_points",
    "direction_aware_open_stretch_points",
    "original_exit_reason",
    "original_net_usd",
    "selected_outcome_id",
    "selected_exit_reason",
    "selected_exit_time",
    "selected_target_price",
    "selected_exit_price",
    "selected_r_multiple",
    "selected_net_usd",
    "notes",
]
_STACK_TYPES = {"target_r", "breakeven"}


class SignalAuctionRegimeTradeAuditError(ValueError):
    """Raised when a selected auction-regime stack cannot be audited."""


def audit_signal_auction_regime_trades(
    *,
    bars: Iterable[dict[str, Any]],
    signal_rows: Iterable[dict[str, Any]],
    regime_rows: Iterable[dict[str, Any]],
    selection_rows: Iterable[dict[str, Any]],
    stack_type: str,
    target_r_multiples: Iterable[float],
    breakeven_trigger_r_multiples: Iterable[float] = (),
    direction_filters: Iterable[str] = ("all",),
    minimum_train_trades: int = 1,
    instrument_root: str | None = None,
    slippage_ticks_per_side: int | None = None,
    entry_match_mode: str = "auto",
) -> list[dict[str, Any]]:
    """Emit one row per selected split candidate after auction/exits are applied."""

    selected_stack_type = stack_type.strip().lower()
    if selected_stack_type not in _STACK_TYPES:
        raise SignalAuctionRegimeTradeAuditError(
            "stack_type must be one of: " + ", ".join(sorted(_STACK_TYPES)),
        )
    if minimum_train_trades <= 0:
        raise SignalAuctionRegimeTradeAuditError("minimum_train_trades must be positive")

    normalized_bars = list(bars)
    signals = list(signal_rows)
    signal_by_id = _signal_rows_by_id(signals)
    if selected_stack_type == "target_r":
        rows = _audit_target_r_stack(
            bars=normalized_bars,
            signals=signals,
            signal_by_id=signal_by_id,
            regime_rows=list(regime_rows),
            selection_rows=selection_rows,
            target_r_multiples=target_r_multiples,
            direction_filters=direction_filters,
            minimum_train_trades=minimum_train_trades,
            instrument_root=instrument_root,
            slippage_ticks_per_side=slippage_ticks_per_side,
            entry_match_mode=entry_match_mode,
        )
    else:
        rows = _audit_breakeven_stack(
            bars=normalized_bars,
            signals=signals,
            signal_by_id=signal_by_id,
            regime_rows=list(regime_rows),
            selection_rows=selection_rows,
            target_r_multiples=target_r_multiples,
            breakeven_trigger_r_multiples=breakeven_trigger_r_multiples,
            direction_filters=direction_filters,
            minimum_train_trades=minimum_train_trades,
            instrument_root=instrument_root,
            slippage_ticks_per_side=slippage_ticks_per_side,
            entry_match_mode=entry_match_mode,
        )
    return _with_duplicate_markers(rows)


def _audit_target_r_stack(
    *,
    bars: list[dict[str, Any]],
    signals: list[dict[str, Any]],
    signal_by_id: dict[str, dict[str, Any]],
    regime_rows: list[dict[str, Any]],
    selection_rows: Iterable[dict[str, Any]],
    target_r_multiples: Iterable[float],
    direction_filters: Iterable[str],
    minimum_train_trades: int,
    instrument_root: str | None,
    slippage_ticks_per_side: int | None,
    entry_match_mode: str,
) -> list[dict[str, Any]]:
    diagnostics = _sort_target_rows(regime_rows)
    targets = _normalize_target_positive_grid(target_r_multiples, "target_r_multiples")
    directions = _normalize_target_direction_filters(direction_filters)
    audit_rows: list[dict[str, Any]] = []
    for train_selection, holdout_selection in _selected_target_train_holdout_pairs(selection_rows):
        train_dates = _target_selection_trade_dates(train_selection)
        train_base = _filter_target_rows_by_dates(diagnostics, train_dates)
        train_eligible = [
            row for row in train_base if _passes_target_selection(row, train_selection)
        ]
        train_signals = _target_signals_for_regime_rows(signals, train_eligible)
        selected_exit = _select_best_train_target_row(
            run_signal_target_r_sweep(
                _filter_target_bars_by_dates(bars, train_dates),
                train_signals,
                target_r_multiples=targets,
                direction_filters=directions,
                instrument_root=instrument_root,
                slippage_ticks_per_side=slippage_ticks_per_side,
                entry_match_mode=entry_match_mode,
            ),
            minimum_train_trades=minimum_train_trades,
        )

        split_id = str(train_selection["split_id"])
        for sample, dates in (
            ("train", train_dates),
            ("holdout", _target_selection_trade_dates(holdout_selection)),
        ):
            sample_base = _filter_target_rows_by_dates(diagnostics, dates)
            outcomes = _target_outcomes_for_selection(
                bars=_filter_target_bars_by_dates(bars, dates),
                signals=_target_signals_for_regime_rows(
                    signals,
                    [
                        row
                        for row in sample_base
                        if _passes_target_selection(row, train_selection)
                    ],
                ),
                selected_exit=selected_exit,
                instrument_root=instrument_root,
                slippage_ticks_per_side=slippage_ticks_per_side,
                entry_match_mode=entry_match_mode,
            )
            audit_rows.extend(
                _sample_audit_rows(
                    sample_base=sample_base,
                    signal_by_id=signal_by_id,
                    outcomes=outcomes,
                    stack_type="target_r",
                    split_id=split_id,
                    sample=sample,
                    selected_on_train=True,
                    trade_dates=dates,
                    selection=train_selection,
                    selected_direction_filter=str(selected_exit["direction_filter"]),
                    selected_target_r=str(selected_exit["target_r_multiple"]),
                    selected_breakeven_trigger="",
                    passes_selection=_passes_target_selection,
                ),
            )
    return audit_rows


def _audit_breakeven_stack(
    *,
    bars: list[dict[str, Any]],
    signals: list[dict[str, Any]],
    signal_by_id: dict[str, dict[str, Any]],
    regime_rows: list[dict[str, Any]],
    selection_rows: Iterable[dict[str, Any]],
    target_r_multiples: Iterable[float],
    breakeven_trigger_r_multiples: Iterable[float],
    direction_filters: Iterable[str],
    minimum_train_trades: int,
    instrument_root: str | None,
    slippage_ticks_per_side: int | None,
    entry_match_mode: str,
) -> list[dict[str, Any]]:
    diagnostics = _sort_breakeven_rows(regime_rows)
    targets = _normalize_breakeven_positive_grid(target_r_multiples, "target_r_multiples")
    triggers = _normalize_breakeven_positive_grid(
        breakeven_trigger_r_multiples,
        "breakeven_trigger_r_multiples",
    )
    directions = _normalize_breakeven_direction_filters(direction_filters)
    audit_rows: list[dict[str, Any]] = []
    for train_selection, holdout_selection in _selected_breakeven_train_holdout_pairs(
        selection_rows,
    ):
        train_dates = _breakeven_selection_trade_dates(train_selection)
        train_base = _filter_breakeven_rows_by_dates(diagnostics, train_dates)
        train_eligible = [
            row for row in train_base if _passes_breakeven_selection(row, train_selection)
        ]
        train_signals = _breakeven_signals_for_regime_rows(signals, train_eligible)
        selected_exit = _select_best_train_exit_row(
            run_signal_breakeven_stop_sweep(
                _filter_breakeven_bars_by_dates(bars, train_dates),
                train_signals,
                target_r_multiples=targets,
                breakeven_trigger_r_multiples=triggers,
                direction_filters=directions,
                instrument_root=instrument_root,
                slippage_ticks_per_side=slippage_ticks_per_side,
                entry_match_mode=entry_match_mode,
            ),
            minimum_train_trades=minimum_train_trades,
        )

        split_id = str(train_selection["split_id"])
        for sample, dates in (
            ("train", train_dates),
            ("holdout", _breakeven_selection_trade_dates(holdout_selection)),
        ):
            sample_base = _filter_breakeven_rows_by_dates(diagnostics, dates)
            outcomes = _breakeven_outcomes_for_selection(
                bars=_filter_breakeven_bars_by_dates(bars, dates),
                signals=_breakeven_signals_for_regime_rows(
                    signals,
                    [
                        row
                        for row in sample_base
                        if _passes_breakeven_selection(row, train_selection)
                    ],
                ),
                selected_exit=selected_exit,
                instrument_root=instrument_root,
                slippage_ticks_per_side=slippage_ticks_per_side,
                entry_match_mode=entry_match_mode,
            )
            audit_rows.extend(
                _sample_audit_rows(
                    sample_base=sample_base,
                    signal_by_id=signal_by_id,
                    outcomes=outcomes,
                    stack_type="breakeven",
                    split_id=split_id,
                    sample=sample,
                    selected_on_train=True,
                    trade_dates=dates,
                    selection=train_selection,
                    selected_direction_filter=str(selected_exit["direction_filter"]),
                    selected_target_r=str(selected_exit["target_r_multiple"]),
                    selected_breakeven_trigger=str(selected_exit["breakeven_trigger_r"]),
                    passes_selection=_passes_breakeven_selection,
                ),
            )
    return audit_rows


def _target_outcomes_for_selection(
    *,
    bars: list[dict[str, Any]],
    signals: list[dict[str, Any]],
    selected_exit: dict[str, Any],
    instrument_root: str | None,
    slippage_ticks_per_side: int | None,
    entry_match_mode: str,
) -> dict[str, dict[str, Any]]:
    adjusted = _signals_with_target_r(
        signals,
        target_r=float(str(selected_exit["target_r_multiple"])),
        direction_filter=str(selected_exit["direction_filter"]),
    )
    outcomes = evaluate_trade_outcomes(
        bars,
        adjusted,
        instrument_root=instrument_root,
        slippage_ticks_per_side=slippage_ticks_per_side,
        entry_match_mode=entry_match_mode,
    )
    return {str(row["signal_id"]): row for row in outcomes}


def _breakeven_outcomes_for_selection(
    *,
    bars: list[dict[str, Any]],
    signals: list[dict[str, Any]],
    selected_exit: dict[str, Any],
    instrument_root: str | None,
    slippage_ticks_per_side: int | None,
    entry_match_mode: str,
) -> dict[str, dict[str, Any]]:
    outcomes = evaluate_signal_breakeven_stop_outcomes(
        bars,
        signals,
        target_r_multiple=float(str(selected_exit["target_r_multiple"])),
        breakeven_trigger_r=float(str(selected_exit["breakeven_trigger_r"])),
        direction_filter=str(selected_exit["direction_filter"]),
        instrument_root=instrument_root,
        slippage_ticks_per_side=slippage_ticks_per_side,
        entry_match_mode=entry_match_mode,
    )
    return {str(row["signal_id"]): row for row in outcomes}


def _sample_audit_rows(
    *,
    sample_base: list[dict[str, Any]],
    signal_by_id: dict[str, dict[str, Any]],
    outcomes: dict[str, dict[str, Any]],
    stack_type: str,
    split_id: str,
    sample: str,
    selected_on_train: bool,
    trade_dates: list[str],
    selection: dict[str, Any],
    selected_direction_filter: str,
    selected_target_r: str,
    selected_breakeven_trigger: str,
    passes_selection: Any,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for regime_row in sample_base:
        signal_id = str(regime_row["signal_id"])
        signal_row = signal_by_id.get(signal_id, {})
        outcome = outcomes.get(signal_id, {})
        auction_eligible = passes_selection(regime_row, selection)
        if outcome:
            decision = "evaluated"
        elif auction_eligible:
            decision = "exit_direction_skipped"
        else:
            decision = "auction_skipped"
        rows.append(
            _audit_row(
                regime_row=regime_row,
                signal_row=signal_row,
                outcome=outcome,
                stack_type=stack_type,
                split_id=split_id,
                sample=sample,
                selected_on_train=selected_on_train,
                trade_dates=trade_dates,
                decision=decision,
                selection=selection,
                selected_direction_filter=selected_direction_filter,
                selected_target_r=selected_target_r,
                selected_breakeven_trigger=selected_breakeven_trigger,
            ),
        )
    return rows


def _audit_row(
    *,
    regime_row: dict[str, Any],
    signal_row: dict[str, Any],
    outcome: dict[str, Any],
    stack_type: str,
    split_id: str,
    sample: str,
    selected_on_train: bool,
    trade_dates: list[str],
    decision: str,
    selection: dict[str, Any],
    selected_direction_filter: str,
    selected_target_r: str,
    selected_breakeven_trigger: str,
) -> dict[str, Any]:
    return OrderedDict(
        [
            ("schema_version", 1),
            ("split_id", split_id),
            ("sample", sample),
            ("selected_on_train", str(selected_on_train).lower()),
            ("trade_dates", ";".join(trade_dates)),
            ("stack_type", stack_type),
            ("trade_date", str(regime_row["entry_time"]).split(maxsplit=1)[0]),
            ("sample_signal_occurrence", ""),
            ("sample_duplicate_signal", ""),
            ("signal_id", regime_row["signal_id"]),
            ("symbol", signal_row.get("symbol", "")),
            ("direction", regime_row["direction"]),
            ("decision", decision),
            ("entry_time", regime_row["entry_time"]),
            ("selected_direction_filter", selected_direction_filter),
            ("selected_target_r_multiple", selected_target_r),
            ("selected_breakeven_trigger_r", selected_breakeven_trigger),
            ("auction_direction_filter", selection["direction_filter"]),
            ("max_original_reward_risk", selection["max_original_reward_risk"]),
            ("min_minutes_after_rth_open", selection["min_minutes_after_rth_open"]),
            ("max_minutes_after_rth_open", selection["max_minutes_after_rth_open"]),
            ("max_session_range_points", selection["max_session_range_points"]),
            ("max_fade_edge_score", selection["max_fade_edge_score"]),
            ("max_vwap_stretch_points", selection["max_vwap_stretch_points"]),
            ("max_open_stretch_points", selection["max_open_stretch_points"]),
            ("original_reward_risk", regime_row["original_reward_risk"]),
            ("minutes_after_rth_open", regime_row["minutes_after_rth_open"]),
            ("session_range_points", regime_row["session_range_points"]),
            ("fade_edge_score", regime_row["fade_edge_score"]),
            (
                "direction_aware_vwap_stretch_points",
                regime_row["direction_aware_vwap_stretch_points"],
            ),
            (
                "direction_aware_open_stretch_points",
                regime_row["direction_aware_open_stretch_points"],
            ),
            ("original_exit_reason", regime_row["exit_reason"]),
            ("original_net_usd", regime_row["net_usd"]),
            ("selected_outcome_id", outcome.get("outcome_id", "")),
            ("selected_exit_reason", outcome.get("exit_reason", "")),
            ("selected_exit_time", outcome.get("exit_time", "")),
            ("selected_target_price", outcome.get("target_price", "")),
            ("selected_exit_price", outcome.get("exit_price", "")),
            ("selected_r_multiple", outcome.get("r_multiple", "")),
            ("selected_net_usd", outcome.get("net_usd", "")),
            ("notes", _decision_note(decision)),
        ],
    )


def _with_duplicate_markers(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter((str(row["sample"]), str(row["signal_id"])) for row in rows)
    occurrences: defaultdict[tuple[str, str], int] = defaultdict(int)
    marked_rows: list[dict[str, Any]] = []
    for row in rows:
        key = (str(row["sample"]), str(row["signal_id"]))
        occurrences[key] += 1
        marked = OrderedDict(row)
        marked["sample_signal_occurrence"] = occurrences[key]
        marked["sample_duplicate_signal"] = str(counts[key] > 1).lower()
        marked_rows.append(marked)
    return marked_rows


def _signal_rows_by_id(signal_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        str(row["signal_id"]): row
        for row in signal_rows
        if str(row.get("event_type", "")) == "candidate_signal"
    }


def _decision_note(decision: str) -> str:
    if decision == "evaluated":
        return "auction rule accepted candidate and selected exit policy evaluated it"
    if decision == "exit_direction_skipped":
        return "auction rule accepted candidate but selected exit direction filter skipped it"
    return "selected auction-regime rule skipped this candidate"
