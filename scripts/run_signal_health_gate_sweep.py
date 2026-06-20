#!/usr/bin/env python3
"""Run strategy health-gate sweeps over signal quality diagnostics."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from axontrade.research import (
    SIGNAL_HEALTH_GATE_SWEEP_HEADER,
    SignalHealthGateExperimentError,
    run_signal_health_gate_sweep,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sweep realized-outcome health gates over signal diagnostics.",
    )
    parser.add_argument("diagnostics", help="Path to signal diagnostic CSV rows.")
    parser.add_argument("output", help="Path to write health-gate sweep CSV rows.")
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
        experiment_rows = run_signal_health_gate_sweep(
            diagnostic_rows,
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
        )
    except (SignalHealthGateExperimentError, OSError) as exc:
        print(f"error: {exc}")
        return 2

    _write_csv(Path(args.output), SIGNAL_HEALTH_GATE_SWEEP_HEADER, experiment_rows)
    best_row = max(experiment_rows, key=lambda row: float(row["net_usd"]), default=None)
    best_summary = (
        "none"
        if best_row is None
        else (
            f"{best_row['experiment_id']} "
            f"net_usd={float(best_row['net_usd']):.2f} "
            f"accepted={best_row['accepted_trades']} "
            f"skipped={best_row['skipped_trades']}"
        )
    )
    print(
        f"wrote {len(experiment_rows)} health-gate sweep rows to {args.output}; "
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


def _parse_int_list(value: str) -> list[int]:
    return [int(part.strip()) for part in value.split(",") if part.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
