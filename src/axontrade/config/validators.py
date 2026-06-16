"""Phase-0 config validators.

These validators only check required structure. They do not certify that
external firm rules are current or complete.
"""

from __future__ import annotations

from typing import Any

from axontrade.config.loader import require_fields


FIRM_REQUIRED_FIELDS = (
    "schema_version",
    "profile_id",
    "firm_name",
    "account_type",
    "account_stage",
    "high_frequency_trading_allowed",
    "microscalping_allowed",
    "live_automated_entries_enabled",
    "simulation_only",
)

INSTRUMENT_REQUIRED_FIELDS = (
    "schema_version",
    "symbol",
    "name",
    "exchange",
    "tick_size",
    "tick_value_usd",
    "point_value_usd",
    "default_commission_per_side_usd",
)

RISK_REQUIRED_FIELDS = (
    "schema_version",
    "profile_id",
    "maximum_open_positions",
    "maximum_trades_per_session",
    "maximum_losing_trades_per_session",
    "personal_daily_stop_usd",
    "cooldown_after_loss_minutes",
    "averaging_down_allowed",
    "major_news_blackout_enabled",
    "minimum_preferred_holding_time_seconds",
    "target_typical_holding_time",
)


def validate_firm_config(data: dict[str, Any]) -> dict[str, Any]:
    return require_fields(data, FIRM_REQUIRED_FIELDS, context="firm config")


def validate_instrument_config(data: dict[str, Any]) -> dict[str, Any]:
    return require_fields(data, INSTRUMENT_REQUIRED_FIELDS, context="instrument config")


def validate_risk_config(data: dict[str, Any]) -> dict[str, Any]:
    return require_fields(data, RISK_REQUIRED_FIELDS, context="risk config")
