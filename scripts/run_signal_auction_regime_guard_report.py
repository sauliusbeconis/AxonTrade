#!/usr/bin/env python3
"""Report accepted/skipped outcomes for selected auction-regime guard rules."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from axontrade.research import (
    SIGNAL_AUCTION_REGIME_GUARD_REPORT_HEADER,
    SignalAuctionRegimeGuardReportError,
    report_signal_auction_regime_guard,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report accepted/skipped outcomes for selected auction-regime rules.",
    )
    parser.add_argument("regime_diagnostics", help="Path to auction-regime diagnostic CSV rows.")
    parser.add_argument("selected_rules", help="Path to auction-regime filter selected-rule CSV rows.")
    parser.add_argument("output", help="Path to write auction-regime guard report CSV rows.")
    parser.add_argument(
        "--include-unselected",
        action="store_true",
        help="Report every rule row instead of only selected_on_train=true rows.",
    )
    args = parser.parse_args()

    try:
        report_rows = report_signal_auction_regime_guard(
            regime_rows=_read_csv(Path(args.regime_diagnostics)),
            selection_rows=_read_csv(Path(args.selected_rules)),
            selected_only=not args.include_unselected,
        )
    except (SignalAuctionRegimeGuardReportError, OSError) as exc:
        print(f"error: {exc}")
        return 2

    output_path = Path(args.output)
    _write_csv(output_path, SIGNAL_AUCTION_REGIME_GUARD_REPORT_HEADER, report_rows)
    holdout_rows = [row for row in report_rows if row["sample"] == "holdout"]
    accepted_trades = sum(int(row["accepted_trades"]) for row in holdout_rows)
    skipped_trades = sum(int(row["skipped_trades"]) for row in holdout_rows)
    net_usd = sum(float(row["net_usd"]) for row in holdout_rows)
    skipped_net_usd = sum(float(row["skipped_net_usd"]) for row in holdout_rows)
    print(
        f"wrote {len(report_rows)} auction-regime guard rows to {output_path}; "
        f"holdout_accepted_trades={accepted_trades}, "
        f"holdout_skipped_trades={skipped_trades}, "
        f"holdout_net_usd={net_usd:.2f}, "
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


if __name__ == "__main__":
    raise SystemExit(main())
