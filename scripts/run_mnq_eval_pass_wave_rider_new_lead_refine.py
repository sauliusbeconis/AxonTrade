#!/usr/bin/env python3
"""Refine the current best MNQ eval-pass wave-rider lead."""

from __future__ import annotations

import argparse
import csv
import importlib.util
import math
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import time
from pathlib import Path


DEFAULT_OUTPUT = "reports/mnq-eval-pass-wave-rider-new-lead-refine.csv"
DEFAULT_REPORT = "reports/mnq-eval-pass-wave-rider-new-lead-refine.md"
DEFAULT_TRAIN_DATE_COUNTS = "120,180,240"
DEFAULT_HOLDOUT_DATE_COUNTS = "40,40,60"


@dataclass(frozen=True)
class RefinedResult:
    row: dict[str, object]
    outcomes: list[object]
    risk: object


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refine the new best MNQ eval-pass wave-rider lead.",
    )
    parser.add_argument("input", nargs="?", help="MNQ Sierra orderflow export path.")
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--report-output", default=DEFAULT_REPORT)
    parser.add_argument("--symbol", default="MNQU26-CME")
    parser.add_argument("--train-date-counts", default=DEFAULT_TRAIN_DATE_COUNTS)
    parser.add_argument("--holdout-date-counts", default=DEFAULT_HOLDOUT_DATE_COUNTS)
    args = parser.parse_args()

    wave = _load_module("run_mnq_eval_pass_wave_rider.py", "mnq_eval_pass_wave_rider")
    deep = _load_module(
        "run_mnq_eval_pass_wave_rider_deep_search.py",
        "mnq_eval_pass_wave_rider_deep_search",
    )
    input_path = args.input or wave.DEFAULT_INPUT
    bars = wave._load_feature_bars(input_path)
    bars_by_date = wave._bars_by_date(bars)
    rows_by_index = wave._rows_by_global_index(bars_by_date)
    strategy_id = (
        "lookback_breakout_deep:lb40:buf2.5:delta600:cl0.5:"
        "start1000:end1230:skipfri0:filterabs1000"
    )
    signals = _new_lead_signals(
        wave,
        deep,
        bars_by_date,
        rows_by_index=rows_by_index,
        strategy_id=strategy_id,
        symbol=args.symbol,
    )
    results = []
    for risk in _dense_risk_grid(wave):
        outcomes = wave._evaluate_signals(signals, bars_by_date, risk)
        row = wave._sweep_row(
            strategy_id,
            "lookback_breakout_deep_refine",
            outcomes,
            risk,
            bars_by_date,
        )
        results.append(RefinedResult(row, outcomes, risk))
    results.sort(key=_refine_ranking_key)
    configs = deep._parse_configs(args.train_date_counts, args.holdout_date_counts)
    unique_results = _unique_results(results)
    benchmark_rows = deep._benchmark_rows(
        wave,
        [
            deep.CandidateResult(result.row, result.outcomes)
            for result in unique_results[:12]
        ],
        sorted(bars_by_date),
        configs,
    )
    stress_rows = _slippage_stress_rows(
        wave,
        bars_by_date,
        signals,
        unique_results[:8],
        strategy_id=strategy_id,
    )
    _write_csv(args.output, [result.row for result in results])
    _write_report(
        args.report_output,
        bars=bars,
        signals=signals,
        results=unique_results,
        stress_rows=stress_rows,
        benchmark_rows=benchmark_rows,
        configs=configs,
    )
    best = unique_results[0].row if unique_results else None
    best_summary = "none"
    if best is not None:
        best_summary = (
            f"qty={best['quantity']} target={best['target_net_usd']} "
            f"stop={best['stop_net_usd']} "
            f"pass={float(best['signal_start_pass_rate']):.3f} "
            f"two_day={float(best['signal_start_two_trade_day_pass_rate']):.3f} "
            f"fail={float(best['signal_start_fail_rate']):.3f}"
        )
    print(
        f"wrote {len(results)} MNQ new-lead refinement rows to {args.output}; "
        f"best={best_summary}",
    )
    return 0


def _load_module(filename: str, module_name: str):
    module_path = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _new_lead_signals(
    wave,
    deep,
    bars_by_date: dict[object, list[object]],
    *,
    rows_by_index: dict[int, int],
    strategy_id: str,
    symbol: str,
) -> list[object]:
    base_strategy_id = strategy_id.rsplit(":filter", 1)[0]
    base_signals = deep._lookback_breakout_signals(
        wave,
        bars_by_date,
        strategy_id=base_strategy_id,
        lookback_bars=40,
        buffer_points=2.5,
        delta_threshold=600.0,
        close_location_threshold=0.5,
        entry_start=time(10, 0),
        entry_end=time(12, 30),
        skip_friday=False,
        symbol=symbol,
    )
    filtered = []
    for signal in base_signals:
        features = wave._signal_features(
            signal,
            bars_by_date=bars_by_date,
            rows_by_index=rows_by_index,
            lookback_bars=40,
        )
        if features.abs_delta <= 1000.0:
            filtered.append(
                wave.Signal(
                    strategy_id=strategy_id,
                    direction=signal.direction,
                    bar=signal.bar,
                    notes=f"{signal.notes}; deep filter abs1000",
                ),
            )
    return filtered


def _dense_risk_grid(wave) -> list[object]:
    risks = []
    for quantity in (4, 5, 6, 8, 10, 12, 14, 15, 16):
        for target_usd in (625.0, 650.0, 675.0, 700.0, 725.0, 750.0, 775.0, 800.0):
            for stop_usd in (500.0, 600.0, 650.0, 700.0, 750.0, 800.0, 850.0, 900.0):
                risk = _make_risk_profile(wave, quantity, target_usd, stop_usd)
                if risk.stop_net_usd <= 950.0:
                    risks.append(risk)
    return risks


def _make_risk_profile(
    wave,
    quantity: int,
    target_usd: float,
    stop_usd: float,
) -> object:
    round_turn_cost = quantity * (
        2.0 * wave.COMMISSION_PER_SIDE_USD
        + wave.SLIPPAGE_TICKS_PER_CONTRACT * wave.TICK_VALUE_USD
    )
    target_points = wave._round_up_to_tick(
        (target_usd + round_turn_cost) / (quantity * wave.POINT_VALUE_USD),
    )
    actual_target_usd = target_points * quantity * wave.POINT_VALUE_USD - round_turn_cost
    stop_points = wave._round_down_to_tick(
        (stop_usd - round_turn_cost) / (quantity * wave.POINT_VALUE_USD),
    )
    if stop_points <= 0.0:
        raise ValueError("stop specification produced non-positive stop points")
    actual_stop_usd = stop_points * quantity * wave.POINT_VALUE_USD + round_turn_cost
    return wave.RiskProfile(
        quantity=quantity,
        target_net_usd=actual_target_usd,
        stop_net_usd=actual_stop_usd,
        target_points=target_points,
        stop_points=stop_points,
        round_turn_cost_usd=round_turn_cost,
    )


def _risk_with_slippage(wave, base_risk: object, slippage_ticks: float) -> object:
    round_turn_cost = base_risk.quantity * (
        2.0 * wave.COMMISSION_PER_SIDE_USD
        + slippage_ticks * wave.TICK_VALUE_USD
    )
    target_net = (
        base_risk.target_points * base_risk.quantity * wave.POINT_VALUE_USD
        - round_turn_cost
    )
    stop_net = (
        base_risk.stop_points * base_risk.quantity * wave.POINT_VALUE_USD
        + round_turn_cost
    )
    return wave.RiskProfile(
        quantity=base_risk.quantity,
        target_net_usd=target_net,
        stop_net_usd=stop_net,
        target_points=base_risk.target_points,
        stop_points=base_risk.stop_points,
        round_turn_cost_usd=round_turn_cost,
    )


def _refine_ranking_key(result: RefinedResult) -> tuple[float, ...]:
    row = result.row
    fail = float(row["signal_start_fail_rate"])
    two_day = float(row["signal_start_two_trade_day_pass_rate"])
    pass_rate = float(row["signal_start_pass_rate"])
    latest = float(row["latest_year_net_usd"])
    full_net = float(row["net_usd"])
    max_dd = abs(float(row["max_trade_sequence_drawdown_usd"]))
    stop = float(row["stop_net_usd"])
    target = float(row["target_net_usd"])
    latest_penalty = 0.0 if latest > 0.0 and int(row["latest_year_trades"]) >= 8 else 1.0
    near_max_loss_penalty = 0.0 if stop <= 800.0 else 1.0
    return (
        latest_penalty,
        near_max_loss_penalty,
        fail,
        -two_day,
        -pass_rate,
        -latest,
        -full_net,
        max_dd,
        stop,
        -target,
    )


def _unique_results(results: list[RefinedResult]) -> list[RefinedResult]:
    unique = []
    seen: set[tuple[object, ...]] = set()
    for result in results:
        row = result.row
        key = (
            row["quantity"],
            row["target_net_usd"],
            row["stop_net_usd"],
            row["target_points"],
            row["stop_points"],
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(result)
    return unique


def _slippage_stress_rows(
    wave,
    bars_by_date: dict[object, list[object]],
    signals: list[object],
    results: list[RefinedResult],
    *,
    strategy_id: str,
) -> list[dict[str, object]]:
    rows = []
    for result in results:
        for slippage_ticks in (1.0, 2.0, 3.0, 4.0, 5.0, 6.0):
            risk = _risk_with_slippage(wave, result.risk, slippage_ticks)
            outcomes = wave._evaluate_signals(signals, bars_by_date, risk)
            row = wave._sweep_row(
                strategy_id,
                "lookback_breakout_deep_refine",
                outcomes,
                risk,
                bars_by_date,
            )
            row["slippage_ticks"] = _format_number(slippage_ticks)
            rows.append(row)
    return rows


def _write_csv(path: str, rows: list[dict[str, object]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_report(
    path: str,
    *,
    bars: list[object],
    signals: list[object],
    results: list[RefinedResult],
    stress_rows: list[dict[str, object]],
    benchmark_rows: list[dict[str, object]],
    configs: list[tuple[int, int]],
) -> None:
    lines = [
        "# MNQ Eval-Pass Wave Rider New Lead Refinement",
        "",
        "Status: offline risk-grid refinement for the current best deep-search lead.",
        "",
        "## Source",
        "",
        f"- rows: `{len(bars)}`",
        f"- dates: `{bars[0].trade_date.isoformat()}` through `{bars[-1].trade_date.isoformat()}`",
        f"- unique dates: `{len({bar.trade_date for bar in bars})}`",
        f"- filtered signal days: `{len(signals)}`",
        "",
        "Risk rows with planned stops above `$800` are treated as aggressive because "
        "the eval max loss is only `-$1000`. They can still appear in fastest-row "
        "tables, but they are not allowed to outrank cleaner practical rows.",
        "",
        "## Frozen Signal",
        "",
        "`lookback_breakout_deep:lb40:buf2.5:delta600:cl0.5:start1000:end1230:skipfri0:filterabs1000`",
        "",
        "- 40-bar lookback breakout continuation",
        "- 2.5-point breakout buffer",
        "- delta threshold `600`",
        "- close location `>= 0.50` long or `<= 0.50` short",
        "- entries from `10:00` through `12:30`",
        "- no Friday exclusion",
        "- signal bar absolute delta capped at `1000`",
        "",
        "## Best Risk Rows",
        "",
        "| Rank | Qty | Target | Stop | Target Pts | Stop Pts | Net | Latest-Year "
        "Net | Max DD | Worst Q | Signal Pass | 2-Day | Fail |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | "
        "---: | ---: | ---: |",
    ]
    for rank, result in enumerate(results[:20], start=1):
        row = result.row
        lines.append(
            "| "
            f"{rank} | {row['quantity']} | {row['target_net_usd']} | "
            f"{row['stop_net_usd']} | {row['target_points']} | "
            f"{row['stop_points']} | {row['net_usd']} | "
            f"{row['latest_year_net_usd']} | "
            f"{row['max_trade_sequence_drawdown_usd']} | "
            f"{row['worst_quarter_net_usd']} | "
            f"{float(row['signal_start_pass_rate']) * 100:.1f}% | "
            f"{float(row['signal_start_two_trade_day_pass_rate']) * 100:.1f}% | "
            f"{float(row['signal_start_fail_rate']) * 100:.1f}% |"
        )

    if results:
        _append_lead_diagnostics(lines, results[0])

    fastest = sorted(
        results,
        key=lambda result: (
            -float(result.row["signal_start_two_trade_day_pass_rate"]),
            float(result.row["signal_start_fail_rate"]),
            -float(result.row["signal_start_pass_rate"]),
        ),
    )
    lines.extend(
        [
            "",
            "## Fastest Two-Day Risk Rows",
            "",
            "| Rank | Qty | Target | Stop | Net | Latest-Year Net | Signal Pass | "
            "2-Day | Fail |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    for rank, result in enumerate(fastest[:12], start=1):
        row = result.row
        lines.append(
            "| "
            f"{rank} | {row['quantity']} | {row['target_net_usd']} | "
            f"{row['stop_net_usd']} | {row['net_usd']} | "
            f"{row['latest_year_net_usd']} | "
            f"{float(row['signal_start_pass_rate']) * 100:.1f}% | "
            f"{float(row['signal_start_two_trade_day_pass_rate']) * 100:.1f}% | "
            f"{float(row['signal_start_fail_rate']) * 100:.1f}% |"
        )

    lines.extend(
        [
            "",
            "## Slippage Stress",
            "",
            "Stress keeps the same target/stop point distances and changes only "
            "transaction cost from `1` to `6` total slippage ticks per contract.",
            "",
            "| Candidate | Slip Ticks | Target | Stop | Net | Latest-Year Net | "
            "Signal Pass | 2-Day | Fail |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ],
    )
    for index, row in enumerate(stress_rows[:48], start=1):
        candidate_name = f"#{math.ceil(index / 6)}"
        lines.append(
            "| "
            f"{candidate_name} `{row['quantity']}` | {row['slippage_ticks']} | "
            f"{row['target_net_usd']} | {row['stop_net_usd']} | "
            f"{row['net_usd']} | {row['latest_year_net_usd']} | "
            f"{float(row['signal_start_pass_rate']) * 100:.1f}% | "
            f"{float(row['signal_start_two_trade_day_pass_rate']) * 100:.1f}% | "
            f"{float(row['signal_start_fail_rate']) * 100:.1f}% |"
        )

    lines.extend(
        [
            "",
            "## Fixed-Candidate Holdout Benchmarks",
            "",
            "Rows freeze the selected risk geometry and evaluate the same rolling "
            f"holdout windows: `{', '.join(f'{a}x{b}' for a, b in configs)}`.",
            "",
            "| Candidate | Config | Trades | Net | Avg | PF | Max DD | Pos Windows | "
            "Neg Windows | Signal Pass | 2-Day | Fail |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | "
            "---: | ---: |",
        ],
    )
    for index, row in enumerate(benchmark_rows[:36], start=1):
        candidate_name = f"#{math.ceil(index / len(configs))}"
        lines.append(
            "| "
            f"{candidate_name} `{row['quantity']}/{row['target_net_usd']}/"
            f"{row['stop_net_usd']}` | {row['config']} | {row['trades']} | "
            f"{row['net_usd']} | {row['average_trade_usd']} | "
            f"{row['profit_factor']} | {row['max_drawdown_usd']} | "
            f"{row['positive_windows']} | {row['negative_windows']} | "
            f"{float(row['signal_start_pass_rate']) * 100:.1f}% | "
            f"{float(row['signal_start_two_trade_day_pass_rate']) * 100:.1f}% | "
            f"{float(row['signal_start_fail_rate']) * 100:.1f}% |"
        )

    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "This refinement holds the signal fixed and searches only risk geometry. "
            "That is deliberately stricter than changing signal and risk together.",
            "",
            "The main tradeoff is not profitability; it is eval survivability. Higher "
            "quantity improves two-day pass odds but pushes a single stopped trade "
            "closer to the `-$1000` max-loss boundary.",
            "",
            "The current practical lead is the highest-ranked row with a planned stop "
            "at or below `$800`, not the absolute largest target/stop combination.",
            "",
        ],
    )
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def _append_lead_diagnostics(lines: list[str], result: RefinedResult) -> None:
    row = result.row
    outcomes = result.outcomes
    lines.extend(
        [
            "",
            "## Practical Lead Diagnostics",
            "",
            f"Lead risk geometry: `{row['quantity']} MNQ`, "
            f"target `${row['target_net_usd']}`, stop `${row['stop_net_usd']}`.",
            "",
        ],
    )
    _append_breakdown(lines, "Year", outcomes, lambda outcome: outcome.entry_time.year)
    _append_breakdown(
        lines,
        "Quarter",
        outcomes,
        lambda outcome: (
            outcome.entry_time.year,
            (outcome.entry_time.month - 1) // 3 + 1,
        ),
    )
    _append_breakdown(lines, "Weekday", outcomes, lambda outcome: outcome.entry_time.strftime("%a"))
    _append_breakdown(lines, "Direction", outcomes, lambda outcome: outcome.direction)
    losing_trades = [outcome for outcome in outcomes if outcome.net_usd < 0.0]
    lines.extend(
        [
            "",
            f"Max consecutive losses: `{_max_consecutive_losses(outcomes)}`.",
            "",
            "Losing trades:",
            "",
            "| Date | Time | Direction | Net | Hold Min |",
            "| --- | --- | --- | ---: | ---: |",
        ],
    )
    for outcome in losing_trades:
        lines.append(
            "| "
            f"{outcome.entry_time.date().isoformat()} | "
            f"{outcome.entry_time.time().isoformat(timespec='minutes')} | "
            f"{outcome.direction} | {_format_number(outcome.net_usd)} | "
            f"{_format_number(outcome.holding_minutes)} |"
        )


def _append_breakdown(
    lines: list[str],
    title: str,
    outcomes: list[object],
    key_function,
) -> None:
    net_by_key: dict[object, float] = defaultdict(float)
    count_by_key: Counter[object] = Counter()
    wins_by_key: Counter[object] = Counter()
    losses_by_key: Counter[object] = Counter()
    for outcome in outcomes:
        key = key_function(outcome)
        net_by_key[key] += outcome.net_usd
        count_by_key[key] += 1
        wins_by_key[key] += outcome.net_usd > 0.0
        losses_by_key[key] += outcome.net_usd < 0.0
    lines.extend(
        [
            "",
            f"{title} breakdown:",
            "",
            "| Bucket | Trades | Net | Wins | Losses |",
            "| --- | ---: | ---: | ---: | ---: |",
        ],
    )
    for key in sorted(count_by_key):
        lines.append(
            "| "
            f"{key} | {count_by_key[key]} | {_format_number(net_by_key[key])} | "
            f"{wins_by_key[key]} | {losses_by_key[key]} |"
        )


def _max_consecutive_losses(outcomes: list[object]) -> int:
    max_losses = 0
    current = 0
    for outcome in sorted(outcomes, key=lambda item: item.entry_time):
        if outcome.net_usd < 0.0:
            current += 1
            max_losses = max(max_losses, current)
        else:
            current = 0
    return max_losses


def _format_number(value: float) -> str:
    if not math.isfinite(value):
        return "0"
    formatted = f"{value:.8f}".rstrip("0").rstrip(".")
    return formatted if formatted else "0"


if __name__ == "__main__":
    raise SystemExit(main())
