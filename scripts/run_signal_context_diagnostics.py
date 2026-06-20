#!/usr/bin/env python3
"""Run rolling context diagnostics for signal quality rows."""

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
    SIGNAL_CONTEXT_DIAGNOSTIC_HEADER,
    SignalContextDiagnosticError,
    run_signal_context_diagnostics,
)


DEFAULT_EXPORT_CONFIG = "config/research/sierra_orderflow_bar_export.yaml"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compute rolling volatility/activity context for signal diagnostics.",
    )
    parser.add_argument("bars_export", help="Path to Sierra exported orderflow bar file.")
    parser.add_argument("quality_diagnostics", help="Path to signal quality diagnostic CSV rows.")
    parser.add_argument("output", help="Path to write signal context diagnostic CSV rows.")
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
    parser.add_argument(
        "--lookback-bars",
        type=int,
        default=50,
        help="Number of bars before entry used for rolling context.",
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
        context_rows = run_signal_context_diagnostics(
            bar_rows=normalized_rows,
            quality_diagnostic_rows=quality_rows,
            lookback_bars=args.lookback_bars,
        )
    except (SierraExportError, SignalContextDiagnosticError, OSError) as exc:
        print(f"error: {exc}")
        return 2

    _write_csv(Path(args.output), SIGNAL_CONTEXT_DIAGNOSTIC_HEADER, context_rows)
    print(f"wrote {len(context_rows)} signal context diagnostics to {args.output}")
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
