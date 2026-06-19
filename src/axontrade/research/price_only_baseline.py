"""First price-only baseline that emits signal-log rows."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path
from typing import Any, Iterable

from axontrade.config import ConfigError, load_yaml, require_fields
from axontrade.research.signal_log import load_signal_log_schema, validate_signal_log_row


DEFAULT_PRICE_ONLY_BASELINE_CONFIG = "config/research/price_only_vwap_reclaim.yaml"
DEFAULT_PRICE_ONLY_LIQUIDITY_SWEEP_CONFIG = (
    "config/research/price_only_liquidity_sweep_reversal.yaml"
)
_TIME_FORMAT = "%H:%M:%S"
_TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
)


class BaselineError(ValueError):
    """Raised when baseline configuration or input rows are invalid."""


BASELINE_REQUIRED_FIELDS = (
    "schema_version",
    "profile_id",
    "strategy_id",
    "default_trade_mode",
    "allowed_session_phases",
    "required_bar_fields",
    "rules.require_previous_bar",
    "rules.opening_range_end_time",
    "rules.minimum_opening_range_width_points",
    "rules.stop_buffer_points",
    "rules.target_r_multiple",
    "rules.confidence",
    "outputs.candidate_event_type",
    "outputs.rejected_event_type",
    "outputs.no_setup_rejection_reason",
    "outputs.insufficient_context_rejection_reason",
    "outputs.outside_session_rejection_reason",
    "outputs.risk_limit_rejection_reason",
    "outputs.ambiguous_setup_rejection_reason",
)
LIQUIDITY_SWEEP_REQUIRED_FIELDS = (
    "schema_version",
    "profile_id",
    "strategy_id",
    "default_trade_mode",
    "allowed_session_phases",
    "required_bar_fields",
    "rules.opening_range_end_time",
    "rules.setup_start_time",
    "rules.setup_end_time",
    "rules.minimum_opening_range_width_points",
    "rules.minimum_sweep_points",
    "rules.close_back_inside_points",
    "rules.stop_buffer_points",
    "rules.maximum_risk_points",
    "rules.target_level",
    "rules.one_signal_per_side_per_day",
    "rules.confidence",
    "outputs.candidate_event_type",
    "outputs.rejected_event_type",
    "outputs.no_setup_rejection_reason",
    "outputs.insufficient_context_rejection_reason",
    "outputs.outside_session_rejection_reason",
    "outputs.duplicate_signal_rejection_reason",
    "outputs.risk_limit_rejection_reason",
    "outputs.ambiguous_setup_rejection_reason",
)


@dataclass(frozen=True)
class PriceOnlyBar:
    """Normalized bar row with precomputed price-only context levels."""

    timestamp: str
    symbol: str
    chart_number: int
    bar_index: int
    open: float
    high: float
    low: float
    close: float
    vwap: float
    opening_range_high: float
    opening_range_low: float
    session_phase: str


def load_price_only_baseline_config(
    path: str = DEFAULT_PRICE_ONLY_BASELINE_CONFIG,
) -> dict[str, Any]:
    """Load and validate the price-only baseline configuration."""

    config = load_yaml(path)
    validate_price_only_baseline_config(config)
    return config


def load_price_only_liquidity_sweep_config(
    path: str = DEFAULT_PRICE_ONLY_LIQUIDITY_SWEEP_CONFIG,
) -> dict[str, Any]:
    """Load and validate the price-only liquidity sweep reversal config."""

    config = load_yaml(path)
    validate_price_only_liquidity_sweep_config(config)
    return config


def validate_price_only_baseline_config(config: dict[str, Any]) -> dict[str, Any]:
    """Validate the first price-only baseline configuration."""

    try:
        require_fields(config, BASELINE_REQUIRED_FIELDS, context="price-only baseline config")
    except ConfigError as exc:
        raise BaselineError(str(exc)) from exc

    if not isinstance(config["allowed_session_phases"], list):
        raise BaselineError("allowed_session_phases must be a list")
    if not isinstance(config["required_bar_fields"], list):
        raise BaselineError("required_bar_fields must be a list")

    numeric_rule_fields = (
        "minimum_opening_range_width_points",
        "stop_buffer_points",
        "target_r_multiple",
        "confidence",
    )
    for field_name in numeric_rule_fields:
        _to_float(config["rules"][field_name], f"rules.{field_name}")
    _parse_time(config["rules"]["opening_range_end_time"], "rules.opening_range_end_time")

    if float(config["rules"]["target_r_multiple"]) <= 0:
        raise BaselineError("rules.target_r_multiple must be positive")
    if float(config["rules"]["stop_buffer_points"]) < 0:
        raise BaselineError("rules.stop_buffer_points must be nonnegative")

    return config


def validate_price_only_liquidity_sweep_config(config: dict[str, Any]) -> dict[str, Any]:
    """Validate the price-only liquidity sweep reversal baseline configuration."""

    try:
        require_fields(
            config,
            LIQUIDITY_SWEEP_REQUIRED_FIELDS,
            context="price-only liquidity sweep config",
        )
    except ConfigError as exc:
        raise BaselineError(str(exc)) from exc

    if not isinstance(config["allowed_session_phases"], list):
        raise BaselineError("allowed_session_phases must be a list")
    if not isinstance(config["required_bar_fields"], list):
        raise BaselineError("required_bar_fields must be a list")
    if not isinstance(config["rules"]["one_signal_per_side_per_day"], bool):
        raise BaselineError("rules.one_signal_per_side_per_day must be a boolean")

    for field_name in (
        "minimum_opening_range_width_points",
        "minimum_sweep_points",
        "close_back_inside_points",
        "stop_buffer_points",
        "maximum_risk_points",
        "confidence",
    ):
        _to_float(config["rules"][field_name], f"rules.{field_name}")

    for field_name in ("opening_range_end_time", "setup_start_time", "setup_end_time"):
        _parse_time(config["rules"][field_name], f"rules.{field_name}")

    setup_start = _parse_time(config["rules"]["setup_start_time"], "rules.setup_start_time")
    setup_end = _parse_time(config["rules"]["setup_end_time"], "rules.setup_end_time")
    if setup_start >= setup_end:
        raise BaselineError("rules.setup_start_time must be before setup_end_time")

    if float(config["rules"]["minimum_sweep_points"]) <= 0:
        raise BaselineError("rules.minimum_sweep_points must be positive")
    if float(config["rules"]["close_back_inside_points"]) < 0:
        raise BaselineError("rules.close_back_inside_points must be nonnegative")
    if float(config["rules"]["stop_buffer_points"]) < 0:
        raise BaselineError("rules.stop_buffer_points must be nonnegative")
    if float(config["rules"]["maximum_risk_points"]) <= 0:
        raise BaselineError("rules.maximum_risk_points must be positive")
    if config["rules"]["target_level"] != "opening_range_midpoint":
        raise BaselineError("rules.target_level currently supports only opening_range_midpoint")

    return config


def load_price_only_bar_rows_csv(path: str | Path) -> list[dict[str, str]]:
    """Load Sierra-exported bar and level rows from CSV."""

    csv_path = Path(path)
    with csv_path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def evaluate_price_only_vwap_reclaim(
    rows: Iterable[dict[str, Any]],
    config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Evaluate rows chronologically and return schema-compatible signal rows."""

    baseline_config = load_price_only_baseline_config() if config is None else config
    validate_price_only_baseline_config(baseline_config)

    signal_rows: list[dict[str, Any]] = []
    previous_bar_by_symbol: dict[str, PriceOnlyBar] = {}
    signal_schema = load_signal_log_schema()

    for source_row in rows:
        bar = _normalize_bar(source_row, baseline_config)
        previous_bar = previous_bar_by_symbol.get(bar.symbol)
        signal_rows.append(_evaluate_bar(bar, previous_bar, baseline_config, signal_schema))
        previous_bar_by_symbol[bar.symbol] = bar

    return signal_rows


def evaluate_price_only_liquidity_sweep_reversal(
    rows: Iterable[dict[str, Any]],
    config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Evaluate the opening-range liquidity sweep reversal proxy baseline."""

    baseline_config = load_price_only_liquidity_sweep_config() if config is None else config
    validate_price_only_liquidity_sweep_config(baseline_config)

    signal_rows: list[dict[str, Any]] = []
    emitted_sides: set[tuple[str, str, str]] = set()
    signal_schema = load_signal_log_schema()

    for source_row in rows:
        bar = _normalize_bar(source_row, baseline_config)
        signal_row, emitted_side = _evaluate_liquidity_sweep_bar(
            bar,
            baseline_config,
            signal_schema,
            emitted_sides,
        )
        signal_rows.append(signal_row)
        if emitted_side is not None:
            emitted_sides.add(emitted_side)

    return signal_rows


def _evaluate_bar(
    bar: PriceOnlyBar,
    previous_bar: PriceOnlyBar | None,
    config: dict[str, Any],
    signal_schema: dict[str, Any],
) -> dict[str, Any]:
    if bar.session_phase not in set(config["allowed_session_phases"]):
        return _rejected_signal_row(
            bar,
            config,
            signal_schema,
            config["outputs"]["outside_session_rejection_reason"],
            "bar is outside allowed session phase",
        )

    opening_range_end_time = _parse_time(
        config["rules"]["opening_range_end_time"],
        "rules.opening_range_end_time",
    )
    if _bar_time(bar) <= opening_range_end_time:
        return _rejected_signal_row(
            bar,
            config,
            signal_schema,
            config["outputs"]["insufficient_context_rejection_reason"],
            "opening range is not complete",
        )

    opening_range_width = bar.opening_range_high - bar.opening_range_low
    minimum_width = float(config["rules"]["minimum_opening_range_width_points"])
    if previous_bar is None or opening_range_width < minimum_width:
        return _rejected_signal_row(
            bar,
            config,
            signal_schema,
            config["outputs"]["insufficient_context_rejection_reason"],
            "previous bar or opening range context is insufficient",
        )

    long_setup = (
        previous_bar.close <= previous_bar.vwap
        and bar.close > bar.vwap
        and bar.close > bar.opening_range_high
    )
    short_setup = (
        previous_bar.close >= previous_bar.vwap
        and bar.close < bar.vwap
        and bar.close < bar.opening_range_low
    )

    if long_setup and short_setup:
        return _rejected_signal_row(
            bar,
            config,
            signal_schema,
            config["outputs"]["ambiguous_setup_rejection_reason"],
            "long and short setup conditions both evaluated true",
        )
    if long_setup:
        return _candidate_signal_row(bar, config, signal_schema, "long")
    if short_setup:
        return _candidate_signal_row(bar, config, signal_schema, "short")

    return _rejected_signal_row(
        bar,
        config,
        signal_schema,
        config["outputs"]["no_setup_rejection_reason"],
        "no VWAP/opening-range reclaim setup",
    )


def _candidate_signal_row(
    bar: PriceOnlyBar,
    config: dict[str, Any],
    signal_schema: dict[str, Any],
    direction: str,
) -> dict[str, Any]:
    stop_buffer = float(config["rules"]["stop_buffer_points"])
    target_r_multiple = float(config["rules"]["target_r_multiple"])

    if direction == "long":
        stop_price = min(bar.low, bar.vwap, bar.opening_range_high) - stop_buffer
        risk_points = bar.close - stop_price
        target_price = bar.close + risk_points * target_r_multiple
    else:
        stop_price = max(bar.high, bar.vwap, bar.opening_range_low) + stop_buffer
        risk_points = stop_price - bar.close
        target_price = bar.close - risk_points * target_r_multiple

    if risk_points <= 0:
        return _rejected_signal_row(
            bar,
            config,
            signal_schema,
            config["outputs"]["risk_limit_rejection_reason"],
            "candidate has nonpositive risk distance",
        )

    row = _base_signal_row(bar, config)
    row.update(
        {
            "event_type": config["outputs"]["candidate_event_type"],
            "direction": direction,
            "action": "candidate",
            "stop_price": _format_price(stop_price),
            "target_price": _format_price(target_price),
            "invalidation_price": _format_price(stop_price),
            "rejection_reason": "not_applicable",
            "confidence": float(config["rules"]["confidence"]),
            "notes": "price-only VWAP/opening-range reclaim candidate",
        },
    )
    row["event_key"] = _event_key(row)
    return validate_signal_log_row(row, signal_schema)


def _evaluate_liquidity_sweep_bar(
    bar: PriceOnlyBar,
    config: dict[str, Any],
    signal_schema: dict[str, Any],
    emitted_sides: set[tuple[str, str, str]],
) -> tuple[dict[str, Any], tuple[str, str, str] | None]:
    if bar.session_phase not in set(config["allowed_session_phases"]):
        return (
            _rejected_signal_row(
                bar,
                config,
                signal_schema,
                config["outputs"]["outside_session_rejection_reason"],
                "bar is outside allowed session phase",
            ),
            None,
        )

    opening_range_end = _parse_time(
        config["rules"]["opening_range_end_time"],
        "rules.opening_range_end_time",
    )
    setup_start = _parse_time(config["rules"]["setup_start_time"], "rules.setup_start_time")
    setup_end = _parse_time(config["rules"]["setup_end_time"], "rules.setup_end_time")
    bar_time = _bar_time(bar)
    if bar_time <= opening_range_end:
        return (
            _rejected_signal_row(
                bar,
                config,
                signal_schema,
                config["outputs"]["insufficient_context_rejection_reason"],
                "opening range is not complete",
            ),
            None,
        )
    if bar_time < setup_start or bar_time > setup_end:
        return (
            _rejected_signal_row(
                bar,
                config,
                signal_schema,
                config["outputs"]["outside_session_rejection_reason"],
                "bar is outside liquidity sweep setup window",
            ),
            None,
        )

    opening_range_width = bar.opening_range_high - bar.opening_range_low
    minimum_width = float(config["rules"]["minimum_opening_range_width_points"])
    if opening_range_width < minimum_width:
        return (
            _rejected_signal_row(
                bar,
                config,
                signal_schema,
                config["outputs"]["insufficient_context_rejection_reason"],
                "opening range width is below configured minimum",
            ),
            None,
        )

    sweep_points = float(config["rules"]["minimum_sweep_points"])
    inside_points = float(config["rules"]["close_back_inside_points"])
    short_setup = (
        bar.high >= bar.opening_range_high + sweep_points
        and bar.close <= bar.opening_range_high - inside_points
    )
    long_setup = (
        bar.low <= bar.opening_range_low - sweep_points
        and bar.close >= bar.opening_range_low + inside_points
    )
    if short_setup and long_setup:
        return (
            _rejected_signal_row(
                bar,
                config,
                signal_schema,
                config["outputs"]["ambiguous_setup_rejection_reason"],
                "bar swept both sides of the opening range",
            ),
            None,
        )

    if short_setup:
        return _liquidity_sweep_candidate(bar, config, signal_schema, "short", emitted_sides)
    if long_setup:
        return _liquidity_sweep_candidate(bar, config, signal_schema, "long", emitted_sides)

    return (
        _rejected_signal_row(
            bar,
            config,
            signal_schema,
            config["outputs"]["no_setup_rejection_reason"],
            "no opening-range liquidity sweep reversal setup",
        ),
        None,
    )


def _liquidity_sweep_candidate(
    bar: PriceOnlyBar,
    config: dict[str, Any],
    signal_schema: dict[str, Any],
    direction: str,
    emitted_sides: set[tuple[str, str, str]],
) -> tuple[dict[str, Any], tuple[str, str, str] | None]:
    emitted_key = (bar.symbol, _bar_date(bar), direction)
    if config["rules"]["one_signal_per_side_per_day"] and emitted_key in emitted_sides:
        return (
            _rejected_signal_row(
                bar,
                config,
                signal_schema,
                config["outputs"]["duplicate_signal_rejection_reason"],
                "liquidity sweep signal already emitted for this symbol/date/side",
            ),
            None,
        )

    stop_buffer = float(config["rules"]["stop_buffer_points"])
    maximum_risk_points = float(config["rules"]["maximum_risk_points"])
    target_price = (bar.opening_range_high + bar.opening_range_low) / 2
    if direction == "short":
        stop_price = bar.high + stop_buffer
        risk_points = stop_price - bar.close
        target_is_valid = target_price < bar.close
    else:
        stop_price = bar.low - stop_buffer
        risk_points = bar.close - stop_price
        target_is_valid = target_price > bar.close

    if risk_points <= 0:
        return (
            _rejected_signal_row(
                bar,
                config,
                signal_schema,
                config["outputs"]["risk_limit_rejection_reason"],
                "candidate has nonpositive risk distance",
            ),
            None,
        )
    if risk_points > maximum_risk_points:
        return (
            _rejected_signal_row(
                bar,
                config,
                signal_schema,
                config["outputs"]["risk_limit_rejection_reason"],
                "candidate risk exceeds configured maximum",
            ),
            None,
        )
    if not target_is_valid:
        return (
            _rejected_signal_row(
                bar,
                config,
                signal_schema,
                config["outputs"]["risk_limit_rejection_reason"],
                "opening-range midpoint target is not beyond entry price",
            ),
            None,
        )

    row = _base_signal_row(bar, config)
    row.update(
        {
            "event_type": config["outputs"]["candidate_event_type"],
            "direction": direction,
            "action": "candidate",
            "stop_price": _format_price(stop_price),
            "target_price": _format_price(target_price),
            "invalidation_price": _format_price(stop_price),
            "rejection_reason": "not_applicable",
            "confidence": float(config["rules"]["confidence"]),
            "notes": "price-only opening-range liquidity sweep reversal candidate",
        },
    )
    row["event_key"] = _event_key(row)
    return validate_signal_log_row(row, signal_schema), emitted_key


def _rejected_signal_row(
    bar: PriceOnlyBar,
    config: dict[str, Any],
    signal_schema: dict[str, Any],
    rejection_reason: str,
    notes: str,
) -> dict[str, Any]:
    row = _base_signal_row(bar, config)
    row.update(
        {
            "event_type": config["outputs"]["rejected_event_type"],
            "direction": "none",
            "action": "reject",
            "stop_price": "",
            "target_price": "",
            "invalidation_price": "",
            "rejection_reason": rejection_reason,
            "confidence": float(config["rules"]["confidence"]),
            "notes": notes,
        },
    )
    row["event_key"] = _event_key(row)
    return validate_signal_log_row(row, signal_schema)


def _base_signal_row(bar: PriceOnlyBar, config: dict[str, Any]) -> dict[str, Any]:
    strategy_id = str(config["strategy_id"])
    return {
        "schema_version": 1,
        "event_key": "",
        "event_type": "",
        "generated_at": bar.timestamp,
        "symbol": bar.symbol,
        "chart_number": bar.chart_number,
        "bar_index": bar.bar_index,
        "bar_start_time": bar.timestamp,
        "trade_mode": str(config["default_trade_mode"]),
        "strategy_id": strategy_id,
        "signal_id": f"{strategy_id}_{bar.symbol}_{bar.bar_index}",
        "direction": "",
        "action": "",
        "signal_price": _format_price(bar.close),
        "stop_price": "",
        "target_price": "",
        "invalidation_price": "",
        "rejection_reason": "",
        "confidence": "",
        "notes": "",
    }


def _event_key(row: dict[str, Any]) -> str:
    return (
        f"{row['symbol']}:{row['chart_number']}:{row['bar_index']}:"
        f"{row['strategy_id']}:{row['event_type']}:{row['direction']}"
    )


def _normalize_bar(row: dict[str, Any], config: dict[str, Any]) -> PriceOnlyBar:
    missing = [field_name for field_name in config["required_bar_fields"] if _is_blank(row.get(field_name))]
    if missing:
        raise BaselineError("Missing required bar fields: " + ", ".join(missing))

    return PriceOnlyBar(
        timestamp=str(row["timestamp"]),
        symbol=str(row["symbol"]),
        chart_number=_to_int(row["chart_number"], "chart_number"),
        bar_index=_to_int(row["bar_index"], "bar_index"),
        open=_to_float(row["open"], "open"),
        high=_to_float(row["high"], "high"),
        low=_to_float(row["low"], "low"),
        close=_to_float(row["close"], "close"),
        vwap=_to_float(row["vwap"], "vwap"),
        opening_range_high=_to_float(row["opening_range_high"], "opening_range_high"),
        opening_range_low=_to_float(row["opening_range_low"], "opening_range_low"),
        session_phase=str(row["session_phase"]),
    )


def _to_int(value: Any, field_name: str) -> int:
    try:
        return int(str(value))
    except ValueError as exc:
        raise BaselineError(f"Invalid integer field {field_name}: {value!r}") from exc


def _to_float(value: Any, field_name: str) -> float:
    try:
        return float(str(value))
    except ValueError as exc:
        raise BaselineError(f"Invalid numeric field {field_name}: {value!r}") from exc


def _bar_time(bar: PriceOnlyBar) -> time:
    timestamp_text = bar.timestamp.strip()
    for timestamp_format in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(timestamp_text, timestamp_format).time()
        except ValueError:
            continue
    raise BaselineError(f"Invalid timestamp: {bar.timestamp!r}")


def _bar_date(bar: PriceOnlyBar) -> str:
    timestamp_text = bar.timestamp.strip()
    for timestamp_format in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(timestamp_text, timestamp_format).date().isoformat()
        except ValueError:
            continue
    raise BaselineError(f"Invalid timestamp: {bar.timestamp!r}")


def _parse_time(value: Any, field_name: str) -> time:
    try:
        return datetime.strptime(str(value).strip(), _TIME_FORMAT).time()
    except ValueError as exc:
        raise BaselineError(f"Invalid time field {field_name}: {value!r}") from exc


def _format_price(value: float) -> str:
    return f"{value:.8f}".rstrip("0").rstrip(".")


def _is_blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""
