#!/usr/bin/env python3
"""Run second-stage veto selection over selected scaled-context trades."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from axontrade.research import (
    SCALED_CONTEXT_SELECTED_VETO_WALK_FORWARD_HEADER,
    ScaledContextFilterExperimentError,
    ScaledContextSelectedVetoError,
    run_scaled_context_selected_veto_walk_forward,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run single-feature veto walk-forward over selected context trades.",
    )
    parser.add_argument("context_diagnostics", help="Path to scaled context diagnostic CSV rows.")
    parser.add_argument("selected_rules", help="Path to selected context walk-forward CSV rows.")
    parser.add_argument("output", help="Path to write selected-veto walk-forward CSV rows.")
    parser.add_argument("--minimum-kept-train-trades", type=int, default=10)
    parser.add_argument("--min-directional-open-distance-points", default="-999999,0,10,20,30,40")
    parser.add_argument(
        "--min-directional-opening-range-breakout-points",
        default="-999999,0,5,10,15,20",
    )
    parser.add_argument("--min-continuation-edge-scores", default="0,0.6,0.75,0.85,0.9")
    parser.add_argument(
        "--min-opening-range-continuation-edge-scores",
        default="0,0.75,1,1.25,1.5",
    )
    parser.add_argument(
        "--min-lookback-directional-move-points",
        default="-999999,0,10,20,30",
    )
    parser.add_argument("--min-lookback-efficiency-ratios", default="0,0.25,0.35,0.45,0.55")
    parser.add_argument(
        "--max-signal-abs-delta-sum-to-average-abs-deltas",
        default="999999,12,10,8,6",
    )
    parser.add_argument("--max-entry-volume-to-average-volumes", default="999999,2,1.5,1.25,1,0.75")
    parser.add_argument(
        "--max-entry-volume-to-session-average-volumes",
        default="999999,2,1.5,1.25,1,0.75",
    )
    parser.add_argument("--max-risk-to-average-bar-ranges", default="999999,4,3,2")
    args = parser.parse_args()

    try:
        split_rows = run_scaled_context_selected_veto_walk_forward(
            context_rows=_read_csv(Path(args.context_diagnostics)),
            selection_rows=_read_csv(Path(args.selected_rules)),
            minimum_kept_train_trades=args.minimum_kept_train_trades,
            min_directional_open_distance_points=_parse_float_list(
                args.min_directional_open_distance_points,
            ),
            min_directional_opening_range_breakout_points=_parse_float_list(
                args.min_directional_opening_range_breakout_points,
            ),
            min_continuation_edge_scores=_parse_float_list(args.min_continuation_edge_scores),
            min_opening_range_continuation_edge_scores=_parse_float_list(
                args.min_opening_range_continuation_edge_scores,
            ),
            min_lookback_directional_move_points=_parse_float_list(
                args.min_lookback_directional_move_points,
            ),
            min_lookback_efficiency_ratios=_parse_float_list(args.min_lookback_efficiency_ratios),
            max_signal_abs_delta_sum_to_average_abs_deltas=_parse_float_list(
                args.max_signal_abs_delta_sum_to_average_abs_deltas,
            ),
            max_entry_volume_to_average_volumes=_parse_float_list(
                args.max_entry_volume_to_average_volumes,
            ),
            max_entry_volume_to_session_average_volumes=_parse_float_list(
                args.max_entry_volume_to_session_average_volumes,
            ),
            max_risk_to_average_bar_ranges=_parse_float_list(
                args.max_risk_to_average_bar_ranges,
            ),
        )
    except (ScaledContextFilterExperimentError, ScaledContextSelectedVetoError, OSError) as exc:
        print(f"error: {exc}")
        return 2

    output_path = Path(args.output)
    _write_csv(output_path, SCALED_CONTEXT_SELECTED_VETO_WALK_FORWARD_HEADER, split_rows)
    holdout_rows = [row for row in split_rows if row["sample"] == "holdout"]
    holdout_trades = sum(int(row["kept_trades"]) for row in holdout_rows)
    holdout_net = sum(float(row["net_usd"]) for row in holdout_rows)
    holdout_unvetoed_trades = sum(int(row["selected_input_trades"]) for row in holdout_rows)
    holdout_unvetoed_net = sum(float(row["unvetoed_net_usd"]) for row in holdout_rows)
    print(
        f"wrote {len(split_rows)} selected-veto walk-forward rows to {output_path}; "
        f"holdout_trades={holdout_trades}, "
        f"holdout_net_usd={holdout_net:.2f}, "
        f"unvetoed_holdout_trades={holdout_unvetoed_trades}, "
        f"unvetoed_holdout_net_usd={holdout_unvetoed_net:.2f}",
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


if __name__ == "__main__":
    raise SystemExit(main())
