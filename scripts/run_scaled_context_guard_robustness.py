#!/usr/bin/env python3
"""Run compact theory-guard robustness checks over scaled context diagnostics."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from axontrade.research import (
    DEFAULT_GUARD_ROBUSTNESS_WINDOW_CONFIGS,
    SCALED_CONTEXT_GUARD_ROBUSTNESS_HEADER,
    ScaledContextLossAttributionError,
    render_scaled_context_guard_robustness_report,
    run_scaled_context_guard_robustness,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run compact scaled-context theory-guard robustness checks.",
    )
    parser.add_argument("context_diagnostics", help="Path to scaled context diagnostic CSV rows.")
    parser.add_argument("output_csv", help="Path to write robustness summary CSV rows.")
    parser.add_argument("output_report", help="Path to write robustness Markdown report.")
    parser.add_argument(
        "--window-configs",
        default=_format_window_configs(DEFAULT_GUARD_ROBUSTNESS_WINDOW_CONFIGS),
        help="Comma-separated train:holdout:step configs, for example 20:5:5,40:5:5.",
    )
    parser.add_argument("--minimum-train-trades", type=int, default=25)
    parser.add_argument("--minimum-train-participation-rate", type=float, default=0.35)
    parser.add_argument(
        "--selection-objective",
        choices=("lower_bound", "net", "average"),
        default="lower_bound",
    )
    args = parser.parse_args()

    try:
        context_rows = _read_csv(Path(args.context_diagnostics))
        robustness_rows = run_scaled_context_guard_robustness(
            context_rows,
            window_configs=_parse_window_configs(args.window_configs),
            minimum_train_trades=args.minimum_train_trades,
            minimum_train_participation_rate=args.minimum_train_participation_rate,
            selection_objective=args.selection_objective,
        )
        report = render_scaled_context_guard_robustness_report(
            robustness_rows,
            context_source=args.context_diagnostics,
        )
    except (ScaledContextLossAttributionError, OSError) as exc:
        print(f"error: {exc}")
        return 2

    output_csv = Path(args.output_csv)
    output_report = Path(args.output_report)
    _write_csv(output_csv, SCALED_CONTEXT_GUARD_ROBUSTNESS_HEADER, robustness_rows)
    output_report.parent.mkdir(parents=True, exist_ok=True)
    output_report.write_text(report, encoding="utf-8")
    best_row = max(robustness_rows, key=lambda row: float(row["guarded_holdout_net_usd"]))
    print(
        f"wrote {len(robustness_rows)} guard robustness rows to {output_csv}; "
        f"best_guarded_holdout_net_usd={float(best_row['guarded_holdout_net_usd']):.2f}",
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


def _parse_window_configs(value: str) -> list[tuple[int, int, int]]:
    configs: list[tuple[int, int, int]] = []
    for raw_config in value.split(","):
        config = raw_config.strip()
        if not config:
            continue
        parts = config.split(":")
        if len(parts) != 3:
            raise ScaledContextLossAttributionError(
                f"Invalid window config: {raw_config!r}",
            )
        try:
            train, holdout, step = (int(part) for part in parts)
        except ValueError as exc:
            raise ScaledContextLossAttributionError(
                f"Invalid window config: {raw_config!r}",
            ) from exc
        configs.append((train, holdout, step))
    if not configs:
        raise ScaledContextLossAttributionError("At least one window config is required")
    return configs


def _format_window_configs(configs: tuple[tuple[int, int, int], ...]) -> str:
    return ",".join(f"{train}:{holdout}:{step}" for train, holdout, step in configs)


if __name__ == "__main__":
    raise SystemExit(main())
