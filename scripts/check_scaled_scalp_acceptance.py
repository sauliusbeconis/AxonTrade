#!/usr/bin/env python3
"""Check fixed scaled-scalp outcomes against acceptance gates."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from axontrade.reports import load_holiday_calendar_dates
from axontrade.research import (
    DEFAULT_SCALED_SCALP_ACCEPTANCE_CONFIG_PATH,
    evaluate_scaled_scalp_acceptance,
    load_scaled_scalp_acceptance_config,
    scaled_scalp_acceptance_passed,
    summarize_scaled_scalp_acceptance_sample,
    write_scaled_scalp_acceptance_report,
)


DEFAULT_OUTCOMES = (
    "data/processed/AxonTrade_ES_delta_impulse_3min_large_scaled_outcomes_all_5_10_8_initial.csv"
)
DEFAULT_SWEEP = "reports/sierra-delta-impulse-3min-large-scaled-exit-sweep.csv"
DEFAULT_HOLIDAY_CALENDAR = "config/research/cme_equity_index_holidays_2026.csv"
DEFAULT_REPORT = "reports/sierra-delta-impulse-3min-fixed-row-acceptance.md"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check fixed scaled-scalp outcome rows against evidence gates.",
    )
    parser.add_argument("--outcomes", default=DEFAULT_OUTCOMES, help="Path to outcome CSV rows.")
    parser.add_argument("--sweep", default=DEFAULT_SWEEP, help="Path to scaled exit sweep CSV.")
    parser.add_argument(
        "--holiday-calendar",
        default=DEFAULT_HOLIDAY_CALENDAR,
        help="Path to holiday/early-close CSV rows.",
    )
    parser.add_argument(
        "--config",
        default=DEFAULT_SCALED_SCALP_ACCEPTANCE_CONFIG_PATH,
        help="Path to fixed scaled-scalp acceptance-gate YAML config.",
    )
    parser.add_argument("--report", default=DEFAULT_REPORT, help="Path to write Markdown report.")
    parser.add_argument("--first-target-points", type=float, default=5)
    parser.add_argument("--stop-points", type=float, default=10)
    parser.add_argument("--runner-target-points", type=float, default=8)
    parser.add_argument(
        "--fail-on-reject",
        action="store_true",
        help="Return exit code 1 when any configured gate fails.",
    )
    args = parser.parse_args()

    config = load_scaled_scalp_acceptance_config(args.config)
    outcome_rows = _read_csv(Path(args.outcomes))
    sweep_rows = _read_csv(Path(args.sweep))
    holiday_dates = load_holiday_calendar_dates(args.holiday_calendar)
    sources = {
        "config": args.config,
        "holiday_calendar": args.holiday_calendar,
        "outcomes": args.outcomes,
        "sweep": args.sweep,
    }
    findings = evaluate_scaled_scalp_acceptance(
        outcome_rows,
        sweep_rows,
        holiday_dates=holiday_dates,
        config=config,
        first_target_points=args.first_target_points,
        stop_points=args.stop_points,
        runner_target_points=args.runner_target_points,
    )
    sample_summary = summarize_scaled_scalp_acceptance_sample(
        outcome_rows,
        sweep_rows,
        holiday_dates=holiday_dates,
        config=config,
        first_target_points=args.first_target_points,
        stop_points=args.stop_points,
        runner_target_points=args.runner_target_points,
    )
    write_scaled_scalp_acceptance_report(
        args.report,
        findings,
        config=config,
        sources=sources,
        sample_summary=sample_summary,
    )
    status = "PASS" if scaled_scalp_acceptance_passed(findings) else "FAIL"
    print(f"wrote fixed scaled-scalp acceptance report to {args.report}; status={status}")
    if args.fail_on_reject and status == "FAIL":
        return 1
    return 0


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    raise SystemExit(main())
