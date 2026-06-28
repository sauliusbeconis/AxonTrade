#!/usr/bin/env python3
"""Check auction-regime stack audit rows against evidence gates."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from axontrade.research import (
    DEFAULT_AUCTION_REGIME_STACK_ACCEPTANCE_CONFIG_PATH,
    auction_regime_stack_acceptance_passed,
    evaluate_auction_regime_stack_acceptance,
    load_auction_regime_stack_acceptance_config,
    summarize_auction_regime_stack_sample,
    write_auction_regime_stack_acceptance_report,
)


DEFAULT_AUDIT = "reports/sierra-signal-log-auction-regime-target-r-trade-audit-holdout1-large-sample.csv"
DEFAULT_REPORT = "reports/sierra-signal-log-auction-regime-target-r-acceptance-holdout1-large-sample.md"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check auction-regime stack audit rows against evidence gates.",
    )
    parser.add_argument("--audit", default=DEFAULT_AUDIT, help="Path to trade audit CSV rows.")
    parser.add_argument(
        "--config",
        default=DEFAULT_AUCTION_REGIME_STACK_ACCEPTANCE_CONFIG_PATH,
        help="Path to auction-regime stack acceptance-gate YAML config.",
    )
    parser.add_argument("--report", default=DEFAULT_REPORT, help="Path to write Markdown report.")
    parser.add_argument(
        "--fail-on-reject",
        action="store_true",
        help="Return exit code 1 when any configured gate fails.",
    )
    args = parser.parse_args()

    config = load_auction_regime_stack_acceptance_config(args.config)
    sources = {
        "audit": args.audit,
        "config": args.config,
    }
    audit_rows = _read_csv(Path(args.audit))
    findings = evaluate_auction_regime_stack_acceptance(audit_rows, config=config)
    sample_summary = summarize_auction_regime_stack_sample(audit_rows, config=config)
    write_auction_regime_stack_acceptance_report(
        args.report,
        findings,
        config=config,
        sources=sources,
        sample_summary=sample_summary,
    )
    status = "PASS" if auction_regime_stack_acceptance_passed(findings) else "FAIL"
    print(f"wrote auction-regime stack acceptance report to {args.report}; status={status}")
    if args.fail_on_reject and status == "FAIL":
        return 1
    return 0


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    raise SystemExit(main())
