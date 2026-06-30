#!/usr/bin/env python3
"""Check scaled context guard candidate rows against acceptance gates."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from axontrade.research import (
    DEFAULT_SCALED_CONTEXT_GUARD_ACCEPTANCE_CONFIG_PATH,
    evaluate_scaled_context_guard_acceptance,
    load_scaled_context_guard_acceptance_config,
    scaled_context_guard_acceptance_passed,
    summarize_scaled_context_guard_acceptance_sample,
    write_scaled_context_guard_acceptance_report,
)


DEFAULT_FIXED_GUARDS = (
    "reports/"
    "sierra-signal-log-scalp-entry-baselines-continuous-240d-"
    "vwap-delta-exhaustion-loss-attribution-fixed-guards.csv"
)
DEFAULT_ROBUSTNESS = (
    "reports/"
    "sierra-signal-log-scalp-entry-baselines-continuous-240d-"
    "vwap-delta-exhaustion-guard-robustness.csv"
)
DEFAULT_REPORT = (
    "reports/"
    "sierra-signal-log-scalp-entry-baselines-continuous-240d-"
    "vwap-delta-exhaustion-guard-acceptance.md"
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check a fixed scaled-context guard against evidence gates.",
    )
    parser.add_argument(
        "--fixed-guards",
        default=DEFAULT_FIXED_GUARDS,
        help="Path to fixed guard evaluation CSV rows.",
    )
    parser.add_argument(
        "--robustness",
        default=DEFAULT_ROBUSTNESS,
        help="Path to guard robustness CSV rows.",
    )
    parser.add_argument(
        "--config",
        default=DEFAULT_SCALED_CONTEXT_GUARD_ACCEPTANCE_CONFIG_PATH,
        help="Path to scaled-context guard acceptance YAML config.",
    )
    parser.add_argument("--report", default=DEFAULT_REPORT, help="Path to write Markdown report.")
    parser.add_argument(
        "--fail-on-reject",
        action="store_true",
        help="Return exit code 1 when any configured gate fails.",
    )
    args = parser.parse_args()

    config = load_scaled_context_guard_acceptance_config(args.config)
    fixed_guard_rows = _read_csv(Path(args.fixed_guards))
    robustness_rows = _read_csv(Path(args.robustness))
    sources = {
        "config": args.config,
        "fixed_guards": args.fixed_guards,
        "robustness": args.robustness,
    }
    findings = evaluate_scaled_context_guard_acceptance(
        fixed_guard_rows,
        robustness_rows,
        config=config,
    )
    sample_summary = summarize_scaled_context_guard_acceptance_sample(
        fixed_guard_rows,
        robustness_rows,
        config=config,
    )
    write_scaled_context_guard_acceptance_report(
        args.report,
        findings,
        config=config,
        sources=sources,
        sample_summary=sample_summary,
    )
    status = "PASS" if scaled_context_guard_acceptance_passed(findings) else "FAIL"
    print(f"wrote scaled context guard acceptance report to {args.report}; status={status}")
    if args.fail_on_reject and status == "FAIL":
        return 1
    return 0


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    raise SystemExit(main())
