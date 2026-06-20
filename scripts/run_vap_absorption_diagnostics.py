#!/usr/bin/env python3
"""Run VAP diagnostics for existing absorption outcomes."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from axontrade.data import load_sierra_bar_study_rows, load_sierra_export_config, normalize_sierra_bar_study_rows
from axontrade.research import VAP_ABSORPTION_DIAGNOSTIC_HEADER, run_vap_absorption_diagnostics


DEFAULT_VAP_INPUT = (
    "/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/"
    "AxonTrade_ES_VolumeAtPriceExport.txt"
)
DEFAULT_VAP_CONFIG = "config/research/sierra_volume_at_price_export.yaml"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run volume-at-price diagnostics for liquidity sweep absorption outcomes.",
    )
    parser.add_argument("signals", help="Path to absorption signal CSV rows.")
    parser.add_argument("outcomes", help="Path to absorption outcome CSV rows.")
    parser.add_argument(
        "output",
        help="Path to write VAP diagnostic rows.",
    )
    parser.add_argument(
        "--vap-input",
        default=DEFAULT_VAP_INPUT,
        help="Path to Sierra volume-at-price export.",
    )
    parser.add_argument(
        "--vap-config",
        default=DEFAULT_VAP_CONFIG,
        help="Sierra volume-at-price export normalization config.",
    )
    parser.add_argument("--symbol", default="ESU26-CME", help="Symbol to use if the VAP export omits symbol.")
    parser.add_argument(
        "--sweep-zone-points",
        type=float,
        default=1.0,
        help="Distance from sweep extreme included in swept-level zone.",
    )
    parser.add_argument(
        "--stop-buffer-points",
        type=float,
        default=0.25,
        help="Stop buffer used to recover sweep extreme from the outcome stop.",
    )
    parser.add_argument(
        "--minimum-zone-aggression-ratio",
        type=float,
        default=1.25,
        help="Minimum sweep-zone aggressor/opposite volume ratio.",
    )
    parser.add_argument(
        "--minimum-zone-volume",
        type=float,
        default=0.0,
        help="Minimum total bid+ask volume in the swept price zone.",
    )
    args = parser.parse_args()

    signal_rows = _read_csv(Path(args.signals))
    outcome_rows = _read_csv(Path(args.outcomes))
    vap_rows = normalize_sierra_bar_study_rows(
        load_sierra_bar_study_rows(args.vap_input),
        symbol=args.symbol,
        config=load_sierra_export_config(args.vap_config),
    )
    diagnostic_rows = run_vap_absorption_diagnostics(
        outcome_rows=outcome_rows,
        signal_rows=signal_rows,
        vap_rows=vap_rows,
        sweep_zone_points=args.sweep_zone_points,
        stop_buffer_points=args.stop_buffer_points,
        minimum_zone_aggression_ratio=args.minimum_zone_aggression_ratio,
        minimum_zone_volume=args.minimum_zone_volume,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=VAP_ABSORPTION_DIAGNOSTIC_HEADER,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(diagnostic_rows)

    passed_rows = [
        row
        for row in diagnostic_rows
        if row["level_absorption_pass"] == "true"
    ]
    pass_net = sum(float(row["net_usd"]) for row in passed_rows)
    print(
        f"wrote {len(diagnostic_rows)} VAP diagnostic rows to {output_path}; "
        f"pass_trades={len(passed_rows)}, "
        f"pass_net_usd={pass_net:.2f}",
    )
    return 0


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    raise SystemExit(main())
