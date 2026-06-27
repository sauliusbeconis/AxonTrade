#!/usr/bin/env python3
"""Run auction-regime diagnostics for signal quality rows."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from axontrade.data import (
    SierraExportError,
    load_sierra_export_config,
    normalize_sierra_bar_study_file,
)
from axontrade.research import (
    SIGNAL_AUCTION_REGIME_DIAGNOSTIC_HEADER,
    SignalAuctionRegimeDiagnosticError,
    run_signal_auction_regime_diagnostics,
)


DEFAULT_EXPORT_CONFIG = "config/research/sierra_orderflow_bar_export.yaml"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compute pre-entry auction-regime diagnostics for signal rows.",
    )
    parser.add_argument("bars_export", help="Path to Sierra exported orderflow bar file.")
    parser.add_argument("quality_diagnostics", help="Path to signal quality diagnostic CSV rows.")
    parser.add_argument("output", help="Path to write auction-regime diagnostic CSV rows.")
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
        help="Sierra export normalization config for orderflow bar rows.",
    )
    args = parser.parse_args()

    try:
        normalized_rows = normalize_sierra_bar_study_file(
            args.bars_export,
            symbol=args.symbol,
            chart_number=args.chart_number,
            session_phase=args.session_phase,
            config=load_sierra_export_config(args.export_config),
            compute_opening_range=True,
        )
        quality_rows = _read_csv(Path(args.quality_diagnostics))
        regime_rows = run_signal_auction_regime_diagnostics(
            bar_rows=normalized_rows,
            quality_diagnostic_rows=quality_rows,
        )
    except (SierraExportError, SignalAuctionRegimeDiagnosticError, OSError) as exc:
        print(f"error: {exc}")
        return 2

    _write_csv(Path(args.output), SIGNAL_AUCTION_REGIME_DIAGNOSTIC_HEADER, regime_rows)
    print(f"wrote {len(regime_rows)} signal auction-regime diagnostics to {args.output}")
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
