#!/usr/bin/env python3
"""Check whether a Sierra volume-at-price export has required footprint columns."""

from __future__ import annotations

import argparse
from pathlib import Path

from axontrade.data import inspect_sierra_bar_study_file, load_sierra_export_config


DEFAULT_INPUT = (
    "/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/"
    "AxonTrade_ES_VolumeAtPriceExport.txt"
)
DEFAULT_CONFIG = "config/research/sierra_volume_at_price_export.yaml"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check a Sierra volume-at-price export for footprint research columns.",
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=DEFAULT_INPUT,
        help="Path to Sierra volume-at-price text or CSV export.",
    )
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG,
        help="Sierra volume-at-price export normalization config to check against.",
    )
    parser.add_argument(
        "--fail-on-missing",
        action="store_true",
        help="Return exit code 1 when required fields are missing.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"status=FAIL file_missing path={input_path}")
        print("manual_sierra_help_needed=yes")
        print("expected_windows_path=C:\\SierraChart\\Data\\AxonTrade_ES_VolumeAtPriceExport.txt")
        return 1 if args.fail_on_missing else 0

    inspection = inspect_sierra_bar_study_file(
        input_path,
        config=load_sierra_export_config(args.config),
        compute_opening_range=False,
    )
    status = "PASS" if inspection["ready"] else "FAIL"
    print(f"status={status} rows={inspection['row_count']} path={input_path}")
    print("manual_sierra_help_needed=no" if inspection["ready"] else "manual_sierra_help_needed=yes")
    print("fields:")
    for field_status in inspection["fields"]:
        matched = f" matched={field_status.matched_header}" if field_status.matched_header else ""
        required = "required" if field_status.required else "optional"
        print(f"- {field_status.field_name}: {field_status.status} {required}{matched}")

    if inspection["missing_required"]:
        print("missing_required=" + ",".join(inspection["missing_required"]))
    if inspection["missing_optional"]:
        print("missing_optional=" + ",".join(inspection["missing_optional"]))

    if args.fail_on_missing and not inspection["ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
