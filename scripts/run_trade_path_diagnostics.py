#!/usr/bin/env python3
"""Run MFE/MAE path diagnostics for evaluated trade outcomes."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from axontrade.data import (
    SierraExportError,
    load_sierra_export_config,
    normalize_sierra_bar_study_file,
)
from axontrade.research import (
    TRADE_PATH_DIAGNOSTIC_CSV_HEADER,
    TradeOutcomeError,
    diagnose_trade_paths,
)


DEFAULT_EXPORT_CONFIG = "config/research/sierra_outcome_bar_export.yaml"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure MFE/MAE and first stop/target touch for outcome rows.",
    )
    parser.add_argument("bars_export", help="Path to Sierra exported bar/study text or CSV file.")
    parser.add_argument("outcomes", help="Path to trade outcome CSV rows.")
    parser.add_argument("diagnostics_output", help="Path to write trade path diagnostics.")
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
        help="Sierra export normalization config for outcome bar rows.",
    )
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
        outcome_rows = _read_csv(Path(args.outcomes))
        diagnostic_rows = diagnose_trade_paths(normalized_rows, outcome_rows)
    except (SierraExportError, TradeOutcomeError) as exc:
        print(f"error: {exc}")
        return 2

    _write_csv(Path(args.diagnostics_output), TRADE_PATH_DIAGNOSTIC_CSV_HEADER, diagnostic_rows)
    labels = Counter(str(row["diagnostic_label"]) for row in diagnostic_rows)
    label_summary = ", ".join(f"{label}={count}" for label, count in sorted(labels.items()))
    print(
        f"wrote {len(diagnostic_rows)} trade path diagnostics to "
        f"{args.diagnostics_output} ({label_summary})",
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
