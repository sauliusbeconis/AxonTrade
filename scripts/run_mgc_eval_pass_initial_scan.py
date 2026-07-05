#!/usr/bin/env python3
"""Initial MGC scan for LucidFlex-style eval-pass candidates."""

from __future__ import annotations

import argparse
import importlib.util
import statistics
import sys
from collections import defaultdict
from datetime import date, time
from pathlib import Path
from types import ModuleType
from typing import Any


DEFAULT_INPUT = (
    "/home/saulius/WinePrefixes/SierraChart/drive_c/SierraChart/Data/"
    "AxonTrade_MGC_OrderflowExport_Expanded.txt"
)
DEFAULT_SWEEP_OUTPUT = "reports/mgc-eval-pass-initial-scan.csv"
DEFAULT_TRADE_AUDIT_OUTPUT = "reports/mgc-eval-pass-initial-best-trade-audit.csv"
DEFAULT_REPORT_OUTPUT = "reports/mgc-eval-pass-initial-scan.md"

POINT_VALUE_USD = 10.0
TICK_SIZE_POINTS = 0.10
TICK_VALUE_USD = 1.00
COMMISSION_PER_SIDE_USD = 0.50
SLIPPAGE_TICKS_PER_CONTRACT = 1.0
SETUP_START = time(8, 20)
OPENING_RANGE_START = time(8, 20)
OPENING_RANGE_END = time(8, 50)
FLATTEN_TIME = time(16, 30)

EXTRA_SWEEP_FIELDS = [
    "signal_frequency_per_trade_day",
    "average_calendar_gap_between_signals",
    "median_calendar_gap_between_signals",
]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run an initial MGC eval-pass continuation scan.",
    )
    parser.add_argument("input", nargs="?", default=DEFAULT_INPUT)
    parser.add_argument("--sweep-output", default=DEFAULT_SWEEP_OUTPUT)
    parser.add_argument("--trade-audit-output", default=DEFAULT_TRADE_AUDIT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT)
    parser.add_argument("--symbol", default="MGC")
    parser.add_argument("--minimum-signal-days", type=int, default=60)
    args = parser.parse_args()

    core = _load_mnq_core()
    _patch_core_for_mgc(core)

    bars = core._load_feature_bars(args.input)
    bars_by_date = _active_bars_by_date(core._bars_by_date(bars))
    signals_by_strategy = _generate_mgc_signals(core, bars_by_date, symbol=args.symbol)
    risk_profiles = _risk_profiles(core)

    sweep_rows = []
    best_row: dict[str, object] | None = None
    best_trades = []
    for strategy_id, signals in signals_by_strategy.items():
        if len(signals) < args.minimum_signal_days:
            continue
        family = strategy_id.split(":", 1)[0]
        for risk in risk_profiles:
            outcomes = core._evaluate_signals(signals, bars_by_date, risk)
            row = core._sweep_row(strategy_id, family, outcomes, risk, bars_by_date)
            row.update(_cadence_metrics(outcomes, bars_by_date))
            sweep_rows.append(row)
            if _is_better_row(row, best_row):
                best_row = row
                best_trades = outcomes

    sweep_rows.sort(key=_ranking_key)
    core._write_csv(
        args.sweep_output,
        [*core.SWEEP_HEADER, *EXTRA_SWEEP_FIELDS],
        sweep_rows,
    )
    if best_row is not None:
        core._write_trade_audit(args.trade_audit_output, best_trades, best_row)
    _write_report(args.report_output, bars, sweep_rows, best_row)

    best_summary = "none"
    if best_row is not None:
        best_summary = (
            f"{best_row['strategy_id']} qty={best_row['quantity']} "
            f"target={best_row['target_net_usd']} stop={best_row['stop_net_usd']} "
            f"calendar_pass={float(best_row['pass_rate']):.3f} "
            f"calendar_fail={float(best_row['fail_rate']):.3f}"
        )
    print(
        f"wrote {len(sweep_rows)} MGC eval-pass initial rows to "
        f"{args.sweep_output}; best={best_summary}",
    )
    return 0


def _load_mnq_core() -> ModuleType:
    script_path = Path(__file__).with_name("run_mnq_eval_pass_wave_rider.py")
    spec = importlib.util.spec_from_file_location("mnq_eval_pass_core", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _patch_core_for_mgc(core: ModuleType) -> None:
    core.POINT_VALUE_USD = POINT_VALUE_USD
    core.TICK_SIZE_POINTS = TICK_SIZE_POINTS
    core.TICK_VALUE_USD = TICK_VALUE_USD
    core.COMMISSION_PER_SIDE_USD = COMMISSION_PER_SIDE_USD
    core.SLIPPAGE_TICKS_PER_CONTRACT = SLIPPAGE_TICKS_PER_CONTRACT
    core.SETUP_START = SETUP_START
    core.OPENING_RANGE_START = OPENING_RANGE_START
    core.OPENING_RANGE_END = OPENING_RANGE_END
    core.FLATTEN_TIME = FLATTEN_TIME


def _active_bars_by_date(
    bars_by_date: dict[date, list[Any]],
) -> dict[date, list[Any]]:
    return {
        trade_date: [
            row
            for row in rows
            if SETUP_START <= row.timestamp.time() <= FLATTEN_TIME
        ]
        for trade_date, rows in bars_by_date.items()
        if any(SETUP_START <= row.timestamp.time() <= FLATTEN_TIME for row in rows)
    }


def _generate_mgc_signals(
    core: ModuleType,
    bars_by_date: dict[date, list[Any]],
    *,
    symbol: str,
) -> dict[str, list[Any]]:
    signals_by_strategy: dict[str, list[Any]] = defaultdict(list)
    entry_ends = (time(10, 30), time(13, 30))
    for skip_friday in (False, True):
        for entry_end in entry_ends:
            _add_opening_range_breakouts(
                core,
                bars_by_date,
                signals_by_strategy,
                entry_end=entry_end,
                skip_friday=skip_friday,
                symbol=symbol,
            )
            _add_lookback_breakouts(
                core,
                bars_by_date,
                signals_by_strategy,
                entry_end=entry_end,
                skip_friday=skip_friday,
                symbol=symbol,
            )
            _add_vwap_pullbacks(
                core,
                bars_by_date,
                signals_by_strategy,
                entry_end=entry_end,
                skip_friday=skip_friday,
                symbol=symbol,
            )
    return dict(signals_by_strategy)


def _add_opening_range_breakouts(
    core: ModuleType,
    bars_by_date: dict[date, list[Any]],
    signals_by_strategy: dict[str, list[Any]],
    *,
    entry_end: time,
    skip_friday: bool,
    symbol: str,
) -> None:
    for min_or_width in (6.0, 10.0, 15.0):
        for buffer_points in (0.0, 0.5):
            for delta_threshold in (0.0, 75.0):
                for close_location_threshold in (0.55,):
                    strategy_id = (
                        "mgc_or_breakout:"
                        f"min_or{min_or_width:g}:buf{buffer_points:g}:"
                        f"delta{delta_threshold:g}:cl{close_location_threshold:g}:"
                        f"end{core._time_id(entry_end)}:skipfri{int(skip_friday)}"
                    )
                    for rows in bars_by_date.values():
                        signal = core._opening_range_breakout_signal(
                            rows,
                            strategy_id=strategy_id,
                            min_or_width=min_or_width,
                            buffer_points=buffer_points,
                            delta_threshold=delta_threshold,
                            close_location_threshold=close_location_threshold,
                            entry_end=entry_end,
                            skip_friday=skip_friday,
                            symbol=symbol,
                        )
                        if signal is not None:
                            signals_by_strategy[strategy_id].append(signal)


def _add_lookback_breakouts(
    core: ModuleType,
    bars_by_date: dict[date, list[Any]],
    signals_by_strategy: dict[str, list[Any]],
    *,
    entry_end: time,
    skip_friday: bool,
    symbol: str,
) -> None:
    for lookback_bars in (30, 60):
        for buffer_points in (0.0, 0.5):
            for delta_threshold in (0.0, 75.0, 125.0):
                for close_location_threshold in (0.55,):
                    strategy_id = (
                        "mgc_lookback_breakout:"
                        f"lb{lookback_bars}:buf{buffer_points:g}:"
                        f"delta{delta_threshold:g}:cl{close_location_threshold:g}:"
                        f"end{core._time_id(entry_end)}:skipfri{int(skip_friday)}"
                    )
                    for rows in bars_by_date.values():
                        signal = core._lookback_breakout_signal(
                            rows,
                            strategy_id=strategy_id,
                            lookback_bars=lookback_bars,
                            buffer_points=buffer_points,
                            delta_threshold=delta_threshold,
                            close_location_threshold=close_location_threshold,
                            entry_end=entry_end,
                            skip_friday=skip_friday,
                            symbol=symbol,
                        )
                        if signal is not None:
                            signals_by_strategy[strategy_id].append(signal)


def _add_vwap_pullbacks(
    core: ModuleType,
    bars_by_date: dict[date, list[Any]],
    signals_by_strategy: dict[str, list[Any]],
    *,
    entry_end: time,
    skip_friday: bool,
    symbol: str,
) -> None:
    for stretch_points in (10.0, 15.0, 25.0):
        for pullback_points in (2.0, 5.0):
            for delta_threshold in (0.0, 75.0):
                for close_location_threshold in (0.55,):
                    strategy_id = (
                        "mgc_vwap_pullback:"
                        f"stretch{stretch_points:g}:pb{pullback_points:g}:"
                        f"delta{delta_threshold:g}:cl{close_location_threshold:g}:"
                        f"end{core._time_id(entry_end)}:skipfri{int(skip_friday)}"
                    )
                    for rows in bars_by_date.values():
                        signal = core._vwap_pullback_signal(
                            rows,
                            strategy_id=strategy_id,
                            stretch_points=stretch_points,
                            pullback_points=pullback_points,
                            delta_threshold=delta_threshold,
                            close_location_threshold=close_location_threshold,
                            entry_end=entry_end,
                            skip_friday=skip_friday,
                            symbol=symbol,
                        )
                        if signal is not None:
                            signals_by_strategy[strategy_id].append(signal)


def _risk_profiles(core: ModuleType) -> list[Any]:
    profiles = []
    for quantity in (3, 4, 5, 6, 8, 10, 12):
        round_turn_cost = quantity * (
            2.0 * COMMISSION_PER_SIDE_USD + SLIPPAGE_TICKS_PER_CONTRACT * TICK_VALUE_USD
        )
        for target_usd in (625.0, 650.0, 700.0):
            target_points = core._round_up_to_tick(
                (target_usd + round_turn_cost) / (quantity * POINT_VALUE_USD),
            )
            actual_target_usd = target_points * quantity * POINT_VALUE_USD - round_turn_cost
            for stop_usd in (350.0, 500.0, 650.0, 800.0):
                if stop_usd <= round_turn_cost:
                    continue
                stop_points = core._round_down_to_tick(
                    (stop_usd - round_turn_cost) / (quantity * POINT_VALUE_USD),
                )
                if stop_points <= 0.0:
                    continue
                actual_stop_usd = stop_points * quantity * POINT_VALUE_USD + round_turn_cost
                profiles.append(
                    core.RiskProfile(
                        quantity=quantity,
                        target_net_usd=actual_target_usd,
                        stop_net_usd=actual_stop_usd,
                        target_points=target_points,
                        stop_points=stop_points,
                        round_turn_cost_usd=round_turn_cost,
                    ),
                )
    return profiles


def _cadence_metrics(
    outcomes: list[Any],
    bars_by_date: dict[date, list[Any]],
) -> dict[str, object]:
    signal_dates = sorted({outcome.entry_time.date() for outcome in outcomes})
    all_dates = sorted(bars_by_date)
    gaps = [
        (right - left).days
        for left, right in zip(signal_dates, signal_dates[1:], strict=False)
    ]
    return {
        "signal_frequency_per_trade_day": _format_number(
            len(signal_dates) / len(all_dates) if all_dates else 0.0,
        ),
        "average_calendar_gap_between_signals": _format_number(
            statistics.mean(gaps) if gaps else 0.0,
        ),
        "median_calendar_gap_between_signals": _format_number(
            statistics.median(gaps) if gaps else 0.0,
        ),
    }


def _ranking_key(row: dict[str, object]) -> tuple[float, float, float, float, float, float]:
    sample_penalty = 0.0 if int(row["evaluated_trades"]) >= 80 else 1.0
    latest_year_penalty = (
        0.0
        if float(row["latest_year_net_usd"]) > 0.0 and int(row["latest_year_trades"]) >= 20
        else 1.0
    )
    return (
        sample_penalty,
        latest_year_penalty,
        float(row["fail_rate"]),
        -float(row["pass_rate"]),
        float(row["median_calendar_gap_between_signals"]) or 999.0,
        -float(row["net_usd"]),
    )


def _is_better_row(
    row: dict[str, object],
    current_best: dict[str, object] | None,
) -> bool:
    if current_best is None:
        return True
    return _ranking_key(row) < _ranking_key(current_best)


def _write_report(
    report_output: str,
    bars: list[Any],
    sweep_rows: list[dict[str, object]],
    best_row: dict[str, object] | None,
) -> None:
    accepted = [
        row for row in sweep_rows
        if int(row["evaluated_trades"]) >= 80
        and int(row["latest_year_trades"]) >= 20
        and float(row["latest_year_net_usd"]) > 0.0
        and float(row["net_usd"]) > 0.0
        and float(row["pass_rate"]) >= 0.45
        and float(row["fail_rate"]) <= 0.15
    ]
    top_rows = sweep_rows[:15]
    lines = [
        "# MGC Eval-Pass Initial Scan",
        "",
        "Status: exploratory MGC-only research. Not a candidate yet.",
        "",
        "## Objective",
        "",
        "- profit target: `$1250`",
        "- max loss: `-$1000`",
        "- consistency: largest winning day must be `<= 50%` of total profit",
        "- desired path: frequent enough to pass faster than the sparse MNQ lead",
        "",
        "## Source",
        "",
        f"- rows: `{len(bars)}`",
        f"- dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        f"- unique dates: `{len({bar.trade_date for bar in bars})}`",
        "- instrument: `MGC`, point value `$10`, tick value `$1`",
        "- cost model: `$0.50/side` commission plus `1` total slippage tick per contract",
        "- setup window: `08:20` to `13:30`, flatten by `16:30`",
        "",
        "## Search Space",
        "",
        "- entry families: COMEX opening-range breakout, lookback breakout, VWAP pullback continuation",
        "- opening range: `08:20` to `08:50`",
        "- quantities: `3`, `4`, `5`, `6`, `8`, `10`, `12` MGC",
        "- target net/trade: around `$625`, `$650`, `$700`, tick-rounded",
        "- stop net/trade: around `$350`, `$500`, `$650`, `$800`, tick-rounded",
        "",
        "## Result",
        "",
    ]
    if best_row is None:
        lines.append("No rows were generated.")
    else:
        lines.extend(
            [
                "Best exploratory row by calendar-start ranking:",
                "",
                "| Metric | Value |",
                "| --- | ---: |",
                f"| Strategy | `{best_row['strategy_id']}` |",
                f"| Quantity | `{best_row['quantity']}` |",
                f"| Target net/trade | `${best_row['target_net_usd']}` |",
                f"| Stop net/trade | `${best_row['stop_net_usd']}` |",
                f"| Trades | `{best_row['evaluated_trades']}` |",
                f"| Full-sample net | `${best_row['net_usd']}` |",
                f"| Latest-year trades | `{best_row['latest_year_trades']}` |",
                f"| Latest-year net | `${best_row['latest_year_net_usd']}` |",
                f"| Worst quarter net | `${best_row['worst_quarter_net_usd']}` |",
                f"| Calendar-start pass rate | `{float(best_row['pass_rate']) * 100:.1f}%` |",
                f"| Calendar-start fail rate | `{float(best_row['fail_rate']) * 100:.1f}%` |",
                f"| Signal-start pass rate | `{float(best_row['signal_start_pass_rate']) * 100:.1f}%` |",
                f"| Signal-start fail rate | `{float(best_row['signal_start_fail_rate']) * 100:.1f}%` |",
                f"| Median signal gap | `{best_row['median_calendar_gap_between_signals']}` calendar days |",
                "",
            ],
        )
        if accepted:
            lines.append(f"Rows meeting the first-pass acceptance lens: `{len(accepted)}`.")
        else:
            lines.append(
                "No row met the first-pass acceptance lens of at least `80` trades, "
                "positive full sample/latest year, calendar pass rate `>=45%`, and "
                "calendar fail rate `<=15%`.",
            )
    lines.extend(
        [
            "",
            "## Top Rows",
            "",
            "| Rank | Family | Qty | Target | Stop | Trades | Latest Net | Calendar Pass | Calendar Fail | Signal Pass | Median Gap | Strategy |",
            "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ],
    )
    for rank, row in enumerate(top_rows, start=1):
        lines.append(
            "| "
            f"{rank} | {row['family']} | {row['quantity']} | "
            f"{row['target_net_usd']} | {row['stop_net_usd']} | "
            f"{row['evaluated_trades']} | {row['latest_year_net_usd']} | "
            f"{float(row['pass_rate']) * 100:.1f}% | "
            f"{float(row['fail_rate']) * 100:.1f}% | "
            f"{float(row['signal_start_pass_rate']) * 100:.1f}% | "
            f"{row['median_calendar_gap_between_signals']} | "
            f"`{row['strategy_id']}` |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This first pass only tests whether MGC has enough continuation behavior to justify "
            "deeper work. It is not slippage-stressed, not walk-forwarded, and not ready for "
            "Sierra replay.",
            "",
        ],
    )
    Path(report_output).write_text("\n".join(lines), encoding="utf-8")


def _format_number(value: float) -> str:
    formatted = f"{value:.8f}".rstrip("0").rstrip(".")
    return formatted if formatted else "0"


if __name__ == "__main__":
    raise SystemExit(main())
