#!/usr/bin/env python3
"""Report selected auction-regime guards stacked with health gates."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from axontrade.research import (
    SIGNAL_AUCTION_REGIME_HEALTH_GATE_REPORT_HEADER,
    SignalAuctionRegimeHealthGateReportError,
    report_signal_auction_regime_health_gate,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report selected auction-regime rules stacked with health gates.",
    )
    parser.add_argument("regime_diagnostics", help="Path to auction-regime diagnostic CSV rows.")
    parser.add_argument("selected_rules", help="Path to selected auction-regime rule CSV rows.")
    parser.add_argument("output", help="Path to write stacked report CSV rows.")
    parser.add_argument(
        "--minimum-train-accepted-trades",
        type=int,
        default=4,
        help="Minimum health-gate accepted training trades required in each selected split.",
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
        report_rows = report_signal_auction_regime_health_gate(
            regime_rows=_read_csv(Path(args.regime_diagnostics)),
            selection_rows=_read_csv(Path(args.selected_rules)),
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
        )
    except (SignalAuctionRegimeHealthGateReportError, OSError) as exc:
        print(f"error: {exc}")
        return 2

    output_path = Path(args.output)
    _write_csv(output_path, SIGNAL_AUCTION_REGIME_HEALTH_GATE_REPORT_HEADER, report_rows)
    holdout_rows = [row for row in report_rows if row["sample"] == "holdout"]
    accepted_trades = sum(int(row["accepted_trades"]) for row in holdout_rows)
    health_skipped_trades = sum(int(row["health_skipped_trades"]) for row in holdout_rows)
    auction_skipped_trades = sum(int(row["auction_skipped_trades"]) for row in holdout_rows)
    net_usd = sum(float(row["net_usd"]) for row in holdout_rows)
    health_skipped_net_usd = sum(float(row["health_skipped_net_usd"]) for row in holdout_rows)
    auction_skipped_net_usd = sum(float(row["auction_skipped_net_usd"]) for row in holdout_rows)
    print(
        f"wrote {len(report_rows)} auction-regime health-gate rows to {output_path}; "
        f"holdout_windows={len(holdout_rows)}, "
        f"holdout_accepted={accepted_trades}, "
        f"holdout_health_skipped={health_skipped_trades}, "
        f"holdout_auction_skipped={auction_skipped_trades}, "
        f"holdout_net_usd={net_usd:.2f}, "
        f"holdout_health_skipped_net_usd={health_skipped_net_usd:.2f}, "
        f"holdout_auction_skipped_net_usd={auction_skipped_net_usd:.2f}",
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
