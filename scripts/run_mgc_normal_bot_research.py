#!/usr/bin/env python3
"""Research MGC normal-profitability bot candidates."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import math
import statistics
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable


DEFAULT_INPUT = (
    "/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/"
    "AxonTrade_MGC_OrderflowExport_Expanded.txt"
)
DEFAULT_OUTPUT = "reports/mgc-normal-bot-research.csv"
DEFAULT_TRADE_AUDIT_OUTPUT = "reports/mgc-normal-bot-best-trade-audit.csv"
DEFAULT_REPORT_OUTPUT = "reports/mgc-normal-bot-research.md"

POINT_VALUE_USD = 10.0
TICK_VALUE_USD = 1.0
COMMISSION_PER_SIDE_USD = 0.50
SLIPPAGE_TICKS_PER_CONTRACT = 1.0


SUMMARY_HEADER = [
    "schema_version",
    "strategy_id",
    "family",
    "quantity",
    "target_points",
    "stop_points",
    "target_net_usd",
    "stop_net_usd",
    "trades",
    "signal_days",
    "net_usd",
    "average_trade_usd",
    "win_rate",
    "profit_factor",
    "max_drawdown_usd",
    "drawdown_to_net",
    "worst_trade_usd",
    "worst_day_usd",
    "year_count",
    "positive_years",
    "negative_years",
    "worst_year_net_usd",
    "latest_year",
    "latest_year_trades",
    "latest_year_net_usd",
    "latest_year_profit_factor",
    "quarter_count",
    "positive_quarters",
    "negative_quarters",
    "worst_quarter_net_usd",
    "recent_120_trade_days_trades",
    "recent_120_trade_days_net_usd",
    "average_holding_minutes",
    "target_hits",
    "stop_hits",
    "eod_exits",
    "signal_frequency_per_trade_day",
    "average_calendar_gap_between_signals",
    "median_calendar_gap_between_signals",
    "notes",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a normal-profitability MGC continuation scan.",
    )
    parser.add_argument("input", nargs="?", default=DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--trade-audit-output", default=DEFAULT_TRADE_AUDIT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--symbol", default="MGC")
    parser.add_argument("--minimum-trades", type=int, default=60)
    args = parser.parse_args()

    mgc_eval = _load_module("run_mgc_eval_pass_initial_scan.py", "mgc_eval_pass_initial")
    core = mgc_eval._load_mnq_core()
    mgc_eval._patch_core_for_mgc(core)

    bars = core._load_feature_bars(args.input)
    bars_by_date = mgc_eval._active_bars_by_date(core._bars_by_date(bars))
    signals_by_strategy = mgc_eval._generate_mgc_signals(
        core,
        bars_by_date,
        symbol=args.symbol,
    )
    risk_profiles = _normal_risk_profiles(core)

    summary_rows = []
    best_row: dict[str, object] | None = None
    best_outcomes = []
    for strategy_id, signals in signals_by_strategy.items():
        if len(signals) < args.minimum_trades:
            continue
        family = strategy_id.split(":", 1)[0]
        for risk in risk_profiles:
            outcomes = core._evaluate_signals(signals, bars_by_date, risk)
            row = _summary_row(core, strategy_id, family, outcomes, risk, bars_by_date)
            summary_rows.append(row)
            if _is_better_row(row, best_row):
                best_row = row
                best_outcomes = outcomes

    summary_rows.sort(key=_ranking_key)
    _write_csv(args.output, summary_rows)
    if best_row is not None:
        core._write_trade_audit(args.trade_audit_output, best_outcomes, best_row)
    _write_report(args.report_output, bars, summary_rows, best_row)

    best_summary = "none"
    if best_row is not None:
        best_summary = (
            f"{best_row['strategy_id']} qty={best_row['quantity']} "
            f"target={best_row['target_points']} stop={best_row['stop_points']} "
            f"pf={best_row['profit_factor']} net={best_row['net_usd']} "
            f"latest={best_row['latest_year_net_usd']}"
        )
    print(
        f"wrote {len(summary_rows)} MGC normal bot rows to {args.output}; "
        f"best={best_summary}",
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


def _normal_risk_profiles(core: ModuleType) -> list[Any]:
    profiles = []
    point_pairs = (
        (6.0, 4.0),
        (8.0, 5.0),
        (10.0, 6.0),
        (12.0, 8.0),
        (15.0, 10.0),
        (20.0, 12.0),
        (25.0, 15.0),
        (8.0, 8.0),
        (12.0, 12.0),
        (20.0, 20.0),
    )
    for quantity in (1, 2, 3, 5):
        round_turn_cost = quantity * (
            2.0 * COMMISSION_PER_SIDE_USD
            + SLIPPAGE_TICKS_PER_CONTRACT * TICK_VALUE_USD
        )
        for target_points, stop_points in point_pairs:
            target_points = core._round_up_to_tick(target_points)
            stop_points = core._round_up_to_tick(stop_points)
            target_net_usd = target_points * quantity * POINT_VALUE_USD - round_turn_cost
            stop_net_usd = stop_points * quantity * POINT_VALUE_USD + round_turn_cost
            profiles.append(
                core.RiskProfile(
                    quantity=quantity,
                    target_net_usd=target_net_usd,
                    stop_net_usd=stop_net_usd,
                    target_points=target_points,
                    stop_points=stop_points,
                    round_turn_cost_usd=round_turn_cost,
                ),
            )
    return profiles


def _summary_row(
    core: ModuleType,
    strategy_id: str,
    family: str,
    outcomes: list[Any],
    risk: Any,
    bars_by_date: dict[date, list[Any]],
) -> dict[str, object]:
    values = [outcome.net_usd for outcome in outcomes]
    positive = [value for value in values if value > 0.0]
    negative = [value for value in values if value < 0.0]
    net = sum(values)
    max_drawdown = core._max_drawdown(values)
    daily_net: dict[date, float] = defaultdict(float)
    yearly_net: dict[int, float] = defaultdict(float)
    quarterly_net: dict[tuple[int, int], float] = defaultdict(float)
    latest_year = max(bars_by_date).year if bars_by_date else 0
    latest_year_values = []
    recent_date_set = set(sorted(bars_by_date)[-120:])
    recent_values = []
    for outcome in outcomes:
        entry_date = outcome.entry_time.date()
        quarter = (outcome.entry_time.month - 1) // 3 + 1
        daily_net[entry_date] += outcome.net_usd
        yearly_net[outcome.entry_time.year] += outcome.net_usd
        quarterly_net[(outcome.entry_time.year, quarter)] += outcome.net_usd
        if outcome.entry_time.year == latest_year:
            latest_year_values.append(outcome.net_usd)
        if entry_date in recent_date_set:
            recent_values.append(outcome.net_usd)

    latest_positive = [value for value in latest_year_values if value > 0.0]
    latest_negative = [value for value in latest_year_values if value < 0.0]
    signal_dates = sorted({outcome.entry_time.date() for outcome in outcomes})
    gaps = [
        (right - left).days
        for left, right in zip(signal_dates, signal_dates[1:], strict=False)
    ]
    trade_dates = sorted(bars_by_date)
    return {
        "schema_version": 1,
        "strategy_id": strategy_id,
        "family": family,
        "quantity": risk.quantity,
        "target_points": _format_number(risk.target_points),
        "stop_points": _format_number(risk.stop_points),
        "target_net_usd": _format_number(risk.target_net_usd),
        "stop_net_usd": _format_number(risk.stop_net_usd),
        "trades": len(outcomes),
        "signal_days": len(signal_dates),
        "net_usd": _format_number(net),
        "average_trade_usd": _format_number(statistics.mean(values) if values else 0.0),
        "win_rate": _format_number(len(positive) / len(values) if values else 0.0),
        "profit_factor": _format_number(sum(positive) / abs(sum(negative)) if negative else 999.0),
        "max_drawdown_usd": _format_number(max_drawdown),
        "drawdown_to_net": _format_number(abs(max_drawdown) / net if net > 0.0 else 999.0),
        "worst_trade_usd": _format_number(min(values) if values else 0.0),
        "worst_day_usd": _format_number(min(daily_net.values()) if daily_net else 0.0),
        "year_count": len(yearly_net),
        "positive_years": sum(value > 0.0 for value in yearly_net.values()),
        "negative_years": sum(value < 0.0 for value in yearly_net.values()),
        "worst_year_net_usd": _format_number(min(yearly_net.values()) if yearly_net else 0.0),
        "latest_year": latest_year,
        "latest_year_trades": len(latest_year_values),
        "latest_year_net_usd": _format_number(sum(latest_year_values)),
        "latest_year_profit_factor": _format_number(
            sum(latest_positive) / abs(sum(latest_negative)) if latest_negative else 999.0,
        ),
        "quarter_count": len(quarterly_net),
        "positive_quarters": sum(value > 0.0 for value in quarterly_net.values()),
        "negative_quarters": sum(value < 0.0 for value in quarterly_net.values()),
        "worst_quarter_net_usd": _format_number(
            min(quarterly_net.values()) if quarterly_net else 0.0,
        ),
        "recent_120_trade_days_trades": len(recent_values),
        "recent_120_trade_days_net_usd": _format_number(sum(recent_values)),
        "average_holding_minutes": _format_number(
            statistics.mean(outcome.holding_minutes for outcome in outcomes)
            if outcomes
            else 0.0,
        ),
        "target_hits": sum(outcome.exit_reason == "target_hit" for outcome in outcomes),
        "stop_hits": sum(outcome.exit_reason == "stop_hit" for outcome in outcomes),
        "eod_exits": sum(
            outcome.exit_reason in {"end_of_session", "no_following_bar"}
            for outcome in outcomes
        ),
        "signal_frequency_per_trade_day": _format_number(
            len(signal_dates) / len(trade_dates) if trade_dates else 0.0,
        ),
        "average_calendar_gap_between_signals": _format_number(
            statistics.mean(gaps) if gaps else 0.0,
        ),
        "median_calendar_gap_between_signals": _format_number(
            statistics.median(gaps) if gaps else 0.0,
        ),
        "notes": "normal profitability scan; one strategy signal per chart date; no eval pass objective",
    }


def _ranking_key(row: dict[str, object]) -> tuple[float, ...]:
    trades = int(row["trades"])
    net = float(row["net_usd"])
    latest_net = float(row["latest_year_net_usd"])
    recent_net = float(row["recent_120_trade_days_net_usd"])
    profit_factor = float(row["profit_factor"])
    drawdown_to_net = float(row["drawdown_to_net"])
    worst_year = float(row["worst_year_net_usd"])
    worst_quarter = float(row["worst_quarter_net_usd"])
    return (
        0.0 if trades >= 100 else 1.0,
        0.0 if net > 0.0 and latest_net > 0.0 and recent_net > 0.0 else 1.0,
        0.0 if profit_factor >= 1.25 else 1.0,
        0.0 if worst_year >= 0.0 else 1.0,
        0.0 if worst_quarter >= -abs(net) * 0.15 else 1.0,
        drawdown_to_net,
        -profit_factor,
        -float(row["average_trade_usd"]),
        -latest_net,
    )


def _is_better_row(
    row: dict[str, object],
    current_best: dict[str, object] | None,
) -> bool:
    if current_best is None:
        return True
    return _ranking_key(row) < _ranking_key(current_best)


def _accepted_rows(rows: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    return [
        row for row in rows
        if int(row["trades"]) >= 100
        and float(row["net_usd"]) > 0.0
        and float(row["latest_year_net_usd"]) > 0.0
        and float(row["recent_120_trade_days_net_usd"]) > 0.0
        and float(row["profit_factor"]) >= 1.25
        and float(row["latest_year_profit_factor"]) >= 1.10
        and float(row["drawdown_to_net"]) <= 0.75
        and int(row["negative_years"]) <= 1
    ]


def _write_csv(path: str, rows: list[dict[str, object]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=SUMMARY_HEADER, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_report(
    path: str,
    bars: list[Any],
    summary_rows: list[dict[str, object]],
    best_row: dict[str, object] | None,
) -> None:
    accepted = _accepted_rows(summary_rows)
    lines = [
        "# MGC Normal Bot Research",
        "",
        "Status: exploratory MGC normal-profitability research. Not an ACSIL candidate yet.",
        "",
        "## Objective",
        "",
        "Find a normal MGC bot candidate, not an eval-pass configuration. Ranking favors "
        "profitability, recent performance, profit factor, yearly/quarterly stability, "
        "and drawdown-to-net ratio.",
        "",
        "## Source",
        "",
        f"- rows: `{len(bars)}`",
        f"- dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        f"- unique dates: `{len({bar.trade_date for bar in bars})}`",
        "- instrument: `MGC`, point value `$10`, tick value `$1`",
        "- cost model: `$0.50/side` commission plus `1` total slippage tick per contract",
        "- setup window inherited from the MGC research profile: `08:20` to `13:30`, flatten by `16:30`",
        "",
        "## Search Space",
        "",
        "- entry families: COMEX opening-range breakout, lookback breakout, VWAP pullback continuation",
        "- one strategy signal per chart date",
        "- quantities: `1`, `2`, `3`, `5` MGC",
        "- target/stop points: `6/4`, `8/5`, `10/6`, `12/8`, `15/10`, `20/12`, "
        "`25/15`, `8/8`, `12/12`, `20/20`",
        "",
        "## Result",
        "",
    ]
    if best_row is None:
        lines.append("No rows were generated.")
    else:
        lines.extend(
            [
                "Best row by normal-profitability ranking:",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Strategy | `{best_row['strategy_id']}` |",
                f"| Quantity | `{best_row['quantity']}` |",
                f"| Target / stop points | `{best_row['target_points']} / {best_row['stop_points']}` |",
                f"| Target / stop net | `${best_row['target_net_usd']} / ${best_row['stop_net_usd']}` |",
                f"| Trades | `{best_row['trades']}` |",
                f"| Net | `${best_row['net_usd']}` |",
                f"| Average trade | `${best_row['average_trade_usd']}` |",
                f"| Win rate | `{float(best_row['win_rate']) * 100:.1f}%` |",
                f"| Profit factor | `{best_row['profit_factor']}` |",
                f"| Max trade-sequence drawdown | `${best_row['max_drawdown_usd']}` |",
                f"| Drawdown / net | `{float(best_row['drawdown_to_net']) * 100:.1f}%` |",
                f"| Latest-year trades | `{best_row['latest_year_trades']}` |",
                f"| Latest-year net | `${best_row['latest_year_net_usd']}` |",
                f"| Recent 120 trade-day net | `${best_row['recent_120_trade_days_net_usd']}` |",
                f"| Worst year | `${best_row['worst_year_net_usd']}` |",
                f"| Worst quarter | `${best_row['worst_quarter_net_usd']}` |",
                f"| Signal frequency | `{float(best_row['signal_frequency_per_trade_day']) * 100:.1f}%` of trade dates |",
                "",
            ],
        )
        if accepted:
            lines.append(f"Rows passing the first normal-profitability lens: `{len(accepted)}`.")
        else:
            lines.append(
                "No row passed the first normal-profitability lens. Treat the top rows "
                "as leads only; they need deeper filtering or a different idea.",
            )
    lines.extend(
        [
            "",
            "## Top Rows",
            "",
            "| Rank | Family | Qty | Target | Stop | Trades | Net | PF | DD/Net | Latest | Recent120 | Worst Q | Strategy |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ],
    )
    for rank, row in enumerate(summary_rows[:20], start=1):
        lines.append(
            "| "
            f"{rank} | {row['family']} | {row['quantity']} | "
            f"{row['target_points']} | {row['stop_points']} | {row['trades']} | "
            f"{row['net_usd']} | {row['profit_factor']} | "
            f"{float(row['drawdown_to_net']) * 100:.1f}% | "
            f"{row['latest_year_net_usd']} | {row['recent_120_trade_days_net_usd']} | "
            f"{row['worst_quarter_net_usd']} | `{row['strategy_id']}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This scan deliberately avoids eval-pass metrics. A real MGC bot candidate still "
            "needs slippage stress, walk-forward/frozen holdout testing, session filtering, "
            "and Sierra replay/mechanics validation before implementation.",
            "",
        ],
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def _format_number(value: float) -> str:
    if not math.isfinite(value):
        return "999"
    formatted = f"{value:.8f}".rstrip("0").rstrip(".")
    return formatted if formatted else "0"


if __name__ == "__main__":
    raise SystemExit(main())
