#!/usr/bin/env python3
"""Run rolling walk-forward filters over scaled context diagnostics."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from axontrade.research import (
    SCALED_CONTEXT_FILTER_WALK_FORWARD_HEADER,
    ScaledContextFilterExperimentError,
    run_scaled_context_filter_walk_forward_sweep,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run rolling scaled-context filter walk-forward selection.",
    )
    parser.add_argument("context_diagnostics", help="Path to scaled context diagnostic CSV rows.")
    parser.add_argument("output", help="Path to write scaled context walk-forward CSV rows.")
    parser.add_argument("--train-date-count", type=int, default=8)
    parser.add_argument("--holdout-date-count", type=int, default=2)
    parser.add_argument("--minimum-train-trades", type=int, default=12)
    parser.add_argument("--window-step-date-count", type=int, default=1)
    parser.add_argument("--min-minutes-after-rth-open", default="0,30,60")
    parser.add_argument("--max-minutes-after-rth-open", default="120,180,240,390")
    parser.add_argument("--max-risk-to-average-bar-ranges", default="4,8,12,999999")
    parser.add_argument("--max-runner-target-to-average-bar-ranges", default="4,8,12,999999")
    parser.add_argument(
        "--min-signal-abs-delta-sum-to-average-abs-deltas",
        default="0,5,10,20",
    )
    parser.add_argument(
        "--max-signal-abs-delta-sum-to-average-abs-deltas",
        default="20,50,100,999999",
    )
    parser.add_argument("--min-entry-volume-to-average-volumes", default="0,0.75,1")
    parser.add_argument("--min-entry-trades-to-average-trades", default="0,0.75,1")
    parser.add_argument("--direction-filters", default="all,long,short")
    args = parser.parse_args()

    try:
        context_rows = _read_csv(Path(args.context_diagnostics))
        split_rows = run_scaled_context_filter_walk_forward_sweep(
            context_rows,
            train_date_count=args.train_date_count,
            holdout_date_count=args.holdout_date_count,
            minimum_train_trades=args.minimum_train_trades,
            window_step_date_count=args.window_step_date_count,
            min_minutes_after_rth_open_values=_parse_float_list(args.min_minutes_after_rth_open),
            max_minutes_after_rth_open_values=_parse_float_list(args.max_minutes_after_rth_open),
            max_risk_to_average_bar_ranges=_parse_float_list(
                args.max_risk_to_average_bar_ranges,
            ),
            max_runner_target_to_average_bar_ranges=_parse_float_list(
                args.max_runner_target_to_average_bar_ranges,
            ),
            min_signal_abs_delta_sum_to_average_abs_deltas=_parse_float_list(
                args.min_signal_abs_delta_sum_to_average_abs_deltas,
            ),
            max_signal_abs_delta_sum_to_average_abs_deltas=_parse_float_list(
                args.max_signal_abs_delta_sum_to_average_abs_deltas,
            ),
            min_entry_volume_to_average_volumes=_parse_float_list(
                args.min_entry_volume_to_average_volumes,
            ),
            min_entry_trades_to_average_trades=_parse_float_list(
                args.min_entry_trades_to_average_trades,
            ),
            direction_filters=_parse_string_list(args.direction_filters),
        )
    except (ScaledContextFilterExperimentError, OSError) as exc:
        print(f"error: {exc}")
        return 2

    _write_csv(Path(args.output), SCALED_CONTEXT_FILTER_WALK_FORWARD_HEADER, split_rows)
    holdout_rows = [row for row in split_rows if row["sample"] == "holdout"]
    holdout_trades = sum(int(row["evaluated_trades"]) for row in holdout_rows)
    holdout_net_usd = sum(float(row["net_usd"]) for row in holdout_rows)
    print(
        f"wrote {len(split_rows)} scaled context walk-forward rows to {args.output}; "
        f"holdout_windows={len(holdout_rows)}, "
        f"holdout_trades={holdout_trades}, "
        f"holdout_net_usd={holdout_net_usd:.2f}",
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
