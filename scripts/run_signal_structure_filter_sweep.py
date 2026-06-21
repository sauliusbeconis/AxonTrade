#!/usr/bin/env python3
"""Run structure-aware entry filter sweeps over signal diagnostics."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from axontrade.research import (
    SIGNAL_STRUCTURE_FILTER_SWEEP_HEADER,
    SignalStructureFilterExperimentError,
    run_signal_structure_filter_sweep,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sweep structure-aware entry filters over signal diagnostic rows.",
    )
    parser.add_argument("diagnostics", help="Path to signal quality diagnostic CSV rows.")
    parser.add_argument("output", help="Path to write structure filter sweep CSV rows.")
    parser.add_argument(
        "--max-original-reward-risks",
        default="2.5,3.5,999",
        help="Comma-separated maximum original reward/risk thresholds.",
    )
    parser.add_argument(
        "--min-minutes-after-rth-open",
        default="0,60",
        help="Comma-separated minimum minutes after RTH open.",
    )
    parser.add_argument(
        "--max-minutes-after-rth-open",
        default="120,240,390",
        help="Comma-separated maximum minutes after RTH open.",
    )
    parser.add_argument(
        "--max-sweep-abs-deltas",
        default="3,10,999999",
        help="Comma-separated maximum absolute sweep delta thresholds.",
    )
    parser.add_argument(
        "--max-bars-after-sweep-values",
        default="1,2,3,5",
        help="Comma-separated maximum bars allowed between sweep and confirmation.",
    )
    parser.add_argument(
        "--min-sweep-aggression-ratios",
        default="1,1.25,2",
        help="Comma-separated minimum sweep-side aggression ratios.",
    )
    parser.add_argument(
        "--min-confirmation-edge-closes",
        default="0.55,0.75,0.9",
        help="Comma-separated minimum direction-aware confirmation close location.",
    )
    parser.add_argument(
        "--direction-filters",
        default="all,long,short",
        help="Comma-separated direction filters to test: all,long,short.",
    )
    args = parser.parse_args()

    try:
        diagnostic_rows = _read_csv(Path(args.diagnostics))
        experiment_rows = run_signal_structure_filter_sweep(
            diagnostic_rows,
            max_original_reward_risks=_parse_float_list(args.max_original_reward_risks),
            min_minutes_after_rth_open_values=_parse_float_list(
                args.min_minutes_after_rth_open,
            ),
            max_minutes_after_rth_open_values=_parse_float_list(
                args.max_minutes_after_rth_open,
            ),
            max_sweep_abs_deltas=_parse_float_list(args.max_sweep_abs_deltas),
            max_bars_after_sweep_values=_parse_float_list(args.max_bars_after_sweep_values),
            min_sweep_aggression_ratios=_parse_float_list(args.min_sweep_aggression_ratios),
            min_confirmation_edge_closes=_parse_float_list(args.min_confirmation_edge_closes),
            direction_filters=_parse_string_list(args.direction_filters),
        )
    except (SignalStructureFilterExperimentError, OSError) as exc:
        print(f"error: {exc}")
        return 2

    _write_csv(Path(args.output), SIGNAL_STRUCTURE_FILTER_SWEEP_HEADER, experiment_rows)
    best_row = max(experiment_rows, key=lambda row: float(row["net_usd"]), default=None)
    best_summary = (
        "none"
        if best_row is None
        else (
            f"{best_row['experiment_id']} "
            f"net_usd={float(best_row['net_usd']):.2f} "
            f"trades={best_row['evaluated_trades']}"
        )
    )
    print(
        f"wrote {len(experiment_rows)} structure filter sweep rows to {args.output}; "
        f"best={best_summary}",
    )
    return 0


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, header: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _parse_float_list(value: str) -> list[float]:
    return [float(part.strip()) for part in value.split(",") if part.strip()]


def _parse_string_list(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
