"""Markdown reporting for fixed scaled-scalp outcome robustness."""

from __future__ import annotations

import csv
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


_TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
)
_DEFAULT_TIME_WINDOWS = (
    ("10:00-10:45", (10, 0), (10, 45)),
    ("10:45-11:00", (10, 45), (11, 0)),
    ("11:00-11:30", (11, 0), (11, 30)),
    ("11:30-12:00", (11, 30), (12, 0)),
    ("12:00-13:00", (12, 0), (13, 0)),
)


class ScaledScalpRobustnessReportError(ValueError):
    """Raised when scaled-scalp robustness inputs are invalid."""


@dataclass(frozen=True)
class _Outcome:
    row: dict[str, Any]
    entry_timestamp: datetime
    trade_date: str
    direction: str
    exit_reason: str
    net_usd: float


def load_csv_rows(path: str | Path) -> list[dict[str, str]]:
    """Load CSV rows from disk."""

    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def load_holiday_calendar_dates(path: str | Path) -> list[str]:
    """Load holiday/early-close dates from a CSV calendar."""

    rows = load_csv_rows(path)
    dates = []
    for row in rows:
        raw_date = str(row.get("date", "")).strip()
        if not raw_date:
            raise ScaledScalpRobustnessReportError(
                "Holiday calendar rows must include a non-empty date field",
            )
        _parse_calendar_date(raw_date)
        dates.append(raw_date)
    return sorted(set(dates))


def load_holiday_calendar_metadata(path: str | Path) -> dict[str, str]:
    """Load optional source metadata from a holiday calendar CSV."""

    rows = load_csv_rows(path)
    metadata = {"source_url": "", "retrieved_date": ""}
    for row in rows:
        if not metadata["source_url"]:
            metadata["source_url"] = str(row.get("source_url", "")).strip()
        if not metadata["retrieved_date"]:
            metadata["retrieved_date"] = str(row.get("retrieved_date", "")).strip()
    return metadata


def write_scaled_scalp_robustness_report(
    path: str | Path,
    outcome_rows: Iterable[dict[str, Any]],
    sweep_rows: Iterable[dict[str, Any]],
    *,
    title: str,
    variant_label: str,
    outcome_source: str,
    sweep_source: str,
    main_summary_source: str | None = None,
    holiday_calendar_source: str | None = None,
    holiday_dates: Iterable[str] = (),
    holiday_source_url: str | None = None,
    holiday_retrieved_date: str | None = None,
    first_target_points: float,
    stop_points: float,
    runner_target_points: float,
) -> str:
    """Render and write a fixed scaled-scalp robustness report."""

    report = render_scaled_scalp_robustness_report(
        outcome_rows,
        sweep_rows,
        title=title,
        variant_label=variant_label,
        outcome_source=outcome_source,
        sweep_source=sweep_source,
        main_summary_source=main_summary_source,
        holiday_calendar_source=holiday_calendar_source,
        holiday_dates=holiday_dates,
        holiday_source_url=holiday_source_url,
        holiday_retrieved_date=holiday_retrieved_date,
        first_target_points=first_target_points,
        stop_points=stop_points,
        runner_target_points=runner_target_points,
    )
    report_path = Path(path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    return report


def render_scaled_scalp_robustness_report(
    outcome_rows: Iterable[dict[str, Any]],
    sweep_rows: Iterable[dict[str, Any]],
    *,
    title: str,
    variant_label: str,
    outcome_source: str,
    sweep_source: str,
    main_summary_source: str | None = None,
    holiday_calendar_source: str | None = None,
    holiday_dates: Iterable[str] = (),
    holiday_source_url: str | None = None,
    holiday_retrieved_date: str | None = None,
    first_target_points: float,
    stop_points: float,
    runner_target_points: float,
) -> str:
    """Render a deterministic robustness report for a fixed scaled-scalp row."""

    outcomes = _prepare_outcomes(outcome_rows)
    if not outcomes:
        raise ScaledScalpRobustnessReportError("outcome_rows must not be empty")
    holidays = set(holiday_dates)
    all_summary = _summarize_outcomes(outcomes)
    excluded_holiday_outcomes = [
        outcome for outcome in outcomes if outcome.trade_date not in holidays
    ]
    holiday_excluded_summary = _summarize_outcomes(excluded_holiday_outcomes)
    daily_rows = _daily_rows(outcomes)
    top_parameter_rows = _top_parameter_rows(sweep_rows)
    neighbor_rows = _nearby_parameter_rows(
        sweep_rows,
        first_target_points=first_target_points,
        stop_points=stop_points,
        runner_target_points=runner_target_points,
    )
    fixed_windows = _fixed_window_rows(outcomes)
    holiday_excluded_windows = _fixed_window_rows(excluded_holiday_outcomes)

    lines = [
        f"# {title}",
        "",
        "This report checks whether the current fixed Sierra overlay row is broad enough",
        "to keep collecting:",
        "",
        f"`{variant_label}`",
        "",
        "## Sources",
        "",
        "- Outcome CSV:",
        f"  `{outcome_source}`",
        "- Exit sweep:",
        f"  `{sweep_source}`",
    ]
    if main_summary_source:
        lines.extend(["- Main summary:", f"  `{main_summary_source}`"])
    if holiday_calendar_source:
        lines.extend(["- Holiday calendar:", f"  `{holiday_calendar_source}`"])
    if holiday_source_url:
        retrieved = (
            f", retrieved {holiday_retrieved_date}"
            if holiday_retrieved_date
            else ""
        )
        lines.extend(
            [
                f"- CME trading-hours reference{retrieved}:",
                f"  `{holiday_source_url}`",
            ],
        )

    lines.extend(
        [
            "",
            "## Fixed Row Result",
            "",
            _summary_table(all_summary),
            "",
            "Direction split:",
            "",
            _direction_table(outcomes),
            "",
            "## Day Stability",
            "",
            _daily_table(daily_rows),
            "",
            (
                f"The equity curve was down `{_format_number(_min_cumulative_net(daily_rows))}` "
                f"at its weakest point and finished at `{_format_number(all_summary['net_usd'])}`."
            ),
            "",
            "## Holiday Handling",
            "",
            _holiday_text(holidays),
            "",
            _holiday_scope_table(all_summary, holiday_excluded_summary, holidays),
            "",
            "Holiday/early-close dates are calendar-driven for later acceptance tests.",
            "",
            "## Time Windows",
            "",
            _time_window_table(excluded_holiday_outcomes),
            "",
            (
                "The time-window table is diagnostic only. Do not promote a thin "
                "time slice as a rule without a larger sample."
            ),
            "",
            "## Parameter Shelf",
            "",
            "Top all-direction `initial` rows:",
            "",
            _parameter_table(top_parameter_rows),
            "",
            "Nearby cells around the current row:",
            "",
            _parameter_table(neighbor_rows),
            "",
            (
                "A narrow profitable neighborhood is a parameter-fit warning. "
                "A broader plateau would be stronger evidence."
            ),
            "",
            "## Fixed Row Rolling Windows",
            "",
            (
                "This check holds the current fixed row constant and rolls dates "
                "using `4` train dates, `2` holdout dates, and a `2` date step."
            ),
            "",
            _window_table(fixed_windows),
            "",
            _window_total_text("Fixed-row rolling holdout total", fixed_windows),
            "",
            "Excluding holiday dates:",
            "",
            _window_table(holiday_excluded_windows),
            "",
            _window_total_text(
                "Holiday-excluded fixed-row rolling holdout total",
                holiday_excluded_windows,
            ),
            "",
            (
                "This separates fixed-row behavior from train-window optimizer "
                "selection, but it still does not prove stability."
            ),
            "",
            "## Risk Gate Checks",
            "",
            _risk_gate_table(outcomes),
            "",
            (
                "Profit gates are especially easy to overfit. Treat them as "
                "risk-control candidates, not as evidence of strategy quality."
            ),
            "",
            "## Conclusion",
            "",
            _conclusion_text(
                variant_label,
                all_summary=all_summary,
                holiday_excluded_summary=holiday_excluded_summary,
            ),
            "",
        ],
    )
    return "\n".join(lines)


def _prepare_outcomes(rows: Iterable[dict[str, Any]]) -> list[_Outcome]:
    outcomes = []
    for row in rows:
        entry_timestamp = _parse_timestamp(str(row.get("entry_time", "")))
        outcomes.append(
            _Outcome(
                row=dict(row),
                entry_timestamp=entry_timestamp,
                trade_date=entry_timestamp.date().isoformat(),
                direction=str(row.get("direction", "")),
                exit_reason=str(row.get("exit_reason", "")),
                net_usd=_to_float(row.get("net_usd"), "net_usd"),
            ),
        )
    return sorted(outcomes, key=lambda outcome: outcome.entry_timestamp)


def _parse_timestamp(value: str) -> datetime:
    normalized = " ".join(value.split())
    for fmt in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(normalized, fmt)
        except ValueError:
            continue
    raise ScaledScalpRobustnessReportError(f"Invalid timestamp: {value!r}")


def _parse_calendar_date(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ScaledScalpRobustnessReportError(
            f"Invalid holiday calendar date: {value!r}",
        ) from exc


def _to_float(value: Any, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ScaledScalpRobustnessReportError(
            f"Invalid {field_name}: {value!r}",
        ) from exc


def _summarize_outcomes(outcomes: list[_Outcome]) -> dict[str, float | int]:
    exit_counts = Counter(outcome.exit_reason for outcome in outcomes)
    return {
        "trades": len(outcomes),
        "net_usd": sum(outcome.net_usd for outcome in outcomes),
        "average_net_usd": (
            sum(outcome.net_usd for outcome in outcomes) / len(outcomes)
            if outcomes
            else 0.0
        ),
        "runner_target_hits": exit_counts["runner_target_hit"],
        "full_stops": exit_counts["full_stop_hit"],
        "runner_initial_stop_exits": exit_counts["runner_initial_stop_hit"],
        "end_or_no_following_exits": (
            exit_counts["end_of_session"] + exit_counts["no_following_bar"]
        ),
        "long_net_usd": sum(
            outcome.net_usd for outcome in outcomes if outcome.direction == "long"
        ),
        "short_net_usd": sum(
            outcome.net_usd for outcome in outcomes if outcome.direction == "short"
        ),
    }


def _summary_table(summary: dict[str, float | int]) -> str:
    return "\n".join(
        [
            "| Metric | Value |",
            "| --- | ---: |",
            f"| Trades | {int(summary['trades'])} |",
            f"| Net USD | {_format_number(float(summary['net_usd']))} |",
            f"| Average Net USD | {_format_number(float(summary['average_net_usd']))} |",
            f"| Runner target hits | {int(summary['runner_target_hits'])} |",
            f"| Full stops | {int(summary['full_stops'])} |",
            f"| Runner initial-stop exits | {int(summary['runner_initial_stop_exits'])} |",
            f"| End/no-following exits | {int(summary['end_or_no_following_exits'])} |",
        ],
    )


def _conclusion_text(
    variant_label: str,
    *,
    all_summary: dict[str, float | int],
    holiday_excluded_summary: dict[str, float | int],
) -> str:
    trades = int(all_summary["trades"])
    net_usd = float(all_summary["net_usd"])
    holiday_excluded_net_usd = float(holiday_excluded_summary["net_usd"])
    if trades >= 100 and net_usd <= 0:
        return (
            f"Reject `{variant_label}` as a fixed row for the current sample. "
            "The sample is now large enough for the configured minimum trade "
            "count, and both the full result and robustness checks are negative."
        )
    if trades >= 100 and holiday_excluded_net_usd <= 0:
        return (
            f"Do not keep collecting `{variant_label}` without a changed "
            "hypothesis. The full sample is positive, but the holiday-adjusted "
            "result is not robust."
        )
    return (
        f"Keep collecting `{variant_label}`, but do not promote it to live "
        "routing until the same fixed-row checks hold on a larger sample."
    )


def _direction_table(outcomes: list[_Outcome]) -> str:
    lines = ["| Direction | Trades | Net USD |", "| --- | ---: | ---: |"]
    for direction in ("long", "short"):
        selected = [outcome for outcome in outcomes if outcome.direction == direction]
        lines.append(
            f"| {direction.title()} | {len(selected)} | "
            f"{_format_number(sum(outcome.net_usd for outcome in selected))} |",
        )
    return "\n".join(lines)


def _daily_rows(outcomes: list[_Outcome]) -> list[dict[str, Any]]:
    rows = []
    cumulative = 0.0
    for trade_date in sorted({outcome.trade_date for outcome in outcomes}):
        selected = [outcome for outcome in outcomes if outcome.trade_date == trade_date]
        net = sum(outcome.net_usd for outcome in selected)
        cumulative += net
        rows.append(
            {
                "trade_date": trade_date,
                "trades": len(selected),
                "net_usd": net,
                "cumulative_net_usd": cumulative,
            },
        )
    return rows


def _daily_table(rows: list[dict[str, Any]]) -> str:
    lines = [
        "| Date | Trades | Net USD | Cumulative Net USD |",
        "| --- | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['trade_date']} | {row['trades']} | "
            f"{_format_number(row['net_usd'])} | "
            f"{_format_number(row['cumulative_net_usd'])} |",
        )
    return "\n".join(lines)


def _min_cumulative_net(rows: list[dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    return min(float(row["cumulative_net_usd"]) for row in rows)


def _holiday_text(holiday_dates: set[str]) -> str:
    if not holiday_dates:
        return "No holiday dates were supplied."
    formatted = ", ".join(f"`{date}`" for date in sorted(holiday_dates))
    return (
        f"Supplied holiday/early-close dates: {formatted}. "
        "These dates are excluded in the holiday-adjusted diagnostics below."
    )


def _holiday_scope_table(
    all_summary: dict[str, float | int],
    holiday_excluded_summary: dict[str, float | int],
    holiday_dates: set[str],
) -> str:
    excluded_label = (
        "Exclude holidays"
        if holiday_dates
        else "No supplied holidays excluded"
    )
    lines = [
        "| Scope | Trades | Net USD | Long Net USD | Short Net USD |",
        "| --- | ---: | ---: | ---: | ---: |",
        (
            f"| All dates | {int(all_summary['trades'])} | "
            f"{_format_number(float(all_summary['net_usd']))} | "
            f"{_format_number(float(all_summary['long_net_usd']))} | "
            f"{_format_number(float(all_summary['short_net_usd']))} |"
        ),
        (
            f"| {excluded_label} | {int(holiday_excluded_summary['trades'])} | "
            f"{_format_number(float(holiday_excluded_summary['net_usd']))} | "
            f"{_format_number(float(holiday_excluded_summary['long_net_usd']))} | "
            f"{_format_number(float(holiday_excluded_summary['short_net_usd']))} |"
        ),
    ]
    return "\n".join(lines)


def _time_window_table(outcomes: list[_Outcome]) -> str:
    lines = ["| NY Time Window | Trades | Net USD |", "| --- | ---: | ---: |"]
    for label, start, end in _DEFAULT_TIME_WINDOWS:
        selected = [
            outcome
            for outcome in outcomes
            if start <= (outcome.entry_timestamp.hour, outcome.entry_timestamp.minute) < end
        ]
        lines.append(
            f"| {label} | {len(selected)} | "
            f"{_format_number(sum(outcome.net_usd for outcome in selected))} |",
        )
    return "\n".join(lines)


def _top_parameter_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    selected = [
        row for row in rows
        if str(row.get("direction_filter")) == "all"
        and str(row.get("runner_stop_mode")) == "initial"
    ]
    return sorted(
        selected,
        key=lambda row: _to_float(row.get("net_usd"), "net_usd"),
        reverse=True,
    )[:5]


def _nearby_parameter_rows(
    rows: Iterable[dict[str, Any]],
    *,
    first_target_points: float,
    stop_points: float,
    runner_target_points: float,
) -> list[dict[str, Any]]:
    selected = []
    for row in rows:
        if str(row.get("direction_filter")) != "all":
            continue
        if str(row.get("runner_stop_mode")) != "initial":
            continue
        first_target = _to_float(row.get("first_target_points"), "first_target_points")
        stop = _to_float(row.get("stop_points"), "stop_points")
        runner_target = _to_float(
            row.get("runner_target_points"),
            "runner_target_points",
        )
        if (
            abs(first_target - first_target_points) <= 1
            and abs(stop - stop_points) <= 2
            and abs(runner_target - runner_target_points) <= 2
        ):
            selected.append(row)
    return sorted(
        selected,
        key=lambda row: (
            _to_float(row.get("first_target_points"), "first_target_points"),
            _to_float(row.get("stop_points"), "stop_points"),
            _to_float(row.get("runner_target_points"), "runner_target_points"),
        ),
    )


def _parameter_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return (
            "| First Target | Stop | Runner Target | Net USD |\n"
            "| ---: | ---: | ---: | ---: |\n"
            "| none | none | none | 0 |"
        )
    lines = [
        "| First Target | Stop | Runner Target | Net USD |",
        "| ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {_format_number(_to_float(row.get('first_target_points'), 'first_target_points'))} "
            f"| {_format_number(_to_float(row.get('stop_points'), 'stop_points'))} "
            f"| {_format_number(_to_float(row.get('runner_target_points'), 'runner_target_points'))} "
            f"| {_format_number(_to_float(row.get('net_usd'), 'net_usd'))} |",
        )
    return "\n".join(lines)


def _fixed_window_rows(
    outcomes: list[_Outcome],
    *,
    train_date_count: int = 4,
    holdout_date_count: int = 2,
    step_date_count: int = 2,
) -> list[dict[str, Any]]:
    dates = sorted({outcome.trade_date for outcome in outcomes})
    max_start = len(dates) - train_date_count - holdout_date_count + 1
    if max_start <= 0:
        return []
    rows = []
    for start_index in range(0, max_start, step_date_count):
        train_dates = dates[start_index:start_index + train_date_count]
        holdout_dates = dates[
            start_index + train_date_count:
            start_index + train_date_count + holdout_date_count
        ]
        train = [
            outcome for outcome in outcomes
            if outcome.trade_date in set(train_dates)
        ]
        holdout = [
            outcome for outcome in outcomes
            if outcome.trade_date in set(holdout_dates)
        ]
        rows.append(
            {
                "window": start_index + 1,
                "train_dates": train_dates,
                "holdout_dates": holdout_dates,
                "train_net_usd": sum(outcome.net_usd for outcome in train),
                "holdout_net_usd": sum(outcome.net_usd for outcome in holdout),
                "holdout_trades": len(holdout),
            },
        )
    return rows


def _window_table(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return (
            "| Window | Train Dates | Train Net USD | Holdout Dates | Holdout Net USD |\n"
            "| ---: | --- | ---: | --- | ---: |\n"
            "| none | none | 0 | none | 0 |"
        )
    lines = [
        "| Window | Train Dates | Train Net USD | Holdout Dates | Holdout Net USD |",
        "| ---: | --- | ---: | --- | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['window']} | {_format_date_span(row['train_dates'])} | "
            f"{_format_number(row['train_net_usd'])} | "
            f"{_format_date_span(row['holdout_dates'])} | "
            f"{_format_number(row['holdout_net_usd'])} |",
        )
    return "\n".join(lines)


def _window_total_text(label: str, rows: list[dict[str, Any]]) -> str:
    trades = sum(int(row["holdout_trades"]) for row in rows)
    net_usd = sum(float(row["holdout_net_usd"]) for row in rows)
    return f"{label}: `{trades}` trades, `{_format_number(net_usd)}` net USD."


def _risk_gate_table(outcomes: list[_Outcome]) -> str:
    gates = [
        ("No gate", lambda day: day),
        ("First 3 signals/day", lambda day: day[:3]),
        (
            "Before 11:00",
            lambda day: [
                outcome for outcome in day
                if (outcome.entry_timestamp.hour, outcome.entry_timestamp.minute) < (11, 0)
            ],
        ),
        ("Stop after daily profit 500", _stop_after_daily_profit(500)),
        ("Stop after daily profit 1000", _stop_after_daily_profit(1000)),
        ("Stop after daily loss 1000", _stop_after_daily_loss(1000)),
    ]
    lines = ["| Gate | Trades | Net USD |", "| --- | ---: | ---: |"]
    for label, gate in gates:
        selected = []
        for trade_date in sorted({outcome.trade_date for outcome in outcomes}):
            day = [outcome for outcome in outcomes if outcome.trade_date == trade_date]
            selected.extend(gate(day))
        lines.append(
            f"| {label} | {len(selected)} | "
            f"{_format_number(sum(outcome.net_usd for outcome in selected))} |",
        )
    return "\n".join(lines)


def _stop_after_daily_profit(limit: float):
    def gate(day: list[_Outcome]) -> list[_Outcome]:
        selected = []
        pnl = 0.0
        for outcome in day:
            if pnl >= limit:
                break
            selected.append(outcome)
            pnl += outcome.net_usd
        return selected

    return gate


def _stop_after_daily_loss(limit: float):
    def gate(day: list[_Outcome]) -> list[_Outcome]:
        selected = []
        pnl = 0.0
        for outcome in day:
            if pnl <= -limit:
                break
            selected.append(outcome)
            pnl += outcome.net_usd
        return selected

    return gate


def _format_date_span(dates: list[str]) -> str:
    if not dates:
        return "none"
    if len(dates) == 1:
        return dates[0]
    return f"{dates[0]} to {dates[-1]}"


def _format_number(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.2f}".rstrip("0").rstrip(".")
