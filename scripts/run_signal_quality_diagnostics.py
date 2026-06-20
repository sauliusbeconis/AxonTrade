#!/usr/bin/env python3
"""Run quality diagnostics for evaluated Sierra overlay signal outcomes."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from axontrade.research import (
    SIGNAL_QUALITY_DIAGNOSTIC_HEADER,
    SignalLogError,
    SignalQualityDiagnosticError,
    load_signal_log_rows_csv,
    run_signal_quality_diagnostics,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Join signal metadata, evaluated outcomes, and optional path metrics.",
    )
    parser.add_argument("signals", help="Path to Sierra overlay signal log CSV rows.")
    parser.add_argument("outcomes", help="Path to evaluated outcome CSV rows.")
    parser.add_argument("output", help="Path to write quality diagnostic CSV rows.")
    parser.add_argument(
        "--path-diagnostics",
        help="Optional path diagnostics CSV with MFE/MAE R-multiple fields.",
    )
    args = parser.parse_args()

    try:
        signal_rows = load_signal_log_rows_csv(args.signals)
        outcome_rows = _read_csv(Path(args.outcomes))
        path_rows = _read_csv(Path(args.path_diagnostics)) if args.path_diagnostics else None
        diagnostic_rows = run_signal_quality_diagnostics(
            signal_rows=signal_rows,
            outcome_rows=outcome_rows,
            path_diagnostic_rows=path_rows,
        )
    except (SignalLogError, SignalQualityDiagnosticError, OSError) as exc:
        print(f"error: {exc}")
        return 2

    _write_csv(Path(args.output), SIGNAL_QUALITY_DIAGNOSTIC_HEADER, diagnostic_rows)
    exits = Counter(str(row["exit_reason"]) for row in diagnostic_rows)
    exit_summary = ", ".join(f"{label}={count}" for label, count in sorted(exits.items()))
    print(f"wrote {len(diagnostic_rows)} signal quality diagnostics to {args.output} ({exit_summary})")
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
