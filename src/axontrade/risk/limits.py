"""Basic development risk checks for simulation-safe research tooling."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RiskDecision:
    """Result of a risk-limit check."""

    allowed: bool
    reasons: tuple[str, ...]


def check_development_risk_limits(
    session_state: dict[str, Any],
    risk_limits: dict[str, Any],
) -> RiskDecision:
    """Check a proposed research/simulation action against development limits.

    This function does not submit, modify, cancel, flatten, or route orders.
    It only returns whether the supplied session state violates configured
    development risk limits.
    """

    reasons: list[str] = []

    open_positions = int(session_state.get("open_positions", 0))
    trades_this_session = int(session_state.get("trades_this_session", 0))
    losing_trades_this_session = int(session_state.get("losing_trades_this_session", 0))
    daily_pnl_usd = float(session_state.get("daily_pnl_usd", 0.0))
    minutes_since_last_loss = session_state.get("minutes_since_last_loss")
    is_averaging_down = bool(session_state.get("is_averaging_down", False))
    is_major_news_blackout = bool(session_state.get("is_major_news_blackout", False))

    if open_positions >= int(risk_limits["maximum_open_positions"]):
        reasons.append("maximum open positions reached")

    if trades_this_session >= int(risk_limits["maximum_trades_per_session"]):
        reasons.append("maximum trades per session reached")

    if losing_trades_this_session >= int(risk_limits["maximum_losing_trades_per_session"]):
        reasons.append("maximum losing trades per session reached")

    personal_daily_stop = float(risk_limits["personal_daily_stop_usd"])
    if daily_pnl_usd <= -personal_daily_stop:
        reasons.append("personal daily stop reached")

    if is_averaging_down and not bool(risk_limits["averaging_down_allowed"]):
        reasons.append("averaging down is not allowed")

    if bool(risk_limits["major_news_blackout_enabled"]) and is_major_news_blackout:
        reasons.append("major news blackout is active")

    cooldown_minutes = int(risk_limits["cooldown_after_loss_minutes"])
    if minutes_since_last_loss is not None and int(minutes_since_last_loss) < cooldown_minutes:
        reasons.append("cooldown after loss is active")

    return RiskDecision(allowed=not reasons, reasons=tuple(reasons))
