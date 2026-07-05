#!/usr/bin/env python3
"""Slippage stress for the refined MGC lookback-breakout lead."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import sys
from collections import Counter
from datetime import date, datetime, time
from pathlib import Path
from types import ModuleType
from typing import Any


DEFAULT_OUTPUT = "reports/mgc-lookback-breakout-stress.csv"
DEFAULT_REPORT_OUTPUT = "reports/mgc-lookback-breakout-stress.md"
FLATTEN_TIME = time(16, 30)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stress the refined MGC lookback-breakout lead against slippage.",
    )
    parser.add_argument("input", nargs="?", default=None)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--symbol", default="MGC")
    args = parser.parse_args()

    normal = _load_module("run_mgc_normal_bot_research.py", "mgc_normal_bot_research")
    mgc_eval = _load_module("run_mgc_eval_pass_initial_scan.py", "mgc_eval_pass_initial")
    comp = _load_module("run_mgc_comprehensive_normal_search.py", "mgc_comprehensive_normal_search")
    core = mgc_eval._load_mnq_core()
    mgc_eval._patch_core_for_mgc(core)

    input_path = args.input or normal.DEFAULT_INPUT
    bars = core._load_feature_bars(input_path)
    bars_by_date = mgc_eval._active_bars_by_date(core._bars_by_date(bars))
    rows_by_index = core._rows_by_global_index(bars_by_date)
    base_signals = comp._all_lookback_breakouts(
        core,
        bars_by_date,
        strategy_id=_base_strategy_id(),
        lookback_bars=10,
        buffer_points=0.0,
        delta_threshold=0.0,
        close_location_threshold=0.50,
        entry_end=time(10, 30),
        symbol=args.symbol,
    )
    signals = [
        signal for signal in sorted(base_signals, key=lambda item: item.bar.timestamp)
        if signal.bar.high - signal.bar.low <= 8.0
    ]

    rows = []
    for target_points, stop_points in ((25.0, 15.0), (30.0, 15.0)):
        for slippage_ticks in (1.0, 2.0, 3.0, 4.0, 5.0, 6.0):
            risk = _risk(
                core,
                normal,
                target_points=target_points,
                stop_points=stop_points,
                slippage_ticks=slippage_ticks,
            )
            outcomes = _evaluate_sequence(core, signals, bars_by_date, rows_by_index, risk)
            row = normal._summary_row(
                core,
                f"{_base_strategy_id()}:filterbar8:maxday1_gap0:slip{slippage_ticks:g}",
                "mgc_lookback_breakout_stress",
                outcomes,
                risk,
                bars_by_date,
            )
            row["slippage_ticks_per_contract"] = normal._format_number(slippage_ticks)
            rows.append(row)

    _write_csv(args.output, [*normal.SUMMARY_HEADER, "slippage_ticks_per_contract"], rows)
    _write_report(args.report_output, bars, signals, rows)
    primary_slip6 = [
        row for row in rows
        if row["target_points"] == "25" and row["stop_points"] == "15"
        and row["slippage_ticks_per_contract"] == "6"
    ][0]
    print(
        f"wrote {len(rows)} MGC lookback stress rows to {args.output}; "
        f"primary_slip6_pf={primary_slip6['profit_factor']} "
        f"net={primary_slip6['net_usd']} latest={primary_slip6['latest_year_net_usd']}",
    )
    return 0


def _load_module(filename: str, module_name: str) -> ModuleType:
    module_path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _base_strategy_id() -> str:
    return "mgc_lookback_breakout_refine_base:lb10:buf0:delta0:cl0.5:end1030"


def _risk(
    core: ModuleType,
    normal: ModuleType,
    *,
    target_points: float,
    stop_points: float,
    slippage_ticks: float,
) -> Any:
    round_turn_cost = 2.0 * normal.COMMISSION_PER_SIDE_USD + slippage_ticks * normal.TICK_VALUE_USD
    return core.RiskProfile(
        quantity=1,
        target_net_usd=target_points * normal.POINT_VALUE_USD - round_turn_cost,
        stop_net_usd=stop_points * normal.POINT_VALUE_USD + round_turn_cost,
        target_points=target_points,
        stop_points=stop_points,
        round_turn_cost_usd=round_turn_cost,
    )


def _evaluate_sequence(
    core: ModuleType,
    signals: list[Any],
    bars_by_date: dict[date, list[Any]],
    rows_by_index: dict[int, int],
    risk: Any,
) -> list[Any]:
    outcomes = []
    trades_by_date: Counter[date] = Counter()
    busy_until = datetime.min
    for signal in signals:
        signal_date = signal.bar.trade_date
        if trades_by_date[signal_date] >= 1:
            continue
        if signal.bar.timestamp <= busy_until:
            continue
        rows = bars_by_date[signal_date]
        local_index = rows_by_index[signal.bar.index]
        following_rows = [
            row for row in rows[local_index + 1:]
            if row.timestamp.time() <= FLATTEN_TIME
        ]
        outcome = core._evaluate_signal(signal, following_rows, risk)
        outcomes.append(outcome)
        trades_by_date[signal_date] += 1
        busy_until = outcome.exit_time
    return outcomes


def _write_csv(path: str, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_report(path: str, bars: list[Any], signals: list[Any], rows: list[dict[str, object]]) -> None:
    lines = [
        "# MGC Lookback Breakout Slippage Stress",
        "",
        "Status: slippage stress for the refined MGC lookback-breakout normal lead.",
        "",
        "## Source",
        "",
        f"- rows: `{len(bars)}`",
        f"- dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        f"- filtered signals: `{len(signals)}`",
        f"- lead: `{_base_strategy_id()}:filterbar8:maxday1_gap0`",
        "- policy: max `1` trade/day, no re-entry",
        "",
        "## Stress Rows",
        "",
        "| Target | Stop | Slip Ticks | Target Net | Stop Net | Trades | Net | PF | DD/Net | Latest | Recent120 | Worst Q |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| "
            f"{row['target_points']} | {row['stop_points']} | {row['slippage_ticks_per_contract']} | "
            f"{row['target_net_usd']} | {row['stop_net_usd']} | {row['trades']} | "
            f"{row['net_usd']} | {row['profit_factor']} | "
            f"{float(row['drawdown_to_net']) * 100:.1f}% | "
            f"{row['latest_year_net_usd']} | {row['recent_120_trade_days_net_usd']} | "
            f"{row['worst_quarter_net_usd']} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This keeps the same entry and one-trade-per-day policy while increasing total "
            "slippage ticks per contract. A build candidate should remain positive in "
            "latest-year and recent windows after this stress, then pass chronological "
            "holdout testing.",
            "",
        ],
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
