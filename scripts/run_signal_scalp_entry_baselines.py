#!/usr/bin/env python3
"""Generate synthetic scalp-entry baselines and test scaled exits."""

from __future__ import annotations

import argparse
import csv
import random
from collections import defaultdict
from datetime import time
from pathlib import Path
from typing import Any

from axontrade.data import (
    SierraExportError,
    load_sierra_bar_study_rows,
    load_sierra_export_config,
    normalize_sierra_bar_study_file,
)
from axontrade.research import (
    SIGNAL_SCALED_SCALP_SWEEP_HEADER,
    SIGNAL_SCALED_SCALP_WALK_FORWARD_HEADER,
    SignalScaledScalpExperimentError,
    run_signal_scaled_scalp_sweep,
    run_signal_scaled_scalp_walk_forward_sweep,
)
from axontrade.research.trade_outcomes import _parse_timestamp


DEFAULT_EXPORT_CONFIG = "config/research/sierra_outcome_bar_export.yaml"
DEFAULT_RANDOM_SEED = 20260628
DEFAULT_MARKET_START = time(9, 45)
DEFAULT_MARKET_END = time(15, 45)
DEFAULT_SESSION_ENTRY_START = time(10, 0)
DEFAULT_SESSION_ENTRY_END = time(15, 15)
DEFAULT_OPENING_RANGE_START = time(9, 30)
DEFAULT_OPENING_RANGE_END = time(10, 0)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate random, VWAP-extension, impulse, and order-flow-proxy "
            "scalp-entry baselines, then test scaled two-contract exits."
        ),
    )
    parser.add_argument("bars_export", help="Path to Sierra exported bar/study text or CSV file.")
    parser.add_argument("output", help="Path to write baseline scalp sweep CSV rows.")
    parser.add_argument("--symbol", required=True, help="Futures symbol for the export, e.g. ESU26-CME.")
    parser.add_argument("--chart-number", type=int, default=2, help="Chart number to write in export rows.")
    parser.add_argument(
        "--session-phase",
        default="rth",
        help="Session phase label for rows when not present in the export.",
    )
    parser.add_argument(
        "--export-config",
        default=DEFAULT_EXPORT_CONFIG,
        help="Sierra export normalization config for outcome bar rows.",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=DEFAULT_RANDOM_SEED,
        help="Deterministic seed for random baseline entries.",
    )
    parser.add_argument(
        "--random-per-day",
        type=int,
        default=25,
        help="Number of random baseline entries to generate per trade date.",
    )
    parser.add_argument(
        "--max-rule-entries-per-day",
        type=int,
        default=20,
        help="Maximum entries per trade date for each non-random rule.",
    )
    parser.add_argument(
        "--minimum-spacing-seconds",
        type=int,
        default=300,
        help="Minimum spacing between generated rule entries.",
    )
    parser.add_argument(
        "--strategy-ids",
        help="Comma-separated generated strategy IDs to include. Defaults to all.",
    )
    parser.add_argument(
        "--entry-family-set",
        choices=("scalp", "session", "all"),
        default="scalp",
        help=(
            "Generated entry families to include. 'scalp' preserves the original "
            "short-horizon rules; 'session' adds time-based OR/VWAP structure rules."
        ),
    )
    parser.add_argument(
        "--output-mode",
        choices=("sweep", "walk_forward"),
        default="sweep",
        help="Write aggregate sweep rows or rolling walk-forward rows.",
    )
    parser.add_argument(
        "--train-date-count",
        type=int,
        default=8,
        help="Number of consecutive generated-signal trade dates per training window.",
    )
    parser.add_argument(
        "--holdout-date-count",
        type=int,
        default=1,
        help="Number of consecutive generated-signal trade dates per holdout window.",
    )
    parser.add_argument(
        "--minimum-train-trades",
        type=int,
        default=4,
        help="Minimum selected training trades required for each generated strategy.",
    )
    parser.add_argument(
        "--window-step-date-count",
        type=int,
        default=1,
        help="Trade-date step between walk-forward windows; use holdout count for non-overlap.",
    )
    parser.add_argument(
        "--first-target-points",
        default="0.5,1,1.5",
        help="Comma-separated fixed first-target point distances to test.",
    )
    parser.add_argument(
        "--stop-points",
        default="1,1.5,2",
        help="Comma-separated fixed initial stop point distances to test.",
    )
    parser.add_argument(
        "--runner-target-points",
        default="1.5,2,3,5",
        help="Comma-separated fixed runner target point distances to test.",
    )
    parser.add_argument(
        "--runner-stop-modes",
        default="breakeven,initial",
        help="Comma-separated runner stop modes to test: breakeven,initial.",
    )
    parser.add_argument(
        "--instrument-root",
        help="Instrument root for cost modeling, e.g. ES or MES. Defaults to symbol inference.",
    )
    parser.add_argument(
        "--slippage-ticks-per-side",
        type=int,
        help="Override default slippage assumption from config/research/default_costs.yaml.",
    )
    parser.add_argument(
        "--slippage-ticks-per-contract",
        type=float,
        help=(
            "Override total slippage ticks per contract for the whole trade; "
            "use 1 to model passive entry plus one-tick market exit."
        ),
    )
    parser.add_argument(
        "--entry-match-mode",
        choices=("bar_index", "timestamp", "auto"),
        default="auto",
        help="How to find bars after each generated entry.",
    )
    parser.add_argument(
        "--entry-fill-mode",
        choices=("immediate", "passive_touch"),
        default="immediate",
        help="Use generated entry immediately, or require a later passive limit touch.",
    )
    parser.add_argument(
        "--maximum-passive-fill-seconds",
        type=int,
        default=60,
        help="Maximum seconds to wait for passive_touch entry fills.",
    )
    args = parser.parse_args()

    try:
        raw_rows = load_sierra_bar_study_rows(args.bars_export)
        normalized_rows = normalize_sierra_bar_study_file(
            args.bars_export,
            symbol=args.symbol,
            chart_number=args.chart_number,
            session_phase=args.session_phase,
            config=load_sierra_export_config(args.export_config),
            compute_opening_range=False,
        )
        feature_rows = _feature_rows(raw_rows, normalized_rows)
        signals_by_strategy = _generate_strategy_signals(
            feature_rows,
            random_seed=args.random_seed,
            random_per_day=args.random_per_day,
            max_rule_entries_per_day=args.max_rule_entries_per_day,
            minimum_spacing_seconds=args.minimum_spacing_seconds,
            entry_family_set=args.entry_family_set,
        )
        signals_by_strategy = _apply_entry_fill_mode(
            signals_by_strategy,
            feature_rows,
            entry_fill_mode=args.entry_fill_mode,
            maximum_passive_fill_seconds=args.maximum_passive_fill_seconds,
        )
        signals_by_strategy = _filter_strategy_signals(
            signals_by_strategy,
            strategy_ids=_parse_optional_string_list(args.strategy_ids),
        )
        experiment_rows = _run_output_mode(
            args.output_mode,
            normalized_rows=normalized_rows,
            signals_by_strategy=signals_by_strategy,
            first_target_points_values=_parse_float_list(args.first_target_points),
            stop_points_values=_parse_float_list(args.stop_points),
            runner_target_points_values=_parse_float_list(args.runner_target_points),
            runner_stop_modes=_parse_string_list(args.runner_stop_modes),
            instrument_root=args.instrument_root,
            slippage_ticks_per_side=args.slippage_ticks_per_side,
            slippage_ticks_per_contract=args.slippage_ticks_per_contract,
            entry_match_mode=args.entry_match_mode,
            train_date_count=args.train_date_count,
            holdout_date_count=args.holdout_date_count,
            minimum_train_trades=args.minimum_train_trades,
            window_step_date_count=args.window_step_date_count,
        )
    except (
        SierraExportError,
        SignalScaledScalpExperimentError,
        ValueError,
    ) as exc:
        print(f"error: {exc}")
        return 2

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        fieldnames = (
            SIGNAL_SCALED_SCALP_WALK_FORWARD_HEADER
            if args.output_mode == "walk_forward"
            else SIGNAL_SCALED_SCALP_SWEEP_HEADER
        )
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(experiment_rows)

    best_summary = _output_summary(args.output_mode, experiment_rows)
    print(
        f"wrote {len(experiment_rows)} scalp-entry baseline {args.output_mode} rows "
        f"to {output_path}; strategies={len(signals_by_strategy)}, {best_summary}",
    )
    return 0


def _run_output_mode(
    output_mode: str,
    *,
    normalized_rows: list[dict[str, Any]],
    signals_by_strategy: dict[str, list[dict[str, Any]]],
    first_target_points_values: list[float],
    stop_points_values: list[float],
    runner_target_points_values: list[float],
    runner_stop_modes: list[str],
    instrument_root: str | None,
    slippage_ticks_per_side: int | None,
    slippage_ticks_per_contract: float | None,
    entry_match_mode: str,
    train_date_count: int,
    holdout_date_count: int,
    minimum_train_trades: int,
    window_step_date_count: int,
) -> list[dict[str, Any]]:
    rows = []
    for signals in signals_by_strategy.values():
        if output_mode == "sweep":
            rows.extend(
                run_signal_scaled_scalp_sweep(
                    normalized_rows,
                    signals,
                    first_target_points_values=first_target_points_values,
                    stop_points_values=stop_points_values,
                    runner_target_points_values=runner_target_points_values,
                    runner_stop_modes=runner_stop_modes,
                    direction_filters=["all"],
                    instrument_root=instrument_root,
                    slippage_ticks_per_side=slippage_ticks_per_side,
                    slippage_ticks_per_contract=slippage_ticks_per_contract,
                    entry_match_mode=entry_match_mode,
                ),
            )
            continue

        rows.extend(
            run_signal_scaled_scalp_walk_forward_sweep(
                normalized_rows,
                signals,
                train_date_count=train_date_count,
                holdout_date_count=holdout_date_count,
                first_target_points_values=first_target_points_values,
                stop_points_values=stop_points_values,
                runner_target_points_values=runner_target_points_values,
                runner_stop_modes=runner_stop_modes,
                direction_filters=["all"],
                minimum_train_trades=minimum_train_trades,
                window_step_date_count=window_step_date_count,
                instrument_root=instrument_root,
                slippage_ticks_per_side=slippage_ticks_per_side,
                slippage_ticks_per_contract=slippage_ticks_per_contract,
                entry_match_mode=entry_match_mode,
            ),
        )
    return rows


def _output_summary(output_mode: str, rows: list[dict[str, Any]]) -> str:
    if output_mode == "walk_forward":
        holdout_rows = [row for row in rows if row["sample"] == "holdout"]
        holdout_trades = sum(int(row["evaluated_trades"]) for row in holdout_rows)
        holdout_net = sum(float(row["net_usd"]) for row in holdout_rows)
        return (
            f"holdout_windows={len(holdout_rows)}, "
            f"holdout_trades={holdout_trades}, "
            f"holdout_net_usd={holdout_net:.2f}"
        )

    best_rows = _best_rows_by_strategy(rows)
    best_summary = ", ".join(
        f"{row['strategy_id']}={float(row['net_usd']):.2f}/{row['evaluated_trades']}"
        for row in best_rows[:3]
    )
    return f"best={best_summary}"


def _feature_rows(
    raw_rows: list[dict[str, str]],
    normalized_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    cumulative_price_volume_by_date: dict[str, float] = defaultdict(float)
    cumulative_volume_by_date: dict[str, float] = defaultdict(float)
    for raw_row, normalized_row in zip(raw_rows, normalized_rows):
        timestamp = _parse_timestamp(str(normalized_row["timestamp"]))
        trade_date = timestamp.date().isoformat()
        close = float(normalized_row["close"])
        high = float(normalized_row["high"])
        low = float(normalized_row["low"])
        volume = _to_float(raw_row.get("Volume"), 0.0)
        exported_vwap = _optional_float(
            _first_raw_value(
                raw_row,
                "VWAP",
                "Volume Weighted Average Price - VWAP",
            ),
        )
        computed_vwap = _computed_session_vwap(
            raw_row,
            trade_date=trade_date,
            high=high,
            low=low,
            close=close,
            volume=volume,
            cumulative_price_volume_by_date=cumulative_price_volume_by_date,
            cumulative_volume_by_date=cumulative_volume_by_date,
        )
        rows.append(
            {
                **normalized_row,
                "parsed_timestamp": timestamp,
                "trade_date": trade_date,
                "open_float": float(normalized_row["open"]),
                "high_float": high,
                "low_float": low,
                "close_float": close,
                "bar_range": high - low,
                "vwap": exported_vwap if exported_vwap is not None else computed_vwap,
                "vwap_source": "exported" if exported_vwap is not None else "computed_session",
                "volume": volume,
                "trades": _to_float(raw_row.get("# of Trades"), 0.0),
                "bid_volume": _to_float(raw_row.get("Bid Volume"), 0.0),
                "ask_volume": _to_float(raw_row.get("Ask Volume"), 0.0),
                "delta": _to_float(raw_row.get("Ask Volume Bid Volume Difference"), 0.0),
                "delta_change": _to_float(
                    raw_row.get("Ask Volume Bid Volume Difference Change"),
                    0.0,
                ),
            },
        )
        rows[-1]["close_location"] = _close_location(
            low=rows[-1]["low_float"],
            high=rows[-1]["high_float"],
            close=rows[-1]["close_float"],
        )
    return rows


def _computed_session_vwap(
    raw_row: dict[str, str],
    *,
    trade_date: str,
    high: float,
    low: float,
    close: float,
    volume: float,
    cumulative_price_volume_by_date: dict[str, float],
    cumulative_volume_by_date: dict[str, float],
) -> float:
    typical_price = _to_float(raw_row.get("HLC Avg"), (high + low + close) / 3)
    if volume > 0:
        cumulative_price_volume_by_date[trade_date] += typical_price * volume
        cumulative_volume_by_date[trade_date] += volume
    if cumulative_volume_by_date[trade_date] <= 0:
        return close
    return cumulative_price_volume_by_date[trade_date] / cumulative_volume_by_date[trade_date]


def _generate_strategy_signals(
    feature_rows: list[dict[str, Any]],
    *,
    random_seed: int,
    random_per_day: int,
    max_rule_entries_per_day: int,
    minimum_spacing_seconds: int,
    entry_family_set: str = "scalp",
) -> dict[str, list[dict[str, Any]]]:
    if entry_family_set == "session":
        return _generate_session_structure_signals(
            feature_rows,
            max_rule_entries_per_day=max_rule_entries_per_day,
            minimum_spacing_seconds=minimum_spacing_seconds,
        )
    if entry_family_set not in {"scalp", "all"}:
        raise ValueError("entry_family_set must be one of: scalp, session, all")

    rows_by_date = _eligible_rows_by_date(feature_rows)
    signals_by_strategy: dict[str, list[dict[str, Any]]] = defaultdict(list)
    rng = random.Random(random_seed)

    for rows in rows_by_date.values():
        sample_size = min(random_per_day, len(rows))
        sample = sorted(rng.sample(rows, sample_size), key=lambda row: row["parsed_timestamp"])
        for index, row in enumerate(sample):
            direction = rng.choice(["long", "short"])
            strategy_id = f"random_{random_per_day}_per_day"
            signals_by_strategy[strategy_id].append(
                _signal_from_row(row, direction, strategy_id, index),
            )

    for threshold in (1.0, 2.0, 3.0, 4.0):
        strategy_id = f"vwap_extension_fade_{threshold:g}pt"
        for rows in rows_by_date.values():
            candidates = []
            for row in rows:
                distance_from_vwap = row["close_float"] - row["vwap"]
                if distance_from_vwap >= threshold:
                    candidates.append((row, "short"))
                elif distance_from_vwap <= -threshold:
                    candidates.append((row, "long"))
            signals_by_strategy[strategy_id].extend(
                _spaced_signals(
                    candidates,
                    strategy_id=strategy_id,
                    minimum_spacing_seconds=minimum_spacing_seconds,
                    max_per_day=max_rule_entries_per_day,
                ),
            )

    for lookback, threshold in ((3, 1.5), (5, 2.0), (10, 3.0)):
        fade_strategy_id = f"impulse_fade_{lookback}bar_{threshold:g}pt"
        continue_strategy_id = f"impulse_continue_{lookback}bar_{threshold:g}pt"
        for rows in rows_by_date.values():
            fade_candidates = []
            continue_candidates = []
            for index in range(lookback, len(rows)):
                row = rows[index]
                move = row["close_float"] - rows[index - lookback]["close_float"]
                if move >= threshold:
                    fade_candidates.append((row, "short"))
                    continue_candidates.append((row, "long"))
                elif move <= -threshold:
                    fade_candidates.append((row, "long"))
                    continue_candidates.append((row, "short"))
            signals_by_strategy[fade_strategy_id].extend(
                _spaced_signals(
                    fade_candidates,
                    strategy_id=fade_strategy_id,
                    minimum_spacing_seconds=minimum_spacing_seconds,
                    max_per_day=max_rule_entries_per_day,
                ),
            )
            signals_by_strategy[continue_strategy_id].extend(
                _spaced_signals(
                    continue_candidates,
                    strategy_id=continue_strategy_id,
                    minimum_spacing_seconds=minimum_spacing_seconds,
                    max_per_day=max_rule_entries_per_day,
                ),
            )

    for lookback, price_threshold, delta_threshold in (
        (3, 1.0, 20.0),
        (5, 1.5, 30.0),
        (10, 2.5, 50.0),
    ):
        strategy_id = (
            f"delta_impulse_continue_{lookback}bar_"
            f"{price_threshold:g}pt_{delta_threshold:g}d"
        )
        for rows in rows_by_date.values():
            candidates = []
            for index in range(lookback, len(rows)):
                row = rows[index]
                move = row["close_float"] - rows[index - lookback]["close_float"]
                delta_sum = sum(
                    previous_row["delta"]
                    for previous_row in rows[index - lookback + 1:index + 1]
                )
                if move >= price_threshold and delta_sum >= delta_threshold:
                    candidates.append((row, "long"))
                elif move <= -price_threshold and delta_sum <= -delta_threshold:
                    candidates.append((row, "short"))
            signals_by_strategy[strategy_id].extend(
                _spaced_signals(
                    candidates,
                    strategy_id=strategy_id,
                    minimum_spacing_seconds=minimum_spacing_seconds,
                    max_per_day=max_rule_entries_per_day,
                ),
            )

    for delta_threshold, close_location_threshold in (
        (10.0, 0.35),
        (20.0, 0.35),
        (30.0, 0.4),
    ):
        strategy_id = (
            f"delta_absorption_fade_{delta_threshold:g}d_"
            f"cl{close_location_threshold:g}"
        )
        for rows in rows_by_date.values():
            candidates = []
            for row in rows:
                close_location = row["close_location"]
                if row["delta"] >= delta_threshold and close_location <= close_location_threshold:
                    candidates.append((row, "short"))
                elif (
                    row["delta"] <= -delta_threshold
                    and close_location >= 1 - close_location_threshold
                ):
                    candidates.append((row, "long"))
            signals_by_strategy[strategy_id].extend(
                _spaced_signals(
                    candidates,
                    strategy_id=strategy_id,
                    minimum_spacing_seconds=minimum_spacing_seconds,
                    max_per_day=max_rule_entries_per_day,
                ),
            )

    for vwap_threshold, delta_threshold, close_location_threshold in (
        (2.0, 10.0, 0.5),
        (3.0, 20.0, 0.5),
        (4.0, 30.0, 0.55),
    ):
        strategy_id = (
            f"vwap_delta_exhaustion_fade_{vwap_threshold:g}pt_"
            f"{delta_threshold:g}d_cl{close_location_threshold:g}"
        )
        for rows in rows_by_date.values():
            candidates = []
            for row in rows:
                distance_from_vwap = row["close_float"] - row["vwap"]
                close_location = row["close_location"]
                if (
                    distance_from_vwap >= vwap_threshold
                    and row["delta"] >= delta_threshold
                    and close_location <= close_location_threshold
                ):
                    candidates.append((row, "short"))
                elif (
                    distance_from_vwap <= -vwap_threshold
                    and row["delta"] <= -delta_threshold
                    and close_location >= 1 - close_location_threshold
                ):
                    candidates.append((row, "long"))
            signals_by_strategy[strategy_id].extend(
                _spaced_signals(
                    candidates,
                    strategy_id=strategy_id,
                    minimum_spacing_seconds=minimum_spacing_seconds,
                    max_per_day=max_rule_entries_per_day,
                ),
            )

    if entry_family_set == "all":
        signals_by_strategy.update(
            _generate_session_structure_signals(
                feature_rows,
                max_rule_entries_per_day=max_rule_entries_per_day,
                minimum_spacing_seconds=minimum_spacing_seconds,
            ),
        )

    return dict(signals_by_strategy)


def _generate_session_structure_signals(
    feature_rows: list[dict[str, Any]],
    *,
    max_rule_entries_per_day: int,
    minimum_spacing_seconds: int,
) -> dict[str, list[dict[str, Any]]]:
    rows_by_date = _rows_by_date(feature_rows)
    signals_by_strategy: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for buffer_points in (0.5, 1.0, 2.0):
        strategy_id = f"opening_range_breakout_continue_30m_{buffer_points:g}pt"
        for rows in rows_by_date.values():
            opening_range = _opening_range(rows)
            if opening_range is None:
                continue
            or_high, or_low = opening_range
            high_break = or_high + buffer_points
            low_break = or_low - buffer_points
            candidates = []
            previous_close = None
            for row in rows:
                row_time = row["parsed_timestamp"].time()
                if previous_close is not None and _is_session_entry_time(row_time):
                    if previous_close < high_break <= row["close_float"]:
                        candidates.append((row, "long"))
                    elif previous_close > low_break >= row["close_float"]:
                        candidates.append((row, "short"))
                previous_close = row["close_float"]
            signals_by_strategy[strategy_id].extend(
                _spaced_signals(
                    candidates,
                    strategy_id=strategy_id,
                    minimum_spacing_seconds=minimum_spacing_seconds,
                    max_per_day=max_rule_entries_per_day,
                ),
            )

    for sweep_points in (0.5, 1.0, 2.0, 3.0):
        strategy_id = f"opening_range_sweep_fade_30m_{sweep_points:g}pt"
        for rows in rows_by_date.values():
            opening_range = _opening_range(rows)
            if opening_range is None:
                continue
            or_high, or_low = opening_range
            candidates = []
            for row in rows:
                if not _is_session_entry_time(row["parsed_timestamp"].time()):
                    continue
                if (
                    row["high_float"] >= or_high + sweep_points
                    and row["close_float"] <= or_high
                    and row["close_location"] <= 0.45
                ):
                    candidates.append((row, "short"))
                elif (
                    row["low_float"] <= or_low - sweep_points
                    and row["close_float"] >= or_low
                    and row["close_location"] >= 0.55
                ):
                    candidates.append((row, "long"))
            signals_by_strategy[strategy_id].extend(
                _spaced_signals(
                    candidates,
                    strategy_id=strategy_id,
                    minimum_spacing_seconds=minimum_spacing_seconds,
                    max_per_day=max_rule_entries_per_day,
                ),
            )

    for lookback_minutes, stretch_points in ((15, 2.0), (30, 3.0), (60, 4.0)):
        strategy_id = f"vwap_reclaim_continue_{lookback_minutes}m_{stretch_points:g}pt"
        for rows in rows_by_date.values():
            candidates = []
            for index in range(1, len(rows)):
                row = rows[index]
                if not _is_session_entry_time(row["parsed_timestamp"].time()):
                    continue
                previous_row = rows[index - 1]
                previous_distance = previous_row["close_float"] - previous_row["vwap"]
                current_distance = row["close_float"] - row["vwap"]
                lookback_rows = _lookback_rows(
                    rows,
                    index=index,
                    lookback_seconds=lookback_minutes * 60,
                )
                if not lookback_rows:
                    continue
                min_distance = min(
                    lookback_row["close_float"] - lookback_row["vwap"]
                    for lookback_row in lookback_rows
                )
                max_distance = max(
                    lookback_row["close_float"] - lookback_row["vwap"]
                    for lookback_row in lookback_rows
                )
                if (
                    min_distance <= -stretch_points
                    and previous_distance <= 0 < current_distance
                    and row["delta"] >= 0
                ):
                    candidates.append((row, "long"))
                elif (
                    max_distance >= stretch_points
                    and previous_distance >= 0 > current_distance
                    and row["delta"] <= 0
                ):
                    candidates.append((row, "short"))
            signals_by_strategy[strategy_id].extend(
                _spaced_signals(
                    candidates,
                    strategy_id=strategy_id,
                    minimum_spacing_seconds=minimum_spacing_seconds,
                    max_per_day=max_rule_entries_per_day,
                ),
            )

    for stretch_points, pullback_buffer_points in ((3.0, 1.0), (5.0, 1.5), (8.0, 2.0)):
        strategy_id = (
            f"vwap_pullback_continue_{stretch_points:g}pt_"
            f"pb{pullback_buffer_points:g}pt"
        )
        for rows in rows_by_date.values():
            candidates = []
            for row in rows:
                if not _is_session_entry_time(row["parsed_timestamp"].time()):
                    continue
                distance_from_vwap = row["close_float"] - row["vwap"]
                if (
                    distance_from_vwap >= stretch_points
                    and row["low_float"] <= row["vwap"] + pullback_buffer_points
                    and row["close_location"] >= 0.6
                    and row["delta"] >= 0
                ):
                    candidates.append((row, "long"))
                elif (
                    distance_from_vwap <= -stretch_points
                    and row["high_float"] >= row["vwap"] - pullback_buffer_points
                    and row["close_location"] <= 0.4
                    and row["delta"] <= 0
                ):
                    candidates.append((row, "short"))
            signals_by_strategy[strategy_id].extend(
                _spaced_signals(
                    candidates,
                    strategy_id=strategy_id,
                    minimum_spacing_seconds=minimum_spacing_seconds,
                    max_per_day=max_rule_entries_per_day,
                ),
            )

    return dict(signals_by_strategy)


def _filter_strategy_signals(
    signals_by_strategy: dict[str, list[dict[str, Any]]],
    *,
    strategy_ids: list[str] | None,
) -> dict[str, list[dict[str, Any]]]:
    if strategy_ids is None:
        return signals_by_strategy
    filtered = {
        strategy_id: signals
        for strategy_id, signals in signals_by_strategy.items()
        if strategy_id in set(strategy_ids)
    }
    missing_ids = sorted(set(strategy_ids) - set(filtered))
    if missing_ids:
        raise ValueError("unknown strategy IDs: " + ", ".join(missing_ids))
    return filtered


def _apply_entry_fill_mode(
    signals_by_strategy: dict[str, list[dict[str, Any]]],
    feature_rows: list[dict[str, Any]],
    *,
    entry_fill_mode: str,
    maximum_passive_fill_seconds: int,
) -> dict[str, list[dict[str, Any]]]:
    if entry_fill_mode == "immediate":
        return signals_by_strategy
    if entry_fill_mode != "passive_touch":
        raise ValueError(f"unsupported entry_fill_mode: {entry_fill_mode}")
    if maximum_passive_fill_seconds <= 0:
        raise ValueError("maximum_passive_fill_seconds must be positive")

    rows_by_date = _rows_by_date(feature_rows)
    filled_signals_by_strategy = {}
    for strategy_id, signals in signals_by_strategy.items():
        filled_signals_by_strategy[strategy_id] = [
            filled_signal
            for signal in signals
            if (
                filled_signal := _passive_touch_signal(
                    signal,
                    rows_by_date,
                    maximum_passive_fill_seconds=maximum_passive_fill_seconds,
                )
            )
            is not None
        ]
    return filled_signals_by_strategy


def _passive_touch_signal(
    signal: dict[str, Any],
    rows_by_date: dict[str, list[dict[str, Any]]],
    *,
    maximum_passive_fill_seconds: int,
) -> dict[str, Any] | None:
    signal_timestamp = _parse_timestamp(str(signal["bar_start_time"]))
    trade_date = signal_timestamp.date().isoformat()
    entry_price = float(signal["signal_price"])
    direction = str(signal["direction"])
    for row in rows_by_date.get(trade_date, []):
        row_timestamp = row["parsed_timestamp"]
        seconds_after_signal = (row_timestamp - signal_timestamp).total_seconds()
        if seconds_after_signal <= 0:
            continue
        if seconds_after_signal > maximum_passive_fill_seconds:
            break
        if _entry_limit_touched(row, direction=direction, entry_price=entry_price):
            filled_signal = dict(signal)
            filled_signal["bar_index"] = row["bar_index"]
            filled_signal["bar_start_time"] = row["timestamp"]
            filled_signal["event_key"] = f"{signal['event_key']}:passive_fill:{row['bar_index']}"
            filled_signal["signal_id"] = f"{signal['signal_id']}_passive_fill_{row['bar_index']}"
            return filled_signal
    return None


def _entry_limit_touched(
    row: dict[str, Any],
    *,
    direction: str,
    entry_price: float,
) -> bool:
    if direction == "long":
        return row["low_float"] <= entry_price
    if direction == "short":
        return row["high_float"] >= entry_price
    raise ValueError(f"unsupported direction: {direction}")


def _eligible_rows_by_date(
    feature_rows: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    rows_by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in feature_rows:
        if DEFAULT_MARKET_START <= row["parsed_timestamp"].time() <= DEFAULT_MARKET_END:
            rows_by_date[row["trade_date"]].append(row)
    return dict(sorted(rows_by_date.items()))


def _rows_by_date(
    feature_rows: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    rows_by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in feature_rows:
        rows_by_date[row["trade_date"]].append(row)
    return dict(sorted(rows_by_date.items()))


def _opening_range(rows: list[dict[str, Any]]) -> tuple[float, float] | None:
    opening_rows = [
        row
        for row in rows
        if DEFAULT_OPENING_RANGE_START <= row["parsed_timestamp"].time() < DEFAULT_OPENING_RANGE_END
    ]
    if not opening_rows:
        return None
    return (
        max(row["high_float"] for row in opening_rows),
        min(row["low_float"] for row in opening_rows),
    )


def _is_session_entry_time(value: time) -> bool:
    return DEFAULT_SESSION_ENTRY_START <= value <= DEFAULT_SESSION_ENTRY_END


def _lookback_rows(
    rows: list[dict[str, Any]],
    *,
    index: int,
    lookback_seconds: int,
) -> list[dict[str, Any]]:
    current_timestamp = rows[index]["parsed_timestamp"]
    selected_rows = []
    for previous_row in reversed(rows[:index]):
        seconds_back = (current_timestamp - previous_row["parsed_timestamp"]).total_seconds()
        if seconds_back > lookback_seconds:
            break
        selected_rows.append(previous_row)
    return selected_rows


def _spaced_signals(
    candidates: list[tuple[dict[str, Any], str]],
    *,
    strategy_id: str,
    minimum_spacing_seconds: int,
    max_per_day: int,
) -> list[dict[str, Any]]:
    signals = []
    last_timestamp = None
    for row, direction in candidates:
        timestamp = row["parsed_timestamp"]
        if (
            last_timestamp is not None
            and (timestamp - last_timestamp).total_seconds() < minimum_spacing_seconds
        ):
            continue
        signals.append(_signal_from_row(row, direction, strategy_id, len(signals)))
        last_timestamp = timestamp
        if len(signals) >= max_per_day:
            break
    return signals


def _signal_from_row(
    row: dict[str, Any],
    direction: str,
    strategy_id: str,
    sequence: int,
) -> dict[str, Any]:
    return {
        "event_type": "candidate_signal",
        "event_key": (
            f"{row['symbol']}:{row['bar_index']}:{strategy_id}:{direction}:{sequence}"
        ),
        "strategy_id": strategy_id,
        "signal_id": (
            f"{strategy_id}_{row['trade_date']}_{row['bar_index']}_{direction}_{sequence}"
        ),
        "symbol": row["symbol"],
        "bar_index": row["bar_index"],
        "bar_start_time": row["timestamp"],
        "direction": direction,
        "signal_price": str(row["close"]),
    }


def _best_rows_by_strategy(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    best_by_strategy: dict[str, dict[str, Any]] = {}
    for row in rows:
        strategy_id = str(row["strategy_id"])
        current_best = best_by_strategy.get(strategy_id)
        if current_best is None or float(row["net_usd"]) > float(current_best["net_usd"]):
            best_by_strategy[strategy_id] = row
    return sorted(
        best_by_strategy.values(),
        key=lambda row: float(row["net_usd"]),
        reverse=True,
    )


def _to_float(value: str | None, default: float) -> float:
    if value is None or not str(value).strip():
        return default
    return float(value)


def _optional_float(value: str | None) -> float | None:
    if value is None or not str(value).strip():
        return None
    return float(value)


def _first_raw_value(raw_row: dict[str, str], *field_names: str) -> str | None:
    for field_name in field_names:
        value = raw_row.get(field_name)
        if value is not None and str(value).strip():
            return value
    return None


def _close_location(*, low: float, high: float, close: float) -> float:
    if high <= low:
        return 0.5
    return (close - low) / (high - low)


def _parse_float_list(value: str) -> list[float]:
    return [float(part.strip()) for part in value.split(",") if part.strip()]


def _parse_string_list(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _parse_optional_string_list(value: str | None) -> list[str] | None:
    if value is None:
        return None
    return _parse_string_list(value)


if __name__ == "__main__":
    raise SystemExit(main())
