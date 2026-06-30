#!/usr/bin/env python3
"""Run loss attribution and theory-guard checks over scaled context diagnostics."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from axontrade.research import (
    SCALED_CONTEXT_DAILY_SUMMARY_HEADER,
    SCALED_CONTEXT_FEATURE_BUCKET_HEADER,
    SCALED_CONTEXT_GUARD_EVALUATION_HEADER,
    SCALED_CONTEXT_GUARD_WALK_FORWARD_HEADER,
    ScaledContextLossAttributionError,
    bucket_scaled_context_features,
    evaluate_scaled_context_fixed_guards,
    render_scaled_context_loss_attribution_report,
    run_scaled_context_guard_walk_forward,
    summarize_scaled_context_daily_performance,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run scaled-context loss attribution and compact theory guards.",
    )
    parser.add_argument("context_diagnostics", help="Path to scaled context diagnostic CSV rows.")
    parser.add_argument(
        "output_prefix",
        help="Output prefix. The script writes -daily-summary.csv, -feature-buckets.csv, "
        "-fixed-guards.csv, -theory-guard-walk-forward.csv, and .md.",
    )
    parser.add_argument("--feature-bucket-count", type=int, default=10)
    parser.add_argument("--minimum-bucket-trades", type=int, default=30)
    parser.add_argument("--train-date-count", type=int, default=40)
    parser.add_argument("--holdout-date-count", type=int, default=5)
    parser.add_argument("--window-step-date-count", type=int, default=5)
    parser.add_argument("--minimum-train-trades", type=int, default=25)
    parser.add_argument("--minimum-train-participation-rate", type=float, default=0.35)
    parser.add_argument(
        "--selection-objective",
        choices=("lower_bound", "net", "average"),
        default="lower_bound",
    )
    args = parser.parse_args()

    try:
        context_rows = _read_csv(Path(args.context_diagnostics))
        daily_rows = summarize_scaled_context_daily_performance(context_rows)
        bucket_rows = bucket_scaled_context_features(
            context_rows,
            bucket_count=args.feature_bucket_count,
            minimum_bucket_trades=args.minimum_bucket_trades,
        )
        fixed_guard_rows = evaluate_scaled_context_fixed_guards(context_rows)
        walk_forward_rows = run_scaled_context_guard_walk_forward(
            context_rows,
            train_date_count=args.train_date_count,
            holdout_date_count=args.holdout_date_count,
            window_step_date_count=args.window_step_date_count,
            minimum_train_trades=args.minimum_train_trades,
            minimum_train_participation_rate=args.minimum_train_participation_rate,
            selection_objective=args.selection_objective,
        )
        report = render_scaled_context_loss_attribution_report(
            context_rows=context_rows,
            daily_rows=daily_rows,
            fixed_guard_rows=fixed_guard_rows,
            walk_forward_rows=walk_forward_rows,
        )
    except (ScaledContextLossAttributionError, OSError) as exc:
        print(f"error: {exc}")
        return 2

    output_prefix = Path(args.output_prefix)
    daily_path = output_prefix.with_name(f"{output_prefix.name}-daily-summary.csv")
    bucket_path = output_prefix.with_name(f"{output_prefix.name}-feature-buckets.csv")
    fixed_path = output_prefix.with_name(f"{output_prefix.name}-fixed-guards.csv")
    walk_forward_path = output_prefix.with_name(
        f"{output_prefix.name}-theory-guard-walk-forward.csv",
    )
    report_path = output_prefix.with_suffix(".md")
    _write_csv(daily_path, SCALED_CONTEXT_DAILY_SUMMARY_HEADER, daily_rows)
    _write_csv(bucket_path, SCALED_CONTEXT_FEATURE_BUCKET_HEADER, bucket_rows)
    _write_csv(fixed_path, SCALED_CONTEXT_GUARD_EVALUATION_HEADER, fixed_guard_rows)
    _write_csv(walk_forward_path, SCALED_CONTEXT_GUARD_WALK_FORWARD_HEADER, walk_forward_rows)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")

    holdout_rows = [row for row in walk_forward_rows if row["sample"] == "holdout"]
    holdout_trades = sum(int(row["kept_trades"]) for row in holdout_rows)
    holdout_net = sum(float(row["net_usd"]) for row in holdout_rows)
    unfiltered_holdout_net = sum(float(row["unfiltered_net_usd"]) for row in holdout_rows)
    print(
        f"wrote loss attribution outputs with prefix {output_prefix}; "
        f"holdout_trades={holdout_trades}, "
        f"holdout_net_usd={holdout_net:.2f}, "
        f"unfiltered_holdout_net_usd={unfiltered_holdout_net:.2f}",
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


if __name__ == "__main__":
    raise SystemExit(main())
