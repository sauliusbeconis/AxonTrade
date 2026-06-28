#!/usr/bin/env python3
"""Write trade-level audit rows for selected auction-regime stacks."""

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
    SIGNAL_AUCTION_REGIME_TRADE_AUDIT_HEADER,
    SignalAuctionRegimeBreakevenReportError,
    SignalAuctionRegimeTargetReportError,
    SignalAuctionRegimeTradeAuditError,
    SignalLogError,
    TradeOutcomeError,
    audit_signal_auction_regime_trades,
    load_signal_log_rows_csv,
    validate_signal_entries_against_bars,
)


DEFAULT_EXPORT_CONFIG = "config/research/sierra_outcome_bar_export.yaml"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit selected auction-regime stack trades one row at a time.",
    )
    parser.add_argument("bars_export", help="Path to Sierra exported bar/study text or CSV file.")
    parser.add_argument("signal_log", help="Path to AxonTrade signal-log CSV rows.")
    parser.add_argument("regime_diagnostics", help="Path to auction-regime diagnostic CSV rows.")
    parser.add_argument("selected_rules", help="Path to selected auction-regime rule CSV rows.")
    parser.add_argument("output", help="Path to write trade audit CSV rows.")
    parser.add_argument(
        "--stack-type",
        required=True,
        choices=("target_r", "breakeven"),
        help="Selected exit stack to audit.",
    )
    parser.add_argument("--symbol", required=True, help="Futures symbol for the export, e.g. ESU26-CME.")
    parser.add_argument("--chart-number", type=int, default=2, help="Chart number to write in export rows.")
    parser.add_argument("--session-phase", default="rth")
    parser.add_argument("--export-config", default=DEFAULT_EXPORT_CONFIG)
    parser.add_argument("--minimum-train-trades", type=int, default=4)
    parser.add_argument(
        "--target-r-multiples",
        default="0.5,1,1.25,1.5,2,2.5,3,3.5,4,4.5,5",
    )
    parser.add_argument(
        "--breakeven-trigger-r-multiples",
        default="0.5,0.75,1,1.25,1.5,2,2.5",
    )
    parser.add_argument("--direction-filters", default="all,long,short")
    parser.add_argument("--instrument-root")
    parser.add_argument("--slippage-ticks-per-side", type=int)
    parser.add_argument(
        "--entry-match-mode",
        choices=("bar_index", "timestamp", "auto"),
        default="auto",
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
        audit_rows = audit_signal_auction_regime_trades(
            bars=normalized_rows,
            signal_rows=signal_rows,
            regime_rows=_read_csv(Path(args.regime_diagnostics)),
            selection_rows=_read_csv(Path(args.selected_rules)),
            stack_type=args.stack_type,
            minimum_train_trades=args.minimum_train_trades,
            target_r_multiples=_parse_float_list(args.target_r_multiples),
            breakeven_trigger_r_multiples=_parse_float_list(
                args.breakeven_trigger_r_multiples,
            ),
            direction_filters=_parse_string_list(args.direction_filters),
            instrument_root=args.instrument_root,
            slippage_ticks_per_side=args.slippage_ticks_per_side,
            entry_match_mode=args.entry_match_mode,
        )
    except (
        SierraExportError,
        SignalAuctionRegimeBreakevenReportError,
        SignalAuctionRegimeTargetReportError,
        SignalAuctionRegimeTradeAuditError,
        SignalLogError,
        TradeOutcomeError,
    ) as exc:
        print(f"error: {exc}")
        return 2

    output_path = Path(args.output)
    _write_csv(output_path, SIGNAL_AUCTION_REGIME_TRADE_AUDIT_HEADER, audit_rows)
    print(_summary(output_path, audit_rows, args.stack_type))
    return 0


def _summary(path: Path, rows: list[dict[str, object]], stack_type: str) -> str:
    holdout_rows = [row for row in rows if row["sample"] == "holdout"]
    evaluated = [row for row in holdout_rows if row["decision"] == "evaluated"]
    unique_evaluated_signals = {str(row["signal_id"]) for row in evaluated}
    duplicate_evaluated = len(evaluated) - len(unique_evaluated_signals)
    skipped = [row for row in holdout_rows if row["decision"] == "auction_skipped"]
    evaluated_net = sum(float(row["selected_net_usd"]) for row in evaluated)
    skipped_original_net = sum(float(row["original_net_usd"]) for row in skipped)
    return (
        f"wrote {len(rows)} {stack_type} auction-regime trade audit rows to {path}; "
        f"holdout_rows={len(holdout_rows)}, "
        f"holdout_evaluated={len(evaluated)}, "
        f"unique_holdout_evaluated_signals={len(unique_evaluated_signals)}, "
        f"duplicate_holdout_evaluated={duplicate_evaluated}, "
        f"holdout_evaluated_net_usd={evaluated_net:.2f}, "
        f"holdout_auction_skipped={len(skipped)}, "
        f"holdout_auction_skipped_original_net_usd={skipped_original_net:.2f}"
    )


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
