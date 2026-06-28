#!/usr/bin/env python3
"""Write trade-level audit rows for generated scalp-entry walk-forward selections."""

from __future__ import annotations

import argparse
import csv
import importlib.util
from collections import Counter
from pathlib import Path
from typing import Any

from axontrade.data import (
    SierraExportError,
    load_sierra_bar_study_rows,
    load_sierra_export_config,
    normalize_sierra_bar_study_file,
)
from axontrade.research import (
    SignalScaledScalpExperimentError,
    evaluate_signal_scaled_scalp_outcomes,
)
from axontrade.research.trade_outcomes import _parse_timestamp


SIGNAL_SCALP_ENTRY_AUDIT_HEADER = [
    "schema_version",
    "split_id",
    "sample",
    "selected_on_train",
    "trade_dates",
    "strategy_id",
    "trade_date",
    "sample_signal_occurrence",
    "sample_duplicate_signal",
    "signal_id",
    "symbol",
    "direction",
    "entry_bar_index",
    "entry_time",
    "entry_price",
    "selected_first_target_points",
    "selected_stop_points",
    "selected_runner_target_points",
    "selected_runner_stop_mode",
    "exit_reason",
    "exit_bar_index",
    "exit_time",
    "stop_price",
    "first_target_price",
    "runner_target_price",
    "leg1_exit_price",
    "runner_exit_price",
    "first_target_hit",
    "holding_bars",
    "gross_points",
    "gross_usd",
    "commission_usd",
    "slippage_usd",
    "net_usd",
    "notes",
]
_BASELINE_MODULE = None


def _baseline_module():
    global _BASELINE_MODULE
    if _BASELINE_MODULE is not None:
        return _BASELINE_MODULE
    script_path = Path(__file__).resolve().parent / "run_signal_scalp_entry_baselines.py"
    spec = importlib.util.spec_from_file_location("run_signal_scalp_entry_baselines", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load run_signal_scalp_entry_baselines.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _BASELINE_MODULE = module
    return module


DEFAULT_EXPORT_CONFIG = _baseline_module().DEFAULT_EXPORT_CONFIG


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Regenerate synthetic scalp-entry signals and audit each trade selected "
            "by a scaled-scalp walk-forward CSV."
        ),
    )
    parser.add_argument("bars_export", help="Path to Sierra exported bar/study text or CSV file.")
    parser.add_argument("selected_rows", help="Path to scaled-scalp walk-forward CSV rows.")
    parser.add_argument("output", help="Path to write trade audit CSV rows.")
    parser.add_argument("--symbol", required=True, help="Futures symbol for the export, e.g. ESU26-CME.")
    parser.add_argument("--chart-number", type=int, default=2, help="Chart number to write in export rows.")
    parser.add_argument("--session-phase", default="rth")
    parser.add_argument("--export-config", default=DEFAULT_EXPORT_CONFIG)
    parser.add_argument(
        "--entry-family-set",
        choices=("scalp", "session", "all"),
        default="scalp",
        help="Generated entry families to include.",
    )
    parser.add_argument(
        "--strategy-ids",
        help="Comma-separated generated strategy IDs to include. Defaults to all selected rows.",
    )
    parser.add_argument("--random-seed", type=int, default=20260628)
    parser.add_argument("--random-per-day", type=int, default=25)
    parser.add_argument("--max-rule-entries-per-day", type=int, default=20)
    parser.add_argument("--minimum-spacing-seconds", type=int, default=300)
    parser.add_argument(
        "--entry-fill-mode",
        choices=("immediate", "passive_touch"),
        default="immediate",
    )
    parser.add_argument("--maximum-passive-fill-seconds", type=int, default=60)
    parser.add_argument("--samples", default="holdout", help="Comma-separated samples to audit.")
    parser.add_argument("--instrument-root")
    parser.add_argument("--slippage-ticks-per-side", type=int)
    parser.add_argument(
        "--slippage-ticks-per-contract",
        type=float,
        help="Override total slippage ticks per contract for the whole trade.",
    )
    parser.add_argument(
        "--entry-match-mode",
        choices=("bar_index", "timestamp", "auto"),
        default="auto",
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
        baseline_module = _baseline_module()
        feature_rows = baseline_module._feature_rows(raw_rows, normalized_rows)
        selection_rows = _read_csv(Path(args.selected_rows))
        strategy_ids = _selected_strategy_ids(selection_rows, args.strategy_ids)
        signals_by_strategy = baseline_module._generate_strategy_signals(
            feature_rows,
            random_seed=args.random_seed,
            random_per_day=args.random_per_day,
            max_rule_entries_per_day=args.max_rule_entries_per_day,
            minimum_spacing_seconds=args.minimum_spacing_seconds,
            entry_family_set=args.entry_family_set,
        )
        signals_by_strategy = baseline_module._apply_entry_fill_mode(
            signals_by_strategy,
            feature_rows,
            entry_fill_mode=args.entry_fill_mode,
            maximum_passive_fill_seconds=args.maximum_passive_fill_seconds,
        )
        signals_by_strategy = baseline_module._filter_strategy_signals(
            signals_by_strategy,
            strategy_ids=strategy_ids,
        )
        audit_rows = audit_generated_scalp_entry_selection(
            bars=normalized_rows,
            signals_by_strategy=signals_by_strategy,
            selection_rows=selection_rows,
            samples=_parse_string_list(args.samples),
            instrument_root=args.instrument_root,
            slippage_ticks_per_side=args.slippage_ticks_per_side,
            slippage_ticks_per_contract=args.slippage_ticks_per_contract,
            entry_match_mode=args.entry_match_mode,
        )
    except (SierraExportError, SignalScaledScalpExperimentError, ValueError) as exc:
        print(f"error: {exc}")
        return 2

    output_path = Path(args.output)
    _write_csv(output_path, SIGNAL_SCALP_ENTRY_AUDIT_HEADER, audit_rows)
    print(_summary(output_path, audit_rows))
    return 0


def audit_generated_scalp_entry_selection(
    *,
    bars: list[dict[str, Any]],
    signals_by_strategy: dict[str, list[dict[str, Any]]],
    selection_rows: list[dict[str, str]],
    samples: list[str],
    instrument_root: str | None,
    slippage_ticks_per_side: int | None,
    slippage_ticks_per_contract: float | None,
    entry_match_mode: str,
) -> list[dict[str, Any]]:
    """Return one audit row per selected generated-signal trade."""

    if not samples:
        raise ValueError("samples must include at least one sample name")

    selected_samples = {sample.strip().lower() for sample in samples}
    audit_rows: list[dict[str, Any]] = []
    for selection in selection_rows:
        sample = str(selection["sample"]).strip().lower()
        if sample not in selected_samples:
            continue
        if str(selection["selected_on_train"]).strip().lower() != "true":
            continue

        strategy_id = str(selection["strategy_id"])
        trade_dates = _parse_trade_dates(selection["trade_dates"])
        signals = _filter_signals_by_dates(
            signals_by_strategy.get(strategy_id, []),
            trade_dates,
        )
        outcomes = evaluate_signal_scaled_scalp_outcomes(
            _filter_bars_by_dates(bars, trade_dates),
            signals,
            first_target_points=float(selection["first_target_points"]),
            stop_points=float(selection["stop_points"]),
            runner_target_points=float(selection["runner_target_points"]),
            runner_stop_mode=str(selection["runner_stop_mode"]),
            instrument_root=instrument_root,
            slippage_ticks_per_side=slippage_ticks_per_side,
            slippage_ticks_per_contract=slippage_ticks_per_contract,
            entry_match_mode=entry_match_mode,
        )
        audit_rows.extend(_audit_rows_for_selection(selection, outcomes))

    return _with_duplicate_markers(audit_rows)


def _audit_rows_for_selection(
    selection: dict[str, str],
    outcomes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []
    for outcome in outcomes:
        entry_time = str(outcome["entry_time"])
        rows.append(
            {
                "schema_version": 1,
                "split_id": selection["split_id"],
                "sample": selection["sample"],
                "selected_on_train": selection["selected_on_train"],
                "trade_dates": selection["trade_dates"],
                "strategy_id": selection["strategy_id"],
                "trade_date": _parse_timestamp(entry_time).date().isoformat(),
                "sample_signal_occurrence": "",
                "sample_duplicate_signal": "",
                "signal_id": outcome["signal_id"],
                "symbol": outcome["symbol"],
                "direction": outcome["direction"],
                "entry_bar_index": outcome["entry_bar_index"],
                "entry_time": entry_time,
                "entry_price": outcome["entry_price"],
                "selected_first_target_points": selection["first_target_points"],
                "selected_stop_points": selection["stop_points"],
                "selected_runner_target_points": selection["runner_target_points"],
                "selected_runner_stop_mode": selection["runner_stop_mode"],
                "exit_reason": outcome["exit_reason"],
                "exit_bar_index": outcome["exit_bar_index"],
                "exit_time": outcome["exit_time"],
                "stop_price": outcome["stop_price"],
                "first_target_price": outcome["first_target_price"],
                "runner_target_price": outcome["runner_target_price"],
                "leg1_exit_price": outcome["leg1_exit_price"],
                "runner_exit_price": outcome["runner_exit_price"],
                "first_target_hit": outcome["first_target_hit"],
                "holding_bars": outcome["holding_bars"],
                "gross_points": outcome["gross_points"],
                "gross_usd": outcome["gross_usd"],
                "commission_usd": outcome["commission_usd"],
                "slippage_usd": outcome["slippage_usd"],
                "net_usd": outcome["net_usd"],
                "notes": outcome["notes"],
            },
        )
    return rows


def _with_duplicate_markers(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: Counter[tuple[str, str]] = Counter(
        (str(row["sample"]), str(row["signal_id"])) for row in rows
    )
    seen: Counter[tuple[str, str]] = Counter()
    marked_rows = []
    for row in rows:
        key = (str(row["sample"]), str(row["signal_id"]))
        seen[key] += 1
        marked_row = dict(row)
        marked_row["sample_signal_occurrence"] = seen[key]
        marked_row["sample_duplicate_signal"] = str(counts[key] > 1).lower()
        marked_rows.append(marked_row)
    return marked_rows


def _selected_strategy_ids(
    selection_rows: list[dict[str, str]],
    strategy_ids: str | None,
) -> list[str] | None:
    if strategy_ids:
        return _parse_string_list(strategy_ids)
    selected = sorted(
        {
            str(row["strategy_id"])
            for row in selection_rows
            if str(row.get("selected_on_train", "")).strip().lower() == "true"
        },
    )
    return selected or None


def _filter_signals_by_dates(
    signals: list[dict[str, Any]],
    trade_dates: list[str],
) -> list[dict[str, Any]]:
    allowed_dates = set(trade_dates)
    return [
        signal
        for signal in signals
        if _parse_timestamp(str(signal["bar_start_time"])).date().isoformat()
        in allowed_dates
    ]


def _filter_bars_by_dates(
    bars: list[dict[str, Any]],
    trade_dates: list[str],
) -> list[dict[str, Any]]:
    allowed_dates = set(trade_dates)
    return [
        bar
        for bar in bars
        if _parse_timestamp(str(bar["timestamp"])).date().isoformat() in allowed_dates
    ]


def _parse_trade_dates(value: str) -> list[str]:
    return [part.strip() for part in value.split(";") if part.strip()]


def _summary(path: Path, rows: list[dict[str, Any]]) -> str:
    holdout_rows = [row for row in rows if row["sample"] == "holdout"]
    unique_holdout_signals = {str(row["signal_id"]) for row in holdout_rows}
    duplicate_holdout = len(holdout_rows) - len(unique_holdout_signals)
    holdout_net = sum(float(row["net_usd"]) for row in holdout_rows)
    full_stops = sum(
        str(row["exit_reason"]) in {"full_stop_hit", "ambiguous_full_stop_first"}
        for row in holdout_rows
    )
    first_target_hits = sum(
        str(row["first_target_hit"]).strip().lower() == "true"
        for row in holdout_rows
    )
    return (
        f"wrote {len(rows)} generated scalp-entry audit rows to {path}; "
        f"holdout_rows={len(holdout_rows)}, "
        f"unique_holdout_signals={len(unique_holdout_signals)}, "
        f"duplicate_holdout_signals={duplicate_holdout}, "
        f"holdout_net_usd={holdout_net:.2f}, "
        f"holdout_full_stops={full_stops}, "
        f"holdout_first_target_hits={first_target_hits}"
    )


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, header: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _parse_string_list(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
