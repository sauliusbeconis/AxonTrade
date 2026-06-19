"""Markdown reporting for price-only baseline outcome runs."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from axontrade.research import summarize_trade_outcomes


def write_price_only_outcome_report(
    path: str | Path,
    signal_rows: Iterable[dict[str, Any]],
    outcome_rows: Iterable[dict[str, Any]],
    *,
    signals_source: str,
    outcomes_source: str,
) -> str:
    """Render and write a Markdown report for signal and outcome rows."""

    report = render_price_only_outcome_report(
        signal_rows,
        outcome_rows,
        signals_source=signals_source,
        outcomes_source=outcomes_source,
    )
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    return report


def render_price_only_outcome_report(
    signal_rows: Iterable[dict[str, Any]],
    outcome_rows: Iterable[dict[str, Any]],
    *,
    signals_source: str,
    outcomes_source: str,
) -> str:
    """Render a deterministic Markdown report from signal and outcome rows."""

    signals = list(signal_rows)
    outcomes = list(outcome_rows)
    signal_counts = Counter(str(row["event_type"]) for row in signals)
    rejection_counts = Counter(
        str(row["rejection_reason"])
        for row in signals
        if str(row["event_type"]) == "rejected_signal"
    )
    direction_counts = Counter(str(row["direction"]) for row in outcomes)
    exit_counts = Counter(str(row["exit_reason"]) for row in outcomes)
    summary = summarize_trade_outcomes(outcomes)

    lines = [
        "# Price-Only Outcome Report",
        "",
        "This report evaluates the current price-only VWAP/opening-range baseline.",
        "It is research-only and does not imply a tradable strategy.",
        "",
        "## Sources",
        "",
        f"- Signals: `{signals_source}`",
        f"- Outcomes: `{outcomes_source}`",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Total signal rows | {len(signals)} |",
        f"| Candidate signals | {signal_counts.get('candidate_signal', 0)} |",
        f"| Rejected signals | {signal_counts.get('rejected_signal', 0)} |",
        f"| Evaluated trades | {summary['total_trades']} |",
        f"| Target hits | {summary['wins']} |",
        f"| Stop/ambiguous losses | {summary['losses']} |",
        f"| Other exits | {summary['other_exits']} |",
        f"| Win rate | {_format_percent(summary['win_rate'])} |",
        f"| Gross USD | {_format_usd(summary['gross_usd'])} |",
        f"| Net USD | {_format_usd(summary['net_usd'])} |",
        f"| Average net USD | {_format_usd(summary['average_net_usd'])} |",
        "",
        "## Exit Reasons",
        "",
        _counter_table(exit_counts, "Exit reason"),
        "",
        "## Candidate Direction",
        "",
        _direction_table(outcomes, direction_counts),
        "",
        "## Rejected Signal Reasons",
        "",
        _counter_table(rejection_counts, "Rejection reason"),
        "",
        "## Interpretation",
        "",
        _interpretation(summary),
        "",
        "## Model Notes",
        "",
        "- Entry price is the signal price.",
        "- Stop and target are evaluated only on later same-day bars.",
        "- If stop and target are touched in the same later bar, stop is counted first.",
        "- Costs use the configured commission and slippage assumptions.",
        "",
    ]
    return "\n".join(lines)


def _counter_table(counter: Counter[str], label: str) -> str:
    if not counter:
        return f"| {label} | Count |\n| --- | ---: |\n| none | 0 |"

    rows = [f"| {label} | Count |", "| --- | ---: |"]
    for key, value in sorted(counter.items()):
        rows.append(f"| {key} | {value} |")
    return "\n".join(rows)


def _direction_table(outcomes: list[dict[str, Any]], direction_counts: Counter[str]) -> str:
    if not direction_counts:
        return "| Direction | Trades | Net USD |\n| --- | ---: | ---: |\n| none | 0 | 0.00 |"

    rows = ["| Direction | Trades | Net USD |", "| --- | ---: | ---: |"]
    for direction, count in sorted(direction_counts.items()):
        net_usd = sum(
            _to_float(row["net_usd"])
            for row in outcomes
            if str(row["direction"]) == direction
        )
        rows.append(f"| {direction} | {count} | {_format_usd(net_usd)} |")
    return "\n".join(rows)


def _interpretation(summary: dict[str, Any]) -> str:
    net_usd = _to_float(summary["net_usd"])
    total_trades = int(summary["total_trades"])
    if total_trades == 0:
        return "No candidate trades were generated in this sample."
    if net_usd > 0:
        return "This sample was positive after configured costs. Treat it as research evidence only."
    if net_usd < 0:
        return "This sample was negative after configured costs. Treat the baseline as a control, not a tradable strategy."
    return "This sample was flat after configured costs. More data is required."


def _format_usd(value: Any) -> str:
    return f"{_to_float(value):.2f}"


def _format_percent(value: Any) -> str:
    return f"{_to_float(value) * 100:.2f}%"


def _to_float(value: Any) -> float:
    return float(str(value))
