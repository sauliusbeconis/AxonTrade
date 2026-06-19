#!/usr/bin/env python3
"""Check price-only research outputs against acceptance gates."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from axontrade.research import (
    DEFAULT_PRICE_ONLY_ACCEPTANCE_CONFIG_PATH,
    evaluate_price_only_acceptance,
    load_price_only_acceptance_config,
    price_only_acceptance_passed,
    write_price_only_acceptance_report,
)


DEFAULT_OUTCOMES = "data/processed/AxonTrade_ES_price_only_outcomes.csv"
DEFAULT_DAILY = "reports/price-only-daily-outcome-sample.csv"
DEFAULT_TRAIN_HOLDOUT = "reports/price-only-train-holdout-sweep-sample.csv"
DEFAULT_WALK_FORWARD = "reports/price-only-walk-forward-sweep-sample.csv"
DEFAULT_REPORT = "reports/price-only-acceptance-sample.md"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check price-only research CSV outputs against acceptance gates.",
    )
    parser.add_argument("--outcomes", default=DEFAULT_OUTCOMES, help="Path to outcome CSV rows.")
    parser.add_argument("--daily", default=DEFAULT_DAILY, help="Path to daily outcome summary CSV.")
    parser.add_argument(
        "--train-holdout",
        default=DEFAULT_TRAIN_HOLDOUT,
        help="Path to train/holdout sweep CSV.",
    )
    parser.add_argument(
        "--walk-forward",
        default=DEFAULT_WALK_FORWARD,
        help="Path to walk-forward sweep CSV.",
    )
    parser.add_argument(
        "--config",
        default=DEFAULT_PRICE_ONLY_ACCEPTANCE_CONFIG_PATH,
        help="Path to acceptance-gate YAML config.",
    )
    parser.add_argument("--report", default=DEFAULT_REPORT, help="Path to write Markdown report.")
    parser.add_argument(
        "--fail-on-reject",
        action="store_true",
        help="Return exit code 1 when any configured gate fails.",
    )
    args = parser.parse_args()

    config = load_price_only_acceptance_config(args.config)
    sources = {
        "config": args.config,
        "daily": args.daily,
        "outcomes": args.outcomes,
        "train_holdout": args.train_holdout,
        "walk_forward": args.walk_forward,
    }
    findings = evaluate_price_only_acceptance(
        _read_csv(Path(args.outcomes)),
        _read_csv(Path(args.daily)),
        _read_csv(Path(args.train_holdout)),
        _read_csv(Path(args.walk_forward)),
        config=config,
    )
    write_price_only_acceptance_report(args.report, findings, config=config, sources=sources)
    status = "PASS" if price_only_acceptance_passed(findings) else "FAIL"
    print(f"wrote acceptance report to {args.report}; status={status}")
    if args.fail_on_reject and status == "FAIL":
        return 1
    return 0


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    raise SystemExit(main())
