#!/usr/bin/env python3
"""Slippage stress for the refined MGC normal-profitability lead."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any


DEFAULT_OUTPUT = "reports/mgc-normal-bot-stress.csv"
DEFAULT_REPORT_OUTPUT = "reports/mgc-normal-bot-stress.md"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stress the refined MGC normal bot lead against slippage.",
    )
    parser.add_argument("input", nargs="?", default=None)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--symbol", default="MGC")
    args = parser.parse_args()

    normal = _load_module("run_mgc_normal_bot_research.py", "mgc_normal_bot_research")
    refine = _load_module("run_mgc_normal_bot_refine.py", "mgc_normal_bot_refine")
    mgc_eval = _load_module("run_mgc_eval_pass_initial_scan.py", "mgc_eval_pass_initial")
    core = mgc_eval._load_mnq_core()
    mgc_eval._patch_core_for_mgc(core)

    input_path = args.input or normal.DEFAULT_INPUT
    bars = core._load_feature_bars(input_path)
    bars_by_date = mgc_eval._active_bars_by_date(core._bars_by_date(bars))
    base_signals = refine._base_vwap_pullback_signals(core, bars_by_date, symbol=args.symbol)
    signals = [
        signal for signal in base_signals
        if 9 * 60 <= signal.bar.timestamp.hour * 60 + signal.bar.timestamp.minute <= 10 * 60 + 30
    ]

    rows = []
    for quantity in (1, 3, 5):
        for slippage_ticks in (1.0, 2.0, 3.0, 4.0, 5.0, 6.0):
            risk = _risk(core, normal, quantity, target_points=30.0, stop_points=15.0, slippage_ticks=slippage_ticks)
            outcomes = core._evaluate_signals(signals, bars_by_date, risk)
            row = normal._summary_row(
                core,
                f"{refine._base_strategy_id()}:filterboth:allweek:0900_1030:none:slip{slippage_ticks:g}",
                "mgc_vwap_pullback_stress",
                outcomes,
                risk,
                bars_by_date,
            )
            row["slippage_ticks_per_contract"] = normal._format_number(slippage_ticks)
            rows.append(row)

    _write_csv(args.output, [*normal.SUMMARY_HEADER, "slippage_ticks_per_contract"], rows)
    _write_report(args.report_output, normal, bars, signals, rows)
    lead = [row for row in rows if row["quantity"] == 1 and row["slippage_ticks_per_contract"] == "6"][0]
    print(
        f"wrote {len(rows)} MGC stress rows to {args.output}; "
        f"qty1_slip6_pf={lead['profit_factor']} net={lead['net_usd']} latest={lead['latest_year_net_usd']}",
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


def _risk(
    core: ModuleType,
    normal: ModuleType,
    quantity: int,
    *,
    target_points: float,
    stop_points: float,
    slippage_ticks: float,
) -> Any:
    round_turn_cost = quantity * (
        2.0 * normal.COMMISSION_PER_SIDE_USD
        + slippage_ticks * normal.TICK_VALUE_USD
    )
    return core.RiskProfile(
        quantity=quantity,
        target_net_usd=target_points * quantity * normal.POINT_VALUE_USD - round_turn_cost,
        stop_net_usd=stop_points * quantity * normal.POINT_VALUE_USD + round_turn_cost,
        target_points=target_points,
        stop_points=stop_points,
        round_turn_cost_usd=round_turn_cost,
    )


def _write_csv(path: str, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_report(
    path: str,
    normal: ModuleType,
    bars: list[Any],
    signals: list[Any],
    rows: list[dict[str, object]],
) -> None:
    lines = [
        "# MGC Normal Bot Slippage Stress",
        "",
        "Status: stress test for the refined MGC VWAP pullback normal-profitability lead.",
        "",
        "## Source",
        "",
        f"- rows: `{len(bars)}`",
        f"- dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        f"- filtered signals: `{len(signals)}`",
        "- lead: `mgc_vwap_pullback:stretch15:pb5:delta0:cl0.55:end1030:skipfri0:filterboth:allweek:0900_1030:none`",
        "- fixed exits: `30` point target, `15` point stop",
        "",
        "## Stress Rows",
        "",
        "| Qty | Slip Ticks | Target Net | Stop Net | Net | PF | DD/Net | Latest | Recent120 | Worst Q |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            "| "
            f"{row['quantity']} | {row['slippage_ticks_per_contract']} | "
            f"{row['target_net_usd']} | {row['stop_net_usd']} | "
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
            "The stress keeps the same target/stop points and increases transaction cost. "
            "Quantity scales the dollars, so the important checks are profit factor, "
            "latest-year net, recent 120-trade-day net, and drawdown-to-net stability.",
            "",
        ],
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
