"""Validate the Sierra delta-impulse overlay against exported bars."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Any, Iterable


DELTA_IMPULSE_STRATEGY_ID = "delta_impulse_continue_10bar_2.5pt_50d"
_TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
)


class DeltaImpulseOverlayValidationError(ValueError):
    """Raised when delta-impulse overlay validation cannot be computed."""


@dataclass(frozen=True)
class DeltaImpulseRuleConfig:
    """Sierra delta-impulse overlay parameters."""

    strategy_id: str = DELTA_IMPULSE_STRATEGY_ID
    setup_start_time: str = "09:45:00"
    setup_end_time: str = "15:45:00"
    lookback_bars: int = 10
    minimum_price_move_points: float = 2.5
    minimum_delta_sum: float = 50.0
    minimum_spacing_seconds: int = 900
    max_signals_per_day: int = 6
    stop_points: float = 10.0
    first_target_points: float = 5.0
    runner_target_points: float = 8.0
    runner_stop_mode: str = "initial"
    trade_mode: str = "replay"
    confidence: float = 0.6


@dataclass(frozen=True)
class DeltaImpulseOverlayComparison:
    """Comparison between Python-reproduced candidates and Sierra log rows."""

    expected_rows: list[dict[str, Any]]
    actual_rows: list[dict[str, Any]]
    matched_rows: list[dict[str, Any]]
    missing_rows: list[dict[str, Any]]
    unexpected_rows: list[dict[str, Any]]
    mismatched_rows: list[dict[str, Any]]

    @property
    def passed(self) -> bool:
        return (
            not self.missing_rows
            and not self.unexpected_rows
            and not self.mismatched_rows
        )


@dataclass(frozen=True)
class _DeltaImpulseBar:
    timestamp: str
    parsed_timestamp: datetime
    symbol: str
    chart_number: int
    bar_index: int
    high: float
    low: float
    close: float
    delta: float


def generate_delta_impulse_overlay_candidates(
    bars: Iterable[dict[str, Any]],
    *,
    config: DeltaImpulseRuleConfig | None = None,
) -> list[dict[str, Any]]:
    """Reproduce accepted Sierra overlay candidate rows from exported bars."""

    rule_config = config or DeltaImpulseRuleConfig()
    _validate_rule_config(rule_config)
    normalized_bars = sorted(
        [_normalize_bar(row) for row in bars],
        key=lambda bar: (bar.parsed_timestamp, bar.bar_index),
    )
    setup_start = _parse_time(rule_config.setup_start_time, "setup_start_time")
    setup_end = _parse_time(rule_config.setup_end_time, "setup_end_time")

    rows: list[dict[str, Any]] = []
    signal_date: str | None = None
    signal_count = 0
    last_signal_time_seconds: int | None = None
    for position, bar in enumerate(normalized_bars):
        current_date = bar.parsed_timestamp.date().isoformat()
        current_time = bar.parsed_timestamp.time()
        if current_date != signal_date:
            signal_date = current_date
            signal_count = 0
            last_signal_time_seconds = None

        evaluation = _evaluate_bar(
            normalized_bars,
            position,
            rule_config=rule_config,
            setup_start=setup_start,
            setup_end=setup_end,
        )
        if evaluation["event_type"] != "candidate_signal":
            continue

        current_seconds = _seconds_since_midnight(current_time)
        if rule_config.max_signals_per_day > 0 and signal_count >= rule_config.max_signals_per_day:
            continue
        if (
            last_signal_time_seconds is not None
            and rule_config.minimum_spacing_seconds > 0
            and 0 <= current_seconds - last_signal_time_seconds < rule_config.minimum_spacing_seconds
        ):
            continue

        signal_count += 1
        last_signal_time_seconds = current_seconds
        rows.append(evaluation)

    return rows


def compare_delta_impulse_overlay_log(
    bars: Iterable[dict[str, Any]],
    signal_rows: Iterable[dict[str, Any]],
    *,
    config: DeltaImpulseRuleConfig | None = None,
    price_tolerance: float = 0.000001,
) -> DeltaImpulseOverlayComparison:
    """Compare Python-reproduced candidates to Sierra's candidate log rows."""

    if price_tolerance < 0:
        raise DeltaImpulseOverlayValidationError("price_tolerance must be nonnegative")

    rule_config = config or DeltaImpulseRuleConfig()
    expected_rows = generate_delta_impulse_overlay_candidates(bars, config=rule_config)
    actual_rows = [
        dict(row)
        for row in signal_rows
        if str(row.get("event_type", "")) == "candidate_signal"
        and str(row.get("strategy_id", "")) == rule_config.strategy_id
    ]

    expected_by_key = {_comparison_key(row): row for row in expected_rows}
    actual_by_key = {_comparison_key(row): row for row in actual_rows}
    duplicate_expected = _duplicate_keys(expected_rows)
    duplicate_actual = _duplicate_keys(actual_rows)
    if duplicate_expected:
        raise DeltaImpulseOverlayValidationError(
            "Duplicate expected comparison keys: " + ", ".join(sorted(duplicate_expected)),
        )
    if duplicate_actual:
        raise DeltaImpulseOverlayValidationError(
            "Duplicate actual comparison keys: " + ", ".join(sorted(duplicate_actual)),
        )

    matched_rows: list[dict[str, Any]] = []
    missing_rows: list[dict[str, Any]] = []
    mismatched_rows: list[dict[str, Any]] = []
    for key, expected in expected_by_key.items():
        actual = actual_by_key.get(key)
        if actual is None:
            missing_rows.append(expected)
            continue
        mismatches = _field_mismatches(expected, actual, price_tolerance=price_tolerance)
        if mismatches:
            mismatched_rows.append(
                {
                    "comparison_key": key,
                    "expected_bar_start_time": expected["bar_start_time"],
                    "actual_bar_start_time": actual.get("bar_start_time", ""),
                    "mismatches": "; ".join(mismatches),
                },
            )
            continue
        matched_rows.append(expected)

    unexpected_rows = [
        actual
        for key, actual in actual_by_key.items()
        if key not in expected_by_key
    ]
    return DeltaImpulseOverlayComparison(
        expected_rows=expected_rows,
        actual_rows=actual_rows,
        matched_rows=matched_rows,
        missing_rows=missing_rows,
        unexpected_rows=unexpected_rows,
        mismatched_rows=mismatched_rows,
    )


def render_delta_impulse_overlay_validation_report(
    comparison: DeltaImpulseOverlayComparison,
    *,
    bars_source: str,
    signal_log_source: str,
    config: DeltaImpulseRuleConfig | None = None,
    max_examples: int = 12,
) -> str:
    """Render a markdown validation report."""

    rule_config = config or DeltaImpulseRuleConfig()
    status = "PASS" if comparison.passed else "FAIL"
    dates = sorted({_row_date(row) for row in comparison.expected_rows})
    lines = [
        "# Sierra Delta Impulse Overlay Validation",
        "",
        f"Status: **{status}**",
        "",
        "## Sources",
        "",
        f"- Bars export: `{bars_source}`",
        f"- Signal log: `{signal_log_source}`",
        "",
        "## Rule",
        "",
        f"- strategy ID: `{rule_config.strategy_id}`",
        f"- setup window: `{rule_config.setup_start_time}` through `{rule_config.setup_end_time}`",
        f"- lookback bars: `{rule_config.lookback_bars}`",
        f"- minimum price move: `{_format_number(rule_config.minimum_price_move_points)}` points",
        f"- minimum delta sum: `{_format_number(rule_config.minimum_delta_sum)}`",
        f"- minimum spacing: `{rule_config.minimum_spacing_seconds}` seconds",
        f"- max signals per day: `{rule_config.max_signals_per_day}`",
        f"- fixed exits: `{_format_number(rule_config.first_target_points)} / "
        f"{_format_number(rule_config.stop_points)} / "
        f"{_format_number(rule_config.runner_target_points)} / {rule_config.runner_stop_mode}`",
        "",
        "## Summary",
        "",
        f"- expected candidates from bars: `{len(comparison.expected_rows)}`",
        f"- Sierra candidate log rows: `{len(comparison.actual_rows)}`",
        f"- matched rows: `{len(comparison.matched_rows)}`",
        f"- missing rows: `{len(comparison.missing_rows)}`",
        f"- unexpected rows: `{len(comparison.unexpected_rows)}`",
        f"- field mismatches: `{len(comparison.mismatched_rows)}`",
        f"- trade dates: `{len(dates)}`",
    ]
    if dates:
        lines.append(f"- date range: `{dates[0]}` through `{dates[-1]}`")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
        ],
    )
    if comparison.passed:
        lines.append(
            "The Python baseline reproduces every Sierra candidate row for the exported bars. "
            "This validates the overlay entry rule, spacing filter, daily cap, and fixed "
            "stop/target fields for this sample.",
        )
    else:
        lines.append(
            "The Python baseline does not match the Sierra log. Regenerate the Sierra export "
            "from the same chart/timezone as the signal log before using these rows for "
            "research acceptance decisions.",
        )
    lines.extend(["", "## Differences", ""])
    lines.extend(_difference_table("Missing", comparison.missing_rows, max_examples=max_examples))
    lines.extend(_difference_table("Unexpected", comparison.unexpected_rows, max_examples=max_examples))
    lines.extend(_mismatch_table(comparison.mismatched_rows, max_examples=max_examples))
    return "\n".join(lines).rstrip() + "\n"


def write_delta_impulse_overlay_validation_report(
    path: str,
    comparison: DeltaImpulseOverlayComparison,
    *,
    bars_source: str,
    signal_log_source: str,
    config: DeltaImpulseRuleConfig | None = None,
) -> None:
    """Write a markdown validation report."""

    from pathlib import Path

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        render_delta_impulse_overlay_validation_report(
            comparison,
            bars_source=bars_source,
            signal_log_source=signal_log_source,
            config=config,
        ),
        encoding="utf-8",
    )


def _evaluate_bar(
    bars: list[_DeltaImpulseBar],
    position: int,
    *,
    rule_config: DeltaImpulseRuleConfig,
    setup_start: time,
    setup_end: time,
) -> dict[str, Any]:
    bar = bars[position]
    bar_time = bar.parsed_timestamp.time()
    if bar_time < setup_start or bar_time > setup_end:
        return _rejection(bar, "outside_session", "bar is outside setup window")

    indices = _eligible_lookback_positions(
        bars,
        position,
        setup_start=setup_start,
        setup_end=setup_end,
        required_indices=rule_config.lookback_bars + 1,
    )
    if len(indices) < rule_config.lookback_bars + 1:
        return _rejection(
            bar,
            "insufficient_context",
            "not enough eligible setup-window bars for lookback",
        )

    price_reference_position = indices[rule_config.lookback_bars]
    price_move = bar.close - bars[price_reference_position].close
    delta_sum = sum(bars[indices[offset]].delta for offset in range(rule_config.lookback_bars))
    direction = "none"
    if (
        price_move >= rule_config.minimum_price_move_points
        and delta_sum >= rule_config.minimum_delta_sum
    ):
        direction = "long"
    elif (
        price_move <= -rule_config.minimum_price_move_points
        and delta_sum <= -rule_config.minimum_delta_sum
    ):
        direction = "short"
    else:
        return _rejection(
            bar,
            "no_setup",
            (
                f"price_move={_format_number(price_move)}; "
                f"delta_sum={_format_number(delta_sum)}; thresholds not met"
            ),
        )

    is_long = direction == "long"
    stop_price = (
        bar.close - rule_config.stop_points
        if is_long
        else bar.close + rule_config.stop_points
    )
    first_target_price = (
        bar.close + rule_config.first_target_points
        if is_long
        else bar.close - rule_config.first_target_points
    )
    runner_target_price = (
        bar.close + rule_config.runner_target_points
        if is_long
        else bar.close - rule_config.runner_target_points
    )
    runner_stop_mode = _normalize_runner_stop_mode(rule_config.runner_stop_mode)
    notes = (
        f"{direction} delta impulse continuation; "
        f"lookback_bars={rule_config.lookback_bars}; "
        f"price_reference_bar_index={bars[price_reference_position].bar_index}; "
        f"price_move={_format_number(price_move)}; "
        f"delta_sum={_format_number(delta_sum)}; "
        f"first_target_points={_format_number(rule_config.first_target_points)}; "
        f"runner_target_points={_format_number(rule_config.runner_target_points)}; "
        f"runner_stop_mode={runner_stop_mode}; "
        f"minimum_spacing_seconds={rule_config.minimum_spacing_seconds}; "
        f"max_signals_per_day={rule_config.max_signals_per_day}"
    )
    signal_id = f"{rule_config.strategy_id}_{bar.symbol}_{bar.bar_index}"
    return {
        "schema_version": 1,
        "event_key": _event_key(
            bar.symbol,
            bar.chart_number,
            bar.bar_index,
            rule_config.strategy_id,
            "candidate_signal",
            direction,
        ),
        "event_type": "candidate_signal",
        "generated_at": bar.timestamp,
        "symbol": bar.symbol,
        "chart_number": bar.chart_number,
        "bar_index": bar.bar_index,
        "bar_start_time": bar.timestamp,
        "trade_mode": rule_config.trade_mode,
        "strategy_id": rule_config.strategy_id,
        "signal_id": signal_id,
        "direction": direction,
        "action": "candidate",
        "signal_price": _format_number(bar.close),
        "stop_price": _format_number(stop_price),
        "target_price": _format_number(runner_target_price),
        "invalidation_price": _format_number(stop_price),
        "rejection_reason": "not_applicable",
        "confidence": _format_number(rule_config.confidence),
        "notes": notes,
        "first_target_price": _format_number(first_target_price),
    }


def _eligible_lookback_positions(
    bars: list[_DeltaImpulseBar],
    position: int,
    *,
    setup_start: time,
    setup_end: time,
    required_indices: int,
) -> list[int]:
    indices: list[int] = []
    current_date = bars[position].parsed_timestamp.date()
    for index in range(position, -1, -1):
        bar = bars[index]
        if bar.parsed_timestamp.date() != current_date:
            break
        bar_time = bar.parsed_timestamp.time()
        if bar_time < setup_start:
            break
        if bar_time > setup_end:
            continue
        indices.append(index)
        if len(indices) >= required_indices:
            break
    return indices


def _rejection(bar: _DeltaImpulseBar, rejection_reason: str, notes: str) -> dict[str, Any]:
    return {
        "event_type": "rejected_signal",
        "signal_price": _format_number(bar.close),
        "rejection_reason": rejection_reason,
        "notes": notes,
    }


def _normalize_bar(row: dict[str, Any]) -> _DeltaImpulseBar:
    timestamp = str(row.get("timestamp", "")).strip()
    if not timestamp:
        raise DeltaImpulseOverlayValidationError("Blank bar timestamp")
    return _DeltaImpulseBar(
        timestamp=timestamp,
        parsed_timestamp=_parse_timestamp(timestamp),
        symbol=str(row.get("symbol", "")).strip(),
        chart_number=_to_int(row.get("chart_number"), "chart_number"),
        bar_index=_to_int(row.get("bar_index"), "bar_index"),
        high=_to_float(row.get("high"), "high"),
        low=_to_float(row.get("low"), "low"),
        close=_to_float(row.get("close"), "close"),
        delta=_bar_delta(row),
    )


def _bar_delta(row: dict[str, Any]) -> float:
    ask_volume = _to_float(row.get("ask_volume"), "ask_volume")
    bid_volume = _to_float(row.get("bid_volume"), "bid_volume")
    return ask_volume - bid_volume


def _comparison_key(row: dict[str, Any]) -> str:
    return ":".join(
        [
            str(row.get("symbol", "")),
            str(row.get("chart_number", "")),
            str(row.get("bar_index", "")),
            str(row.get("direction", "")),
        ],
    )


def _field_mismatches(
    expected: dict[str, Any],
    actual: dict[str, Any],
    *,
    price_tolerance: float,
) -> list[str]:
    mismatches = []
    for field_name in (
        "event_key",
        "event_type",
        "strategy_id",
        "signal_id",
        "direction",
        "action",
        "rejection_reason",
    ):
        if str(expected.get(field_name, "")) != str(actual.get(field_name, "")):
            mismatches.append(
                f"{field_name}: expected {expected.get(field_name)!r}, got {actual.get(field_name)!r}",
            )

    for field_name in (
        "signal_price",
        "stop_price",
        "target_price",
        "invalidation_price",
        "confidence",
    ):
        expected_value = _to_float(expected.get(field_name), field_name)
        actual_value = _to_float(actual.get(field_name), field_name)
        if abs(expected_value - actual_value) > price_tolerance:
            mismatches.append(
                f"{field_name}: expected {_format_number(expected_value)}, "
                f"got {_format_number(actual_value)}",
            )

    if _parse_timestamp(str(expected["bar_start_time"])) != _parse_timestamp(
        str(actual.get("bar_start_time", "")),
    ):
        mismatches.append(
            f"bar_start_time: expected {expected['bar_start_time']!r}, "
            f"got {actual.get('bar_start_time')!r}",
        )
    return mismatches


def _difference_table(
    title: str,
    rows: list[dict[str, Any]],
    *,
    max_examples: int,
) -> list[str]:
    lines = [f"### {title}", ""]
    if not rows:
        lines.extend(["None.", ""])
        return lines
    lines.extend(
        [
            "| bar_start_time | bar_index | direction | signal_price | event_key |",
            "| --- | ---: | --- | ---: | --- |",
        ],
    )
    for row in rows[:max_examples]:
        lines.append(
            f"| `{row.get('bar_start_time', '')}` | `{row.get('bar_index', '')}` | "
            f"`{row.get('direction', '')}` | `{row.get('signal_price', '')}` | "
            f"`{row.get('event_key', '')}` |",
        )
    if len(rows) > max_examples:
        lines.append(f"| ... | ... | ... | ... | `{len(rows) - max_examples} more rows` |")
    lines.append("")
    return lines


def _mismatch_table(rows: list[dict[str, Any]], *, max_examples: int) -> list[str]:
    lines = ["### Field Mismatches", ""]
    if not rows:
        lines.extend(["None.", ""])
        return lines
    lines.extend(
        [
            "| key | expected time | actual time | mismatches |",
            "| --- | --- | --- | --- |",
        ],
    )
    for row in rows[:max_examples]:
        lines.append(
            f"| `{row['comparison_key']}` | `{row['expected_bar_start_time']}` | "
            f"`{row['actual_bar_start_time']}` | `{row['mismatches']}` |",
        )
    if len(rows) > max_examples:
        lines.append(f"| ... | ... | ... | `{len(rows) - max_examples} more rows` |")
    lines.append("")
    return lines


def _duplicate_keys(rows: list[dict[str, Any]]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for row in rows:
        key = _comparison_key(row)
        if key in seen:
            duplicates.add(key)
        seen.add(key)
    return duplicates


def _row_date(row: dict[str, Any]) -> str:
    return _parse_timestamp(str(row["bar_start_time"])).date().isoformat()


def _event_key(
    symbol: str,
    chart_number: int,
    bar_index: int,
    strategy_id: str,
    event_type: str,
    direction: str,
) -> str:
    return f"{symbol}:{chart_number}:{bar_index}:{strategy_id}:{event_type}:{direction}"


def _validate_rule_config(config: DeltaImpulseRuleConfig) -> None:
    if config.lookback_bars <= 0:
        raise DeltaImpulseOverlayValidationError("lookback_bars must be positive")
    if config.minimum_price_move_points <= 0:
        raise DeltaImpulseOverlayValidationError("minimum_price_move_points must be positive")
    if config.minimum_delta_sum <= 0:
        raise DeltaImpulseOverlayValidationError("minimum_delta_sum must be positive")
    if config.stop_points <= 0:
        raise DeltaImpulseOverlayValidationError("stop_points must be positive")
    if config.first_target_points <= 0:
        raise DeltaImpulseOverlayValidationError("first_target_points must be positive")
    if config.runner_target_points <= config.first_target_points:
        raise DeltaImpulseOverlayValidationError(
            "runner_target_points must be greater than first_target_points",
        )
    if config.runner_stop_mode not in {"initial", "breakeven"}:
        raise DeltaImpulseOverlayValidationError(
            "runner_stop_mode must be one of: initial, breakeven",
        )


def _normalize_runner_stop_mode(value: str) -> str:
    return "initial" if value == "initial" else "breakeven"


def _parse_timestamp(value: str) -> datetime:
    timestamp_text = _normalize_timestamp_text(value.strip())
    for timestamp_format in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(timestamp_text, timestamp_format)
        except ValueError:
            continue
    raise DeltaImpulseOverlayValidationError(f"Invalid timestamp: {value!r}")


def _normalize_timestamp_text(value: str) -> str:
    parts = value.split(maxsplit=1)
    if len(parts) != 2 or "-" not in parts[0]:
        return value
    date_parts = parts[0].split("-")
    if len(date_parts) != 3:
        return value
    normalized_date = "-".join(
        [date_parts[0], date_parts[1].zfill(2), date_parts[2].zfill(2)],
    )
    return f"{normalized_date} {parts[1]}"


def _parse_time(value: str, field_name: str) -> time:
    try:
        return datetime.strptime(str(value).strip(), "%H:%M:%S").time()
    except ValueError as exc:
        raise DeltaImpulseOverlayValidationError(f"Invalid {field_name}: {value!r}") from exc


def _seconds_since_midnight(value: time) -> int:
    return value.hour * 3600 + value.minute * 60 + value.second


def _to_int(value: Any, field_name: str) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError) as exc:
        raise DeltaImpulseOverlayValidationError(
            f"Invalid integer field {field_name}: {value!r}",
        ) from exc


def _to_float(value: Any, field_name: str) -> float:
    try:
        return float(str(value))
    except (TypeError, ValueError) as exc:
        raise DeltaImpulseOverlayValidationError(
            f"Invalid numeric field {field_name}: {value!r}",
        ) from exc


def _format_number(value: float) -> str:
    if abs(value) < 0.0000000001:
        value = 0.0
    return f"{value:.10f}".rstrip("0").rstrip(".")
