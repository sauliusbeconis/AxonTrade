#!/usr/bin/env python3
"""Run rolling walk-forward strategy health-gate sweeps."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from axontrade.research import (
    SIGNAL_HEALTH_GATE_WALK_FORWARD_HEADER,
    SignalHealthGateExperimentError,
    run_signal_health_gate_walk_forward_sweep,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run rolling health-gate walk-forward selection.",
    )
    parser.add_argument("diagnostics", help="Path to signal diagnostic CSV rows.")
    parser.add_argument("output", help="Path to write health-gate walk-forward CSV rows.")
    parser.add_argument(
        "--train-date-count",
        type=int,
        default=8,
        help="Number of consecutive candidate trade dates per training window.",
    )
    parser.add_argument(
        "--holdout-date-count",
        type=int,
        default=2,
        help="Number of consecutive candidate trade dates per holdout window.",
    )
    parser.add_argument(
        "--minimum-train-accepted-trades",
        type=int,
        default=4,
        help="Minimum accepted training trades required in each window.",
    )
    parser.add_argument(
        "--window-step-date-count",
        type=int,
        default=1,
        help="Trade-date step between walk-forward windows; use holdout count for non-overlap.",
    )
    parser.add_argument(
        "--maximum-daily-losses",
        default="1,2,999",
        help="Comma-separated max accepted losing trades per trade date.",
    )
    parser.add_argument(
        "--daily-loss-limits-usd",
        default="150,300,500,999999",
        help="Comma-separated realized daily loss limits in USD.",
    )
    parser.add_argument(
        "--maximum-consecutive-losses",
        default="1,2,999",
        help="Comma-separated max accepted consecutive losing trades.",
    )
    parser.add_argument(
        "--consecutive-loss-pause-trade-dates",
        default="0,1,2",
        help="Comma-separated future trade dates to pause after consecutive-loss trigger.",
    )
    parser.add_argument(
        "--maximum-equity-drawdowns-usd",
        default="250,500,1000,999999",
        help="Comma-separated accepted-equity drawdown limits in USD.",
    )
    parser.add_argument(
        "--drawdown-pause-trade-dates",
        default="0,1,2,3",
        help="Comma-separated future trade dates to pause after drawdown trigger.",
    )
    args = parser.parse_args()

    try:
        diagnostic_rows = _read_csv(Path(args.diagnostics))
        split_rows = run_signal_health_gate_walk_forward_sweep(
            diagnostic_rows,
            train_date_count=args.train_date_count,
            holdout_date_count=args.holdout_date_count,
            minimum_train_accepted_trades=args.minimum_train_accepted_trades,
            maximum_daily_losses=_parse_int_list(args.maximum_daily_losses),
            daily_loss_limits_usd=_parse_float_list(args.daily_loss_limits_usd),
            maximum_consecutive_losses=_parse_int_list(args.maximum_consecutive_losses),
            consecutive_loss_pause_trade_dates=_parse_int_list(
                args.consecutive_loss_pause_trade_dates,
            ),
            maximum_equity_drawdowns_usd=_parse_float_list(
                args.maximum_equity_drawdowns_usd,
            ),
            drawdown_pause_trade_dates=_parse_int_list(args.drawdown_pause_trade_dates),
            window_step_date_count=args.window_step_date_count,
        )
    except (SignalHealthGateExperimentError, OSError) as exc:
        print(f"error: {exc}")
        return 2

    _write_csv(Path(args.output), SIGNAL_HEALTH_GATE_WALK_FORWARD_HEADER, split_rows)
    holdout_rows = [row for row in split_rows if row["sample"] == "holdout"]
    holdout_accepted = sum(int(row["accepted_trades"]) for row in holdout_rows)
    holdout_skipped = sum(int(row["skipped_trades"]) for row in holdout_rows)
    holdout_net_usd = sum(float(row["net_usd"]) for row in holdout_rows)
    skipped_net_usd = sum(float(row["skipped_net_usd"]) for row in holdout_rows)
    print(
        f"wrote {len(split_rows)} health-gate walk-forward rows to {args.output}; "
        f"holdout_windows={len(holdout_rows)}, "
        f"holdout_accepted={holdout_accepted}, "
        f"holdout_skipped={holdout_skipped}, "
        f"holdout_net_usd={holdout_net_usd:.2f}, "
        f"holdout_skipped_net_usd={skipped_net_usd:.2f}",
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


def _parse_int_list(value: str) -> list[int]:
    return [int(part.strip()) for part in value.split(",") if part.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
