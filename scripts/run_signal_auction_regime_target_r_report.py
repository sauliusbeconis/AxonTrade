#!/usr/bin/env python3
"""Report selected auction-regime guards stacked with target-R selection."""

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
    SIGNAL_AUCTION_REGIME_TARGET_R_REPORT_HEADER,
    SignalAuctionRegimeTargetReportError,
    SignalLogError,
    TradeOutcomeError,
    load_signal_log_rows_csv,
    report_signal_auction_regime_target_r,
    validate_signal_entries_against_bars,
)


DEFAULT_EXPORT_CONFIG = "config/research/sierra_outcome_bar_export.yaml"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report selected auction-regime rules stacked with target-R selection.",
    )
    parser.add_argument("bars_export", help="Path to Sierra exported bar/study text or CSV file.")
    parser.add_argument("signal_log", help="Path to AxonTrade signal-log CSV rows.")
    parser.add_argument("regime_diagnostics", help="Path to auction-regime diagnostic CSV rows.")
    parser.add_argument("selected_rules", help="Path to selected auction-regime rule CSV rows.")
    parser.add_argument("output", help="Path to write stacked report CSV rows.")
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
    parser.add_argument(
        "--minimum-train-trades",
        type=int,
        default=4,
        help="Minimum selected training trades required in each selected split.",
    )
    parser.add_argument(
        "--target-r-multiples",
        default="0.5,1,1.5,2,2.5,3,3.5,4,4.5,5",
        help="Comma-separated target R multiples to test.",
    )
    parser.add_argument(
        "--direction-filters",
        default="all,long,short",
        help="Comma-separated target direction filters to test: all,long,short.",
    )
    parser.add_argument(
        "--instrument-root",
        help="Instrument root for cost modeling, e.g. ES or MES. Defaults to symbol inference.",
    )
    parser.add_argument(
        "--slippage-ticks-per-side",
        type=int,
        help="Override default slippage assumption from config/research/default_costs.yaml.",
    )
    parser.add_argument(
        "--entry-match-mode",
        choices=("bar_index", "timestamp", "auto"),
        default="auto",
        help="How to find bars after each logged signal entry.",
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
        signal_rows = load_signal_log_rows_csv(args.signal_log)
        validate_signal_entries_against_bars(normalized_rows, signal_rows)
        report_rows = report_signal_auction_regime_target_r(
            bars=normalized_rows,
            signal_rows=signal_rows,
            regime_rows=_read_csv(Path(args.regime_diagnostics)),
            selection_rows=_read_csv(Path(args.selected_rules)),
            minimum_train_trades=args.minimum_train_trades,
            target_r_multiples=_parse_float_list(args.target_r_multiples),
            direction_filters=_parse_string_list(args.direction_filters),
            instrument_root=args.instrument_root,
            slippage_ticks_per_side=args.slippage_ticks_per_side,
            entry_match_mode=args.entry_match_mode,
        )
    except (
        SierraExportError,
        SignalAuctionRegimeTargetReportError,
        SignalLogError,
        TradeOutcomeError,
    ) as exc:
        print(f"error: {exc}")
        return 2

    output_path = Path(args.output)
    _write_csv(output_path, SIGNAL_AUCTION_REGIME_TARGET_R_REPORT_HEADER, report_rows)
    holdout_rows = [row for row in report_rows if row["sample"] == "holdout"]
    holdout_trades = sum(int(row["evaluated_trades"]) for row in holdout_rows)
    holdout_net_usd = sum(float(row["net_usd"]) for row in holdout_rows)
    auction_skipped_trades = sum(int(row["auction_skipped_trades"]) for row in holdout_rows)
    auction_skipped_net_usd = sum(float(row["auction_skipped_net_usd"]) for row in holdout_rows)
    print(
        f"wrote {len(report_rows)} auction-regime target-R rows to {output_path}; "
        f"holdout_windows={len(holdout_rows)}, "
        f"holdout_trades={holdout_trades}, "
        f"holdout_net_usd={holdout_net_usd:.2f}, "
        f"holdout_auction_skipped={auction_skipped_trades}, "
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


def _parse_string_list(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
