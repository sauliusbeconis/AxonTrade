"""Order-flow absorption filter for liquidity sweep reversal research."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path
from typing import Any, Iterable

from axontrade.config import ConfigError, load_yaml, require_fields
from axontrade.research.signal_log import load_signal_log_schema, validate_signal_log_row


DEFAULT_LIQUIDITY_SWEEP_ABSORPTION_CONFIG = (
    "config/research/liquidity_sweep_absorption_reversal.yaml"
)
_TIME_FORMAT = "%H:%M:%S"
_TIMESTAMP_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
)
_REQUIRED_CONFIG_FIELDS = (
    "schema_version",
    "profile_id",
    "strategy_id",
    "default_trade_mode",
    "allowed_session_phases",
    "required_bar_fields",
    "optional_bar_fields",
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
    "rules.minimum_total_volume",
    "rules.minimum_aggressive_delta",
    "rules.minimum_aggression_ratio",
    "rules.short_max_close_location",
    "rules.long_min_close_location",
    "rules.confidence",
    "outputs.candidate_event_type",
    "outputs.rejected_event_type",
    "outputs.no_setup_rejection_reason",
    "outputs.no_absorption_rejection_reason",
    "outputs.insufficient_context_rejection_reason",
    "outputs.outside_session_rejection_reason",
    "outputs.duplicate_signal_rejection_reason",
    "outputs.risk_limit_rejection_reason",
    "outputs.ambiguous_setup_rejection_reason",
)


class LiquiditySweepAbsorptionError(ValueError):
    """Raised when liquidity sweep absorption inputs are invalid."""


@dataclass(frozen=True)
class AbsorptionBar:
    """Normalized bar row with bid/ask volume fields for absorption research."""

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
    bid_volume: float
    ask_volume: float
    delta: float
    volume: float
    session_phase: str

    @property
    def total_volume(self) -> float:
        if self.volume > 0:
            return self.volume
        return self.bid_volume + self.ask_volume

    @property
    def close_location(self) -> float:
        bar_range = self.high - self.low
        if bar_range <= 0:
            return 0.5
        return (self.close - self.low) / bar_range


def load_liquidity_sweep_absorption_config(
    path: str | Path = DEFAULT_LIQUIDITY_SWEEP_ABSORPTION_CONFIG,
) -> dict[str, Any]:
    """Load and validate the liquidity sweep absorption config."""

    config = load_yaml(path)
    validate_liquidity_sweep_absorption_config(config)
    return config


def validate_liquidity_sweep_absorption_config(config: dict[str, Any]) -> dict[str, Any]:
    """Validate liquidity sweep absorption configuration."""

    try:
        require_fields(config, _REQUIRED_CONFIG_FIELDS, context="liquidity sweep absorption config")
    except ConfigError as exc:
        raise LiquiditySweepAbsorptionError(str(exc)) from exc

    if not isinstance(config["allowed_session_phases"], list):
        raise LiquiditySweepAbsorptionError("allowed_session_phases must be a list")
    if not isinstance(config["required_bar_fields"], list):
        raise LiquiditySweepAbsorptionError("required_bar_fields must be a list")
    if not isinstance(config["optional_bar_fields"], list):
        raise LiquiditySweepAbsorptionError("optional_bar_fields must be a list")
    if not isinstance(config["rules"]["one_signal_per_side_per_day"], bool):
        raise LiquiditySweepAbsorptionError("rules.one_signal_per_side_per_day must be a boolean")

    for field_name in (
        "minimum_opening_range_width_points",
        "minimum_sweep_points",
        "close_back_inside_points",
        "stop_buffer_points",
        "maximum_risk_points",
        "minimum_total_volume",
        "minimum_aggressive_delta",
        "minimum_aggression_ratio",
        "short_max_close_location",
        "long_min_close_location",
        "confidence",
    ):
        _to_float(config["rules"][field_name], f"rules.{field_name}")

    for field_name in ("opening_range_end_time", "setup_start_time", "setup_end_time"):
        _parse_time(config["rules"][field_name], f"rules.{field_name}")

    setup_start = _parse_time(config["rules"]["setup_start_time"], "rules.setup_start_time")
    setup_end = _parse_time(config["rules"]["setup_end_time"], "rules.setup_end_time")
    if setup_start >= setup_end:
        raise LiquiditySweepAbsorptionError("rules.setup_start_time must be before setup_end_time")
    if float(config["rules"]["minimum_sweep_points"]) <= 0:
        raise LiquiditySweepAbsorptionError("rules.minimum_sweep_points must be positive")
    if float(config["rules"]["minimum_aggression_ratio"]) < 1:
        raise LiquiditySweepAbsorptionError("rules.minimum_aggression_ratio must be at least 1")
    if config["rules"]["target_level"] != "opening_range_midpoint":
        raise LiquiditySweepAbsorptionError(
            "rules.target_level currently supports only opening_range_midpoint",
        )

    for field_name in ("short_max_close_location", "long_min_close_location"):
        value = float(config["rules"][field_name])
        if value < 0 or value > 1:
            raise LiquiditySweepAbsorptionError(f"rules.{field_name} must be between 0 and 1")

    return config


def evaluate_liquidity_sweep_absorption_reversal(
    rows: Iterable[dict[str, Any]],
    config: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Evaluate liquidity sweep reversal rows with bid/ask absorption filters."""

    strategy_config = load_liquidity_sweep_absorption_config() if config is None else config
    validate_liquidity_sweep_absorption_config(strategy_config)

    signal_rows: list[dict[str, Any]] = []
    emitted_sides: set[tuple[str, str, str]] = set()
    signal_schema = load_signal_log_schema()

    for source_row in rows:
        bar = _normalize_bar(source_row, strategy_config)
        signal_row, emitted_side = _evaluate_bar(
            bar,
            strategy_config,
            signal_schema,
            emitted_sides,
        )
        signal_rows.append(signal_row)
        if emitted_side is not None:
            emitted_sides.add(emitted_side)

    return signal_rows


def _evaluate_bar(
    bar: AbsorptionBar,
    config: dict[str, Any],
    signal_schema: dict[str, Any],
    emitted_sides: set[tuple[str, str, str]],
) -> tuple[dict[str, Any], tuple[str, str, str] | None]:
    if bar.session_phase not in set(config["allowed_session_phases"]):
        return _reject(bar, config, signal_schema, "outside_session", "bar is outside allowed session phase")

    opening_range_end = _parse_time(
        config["rules"]["opening_range_end_time"],
        "rules.opening_range_end_time",
    )
    setup_start = _parse_time(config["rules"]["setup_start_time"], "rules.setup_start_time")
    setup_end = _parse_time(config["rules"]["setup_end_time"], "rules.setup_end_time")
    bar_time = _bar_time(bar)
    if bar_time <= opening_range_end:
        return _reject(bar, config, signal_schema, "insufficient_context", "opening range is not complete")
    if bar_time < setup_start or bar_time > setup_end:
        return _reject(bar, config, signal_schema, "outside_session", "bar is outside setup window")

    opening_range_width = bar.opening_range_high - bar.opening_range_low
    if opening_range_width < float(config["rules"]["minimum_opening_range_width_points"]):
        return _reject(
            bar,
            config,
            signal_schema,
            "insufficient_context",
            "opening range width is below configured minimum",
        )

    direction = _sweep_direction(bar, config)
    if direction == "ambiguous":
        return _reject(bar, config, signal_schema, "ambiguous_setup", "bar swept both opening-range sides")
    if direction is None:
        return _reject(bar, config, signal_schema, "no_setup", "no liquidity sweep reversal setup")

    emitted_key = (bar.symbol, _bar_date(bar), direction)
    if config["rules"]["one_signal_per_side_per_day"] and emitted_key in emitted_sides:
        return _reject(
            bar,
            config,
            signal_schema,
            "duplicate_signal",
            "liquidity sweep signal already emitted for this symbol/date/side",
        )

    absorption_ok, absorption_notes = _has_absorption(bar, config, direction)
    if not absorption_ok:
        return _reject(bar, config, signal_schema, "no_absorption", absorption_notes)

    candidate = _candidate_signal_row(bar, config, signal_schema, direction, absorption_notes)
    if candidate["event_type"] == config["outputs"]["candidate_event_type"]:
        return candidate, emitted_key
    return candidate, None


def _sweep_direction(bar: AbsorptionBar, config: dict[str, Any]) -> str | None:
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
        return "ambiguous"
    if short_setup:
        return "short"
    if long_setup:
        return "long"
    return None


def _has_absorption(
    bar: AbsorptionBar,
    config: dict[str, Any],
    direction: str,
) -> tuple[bool, str]:
    minimum_total_volume = float(config["rules"]["minimum_total_volume"])
    minimum_delta = float(config["rules"]["minimum_aggressive_delta"])
    minimum_ratio = float(config["rules"]["minimum_aggression_ratio"])
    if bar.total_volume < minimum_total_volume:
        return False, f"total volume {bar.total_volume:.2f} below absorption minimum"

    if direction == "short":
        aggression_ratio = _safe_ratio(bar.ask_volume, bar.bid_volume)
        delta_ok = bar.delta > 0 and abs(bar.delta) >= minimum_delta
        ratio_ok = aggression_ratio >= minimum_ratio
        close_ok = bar.close_location <= float(config["rules"]["short_max_close_location"])
        notes = (
            "short absorption proxy "
            f"delta={bar.delta:.2f}; ratio={aggression_ratio:.2f}; "
            f"close_location={bar.close_location:.2f}"
        )
    else:
        aggression_ratio = _safe_ratio(bar.bid_volume, bar.ask_volume)
        delta_ok = bar.delta < 0 and abs(bar.delta) >= minimum_delta
        ratio_ok = aggression_ratio >= minimum_ratio
        close_ok = bar.close_location >= float(config["rules"]["long_min_close_location"])
        notes = (
            "long absorption proxy "
            f"delta={bar.delta:.2f}; ratio={aggression_ratio:.2f}; "
            f"close_location={bar.close_location:.2f}"
        )

    if delta_ok and ratio_ok and close_ok:
        return True, notes
    failed = []
    if not delta_ok:
        failed.append("delta")
    if not ratio_ok:
        failed.append("aggression_ratio")
    if not close_ok:
        failed.append("close_location")
    return False, notes + "; failed=" + ",".join(failed)


def _candidate_signal_row(
    bar: AbsorptionBar,
    config: dict[str, Any],
    signal_schema: dict[str, Any],
    direction: str,
    notes: str,
) -> dict[str, Any]:
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
        return _rejected_signal_row(
            bar,
            config,
            signal_schema,
            config["outputs"]["risk_limit_rejection_reason"],
            "candidate has nonpositive risk distance",
        )
    if risk_points > maximum_risk_points:
        return _rejected_signal_row(
            bar,
            config,
            signal_schema,
            config["outputs"]["risk_limit_rejection_reason"],
            "candidate risk exceeds configured maximum",
        )
    if not target_is_valid:
        return _rejected_signal_row(
            bar,
            config,
            signal_schema,
            config["outputs"]["risk_limit_rejection_reason"],
            "opening-range midpoint target is not beyond entry price",
        )

    row = _base_signal_row(bar, config)
    row.update(
        {
            "event_type": config["outputs"]["candidate_event_type"],
            "direction": direction,
            "action": "candidate",
            "stop_price": _format_number(stop_price),
            "target_price": _format_number(target_price),
            "invalidation_price": _format_number(stop_price),
            "rejection_reason": "not_applicable",
            "confidence": float(config["rules"]["confidence"]),
            "notes": notes,
        },
    )
    row["event_key"] = _event_key(row)
    return validate_signal_log_row(row, signal_schema)


def _reject(
    bar: AbsorptionBar,
    config: dict[str, Any],
    signal_schema: dict[str, Any],
    reason_key: str,
    notes: str,
) -> tuple[dict[str, Any], None]:
    output_key = f"{reason_key}_rejection_reason"
    return (
        _rejected_signal_row(
            bar,
            config,
            signal_schema,
            config["outputs"][output_key],
            notes,
        ),
        None,
    )


def _rejected_signal_row(
    bar: AbsorptionBar,
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


def _base_signal_row(bar: AbsorptionBar, config: dict[str, Any]) -> dict[str, Any]:
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
        "signal_price": _format_number(bar.close),
        "stop_price": "",
        "target_price": "",
        "invalidation_price": "",
        "rejection_reason": "",
        "confidence": "",
        "notes": "",
    }


def _normalize_bar(row: dict[str, Any], config: dict[str, Any]) -> AbsorptionBar:
    required_missing = [
        field_name for field_name in config["required_bar_fields"] if _is_blank(row.get(field_name))
    ]
    if required_missing:
        raise LiquiditySweepAbsorptionError(
            "Missing required absorption bar fields: " + ", ".join(required_missing),
        )

    bid_volume = _to_float(row["bid_volume"], "bid_volume")
    ask_volume = _to_float(row["ask_volume"], "ask_volume")
    delta = _optional_float(row.get("delta"), ask_volume - bid_volume, "delta")
    volume = _optional_float(row.get("volume"), 0.0, "volume")
    return AbsorptionBar(
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
        bid_volume=bid_volume,
        ask_volume=ask_volume,
        delta=delta,
        volume=volume,
        session_phase=str(row["session_phase"]),
    )


def _event_key(row: dict[str, Any]) -> str:
    return (
        f"{row['symbol']}:{row['chart_number']}:{row['bar_index']}:"
        f"{row['strategy_id']}:{row['event_type']}:{row['direction']}"
    )


def _bar_time(bar: AbsorptionBar) -> time:
    return _parse_timestamp(bar.timestamp).time()


def _bar_date(bar: AbsorptionBar) -> str:
    return _parse_timestamp(bar.timestamp).date().isoformat()


def _parse_timestamp(value: str) -> datetime:
    timestamp_text = value.strip()
    for timestamp_format in _TIMESTAMP_FORMATS:
        try:
            return datetime.strptime(timestamp_text, timestamp_format)
        except ValueError:
            continue
    raise LiquiditySweepAbsorptionError(f"Invalid timestamp: {value!r}")


def _parse_time(value: Any, field_name: str) -> time:
    try:
        return datetime.strptime(str(value).strip(), _TIME_FORMAT).time()
    except ValueError as exc:
        raise LiquiditySweepAbsorptionError(f"Invalid time field {field_name}: {value!r}") from exc


def _to_int(value: Any, field_name: str) -> int:
    try:
        return int(str(value))
    except ValueError as exc:
        raise LiquiditySweepAbsorptionError(f"Invalid integer field {field_name}: {value!r}") from exc


def _to_float(value: Any, field_name: str) -> float:
    try:
        return float(str(value))
    except ValueError as exc:
        raise LiquiditySweepAbsorptionError(f"Invalid numeric field {field_name}: {value!r}") from exc


def _optional_float(value: Any, default: float, field_name: str) -> float:
    if _is_blank(value):
        return default
    return _to_float(value, field_name)


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return float("inf") if numerator > 0 else 0.0
    return numerator / denominator


def _format_number(value: float) -> str:
    return f"{value:.8f}".rstrip("0").rstrip(".")


def _is_blank(value: Any) -> bool:
    return value is None or str(value).strip() == ""
