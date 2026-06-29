#!/usr/bin/env python3
"""Compute rolling context diagnostics for fixed scaled-scalp outcomes."""

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
    SCALED_CONTEXT_DIAGNOSTIC_HEADER,
    ScaledContextDiagnosticError,
    load_signal_log_rows_csv,
    run_scaled_outcome_context_diagnostics,
)


DEFAULT_EXPORT_CONFIG = "config/research/sierra_delta_impulse_bar_export.yaml"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compute pre-entry normalized context for fixed scaled-scalp outcomes.",
    )
    parser.add_argument("bars_export", help="Path to Sierra exported orderflow bar file.")
    parser.add_argument("scaled_outcomes", help="Path to fixed scaled-scalp outcome CSV rows.")
    parser.add_argument("signal_log", help="Path to matching signal-log CSV rows.")
    parser.add_argument("output", help="Path to write scaled context diagnostic CSV rows.")
    parser.add_argument("--symbol", default="ESU26-CME")
    parser.add_argument("--chart-number", type=int, default=2)
    parser.add_argument("--session-phase", default="rth")
    parser.add_argument("--export-config", default=DEFAULT_EXPORT_CONFIG)
    parser.add_argument("--lookback-bars", type=int, default=20)
    args = parser.parse_args()

    try:
        normalized_rows = normalize_sierra_bar_study_file(
            args.bars_export,
            symbol=args.symbol,
            chart_number=args.chart_number,
            session_phase=args.session_phase,
            config=load_sierra_export_config(args.export_config),
            compute_opening_range=False,
        )
        outcome_rows = _read_csv(Path(args.scaled_outcomes))
        signal_rows = load_signal_log_rows_csv(args.signal_log)
        context_rows = run_scaled_outcome_context_diagnostics(
            bar_rows=normalized_rows,
            scaled_outcome_rows=outcome_rows,
            signal_rows=signal_rows,
            lookback_bars=args.lookback_bars,
        )
    except (SierraExportError, ScaledContextDiagnosticError, OSError) as exc:
        print(f"error: {exc}")
        return 2

    _write_csv(Path(args.output), SCALED_CONTEXT_DIAGNOSTIC_HEADER, context_rows)
    print(f"wrote {len(context_rows)} scaled context diagnostics to {args.output}")
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
