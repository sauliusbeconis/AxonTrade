#!/usr/bin/env python3
"""Compare logged Delta Impulse continuation signals with inverted fade variants."""

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
from axontrade.research import (
    SIGNAL_SCALED_SCALP_SWEEP_HEADER,
    SIGNAL_SCALED_SCALP_WALK_FORWARD_HEADER,
    SignalLogError,
    SignalScaledScalpExperimentError,
    TradeOutcomeError,
    load_signal_log_rows_csv,
    run_signal_scaled_scalp_sweep,
    run_signal_scaled_scalp_walk_forward_sweep,
    validate_signal_entries_against_bars,
)


DEFAULT_EXPORT_CONFIG = "config/research/sierra_outcome_bar_export.yaml"
DEFAULT_REPORT = "reports/sierra-delta-impulse-direction-variant-diagnostics.md"
DEFAULT_LOGGED_SWEEP = "reports/sierra-delta-impulse-direction-variant-sweep-logged.csv"
DEFAULT_INVERTED_SWEEP = "reports/sierra-delta-impulse-direction-variant-sweep-inverted.csv"
DEFAULT_LOGGED_WALK_FORWARD = (
    "reports/sierra-delta-impulse-direction-variant-walk-forward-logged.csv"
)
DEFAULT_INVERTED_WALK_FORWARD = (
    "reports/sierra-delta-impulse-direction-variant-walk-forward-inverted.csv"
)
DEFAULT_FIRST_TARGETS = "1,2,3,4,5"
DEFAULT_STOPS = "2,3,4,5,6,8,10"
DEFAULT_RUNNER_TARGETS = "2,3,5,8,10,15"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare logged Delta Impulse continuation signals with an inverted "
            "fade-direction variant using the same scaled-scalp exit grid."
        ),
    )
    parser.add_argument("bars_export", help="Path to Sierra exported bar/study text or CSV file.")
    parser.add_argument("signal_log", help="Path to AxonTrade delta-impulse signal-log CSV rows.")
    parser.add_argument("--symbol", default="ESU26-CME")
    parser.add_argument("--chart-number", type=int, default=2)
    parser.add_argument("--session-phase", default="rth")
    parser.add_argument("--export-config", default=DEFAULT_EXPORT_CONFIG)
    parser.add_argument("--report", default=DEFAULT_REPORT)
    parser.add_argument("--logged-sweep-output", default=DEFAULT_LOGGED_SWEEP)
    parser.add_argument("--inverted-sweep-output", default=DEFAULT_INVERTED_SWEEP)
    parser.add_argument("--logged-walk-forward-output", default=DEFAULT_LOGGED_WALK_FORWARD)
    parser.add_argument("--inverted-walk-forward-output", default=DEFAULT_INVERTED_WALK_FORWARD)
    parser.add_argument("--first-target-points", default=DEFAULT_FIRST_TARGETS)
    parser.add_argument("--stop-points", default=DEFAULT_STOPS)
    parser.add_argument("--runner-target-points", default=DEFAULT_RUNNER_TARGETS)
    parser.add_argument("--runner-stop-modes", default="breakeven,initial")
    parser.add_argument("--direction-filters", default="all,long,short")
    parser.add_argument("--train-date-count", type=int, default=20)
    parser.add_argument("--holdout-date-count", type=int, default=5)
    parser.add_argument("--minimum-train-trades", type=int, default=20)
    parser.add_argument("--window-step-date-count", type=int, default=5)
    parser.add_argument("--instrument-root")
    parser.add_argument("--slippage-ticks-per-side", type=int)
    parser.add_argument("--slippage-ticks-per-contract", type=float)
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
        inverted_rows = invert_candidate_signal_directions(signal_rows)
        grid = _grid_from_args(args)
        logged_sweep = _run_sweep(normalized_rows, signal_rows, args, grid)
        inverted_sweep = _run_sweep(normalized_rows, inverted_rows, args, grid)
        logged_walk_forward = _run_walk_forward(normalized_rows, signal_rows, args, grid)
        inverted_walk_forward = _run_walk_forward(normalized_rows, inverted_rows, args, grid)
    except (
        SierraExportError,
        SignalLogError,
        SignalScaledScalpExperimentError,
        TradeOutcomeError,
        ValueError,
        OSError,
    ) as exc:
        print(f"error: {exc}")
        return 2

    _write_csv(Path(args.logged_sweep_output), SIGNAL_SCALED_SCALP_SWEEP_HEADER, logged_sweep)
    _write_csv(Path(args.inverted_sweep_output), SIGNAL_SCALED_SCALP_SWEEP_HEADER, inverted_sweep)
    _write_csv(
        Path(args.logged_walk_forward_output),
        SIGNAL_SCALED_SCALP_WALK_FORWARD_HEADER,
        logged_walk_forward,
    )
    _write_csv(
        Path(args.inverted_walk_forward_output),
        SIGNAL_SCALED_SCALP_WALK_FORWARD_HEADER,
        inverted_walk_forward,
    )
    report = render_direction_variant_report(
        bars_source=args.bars_export,
        signal_log_source=args.signal_log,
        logged_sweep=logged_sweep,
        inverted_sweep=inverted_sweep,
        logged_walk_forward=logged_walk_forward,
        inverted_walk_forward=inverted_walk_forward,
        logged_sweep_source=args.logged_sweep_output,
        inverted_sweep_source=args.inverted_sweep_output,
        logged_walk_forward_source=args.logged_walk_forward_output,
        inverted_walk_forward_source=args.inverted_walk_forward_output,
        train_date_count=args.train_date_count,
        holdout_date_count=args.holdout_date_count,
        minimum_train_trades=args.minimum_train_trades,
        window_step_date_count=args.window_step_date_count,
    )
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")

    logged_holdout = summarize_walk_forward_holdouts(logged_walk_forward)
    inverted_holdout = summarize_walk_forward_holdouts(inverted_walk_forward)
    print(
        f"wrote direction-variant diagnostics to {report_path}; "
        f"logged_holdout_net_usd={logged_holdout['net_usd']:.2f}; "
        f"inverted_holdout_net_usd={inverted_holdout['net_usd']:.2f}",
    )
    return 0


def invert_candidate_signal_directions(signal_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return candidate rows with long/short directions flipped."""

    inverted_rows: list[dict[str, Any]] = []
    for row in signal_rows:
        if str(row.get("event_type", "")) != "candidate_signal":
            continue
        direction = str(row.get("direction", ""))
        if direction == "long":
            inverted_direction = "short"
        elif direction == "short":
            inverted_direction = "long"
        else:
            continue
        inverted = dict(row)
        inverted["direction"] = inverted_direction
        inverted["strategy_id"] = f"{row.get('strategy_id', '')}_inverted_fade"
        inverted["signal_id"] = f"{row.get('signal_id', '')}_inverted_fade"
        inverted["event_key"] = f"{row.get('event_key', '')}:inverted_fade"
        inverted["notes"] = f"inverted fade test; {row.get('notes', '')}"
        inverted_rows.append(inverted)
    return inverted_rows


def render_direction_variant_report(
    *,
    bars_source: str,
    signal_log_source: str,
    logged_sweep: list[dict[str, Any]],
    inverted_sweep: list[dict[str, Any]],
    logged_walk_forward: list[dict[str, Any]],
    inverted_walk_forward: list[dict[str, Any]],
    logged_sweep_source: str,
    inverted_sweep_source: str,
    logged_walk_forward_source: str,
    inverted_walk_forward_source: str,
    train_date_count: int,
    holdout_date_count: int,
    minimum_train_trades: int,
    window_step_date_count: int,
) -> str:
    """Render a Markdown comparison of logged versus inverted signal directions."""

    logged_holdout = summarize_walk_forward_holdouts(logged_walk_forward)
    inverted_holdout = summarize_walk_forward_holdouts(inverted_walk_forward)
    lines = [
        "# Sierra Delta Impulse Direction Variant Diagnostics",
        "",
        "Status: **diagnostic only**",
        "",
        "## Sources",
        "",
        f"- Bars export: `{bars_source}`",
        f"- Signal log: `{signal_log_source}`",
        f"- Logged-direction sweep: `{logged_sweep_source}`",
        f"- Inverted-direction sweep: `{inverted_sweep_source}`",
        f"- Logged-direction walk-forward: `{logged_walk_forward_source}`",
        f"- Inverted-direction walk-forward: `{inverted_walk_forward_source}`",
        "",
        "## Method",
        "",
        "- `logged`: uses Sierra's original Delta Impulse continuation direction.",
        "- `inverted`: flips every candidate direction and tests the same entry bar as a fade.",
        f"- train dates per walk-forward window: `{train_date_count}`",
        f"- holdout dates per walk-forward window: `{holdout_date_count}`",
        f"- minimum selected train trades: `{minimum_train_trades}`",
        f"- window step: `{window_step_date_count}` trade dates",
        "",
        "## Best In-Sample Sweep Rows",
        "",
        "Logged direction:",
        "",
        _sweep_table(best_sweep_rows(logged_sweep, limit=5)),
        "",
        "Inverted direction:",
        "",
        _sweep_table(best_sweep_rows(inverted_sweep, limit=5)),
        "",
        "## Walk-Forward Holdouts",
        "",
        "| Variant | Holdout Windows | Holdout Trades | Holdout Net USD |",
        "| --- | ---: | ---: | ---: |",
        (
            f"| Logged | {logged_holdout['windows']} | {logged_holdout['trades']} | "
            f"{_format_money(logged_holdout['net_usd'])} |"
        ),
        (
            f"| Inverted | {inverted_holdout['windows']} | {inverted_holdout['trades']} | "
            f"{_format_money(inverted_holdout['net_usd'])} |"
        ),
        "",
        "Inverted holdout rows:",
        "",
        _walk_forward_table([row for row in inverted_walk_forward if row["sample"] == "holdout"]),
        "",
        "## Interpretation",
        "",
        (
            "The inverted/fade direction produces positive in-sample rows, which means "
            "the failed continuation rule contains some information. However, the "
            "walk-forward holdout remains negative. Treat this as a parameter-fit "
            "warning, not as a tradable fade rule."
        ),
        "",
        (
            "A future Delta Impulse variant needs a materially different entry "
            "hypothesis, such as a stricter auction regime or liquidity-sweep context, "
            "before more exit optimization is useful."
        ),
        "",
    ]
    return "\n".join(lines)


def best_sweep_rows(rows: list[dict[str, Any]], *, limit: int) -> list[dict[str, Any]]:
    """Return the highest-net sweep rows."""

    return sorted(
        rows,
        key=lambda row: (
            float(row["net_usd"]),
            float(row["positive_net_rate"]),
            int(row["evaluated_trades"]),
        ),
        reverse=True,
    )[:limit]


def summarize_walk_forward_holdouts(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    """Summarize holdout rows from a walk-forward CSV."""

    holdouts = [row for row in rows if row["sample"] == "holdout"]
    return {
        "windows": len(holdouts),
        "trades": sum(int(row["evaluated_trades"]) for row in holdouts),
        "net_usd": sum(float(row["net_usd"]) for row in holdouts),
    }


def _run_sweep(
    bars: list[dict[str, Any]],
    signals: list[dict[str, Any]],
    args: argparse.Namespace,
    grid: dict[str, list[float] | list[str]],
) -> list[dict[str, Any]]:
    return run_signal_scaled_scalp_sweep(
        bars,
        signals,
        first_target_points_values=grid["first_targets"],
        stop_points_values=grid["stops"],
        runner_target_points_values=grid["runner_targets"],
        runner_stop_modes=grid["runner_stop_modes"],
        direction_filters=grid["direction_filters"],
        instrument_root=args.instrument_root,
        slippage_ticks_per_side=args.slippage_ticks_per_side,
        slippage_ticks_per_contract=args.slippage_ticks_per_contract,
        entry_match_mode=args.entry_match_mode,
    )


def _run_walk_forward(
    bars: list[dict[str, Any]],
    signals: list[dict[str, Any]],
    args: argparse.Namespace,
    grid: dict[str, list[float] | list[str]],
) -> list[dict[str, Any]]:
    return run_signal_scaled_scalp_walk_forward_sweep(
        bars,
        signals,
        train_date_count=args.train_date_count,
        holdout_date_count=args.holdout_date_count,
        first_target_points_values=grid["first_targets"],
        stop_points_values=grid["stops"],
        runner_target_points_values=grid["runner_targets"],
        runner_stop_modes=grid["runner_stop_modes"],
        direction_filters=grid["direction_filters"],
        minimum_train_trades=args.minimum_train_trades,
        window_step_date_count=args.window_step_date_count,
        instrument_root=args.instrument_root,
        slippage_ticks_per_side=args.slippage_ticks_per_side,
        slippage_ticks_per_contract=args.slippage_ticks_per_contract,
        entry_match_mode=args.entry_match_mode,
    )


def _grid_from_args(args: argparse.Namespace) -> dict[str, list[float] | list[str]]:
    return {
        "first_targets": _parse_float_list(args.first_target_points),
        "stops": _parse_float_list(args.stop_points),
        "runner_targets": _parse_float_list(args.runner_target_points),
        "runner_stop_modes": _parse_string_list(args.runner_stop_modes),
        "direction_filters": _parse_string_list(args.direction_filters),
    }


def _write_csv(path: Path, header: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _sweep_table(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| Direction | First Target | Stop | Runner Target | Runner Stop | Trades | Net USD |",
        "| --- | ---: | ---: | ---: | --- | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['direction_filter']} | {row['first_target_points']} | "
            f"{row['stop_points']} | {row['runner_target_points']} | "
            f"{row['runner_stop_mode']} | {row['evaluated_trades']} | "
            f"{_format_money(float(row['net_usd']))} |",
        )
    return "\n".join(lines)


def _walk_forward_table(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| Holdout Dates | Direction | First Target | Stop | Runner Target | Runner Stop | Trades | Net USD |",
        "| --- | --- | ---: | ---: | ---: | --- | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| `{row['trade_dates']}` | {row['direction_filter']} | "
            f"{row['first_target_points']} | {row['stop_points']} | "
            f"{row['runner_target_points']} | {row['runner_stop_mode']} | "
            f"{row['evaluated_trades']} | {_format_money(float(row['net_usd']))} |",
        )
    return "\n".join(lines)


def _parse_float_list(value: str) -> list[float]:
    return [float(part.strip()) for part in value.split(",") if part.strip()]


def _parse_string_list(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _format_money(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


if __name__ == "__main__":
    raise SystemExit(main())
