#!/usr/bin/env python3
"""Run the fixed-row delta-impulse scaled-scalp research pipeline."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

from axontrade.data import (
    SierraExportError,
    load_sierra_export_config,
    normalize_sierra_bar_study_file,
)
from axontrade.reports import (
    load_holiday_calendar_dates,
    load_holiday_calendar_metadata,
    write_scaled_scalp_robustness_report,
    write_signal_log_report,
)
from axontrade.research import (
    DEFAULT_SCALED_SCALP_ACCEPTANCE_CONFIG_PATH,
    SIGNAL_SCALED_SCALP_SWEEP_HEADER,
    SignalLogError,
    SignalScaledScalpExperimentError,
    evaluate_scaled_scalp_acceptance,
    evaluate_signal_scaled_scalp_outcomes,
    load_scaled_scalp_acceptance_config,
    load_signal_log_rows_csv,
    run_signal_scaled_scalp_sweep,
    scaled_scalp_acceptance_passed,
    summarize_scaled_scalp_acceptance_sample,
    validate_signal_entries_against_bars,
    write_scaled_scalp_acceptance_report,
)


DEFAULT_EXPORT_CONFIG = "config/research/sierra_outcome_bar_export.yaml"
DEFAULT_OUTCOMES = (
    "data/processed/AxonTrade_ES_delta_impulse_3min_large_scaled_outcomes_all_5_10_8_initial.csv"
)
DEFAULT_SWEEP = "reports/sierra-delta-impulse-3min-large-scaled-exit-sweep.csv"
DEFAULT_SIGNAL_REPORT = "reports/sierra-delta-impulse-signal-log-live.md"
DEFAULT_ROBUSTNESS_REPORT = "reports/sierra-delta-impulse-3min-large-robustness.md"
DEFAULT_ACCEPTANCE_REPORT = "reports/sierra-delta-impulse-3min-fixed-row-acceptance.md"
DEFAULT_HOLIDAY_CALENDAR = "config/research/cme_equity_index_holidays_2026.csv"
DEFAULT_SWEEP_FIRST_TARGETS = "1,2,3,4,5"
DEFAULT_SWEEP_STOPS = "2,3,4,5,6,8,10"
DEFAULT_SWEEP_RUNNER_TARGETS = "2,3,5,8,10,15"
SCALED_SCALP_OUTCOME_HEADER = [
    "schema_version",
    "outcome_id",
    "event_key",
    "signal_id",
    "symbol",
    "direction",
    "entry_bar_index",
    "exit_bar_index",
    "entry_time",
    "exit_time",
    "entry_price",
    "stop_price",
    "first_target_price",
    "runner_target_price",
    "leg1_exit_price",
    "runner_exit_price",
    "exit_reason",
    "first_target_hit",
    "holding_bars",
    "gross_points",
    "gross_usd",
    "commission_usd",
    "slippage_usd",
    "net_usd",
    "notes",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Regenerate fixed delta-impulse scaled-scalp outcomes, sweep rows, "
            "robustness report, and acceptance report from one Sierra export."
        ),
    )
    parser.add_argument("bars_export", help="Path to Sierra exported bar/study text or CSV file.")
    parser.add_argument("signal_log", help="Path to AxonTrade signal-log CSV rows.")
    parser.add_argument("--symbol", default="ESU26-CME")
    parser.add_argument("--chart-number", type=int, default=2)
    parser.add_argument("--session-phase", default="rth")
    parser.add_argument("--export-config", default=DEFAULT_EXPORT_CONFIG)
    parser.add_argument("--first-target-points", type=float, default=5)
    parser.add_argument("--stop-points", type=float, default=10)
    parser.add_argument("--runner-target-points", type=float, default=8)
    parser.add_argument(
        "--runner-stop-mode",
        choices=("breakeven", "initial"),
        default="initial",
    )
    parser.add_argument("--direction-filter", choices=("all", "long", "short"), default="all")
    parser.add_argument("--outcomes-output", default=DEFAULT_OUTCOMES)
    parser.add_argument("--sweep-output", default=DEFAULT_SWEEP)
    parser.add_argument("--signal-report", default=DEFAULT_SIGNAL_REPORT)
    parser.add_argument("--robustness-report", default=DEFAULT_ROBUSTNESS_REPORT)
    parser.add_argument("--acceptance-report", default=DEFAULT_ACCEPTANCE_REPORT)
    parser.add_argument("--holiday-calendar", default=DEFAULT_HOLIDAY_CALENDAR)
    parser.add_argument("--acceptance-config", default=DEFAULT_SCALED_SCALP_ACCEPTANCE_CONFIG_PATH)
    parser.add_argument("--sweep-first-target-points", default=DEFAULT_SWEEP_FIRST_TARGETS)
    parser.add_argument("--sweep-stop-points", default=DEFAULT_SWEEP_STOPS)
    parser.add_argument("--sweep-runner-target-points", default=DEFAULT_SWEEP_RUNNER_TARGETS)
    parser.add_argument("--sweep-runner-stop-modes", default="breakeven,initial")
    parser.add_argument("--sweep-direction-filters", default="all,long,short")
    parser.add_argument("--instrument-root")
    parser.add_argument("--slippage-ticks-per-side", type=int)
    parser.add_argument("--slippage-ticks-per-contract", type=float)
    parser.add_argument(
        "--entry-match-mode",
        choices=("bar_index", "timestamp", "auto"),
        default="auto",
    )
    parser.add_argument(
        "--fail-on-reject",
        action="store_true",
        help="Return exit code 1 when the acceptance gate fails.",
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
        entry_diagnostics = validate_signal_entries_against_bars(
            normalized_rows,
            signal_rows,
        )
        outcome_rows = evaluate_signal_scaled_scalp_outcomes(
            normalized_rows,
            signal_rows,
            first_target_points=args.first_target_points,
            stop_points=args.stop_points,
            runner_target_points=args.runner_target_points,
            runner_stop_mode=args.runner_stop_mode,
            direction_filter=args.direction_filter,
            instrument_root=args.instrument_root,
            slippage_ticks_per_side=args.slippage_ticks_per_side,
            slippage_ticks_per_contract=args.slippage_ticks_per_contract,
            entry_match_mode=args.entry_match_mode,
        )
        sweep_rows = run_signal_scaled_scalp_sweep(
            normalized_rows,
            signal_rows,
            first_target_points_values=_parse_float_list(args.sweep_first_target_points),
            stop_points_values=_parse_float_list(args.sweep_stop_points),
            runner_target_points_values=_parse_float_list(args.sweep_runner_target_points),
            runner_stop_modes=_parse_string_list(args.sweep_runner_stop_modes),
            direction_filters=_parse_string_list(args.sweep_direction_filters),
            instrument_root=args.instrument_root,
            slippage_ticks_per_side=args.slippage_ticks_per_side,
            slippage_ticks_per_contract=args.slippage_ticks_per_contract,
            entry_match_mode=args.entry_match_mode,
        )
        holiday_dates = load_holiday_calendar_dates(args.holiday_calendar)
        holiday_metadata = load_holiday_calendar_metadata(args.holiday_calendar)
        acceptance_config = load_scaled_scalp_acceptance_config(args.acceptance_config)
        findings = evaluate_scaled_scalp_acceptance(
            outcome_rows,
            sweep_rows,
            holiday_dates=holiday_dates,
            config=acceptance_config,
            first_target_points=args.first_target_points,
            stop_points=args.stop_points,
            runner_target_points=args.runner_target_points,
        )
        sample_summary = summarize_scaled_scalp_acceptance_sample(
            outcome_rows,
            sweep_rows,
            holiday_dates=holiday_dates,
            config=acceptance_config,
            first_target_points=args.first_target_points,
            stop_points=args.stop_points,
            runner_target_points=args.runner_target_points,
        )
    except (SierraExportError, SignalLogError, SignalScaledScalpExperimentError, ValueError) as exc:
        print(f"error: {exc}")
        return 2

    write_signal_log_report(args.signal_report, signal_rows, source=args.signal_log)
    _write_csv(Path(args.outcomes_output), SCALED_SCALP_OUTCOME_HEADER, outcome_rows)
    _write_csv(Path(args.sweep_output), SIGNAL_SCALED_SCALP_SWEEP_HEADER, sweep_rows)
    write_scaled_scalp_robustness_report(
        args.robustness_report,
        outcome_rows,
        sweep_rows,
        title="Sierra Delta Impulse 3-Min Fixed Row Robustness",
        variant_label=_variant_label(args),
        outcome_source=args.outcomes_output,
        sweep_source=args.sweep_output,
        main_summary_source="reports/sierra-delta-impulse-3min-large-sample-outcomes.md",
        holiday_calendar_source=args.holiday_calendar,
        holiday_dates=holiday_dates,
        holiday_source_url=holiday_metadata["source_url"] or None,
        holiday_retrieved_date=holiday_metadata["retrieved_date"] or None,
        first_target_points=args.first_target_points,
        stop_points=args.stop_points,
        runner_target_points=args.runner_target_points,
    )
    sources = {
        "config": args.acceptance_config,
        "holiday_calendar": args.holiday_calendar,
        "outcomes": args.outcomes_output,
        "sweep": args.sweep_output,
    }
    write_scaled_scalp_acceptance_report(
        args.acceptance_report,
        findings,
        config=acceptance_config,
        sources=sources,
        sample_summary=sample_summary,
    )
    status = "PASS" if scaled_scalp_acceptance_passed(findings) else "FAIL"
    outcome_net = sum(float(row["net_usd"]) for row in outcome_rows)
    print(
        f"validated {len(entry_diagnostics)} entries; "
        f"outcomes={len(outcome_rows)} net_usd={outcome_net:.2f}; "
        f"sweep_rows={len(sweep_rows)}; acceptance={status}",
    )
    if args.fail_on_reject and status == "FAIL":
        return 1
    return 0


def _write_csv(path: Path, header: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header)
        writer.writeheader()
        writer.writerows(rows)


def _parse_float_list(value: str) -> list[float]:
    return [float(part.strip()) for part in value.split(",") if part.strip()]


def _parse_string_list(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _variant_label(args: argparse.Namespace) -> str:
    return (
        f"{_format_number(args.first_target_points)} / "
        f"{_format_number(args.stop_points)} / "
        f"{_format_number(args.runner_target_points)} / "
        f"{args.runner_stop_mode}"
    )


def _format_number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:g}"


if __name__ == "__main__":
    raise SystemExit(main())
