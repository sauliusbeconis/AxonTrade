#!/usr/bin/env python3
"""Write trade-level audit rows for selected scaled-context filters."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from axontrade.research import (
    SCALED_CONTEXT_SELECTED_TRADE_AUDIT_HEADER,
    ScaledContextFilterExperimentError,
    ScaledContextSelectedVetoError,
    audit_scaled_context_selected_trades,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit trades selected by scaled-context walk-forward rows.",
    )
    parser.add_argument("context_diagnostics", help="Path to scaled context diagnostic CSV rows.")
    parser.add_argument("selected_rules", help="Path to selected context walk-forward CSV rows.")
    parser.add_argument("output", help="Path to write selected-trade audit CSV rows.")
    args = parser.parse_args()

    try:
        audit_rows = audit_scaled_context_selected_trades(
            context_rows=_read_csv(Path(args.context_diagnostics)),
            selection_rows=_read_csv(Path(args.selected_rules)),
        )
    except (ScaledContextFilterExperimentError, ScaledContextSelectedVetoError, OSError) as exc:
        print(f"error: {exc}")
        return 2

    output_path = Path(args.output)
    _write_csv(output_path, SCALED_CONTEXT_SELECTED_TRADE_AUDIT_HEADER, audit_rows)
    holdout_rows = [row for row in audit_rows if row["sample"] == "holdout"]
    holdout_net = sum(float(row["net_usd"]) for row in holdout_rows)
    print(
        f"wrote {len(audit_rows)} selected context trade audit rows to {output_path}; "
        f"holdout_trades={len(holdout_rows)}, "
        f"holdout_net_usd={holdout_net:.2f}",
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


if __name__ == "__main__":
    raise SystemExit(main())
