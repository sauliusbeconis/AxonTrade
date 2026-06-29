#!/usr/bin/env python3
"""Validate the Sierra delta-impulse overlay log against exported bars."""

from __future__ import annotations

import argparse

from axontrade.data import (
    SierraExportError,
    load_sierra_export_config,
    normalize_sierra_bar_study_file,
)
from axontrade.research import SignalLogError, load_signal_log_rows_csv
from axontrade.research.delta_impulse_overlay_validation import (
    DeltaImpulseOverlayValidationError,
    DeltaImpulseRuleConfig,
    compare_delta_impulse_overlay_log,
    write_delta_impulse_overlay_validation_report,
)


DEFAULT_EXPORT_CONFIG = "config/research/sierra_delta_impulse_bar_export.yaml"
DEFAULT_REPORT = "reports/sierra-delta-impulse-overlay-validation.md"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare Python-reproduced delta-impulse candidates with Sierra log rows.",
    )
    parser.add_argument("bars_export", help="Path to Sierra exported bar/study text or CSV file.")
    parser.add_argument("signal_log", help="Path to AxonTrade delta-impulse signal-log CSV rows.")
    parser.add_argument("--symbol", default="ESU26-CME")
    parser.add_argument("--chart-number", type=int, default=2)
    parser.add_argument("--session-phase", default="rth")
    parser.add_argument("--export-config", default=DEFAULT_EXPORT_CONFIG)
    parser.add_argument("--report", default=DEFAULT_REPORT)
    parser.add_argument("--setup-start-time", default="09:45:00")
    parser.add_argument("--setup-end-time", default="15:45:00")
    parser.add_argument("--lookback-bars", type=int, default=10)
    parser.add_argument("--minimum-price-move-points", type=float, default=2.5)
    parser.add_argument("--minimum-delta-sum", type=float, default=50.0)
    parser.add_argument("--minimum-spacing-seconds", type=int, default=900)
    parser.add_argument("--max-signals-per-day", type=int, default=6)
    parser.add_argument("--stop-points", type=float, default=10.0)
    parser.add_argument("--first-target-points", type=float, default=5.0)
    parser.add_argument("--runner-target-points", type=float, default=8.0)
    parser.add_argument("--runner-stop-mode", choices=("initial", "breakeven"), default="initial")
    parser.add_argument("--trade-mode", default="replay")
    parser.add_argument("--confidence", type=float, default=0.6)
    parser.add_argument("--fail-on-mismatch", action="store_true")
    args = parser.parse_args()

    rule_config = DeltaImpulseRuleConfig(
        setup_start_time=args.setup_start_time,
        setup_end_time=args.setup_end_time,
        lookback_bars=args.lookback_bars,
        minimum_price_move_points=args.minimum_price_move_points,
        minimum_delta_sum=args.minimum_delta_sum,
        minimum_spacing_seconds=args.minimum_spacing_seconds,
        max_signals_per_day=args.max_signals_per_day,
        stop_points=args.stop_points,
        first_target_points=args.first_target_points,
        runner_target_points=args.runner_target_points,
        runner_stop_mode=args.runner_stop_mode,
        trade_mode=args.trade_mode,
        confidence=args.confidence,
    )

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
        comparison = compare_delta_impulse_overlay_log(
            normalized_rows,
            signal_rows,
            config=rule_config,
        )
    except (
        SierraExportError,
        SignalLogError,
        DeltaImpulseOverlayValidationError,
        OSError,
        ValueError,
    ) as exc:
        print(f"error: {exc}")
        return 2

    write_delta_impulse_overlay_validation_report(
        args.report,
        comparison,
        bars_source=args.bars_export,
        signal_log_source=args.signal_log,
        config=rule_config,
    )
    status = "PASS" if comparison.passed else "FAIL"
    print(
        f"overlay_validation={status}; "
        f"expected={len(comparison.expected_rows)}; "
        f"actual={len(comparison.actual_rows)}; "
        f"matched={len(comparison.matched_rows)}; "
        f"missing={len(comparison.missing_rows)}; "
        f"unexpected={len(comparison.unexpected_rows)}; "
        f"mismatched={len(comparison.mismatched_rows)}; "
        f"report={args.report}",
    )
    if args.fail_on_mismatch and not comparison.passed:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
