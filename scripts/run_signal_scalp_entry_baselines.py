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
    SignalScaledScalpExperimentError,
    run_signal_scaled_scalp_sweep,
)
from axontrade.research.trade_outcomes import _parse_timestamp


DEFAULT_EXPORT_CONFIG = "config/research/sierra_outcome_bar_export.yaml"
DEFAULT_RANDOM_SEED = 20260628
DEFAULT_MARKET_START = time(9, 45)
DEFAULT_MARKET_END = time(15, 45)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate random, VWAP-extension, and impulse scalp-entry "
            "baselines, then test scaled two-contract exits."
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
        "--entry-match-mode",
        choices=("bar_index", "timestamp", "auto"),
        default="auto",
        help="How to find bars after each generated entry.",
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
        )
        experiment_rows = []
        for signals in signals_by_strategy.values():
            experiment_rows.extend(
                run_signal_scaled_scalp_sweep(
                    normalized_rows,
                    signals,
                    first_target_points_values=_parse_float_list(args.first_target_points),
                    stop_points_values=_parse_float_list(args.stop_points),
                    runner_target_points_values=_parse_float_list(args.runner_target_points),
                    runner_stop_modes=_parse_string_list(args.runner_stop_modes),
                    direction_filters=["all"],
                    instrument_root=args.instrument_root,
                    slippage_ticks_per_side=args.slippage_ticks_per_side,
                    entry_match_mode=args.entry_match_mode,
                ),
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
        writer = csv.DictWriter(
            handle,
            fieldnames=SIGNAL_SCALED_SCALP_SWEEP_HEADER,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(experiment_rows)

    best_rows = _best_rows_by_strategy(experiment_rows)
    best_summary = ", ".join(
        f"{row['strategy_id']}={float(row['net_usd']):.2f}/{row['evaluated_trades']}"
        for row in best_rows[:3]
    )
    print(
        f"wrote {len(experiment_rows)} scalp-entry baseline rows to {output_path}; "
        f"strategies={len(signals_by_strategy)}, best={best_summary}",
    )
    return 0


def _feature_rows(
    raw_rows: list[dict[str, str]],
    normalized_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for raw_row, normalized_row in zip(raw_rows, normalized_rows):
        timestamp = _parse_timestamp(str(normalized_row["timestamp"]))
        close = float(normalized_row["close"])
        rows.append(
            {
                **normalized_row,
                "parsed_timestamp": timestamp,
                "trade_date": timestamp.date().isoformat(),
                "open_float": float(normalized_row["open"]),
                "high_float": float(normalized_row["high"]),
                "low_float": float(normalized_row["low"]),
                "close_float": close,
                "vwap": _to_float(raw_row.get("VWAP"), close),
            },
        )
    return rows


def _generate_strategy_signals(
    feature_rows: list[dict[str, Any]],
    *,
    random_seed: int,
    random_per_day: int,
    max_rule_entries_per_day: int,
    minimum_spacing_seconds: int,
) -> dict[str, list[dict[str, Any]]]:
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

    return dict(signals_by_strategy)


def _eligible_rows_by_date(
    feature_rows: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    rows_by_date: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in feature_rows:
        if DEFAULT_MARKET_START <= row["parsed_timestamp"].time() <= DEFAULT_MARKET_END:
            rows_by_date[row["trade_date"]].append(row)
    return dict(sorted(rows_by_date.items()))


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


def _parse_float_list(value: str) -> list[float]:
    return [float(part.strip()) for part in value.split(",") if part.strip()]


def _parse_string_list(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
